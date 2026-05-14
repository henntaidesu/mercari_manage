# -*- coding: utf-8 -*-
"""
煤炉账号「自动数据获取」后台调度。

开启且 status=active 的账号，按 fetch_interval 节流，依次执行（与同账号 run_meilu_serial 串行）：
1) batch_refresh_orders_info — 对应订单页「更新状态」
2) sync_new_data — 对应订单页「更新列表」
3) sync_on_sale_items_from_mercari — 对应在售页「从煤炉同步」

环境变量：
- MEILU_AUTO_FETCH：设为 0/false/off 关闭本循环（默认开启）
- MEILU_AUTO_FETCH_TICK_SEC：轮询间隔秒（默认 60，最小 15）
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from .db_manage.models.meilu_account import MeiluAccountModel
from .operation_mercari.on_sale_items_sync import sync_on_sale_items_from_mercari
from .operation_mercari.sync_data import batch_refresh_orders_info, sync_new_data
from .web_drive.account_serial_queue import queue_key_for_meilu_account, run_meilu_serial

log = logging.getLogger(__name__)

_INTERVAL_SEC = {
    "15": 15 * 60,
    "30": 30 * 60,
    "60": 60 * 60,
    "3h": 3 * 3600,
    "6h": 6 * 3600,
    "10": 10 * 60,
    "12h": 12 * 3600,
    "24h": 24 * 3600,
}


def _interval_seconds(iv: Optional[str]) -> int:
    key = (iv or "").strip()
    return _INTERVAL_SEC.get(key, 30 * 60)


def _parse_last_at(raw: Optional[str]) -> Optional[datetime]:
    if raw is None or not str(raw).strip():
        return None
    s = str(raw).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _account_due(item: MeiluAccountModel, now: datetime) -> bool:
    if not _normalize_row_is_open(item.is_open):
        return False
    iv = (item.fetch_interval or "").strip()
    if not iv:
        return False
    last = _parse_last_at(getattr(item, "auto_fetch_last_at", None))
    if last is None:
        return True
    elapsed = (now - last).total_seconds()
    return elapsed >= _interval_seconds(iv)


def _normalize_row_is_open(v) -> bool:
    if v is True:
        return True
    if v is False or v is None:
        return False
    try:
        return bool(int(v))
    except (TypeError, ValueError):
        return False


def _run_auto_fetch_for_account(aid: int) -> None:
    """在同一 meilu_{id} 队列内顺序执行三步（与前端订单页 / 在售页按钮同源逻辑）。"""
    def _body():
        batch_refresh_orders_info(account_id=aid)
        sync_new_data(account_id=aid)
        sync_on_sale_items_from_mercari(account_id=aid)

    run_meilu_serial(queue_key_for_meilu_account(aid), _body)


def _mark_last_at(aid: int) -> None:
    item = MeiluAccountModel.find_by_id(id=aid)
    if not item:
        return
    item.auto_fetch_last_at = _now_iso()
    item.save()


def run_meilu_auto_fetch_tick() -> None:
    raw = (os.environ.get("MEILU_AUTO_FETCH") or "1").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return

    now = datetime.now(timezone.utc)
    rows = MeiluAccountModel.find_all(
        where="[is_open] = 1 AND [status] = ?",
        params=("active",),
    )
    for item in rows:
        aid = getattr(item, "id", None)
        if aid is None:
            continue
        try:
            if not _account_due(item, now):
                continue
            sid = str(item.seller_id or "").strip()
            if not sid:
                log.warning("[meilu_auto_fetch] 账号 id=%s 已开启自动获取但未配置 seller_id，跳过", aid)
                continue
            log.info("[meilu_auto_fetch] 开始账号 id=%s seller_id=%s", aid, sid)
            _run_auto_fetch_for_account(int(aid))
            _mark_last_at(int(aid))
            log.info("[meilu_auto_fetch] 完成账号 id=%s", aid)
        except Exception:
            log.exception("[meilu_auto_fetch] 账号 id=%s 本轮失败", aid)


def _tick_seconds() -> int:
    try:
        n = int((os.environ.get("MEILU_AUTO_FETCH_TICK_SEC") or "60").strip() or "60")
    except ValueError:
        n = 60
    return max(15, n)


async def meilu_auto_fetch_loop() -> None:
    sec = _tick_seconds()
    log.info("[meilu_auto_fetch] 后台循环已启动，tick=%ss", sec)
    while True:
        try:
            await asyncio.to_thread(run_meilu_auto_fetch_tick)
        except Exception:
            log.exception("[meilu_auto_fetch] tick 外层异常")
        await asyncio.sleep(sec)
