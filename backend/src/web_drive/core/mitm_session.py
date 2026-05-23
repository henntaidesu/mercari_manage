# -*- coding: utf-8 -*-
"""
MITM 自动化：在持久化无头浏览器（``meilu_{id}__auto``）上打开任务标签页执行操作，
操作完成后只关闭任务标签页，不关闭浏览器。

持久化浏览器生命周期：
- 系统启动时由 ``startup_browsers_for_all_active_accounts`` 预热
- 后续由 ``ensure_persistent_browser`` 懒启动（首次操作时自动启动）
- 全程不因单次操作关闭，浏览器进程持续存活

任务执行流程（每次 MITM 操作）：
  1. 确保持久化浏览器已启动
  2. 从有头主会话（``meilu_{id}``）同步 Cookie 到无头自动化会话（``meilu_{id}__auto``）
  3. 在无头浏览器内打开新标签页并导航到目标 URL
  4. yield (mgr, auto_key) — 与旧接口完全兼容
  5. 操作完成后：关闭任务标签页，浏览器保持运行，等待下一个队列任务

与旧版本的区别：
  旧版 mitm_automation_browser: 每次操作都 ``ensure_session_for_mitm``（强制关闭再重开）→ 操作结束后 ``close_session(force=True)`` 关闭整个浏览器。
  新版 mitm_automation_browser: 持久化浏览器长驻，仅管理标签页生命周期。
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Dict, Optional, Tuple

from ...ssl_mitm_proxy.runner import default_mitm_proxy_url, start_mitm_proxy
from .manager import EdgeWebDriveManager, get_web_drive_manager
from .paths import meilu_account_key, meilu_automation_key, seed_automation_profile_from_account
from .persistent_browser import ensure_persistent_browser, close_task_tab_safely

log = logging.getLogger(__name__)

_MITM_PAGE_RELOAD_INTERVAL_SEC = 20.0


@asynccontextmanager
async def mitm_automation_browser(
    account_id: int,
    *,
    start_url: str,
    headless: bool,  # 保留参数兼容旧调用方，持久化模式始终使用无头
) -> AsyncIterator[Tuple[EdgeWebDriveManager, str]]:
    """
    上下文管理器：在持久化无头浏览器内为当前任务打开一个新标签页。

    **进入时：**
      1. 确保 MITM 代理已启动
      2. 确保该账号的持久化无头浏览器已启动（懒启动）
      3. 从有头主会话同步 Cookie（若用户窗口已登录）
      4. 打开新任务标签页并导航到 ``start_url``

    **退出时：**
      - 关闭任务标签页（若关闭后无剩余标签，自动补一个空白页保持浏览器存活）
      - **不关闭浏览器**，浏览器持续运行以备下一个队列任务

    与旧接口完全兼容：yield ``(mgr, auto_key)``，调用方无需修改。
    """
    r = start_mitm_proxy()
    if r.get("error"):
        raise RuntimeError(f"MITM 代理不可用: {r['error']}")

    mgr = get_web_drive_manager()
    main_key = meilu_account_key(account_id)
    auto_key = meilu_automation_key(account_id)

    # ── 步骤1：确保持久化无头浏览器已启动（首次时自动启动，后续直接复用）──
    await ensure_persistent_browser(account_id)

    # ── 步骤2：从有头主会话同步 Cookie（若用户在账号管理页已打开有头浏览器并登录）──
    n_cookies = await mgr.copy_cookies_between_sessions(main_key, auto_key)
    if n_cookies > 0:
        log.info(
            "MITM 自动化已从有头会话 %s 注入 %s 条 Cookie 到 %s",
            main_key,
            n_cookies,
            auto_key,
        )

    # ── 步骤3：在持久化浏览器内打开新任务标签页 ──
    # 新标签页成为 ctx.pages[-1]，现有代码（_page_for_session / reload_active_tab）
    # 均以 ctx.pages[-1] 定位当前活动页，因此无需修改调用方。
    s = mgr._prepare_async()
    task_page: Any = None
    async with s.lock:  # type: ignore[union-attr]
        ctx = s.contexts.get(auto_key)
        if ctx is None or not mgr._is_context_alive(ctx):
            raise RuntimeError(
                f"持久化浏览器不可用: {auto_key}。"
                "请检查账号浏览器状态，或重启服务后重试。"
            )
        task_page = await ctx.new_page()

    # 在锁外导航（避免长时间持有锁）
    try:
        await task_page.goto(start_url, wait_until="domcontentloaded", timeout=60_000)
        if n_cookies > 0:
            # Cookie 注入后重新打开页面以确保会话生效
            await task_page.goto(start_url, wait_until="domcontentloaded", timeout=60_000)
    except Exception as exc:
        # 导航失败：关闭标签页，但不关闭浏览器
        try:
            await task_page.close()
        except Exception:
            pass
        await close_task_tab_safely(task_page, account_id)
        raise RuntimeError(f"任务标签页导航失败 {start_url}: {exc}") from exc

    try:
        yield mgr, auto_key
    finally:
        # ── 退出：仅关闭任务标签页，浏览器保持运行 ──
        await close_task_tab_safely(task_page, account_id)
        log.debug(
            "MITM 任务标签页已关闭，持久化浏览器继续运行 account_id=%d key=%s",
            account_id,
            auto_key,
        )


async def wait_mitm_capture(
    *,
    mgr: EdgeWebDriveManager,
    auto_key: str,
    start_url: str,
    read_response: Callable[[], Optional[Dict[str, Any]]],
    since_ms: int,
    wait_seconds: int,
    error_detail: str,
    reload_interval_sec: float = _MITM_PAGE_RELOAD_INTERVAL_SEC,
) -> Dict[str, Any]:
    """
    轮询 MITM 落盘文件；超时前按间隔刷新任务标签页以再次触发目标 API。

    ``mgr.reload_active_tab`` 始终操作 ``ctx.pages[-1]``，
    在持久化浏览器中，任务标签页是最后打开的页（最后一个），因此行为与旧版一致。
    """
    deadline = time.monotonic() + wait_seconds
    next_reload = time.monotonic() + reload_interval_sec
    while time.monotonic() < deadline:
        data = read_response()
        if data and int(data.get("ts") or 0) >= since_ms:
            return data
        if time.monotonic() >= next_reload:
            next_reload += reload_interval_sec
            try:
                await mgr.reload_active_tab(auto_key, start_url)
            except Exception as exc:
                log.debug("MITM 等待中刷新任务标签页失败: %s", exc)
        await asyncio.sleep(0.35)
    raise RuntimeError(
        f"{wait_seconds}s 内未截获目标 API 响应（{error_detail}）。"
        "请确认 MITM 已启动；若仅在账号管理页有头浏览器中登录，请保持该窗口打开后重试"
        "（系统会从有头会话同步 Cookie 到无头 MITM 浏览器）。"
    )
