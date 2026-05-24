# -*- coding: utf-8 -*-
"""
MITM 自动化：按账号打开主 profile ``meilu_{id}`` 的有头 Edge 浏览器,
经 MITM 代理捕获煤炉 API 响应。

设计要点：
  - 直接使用主 profile,登录态由 Edge 持久化 cookie 自动维护,无需 cookie seed
    与首页 prewarm。
  - 同账号通过 ``run_meilu_serial_async`` 串行执行,无并发问题;
    浏览器自动关闭由队列(``account_serial_queue.py``)负责:队列归 0 后
    经 ``WEB_DRIVE_QUEUE_IDLE_CLOSE_SEC`` 秒延迟自动关闭。
  - 若同账号已存在「非 MITM 代理」的主浏览器(用户从 /meilu-accounts 打开的),
    首次进入会强制关闭并以 MITM 代理重新启动。
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Dict, Optional, Tuple

from ...ssl_mitm_proxy.runner import default_mitm_proxy_url, start_mitm_proxy
from .manager import EdgeWebDriveManager, get_web_drive_manager
from .paths import meilu_account_key

log = logging.getLogger(__name__)

_MITM_PAGE_RELOAD_INTERVAL_SEC = 20.0


def _default_minimized() -> bool:
    """MITM 自动化浏览器是否默认在后台(最小化)运行。

    通过 ``WEB_DRIVE_MITM_MINIMIZED`` 环境变量覆盖,接受 0/false/no/off 关闭;
    其余值(含未设置)视为开启,即默认窗口最小化、不抢占前台。
    """
    raw = (os.environ.get("WEB_DRIVE_MITM_MINIMIZED") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


async def _is_context_alive(mgr: EdgeWebDriveManager, key: str) -> bool:
    """检查指定 key 的 context 在 manager 内是否仍存活(用户未手动关窗)。"""
    s = mgr._prepare_async()
    async with s.lock:  # type: ignore[union-attr]
        ctx = s.contexts.get(key)
        return ctx is not None and mgr._is_context_alive(ctx)


async def _launch_with_mitm(
    *,
    mgr: EdgeWebDriveManager,
    account_id: int,
    main_key: str,
    target_url: str,
    minimized: bool = True,
) -> None:
    """启动账号主 profile 有头 Edge,直接进入目标页(经 MITM 代理)。

    若同 profile 已有进程(无 MITM 代理),强制关闭后重启。
    ``minimized=True`` 时浏览器窗口最小化到任务栏(后台运行,不抢前台)。
    """
    r = start_mitm_proxy()
    if r.get("error"):
        raise RuntimeError(f"MITM 代理不可用: {r['error']}")

    if mgr.is_interactive_session_running(main_key):
        log.info(
            "[mitm] account_id=%d 主浏览器已在运行(无 MITM 代理),强制关闭后以 MITM 重新打开",
            account_id,
        )
        try:
            await mgr.close_session(main_key, force=True)
        except Exception as exc:
            log.warning("[mitm] 关闭主浏览器失败(继续尝试启动): %s", exc)

    proxy = default_mitm_proxy_url()
    target = (target_url or "").strip() or "https://jp.mercari.com/"

    await mgr.open_session(
        main_key,
        headless=False,
        start_url=target,
        proxy_server=proxy,
        interactive=True,
        restore_tabs=False,
        start_minimized=bool(minimized),
    )

    if not await _is_context_alive(mgr, main_key):
        raise RuntimeError(
            f"主 profile MITM 浏览器启动失败: {main_key}。请检查 Edge / Playwright 状态后重试。"
        )


async def shutdown_mitm_leases() -> None:
    """旧版兼容入口:新版无内部租借状态需要清理(由队列负责),保留为 no-op。"""
    return None


@asynccontextmanager
async def mitm_automation_browser(
    account_id: int,
    *,
    start_url: str,
    minimized: Optional[bool] = None,
) -> AsyncIterator[Tuple[EdgeWebDriveManager, str]]:
    """
    上下文管理器:进入时确保账号主 profile 浏览器已开(走 MITM 代理),并导航到目标页。

    yield ``(mgr, main_key)``;退出时**不关闭**浏览器——关闭由队列层
    (``account_serial_queue._delayed_close_browser``)按 ``WEB_DRIVE_QUEUE_IDLE_CLOSE_SEC``
    延迟自动处理。

    ``minimized``: 启动时是否最小化(后台运行)。``None`` = 读环境变量
    ``WEB_DRIVE_MITM_MINIMIZED``(默认 ``"1"`` = 最小化)。已有浏览器复用时仅
    刷新标签页,不会重新决定窗口状态。
    """
    aid = int(account_id)
    main_key = meilu_account_key(aid)
    mgr = get_web_drive_manager()
    target_url = (start_url or "").strip()
    use_minimized = _default_minimized() if minimized is None else bool(minimized)

    if await _is_context_alive(mgr, main_key):
        # 复用:仅刷新当前标签页到目标 URL
        if target_url:
            try:
                await mgr.reload_active_tab(main_key, target_url)
                log.debug("[mitm] 复用主浏览器 account_id=%d → %s", aid, target_url)
            except Exception as exc:
                log.warning(
                    "[mitm] 复用 reload 失败,强制重启浏览器 account_id=%d: %s",
                    aid,
                    exc,
                )
                try:
                    await mgr.close_session(main_key, force=True)
                except Exception:
                    pass
                await _launch_with_mitm(
                    mgr=mgr,
                    account_id=aid,
                    main_key=main_key,
                    target_url=target_url,
                    minimized=use_minimized,
                )
    else:
        await _launch_with_mitm(
            mgr=mgr,
            account_id=aid,
            main_key=main_key,
            target_url=target_url,
            minimized=use_minimized,
        )

    yield mgr, main_key


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
    轮询 MITM 落盘文件;超时前按间隔刷新当前标签页以再次触发目标 API。

    形参名 ``auto_key`` 系历史命名,实际传任意会话 key
    (新版传入 ``meilu_account_key(aid)`` 主 profile key)。
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
                log.debug("MITM 等待中刷新标签页失败: %s", exc)
        await asyncio.sleep(0.35)
    raise RuntimeError(
        f"{wait_seconds}s 内未截获目标 API 响应({error_detail})。"
        "请确认 MITM 已启动;并先在账号管理页对该账号完成 Mercari 登录(主 profile 会持久化登录态)。"
    )
