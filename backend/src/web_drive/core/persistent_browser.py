# -*- coding: utf-8 -*-
"""
持久化无头浏览器池：系统启动时为每个活跃煤炉账号启动一个持久化无头 Edge 会话，
会话在整个进程生命周期内保持运行，不因单次操作结束而关闭。

每次自动化任务的生命周期：
  1. 从 queue 获取任务
  2. 在持久化浏览器内打开新标签页，导航到目标 URL
  3. 执行操作（截获 MITM API、点击等）
  4. 关闭任务标签页（浏览器保留，等待下一个任务）

这样避免了浏览器反复冷启动的开销，也不会因为浏览器关闭导致 Edge profile 锁定问题。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Set

log = logging.getLogger(__name__)

# 记录已成功启动持久化浏览器的账号 ID（进程级别，重启后清零）
_started_account_ids: Set[int] = set()
_pool_lock: Optional[asyncio.Lock] = None


def _get_pool_lock() -> asyncio.Lock:
    """懒初始化 asyncio.Lock（必须在 event loop 创建后调用）。"""
    global _pool_lock
    if _pool_lock is None:
        _pool_lock = asyncio.Lock()
    return _pool_lock


async def ensure_persistent_browser(account_id: int) -> None:
    """
    确保指定账号的持久化无头浏览器已启动并存活。

    - 使用 ``meilu_{id}__auto`` profile（与有头用户窗口完全隔离）
    - 配置 MITM 代理（与 MITM 截获操作共用）
    - 若浏览器已在运行且存活，直接返回（不重新导航、不打扰运行中的标签页）
    - 若进程重启或浏览器异常退出，自动重新启动

    懒启动：若系统启动时账号浏览器未能成功预热，首次操作时会自动调用此函数。
    """
    from .paths import meilu_automation_key, seed_automation_profile_from_account
    from .manager import get_web_drive_manager
    from ...ssl_mitm_proxy.runner import default_mitm_proxy_url, start_mitm_proxy

    auto_key = meilu_automation_key(account_id)
    mgr = get_web_drive_manager()

    async with _get_pool_lock():
        # 若已记录为已启动，先验证浏览器是否仍然存活
        if account_id in _started_account_ids:
            s = mgr._ts()
            ctx = s.contexts.get(auto_key)
            if ctx is not None and mgr._is_context_alive(ctx):
                return  # 浏览器正常运行，直接返回
            # 浏览器已失效（用户关闭窗口 / 进程崩溃），需要重启
            _started_account_ids.discard(account_id)
            log.info("持久化浏览器 %s 已失效，准备重新启动", auto_key)

        # 确保 MITM 代理已启动（与 mitm_session 共用）
        r = start_mitm_proxy()
        if r.get("error"):
            log.warning(
                "持久化浏览器启动：MITM 代理未就绪（浏览器仍将启动，操作时可能无法截获响应）: %s",
                r["error"],
            )

        # 将主账号 profile 的 Cookie 文件复制到 auto profile（冷启动用于提供初始登录状态）
        try:
            seed_automation_profile_from_account(account_id)
        except Exception as exc:
            log.warning(
                "持久化浏览器 seed profile 失败 %s（将尝试直接启动）: %s", auto_key, exc
            )

        proxy = default_mitm_proxy_url()

        # 启动持久化无头浏览器。
        # start_url="about:blank"：让 _navigate_one_tab 收敛到单一空白标签页，
        # 避免 Edge 从 profile 恢复多余的历史标签。
        result = await mgr.open_session(
            auto_key,
            headless=True,
            start_url="about:blank",
            proxy_server=proxy,
            interactive=False,
        )
        _started_account_ids.add(account_id)
        log.info(
            "持久化无头浏览器就绪 account_id=%d key=%s already_running=%s",
            account_id,
            auto_key,
            result.get("already_running"),
        )


async def startup_browsers_for_all_active_accounts() -> None:
    """
    系统启动时调用：为数据库中所有 status='active' 的煤炉账号启动持久化无头浏览器。

    - 顺序逐个启动，避免同时并发抢占 profile 目录锁
    - 单个账号启动失败只记录警告，不影响其他账号及系统整体启动
    - 若数据库中无活跃账号，则跳过（静默）
    """
    try:
        from ...db_manage.database import DatabaseManager

        db = DatabaseManager()
        rows = db.execute_query(
            "SELECT [id] FROM [meilu_accounts] WHERE LOWER(TRIM([status])) = 'active' ORDER BY [id]"
        )
        account_ids = [int(r[0]) for r in rows]
    except Exception as exc:
        log.warning("startup_browsers: 读取活跃账号列表失败，跳过持久化浏览器预启动: %s", exc)
        return

    if not account_ids:
        log.info("startup_browsers: 无活跃煤炉账号，跳过持久化浏览器预启动")
        return

    log.info(
        "startup_browsers: 开始为 %d 个活跃账号预启动持久化无头浏览器 %s",
        len(account_ids),
        account_ids,
    )
    for aid in account_ids:
        try:
            await ensure_persistent_browser(aid)
        except Exception as exc:
            log.warning(
                "startup_browsers: 账号 %d 持久化浏览器启动失败（首次操作时将懒启动）: %s",
                aid,
                exc,
            )

    log.info("startup_browsers: 持久化浏览器预启动完成")


async def close_task_tab_safely(page: object, account_id: int) -> None:
    """
    安全关闭任务标签页（操作完成后调用）。

    - 关闭指定的 page 对象（任务标签页）
    - 若关闭后浏览器没有剩余标签页，自动新建一个空白页以防止浏览器进程退出
    - 本函数不关闭浏览器 context，浏览器保持存活以处理下一个队列任务
    """
    from .paths import meilu_automation_key
    from .manager import get_web_drive_manager

    auto_key = meilu_automation_key(account_id)
    mgr = get_web_drive_manager()

    try:
        await page.close()  # type: ignore[attr-defined]
        log.debug("持久化浏览器：任务标签页已关闭 %s", auto_key)
    except Exception as exc:
        log.debug("持久化浏览器：关闭任务标签页时出错（忽略）%s: %s", auto_key, exc)

    # 确保浏览器至少保留一个标签页（Chromium 在 0 标签时可能退出 / 报错）
    try:
        s = mgr._prepare_async()
        async with s.lock:  # type: ignore[union-attr]
            ctx = s.contexts.get(auto_key)
            if ctx is not None and mgr._is_context_alive(ctx) and not ctx.pages:
                await ctx.new_page()
                log.debug("持久化浏览器：已新建空白标签页以维持浏览器存活 %s", auto_key)
    except Exception as exc:
        log.debug("持久化浏览器：维持存活标签页操作失败（忽略）%s: %s", auto_key, exc)
