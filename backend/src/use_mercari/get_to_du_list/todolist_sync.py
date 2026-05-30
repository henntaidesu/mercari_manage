# -*- coding: utf-8 -*-
"""
待办事项同步入口：

- 解析单个 todo（拆 args、转毫秒时间戳）
- 按 ``(account_id, uuid)`` UPSERT 到 ``todo_items``
- 软删除：API 未返回但本地 ``is_delete=0`` 的行 → 标 ``is_delete=1``
- ``sync_todos_from_mercari``：解析账号 → 打开有头浏览器 → 抓取 → 写库
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...db_manage.database import DatabaseManager
from ...db_manage.models.mercari_account import MercariAccountModel
from ...ssl_mitm_proxy.capture_config import clear_todolist_response_file
from ...web_drive.core.mitm_session import mitm_automation_browser
from ..sync_progress import make_sync_reporter
from .todolist_capture import TODOS_PAGE_URL, capture_todolist_via_mitm_session

log = logging.getLogger(__name__)


_RFC3339_FRAC_RE = re.compile(r"\.(\d+)")


def _parse_rfc3339_to_ms(raw: Optional[str]) -> Optional[int]:
    """把 ``2026-05-23T09:06:24.336973679Z`` 这种 9 位纳秒时间戳转毫秒。

    Python ``datetime.fromisoformat`` 仅接受最多 6 位小数（微秒），故先截到 6 位。
    """
    s = (raw or "").strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    s = _RFC3339_FRAC_RE.sub(lambda m: "." + m.group(1)[:6], s)
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except (ValueError, OverflowError):
        return None


def _safe_json_loads_dict(raw: Optional[str]) -> Dict[str, Any]:
    """args/intent 是 JSON 字符串；坏数据返回空 dict。"""
    s = (raw or "").strip()
    if not s:
        return {}
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _normalize_todo_row(account_id: int, item: Dict[str, Any], synced_at_ms: int) -> Dict[str, Any]:
    """把煤炉 todolist 原始项扁平化为本地表行。"""
    args_raw = item.get("args")
    intent_raw = item.get("intent")
    args_obj = _safe_json_loads_dict(args_raw if isinstance(args_raw, str) else "")
    return {
        "account_id": int(account_id),
        "uuid": str(item.get("uuid") or "").strip(),
        "kind": (str(item.get("kind") or "").strip() or None),
        "title": (item.get("title") or None),
        "message": (item.get("message") or None),
        "photo_url": (item.get("photoUrl") or None),
        "photo_type": (item.get("photoType") or None),
        "status": (str(item.get("status") or "").strip() or None),
        "args_json": (args_raw if isinstance(args_raw, str) and args_raw.strip() else None),
        "intent_json": (intent_raw if isinstance(intent_raw, str) and intent_raw.strip() else None),
        "item_id": (str(args_obj.get("item_id") or "").strip() or None),
        "item_name": (str(args_obj.get("item_name") or "").strip() or None),
        "sender_id": (str(args_obj.get("sender_id") or "").strip() or None),
        "mercari_created": _parse_rfc3339_to_ms(item.get("created")),
        "mercari_updated": _parse_rfc3339_to_ms(item.get("updated")),
        "is_delete": 0,
        "synced_at": synced_at_ms,
    }


_UPSERT_COLS = (
    "account_id",
    "uuid",
    "kind",
    "title",
    "message",
    "photo_url",
    "photo_type",
    "status",
    "args_json",
    "intent_json",
    "item_id",
    "item_name",
    "sender_id",
    "mercari_created",
    "mercari_updated",
    "is_delete",
    "synced_at",
)


def _upsert_todo_row(db: DatabaseManager, row: Dict[str, Any]) -> str:
    """SQLite UPSERT on (account_id, uuid)。返回 inserted / updated / skipped。"""
    if not row.get("uuid"):
        return "skipped"
    cols_sql = ", ".join(f"[{c}]" for c in _UPSERT_COLS)
    placeholders = ", ".join(["?"] * len(_UPSERT_COLS))
    update_assigns = ", ".join(
        f"[{c}] = excluded.[{c}]" for c in _UPSERT_COLS if c not in ("account_id", "uuid")
    )
    sql = (
        f"INSERT INTO [todo_items] ({cols_sql}) VALUES ({placeholders}) "
        f"ON CONFLICT([account_id], [uuid]) DO UPDATE SET {update_assigns}"
    )
    params = tuple(row.get(c) for c in _UPSERT_COLS)
    # 先查存在与否（无法靠 lastrowid 区分 insert/update）
    pre = db.execute_query(
        "SELECT 1 FROM [todo_items] WHERE [account_id] = ? AND [uuid] = ? LIMIT 1",
        (row["account_id"], row["uuid"]),
    )
    db.execute_update(sql, params)
    return "updated" if pre else "inserted"


def apply_todolist_sync(account_id: int, items: List[Dict[str, Any]]) -> Dict[str, int]:
    """写入本地 ``todo_items``，并软删除本次未出现的旧行。"""
    db = DatabaseManager()
    synced_at_ms = int(time.time() * 1000)

    inserted = 0
    updated = 0
    skipped = 0
    incoming_uuids: List[str] = []

    for item in items:
        if not isinstance(item, dict):
            skipped += 1
            continue
        row = _normalize_todo_row(account_id, item, synced_at_ms)
        if not row["uuid"]:
            skipped += 1
            continue
        incoming_uuids.append(row["uuid"])
        action = _upsert_todo_row(db, row)
        if action == "inserted":
            inserted += 1
        elif action == "updated":
            updated += 1
        else:
            skipped += 1

    # 软删除：当前账号下、未在本次返回中的活跃行
    marked_deleted = 0
    if incoming_uuids:
        placeholders = ",".join(["?"] * len(incoming_uuids))
        marked_deleted = db.execute_update(
            f"UPDATE [todo_items] SET [is_delete] = 1 "
            f"WHERE [account_id] = ? AND COALESCE([is_delete], 0) = 0 "
            f"AND [uuid] NOT IN ({placeholders})",
            tuple([account_id] + incoming_uuids),
        )
    else:
        # 空列表也要标全部为已删
        marked_deleted = db.execute_update(
            "UPDATE [todo_items] SET [is_delete] = 1 "
            "WHERE [account_id] = ? AND COALESCE([is_delete], 0) = 0",
            (account_id,),
        )

    return {
        "total": len(items),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "marked_deleted": int(marked_deleted or 0),
    }


def _resolve_account_id(account_id: Optional[int]) -> int:
    """显式 account_id 优先；否则取第一个 is_open=1 且 status=active 的账号。"""
    if account_id is not None:
        acc = MercariAccountModel.find_by_id(id=int(account_id))
        if acc is None:
            raise ValueError(f"煤炉账号 id={account_id} 不存在")
        return int(account_id)
    rows = MercariAccountModel.find_all(
        where="[status] = ? AND [is_open] = 1",
        params=("active",),
        order_by="[id] ASC",
        limit=1,
    )
    if not rows:
        raise ValueError("没有可用的煤炉账号（status=active 且 is_open=1）")
    return int(rows[0].id)


async def sync_todos_from_mercari(
    account_id: Optional[int] = None,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """从煤炉拉取待办事项并同步本地 ``todo_items``。

    ``progress_job_id`` 配合通用 ``sync_progress``：每个阶段把中文步骤写入内存，
    前端轮询 GET /use_web/todos/sync-progress/{job_id} 展示全屏等待框。
    """
    report = make_sync_reporter(progress_job_id)
    report("resolve_account", "正在准备煤炉账号…")
    aid = _resolve_account_id(account_id)
    log.info("[todolist] 开始同步 account_id=%s", aid)

    # 浏览器打开 /todos 时立刻发起 API；必须先清空旧文件并取 since_ms，
    # 否则首批响应会先于 capture 入参就位而被误判为旧数据。
    clear_todolist_response_file()
    since_ms = int(time.time() * 1000)

    report("open_browser", "正在启动浏览器与 MITM 代理…")
    async with mitm_automation_browser(int(aid), start_url=TODOS_PAGE_URL) as (mgr, auto_key):
        report("capture_todos", "已打开待办事项页，等待煤炉返回待办列表…")
        items = await capture_todolist_via_mitm_session(mgr, auto_key, since_ms=since_ms)

    report("apply_sync", f"已获取 {len(items)} 条待办事项，正在写入本地数据库…")
    stats = apply_todolist_sync(int(aid), items)
    stats["account_id"] = int(aid)
    log.info(
        "[todolist] 同步完成 account_id=%s total=%d inserted=%d updated=%d marked_deleted=%d",
        aid,
        stats.get("total", 0),
        stats.get("inserted", 0),
        stats.get("updated", 0),
        stats.get("marked_deleted", 0),
    )
    report(
        "done",
        (
            f"同步完成：新增 {stats.get('inserted', 0)}，"
            f"更新 {stats.get('updated', 0)}，"
            f"标记完成 {stats.get('marked_deleted', 0)}"
        ),
    )
    return stats
