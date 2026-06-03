# -*- coding: utf-8 -*-
"""待办列表同步 + 交易详情批量预缓存"""

import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException
from .....use_mercari.get_to_du_list.todolist_sync import resolve_enabled_account_ids, sync_todos_from_mercari
from .....use_mercari.get_to_du_list.transaction_detail import fetch_transaction_detail, list_uncached_detail_todo_ids
from .....use_mercari.sync.sync_progress import clear_sync_progress, set_sync_progress
from .....use_mercari.sync.sync_lock import LABEL_FULL, begin_or_conflict as sync_lock_begin, end as sync_lock_end
from .....web_drive.core.account_serial_queue import queue_key_for_mercari_account, run_mercari_serial_async
from .....web_drive.core.manager import get_web_drive_manager
from .....web_drive.core.paths import mercari_account_key
from ..todos_models import SyncTodosRequest
from .detail import _SYNC_JOB_ID_RE

log = logging.getLogger(__name__)


async def sync_todos(req: SyncTodosRequest) -> Dict[str, Any]:
    """从煤炉同步所有启用账号（status=active；不要求自动获取开启）的待办事项；按账号串行避免浏览器抢占。

    不再指定单个账号：点击即同步全部已开启账号，逐个执行并汇总结果。
    ``progress_job_id`` 与 GET /use_web/todos/sync-progress/{job_id} 配合，
    供前端轮询当前步骤展示全屏等待框。
    """
    jid = (req.progress_job_id or "").strip() or None
    if jid and not _SYNC_JOB_ID_RE.fullmatch(jid):
        raise HTTPException(status_code=400, detail="invalid progress_job_id")

    try:
        account_ids = resolve_enabled_account_ids()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    lock_token = sync_lock_begin("page", LABEL_FULL)
    accounts: list[Dict[str, Any]] = []
    inserted = updated = marked_deleted = total = 0
    fail_count = 0
    mgr = get_web_drive_manager()
    try:
        # 逐个账号严格串行：每个账号 await 完成（抓取 + 写库）后，必须先关闭其浏览器，
        # 再开始下一个账号。todolist 抓取走单一全局响应文件（请求路径不含 seller_id，
        # 无法区分账号），若两个账号的 /todos 页同时在线会导致响应串台。
        for aid in account_ids:
            try:
                stats = await run_mercari_serial_async(
                    queue_key_for_mercari_account(aid),
                    lambda aid=aid: sync_todos_from_mercari(
                        account_id=aid,
                        progress_job_id=jid,
                    ),
                )
            except Exception as exc:  # noqa: BLE001 单个账号失败不影响其余账号
                fail_count += 1
                accounts.append({"account_id": aid, "error": str(exc)})
                continue
            else:
                inserted += int(stats.get("inserted", 0) or 0)
                updated += int(stats.get("updated", 0) or 0)
                marked_deleted += int(stats.get("marked_deleted", 0) or 0)
                total += int(stats.get("total", 0) or 0)
                accounts.append(stats)
            finally:
                # 关闭当前账号浏览器，确保与下一账号不重叠（队列层默认 ~10s 后才关，
                # 这里立即强制关闭以消除全局响应文件的串台窗口）。
                try:
                    await mgr.close_session(mercari_account_key(aid), force=True)
                except Exception as close_exc:  # noqa: BLE001 关闭失败不阻断后续账号
                    log.warning(
                        "[todolist] 关闭 account_id=%s 浏览器失败: %s", aid, close_exc
                    )

        # ── 交易详情预缓存：列表同步完后，为「待发货」「待回复」且尚无交易详情缓存的待办
        #    静默无头补抓一次详情，使前端「处理」面板打开即有缓存可用（无需逐条手动「刷新抓取」）。──
        detail_fetched, detail_failed = await _precache_detail_todos(
            account_ids, jid, mgr
        )
    finally:
        sync_lock_end(lock_token)
        if jid:
            clear_sync_progress(jid)

    return {
        "accounts": accounts,
        "account_count": len(account_ids),
        "fail_count": fail_count,
        "inserted": inserted,
        "updated": updated,
        "marked_deleted": marked_deleted,
        "total": total,
        "detail_fetched": detail_fetched,
        "detail_failed": detail_failed,
    }

async def _precache_detail_todos(
    account_ids: list[int], jid: Optional[str], mgr: Any
) -> tuple[int, int]:
    """为各账号下「待发货」「待回复」且无交易详情缓存的待办，按账号串行补抓详情（静默无头）。

    返回 ``(成功条数, 失败条数)``。单条/单账号失败均不抛出，不影响同步整体结果。
    """
    fetched = 0
    failed = 0
    for aid in account_ids:
        todo_ids = list_uncached_detail_todo_ids(aid)
        if not todo_ids:
            continue
        log.info(
            "[todolist] 交易详情预缓存 account_id=%s 共 %d 条", aid, len(todo_ids)
        )
        try:
            for idx, tid in enumerate(todo_ids, start=1):
                if jid:
                    set_sync_progress(
                        jid,
                        "precache_detail",
                        f"补抓交易详情（{idx}/{len(todo_ids)}）…",
                    )
                try:
                    # 同账号多条复用同一浏览器会话（mitm_automation_browser 退出不关闭，
                    # 仅刷新标签页）；串行队列保证不与其它操作抢占同一账号。
                    await run_mercari_serial_async(
                        queue_key_for_mercari_account(aid),
                        lambda tid=tid: fetch_transaction_detail(
                            int(tid), progress_job_id=jid, force_headless=True
                        ),
                        suppress_idle_close=True,
                    )
                    fetched += 1
                except Exception as exc:  # noqa: BLE001 单条失败不阻断其余
                    failed += 1
                    log.warning(
                        "[todolist] 交易详情预缓存失败 todo_id=%s: %s", tid, exc
                    )
        finally:
            # 该账号补抓完毕，强制关闭其浏览器，避免与下一账号或后续操作重叠。
            try:
                await mgr.close_session(mercari_account_key(aid), force=True)
            except Exception as close_exc:  # noqa: BLE001
                log.warning(
                    "[todolist] 预缓存后关闭 account_id=%s 浏览器失败: %s", aid, close_exc
                )
    return fetched, failed
