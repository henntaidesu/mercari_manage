# -*- coding: utf-8 -*-
"""交易详情批量预缓存（共享）。

为某账号下「待发货 / 待回复 / 待评价」且尚无交易详情缓存的待办，逐条静默无头补抓
详情，使前端「处理」面板打开即有缓存可用（无需逐条手动「刷新抓取」）。

被以下入口复用，行为与待办页「从煤炉同步」一致：
- 待办页「从煤炉同步」（use_web/todos）
- 单账号「同步数据」（use_web/mercari_accounts）
- 后台「自动数据获取」循环（mercari_auto_fetch_loop）
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from ...sync.sync_progress import make_sync_reporter
from ._cache import list_uncached_detail_todo_ids
from .detail import fetch_transaction_detail

log = logging.getLogger(__name__)


async def precache_uncached_todo_details(
    account_id: int, *, progress_job_id: Optional[str] = None
) -> Tuple[int, int]:
    """为某账号无缓存的待发货/待回复/待评价待办按序补抓交易详情，返回 ``(成功条数, 失败条数)``。

    **必须在该账号的串行队列内调用**：本函数不获取队列锁，直接复用已打开的浏览器会话
    （与 ``fetch_transaction_detail`` 一致，``force_headless=True`` 静默无头）。单条失败仅记录、
    不抛出，不影响其余条目与调用方整体结果。
    """
    todo_ids = list_uncached_detail_todo_ids(int(account_id))
    if not todo_ids:
        return 0, 0

    report = make_sync_reporter(progress_job_id)
    total = len(todo_ids)
    log.info("[txdetail] 交易详情预缓存 account_id=%s 共 %d 条", account_id, total)

    fetched = 0
    failed = 0
    for idx, tid in enumerate(todo_ids, start=1):
        report("precache_detail", f"补抓交易详情（{idx}/{total}）…")
        try:
            await fetch_transaction_detail(
                int(tid), progress_job_id=progress_job_id, force_headless=True
            )
            fetched += 1
        except Exception as exc:  # noqa: BLE001 单条失败不阻断其余
            failed += 1
            log.warning("[txdetail] 交易详情预缓存失败 todo_id=%s: %s", tid, exc)
    return fetched, failed
