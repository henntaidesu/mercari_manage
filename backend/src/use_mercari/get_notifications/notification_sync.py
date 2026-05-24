# -*- coding: utf-8 -*-
"""
お知らせ通知同步入口：

- 解析单个 notification（拆 args / intent、转毫秒时间戳）
- 按 ``(account_id, uuid)`` UPSERT 到 ``notifications``
- ``is_read`` 不在同步阶段触碰（保留本地状态）
- ``sync_notifications_from_mercari``：解析账号 → 打开有头浏览器 → 抓取 → 写库
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...db_manage.database import DatabaseManager
from ...db_manage.models.meilu_account import MeiluAccountModel
from ...ssl_mitm_proxy.capture_config import clear_notification_response_file
from ...web_drive.core.mitm_session import mitm_automation_browser
from .notification_capture import (
    NOTIFICATIONS_PAGE_URL,
    capture_notifications_via_mitm_session,
)

log = logging.getLogger(__name__)


_RFC3339_FRAC_RE = re.compile(r"\.(\d+)")


def _parse_rfc3339_to_ms(raw: Optional[str]) -> Optional[int]:
    """把 ``2026-05-23T18:24:07.186724371Z`` 这种纳秒精度 RFC3339 转毫秒。"""
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
    s = (raw or "").strip()
    if not s:
        return {}
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _to_int_or_none(val: Any) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        try:
            return int(val)
        except (ValueError, OverflowError):
            return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except (ValueError, OverflowError):
            return None


def _normalize_notification_row(
    account_id: int, item: Dict[str, Any], synced_at_ms: int
) -> Dict[str, Any]:
    """把煤炉 notification 原始项扁平化为本地表行。"""
    args_raw = item.get("args")
    intent_raw = item.get("intent")
    args_obj = _safe_json_loads_dict(args_raw if isinstance(args_raw, str) else "")
    intent_obj = _safe_json_loads_dict(intent_raw if isinstance(intent_raw, str) else "")
    extra = intent_obj.get("extra") if isinstance(intent_obj, dict) else None
    extra_dict = extra if isinstance(extra, dict) else {}

    activity = str(intent_obj.get("activity") or "").strip() or None

    # WebActivity / ExternalWebActivity 在 extra.url 里直接给跳转地址
    target_url = None
    raw_url = extra_dict.get("url")
    if isinstance(raw_url, str) and raw_url.strip():
        target_url = raw_url.strip()
    # 商品详情类 intent (ItemDetailActivity) 直接组装煤炉商品页 URL
    elif activity == "ItemDetailActivity":
        iid = str(extra_dict.get("id") or args_obj.get("item_id") or "").strip()
        if iid:
            target_url = f"https://jp.mercari.com/item/{iid}"

    return {
        "account_id": int(account_id),
        "uuid": str(item.get("uuid") or "").strip(),
        "kind": (str(item.get("kind") or "").strip() or None),
        "message": (item.get("message") or None),
        "action_url": (item.get("actionUrl") or None),
        "photo_url": (item.get("photoUrl") or None),
        "photo_type": (item.get("photoType") or None),
        "args_json": (args_raw if isinstance(args_raw, str) and args_raw.strip() else None),
        "intent_json": (intent_raw if isinstance(intent_raw, str) and intent_raw.strip() else None),
        "item_id": (str(args_obj.get("item_id") or "").strip() or None),
        "item_name": (str(args_obj.get("item_name") or "").strip() or None),
        "item_thumbnail": (str(args_obj.get("item_thumbnail") or "").strip() or None),
        "sender_id": (str(args_obj.get("sender_id") or "").strip() or None),
        "price": _to_int_or_none(args_obj.get("price")),
        "bid_price": _to_int_or_none(args_obj.get("bid_price")),
        "activity": activity,
        "target_url": target_url,
        "mercari_created": _parse_rfc3339_to_ms(item.get("created")),
        "synced_at": synced_at_ms,
    }


# 不在 UPSERT 中重置 is_read（本地维护的已读状态）
_UPSERT_COLS = (
    "account_id",
    "uuid",
    "kind",
    "message",
    "action_url",
    "photo_url",
    "photo_type",
    "args_json",
    "intent_json",
    "item_id",
    "item_name",
    "item_thumbnail",
    "sender_id",
    "price",
    "bid_price",
    "activity",
    "target_url",
    "mercari_created",
    "synced_at",
)


def _upsert_notification_row(db: DatabaseManager, row: Dict[str, Any]) -> str:
    """SQLite UPSERT on (account_id, uuid)。返回 inserted / updated / skipped。"""
    if not row.get("uuid"):
        return "skipped"
    cols_sql = ", ".join(f"[{c}]" for c in _UPSERT_COLS)
    placeholders = ", ".join(["?"] * len(_UPSERT_COLS))
    update_assigns = ", ".join(
        f"[{c}] = excluded.[{c}]" for c in _UPSERT_COLS if c not in ("account_id", "uuid")
    )
    sql = (
        f"INSERT INTO [notifications] ({cols_sql}) VALUES ({placeholders}) "
        f"ON CONFLICT([account_id], [uuid]) DO UPDATE SET {update_assigns}"
    )
    params = tuple(row.get(c) for c in _UPSERT_COLS)
    pre = db.execute_query(
        "SELECT 1 FROM [notifications] WHERE [account_id] = ? AND [uuid] = ? LIMIT 1",
        (row["account_id"], row["uuid"]),
    )
    db.execute_update(sql, params)
    return "updated" if pre else "inserted"


def apply_notifications_sync(account_id: int, items: List[Dict[str, Any]]) -> Dict[str, int]:
    """写入本地 ``notifications``。通知是增量历史记录，不做软删除。"""
    db = DatabaseManager()
    synced_at_ms = int(time.time() * 1000)

    inserted = 0
    updated = 0
    skipped = 0

    for item in items:
        if not isinstance(item, dict):
            skipped += 1
            continue
        row = _normalize_notification_row(account_id, item, synced_at_ms)
        if not row["uuid"]:
            skipped += 1
            continue
        action = _upsert_notification_row(db, row)
        if action == "inserted":
            inserted += 1
        elif action == "updated":
            updated += 1
        else:
            skipped += 1

    return {
        "total": len(items),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }


def _resolve_account_id(account_id: Optional[int]) -> int:
    """显式 account_id 优先；否则取第一个 is_open=1 且 status=active 的账号。"""
    if account_id is not None:
        acc = MeiluAccountModel.find_by_id(id=int(account_id))
        if acc is None:
            raise ValueError(f"煤炉账号 id={account_id} 不存在")
        return int(account_id)
    rows = MeiluAccountModel.find_all(
        where="[status] = ? AND [is_open] = 1",
        params=("active",),
        order_by="[id] ASC",
        limit=1,
    )
    if not rows:
        raise ValueError("没有可用的煤炉账号（status=active 且 is_open=1）")
    return int(rows[0].id)


async def sync_notifications_from_mercari(
    account_id: Optional[int] = None,
) -> Dict[str, Any]:
    """从煤炉拉取通知并同步本地 ``notifications`` 表。

    通过 ``mitm_automation_browser`` 租借账号主 profile ``meilu_{id}`` 的有头浏览器
    （登录态由 Edge 持久化 cookie 自动维护，无需 cookie seed / 首页 prewarm）。
    抓取完毕后浏览器保持打开，由用户决定何时关闭。
    """
    aid = _resolve_account_id(account_id)
    log.info("[notification] 开始同步 account_id=%s", aid)

    clear_notification_response_file()
    since_ms = int(time.time() * 1000)

    async with mitm_automation_browser(
        int(aid), start_url=NOTIFICATIONS_PAGE_URL
    ) as (mgr, main_key):
        items = await capture_notifications_via_mitm_session(
            mgr, main_key, since_ms=since_ms
        )

    stats = apply_notifications_sync(int(aid), items)
    stats["account_id"] = int(aid)
    log.info(
        "[notification] 同步完成 account_id=%s total=%d inserted=%d updated=%d",
        aid,
        stats.get("total", 0),
        stats.get("inserted", 0),
        stats.get("updated", 0),
    )
    return stats
