# -*- coding: utf-8 -*-
"""
MITM 自动化:按账号租借一个**主 profile** ``meilu_{id}`` 的有头 Edge 浏览器,
同账号多个 MITM 请求复用同一进程;不再使用 ``meilu_{id}__auto`` 副本与 cookie seed。

设计要点:
  - 直接打开账号主 profile（与 /meilu-accounts 「打开浏览器」一致）,登录态由 Edge
    持久化 cookie 自动维护,无需先开首页 + sleep prewarm。
  - 同账号并发请求通过 ``state.refs`` 计数避免互相覆盖目标 URL。
  - 浏览器**保持打开**,由用户在前端手动关闭(或进程退出时统一清理),
    不再有空闲自动关闭逻辑——主窗口对用户可见,自动关闭会打断用户操作。
  - 若同账号已存在「非 MITM 代理」的主浏览器(例如用户从 /meilu-accounts 打开的),
    首次租借会强制关闭并以 MITM 代理重新启动,以确保 API 请求经过代理被截获。

注意:
  - 全栈(/todos / /on-sale-items / /orders / /notifications / /meilu-accounts auth)
    均已统一到主 profile + MITM 代理方案,不再有 ``__auto`` 副本与 cookie seed 逻辑。
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Dict, Optional, Tuple

from ...ssl_mitm_proxy.runner import default_mitm_proxy_url, start_mitm_proxy
from .manager import EdgeWebDriveManager, get_web_drive_manager
from .paths import meilu_account_key

log = logging.getLogger(__name__)

_MITM_PAGE_RELOAD_INTERVAL_SEC = 20.0


@dataclass
class _MitmLeaseState:
    """每个煤炉账号一份的租借状态(仅用于并发 refs 计数,不再做自动关闭)。"""

    refs: int = 0
    started: bool = False
    lock: Optional[asyncio.Lock] = None


_leases: Dict[int, _MitmLeaseState] = {}
_leases_guard: Optional[asyncio.Lock] = None


def _ensure_leases_guard() -> asyncio.Lock:
    global _leases_guard
    if _leases_guard is None:
        _leases_guard = asyncio.Lock()
    return _leases_guard


async def _get_lease(account_id: int) -> _MitmLeaseState:
    aid = int(account_id)
    async with _ensure_leases_guard():
        st = _leases.get(aid)
        if st is None:
            st = _MitmLeaseState(lock=asyncio.Lock())
            _leases[aid] = st
        elif st.lock is None:
            st.lock = asyncio.Lock()
        return st


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
) -> None:
    """启动账号主 profile ``meilu_{id}`` 的有头 Edge,直接进入目标页(经 MITM 代理)。

    若同 profile 已有进程(无 MITM 代理),强制关闭后重启。
    """
    r = start_mitm_proxy()
    if r.get("error"):
        raise RuntimeError(f"MITM 代理不可用: {r['error']}")

    # 如果同账号主浏览器已经在运行(很可能是用户从 /meilu-accounts 打开的,未走 MITM),
    # 强制关闭后用 MITM 代理重新启动,否则 API 请求不会经过代理。
    if mgr.is_interactive_session_running(main_key):
        log.info(
            "[mitm-lease] account_id=%d 主浏览器已在运行(无 MITM 代理),强制关闭后以 MITM 重新打开",
            account_id,
        )
        try:
            await mgr.close_session(main_key, force=True)
        except Exception as exc:
            log.warning("[mitm-lease] 关闭主浏览器失败(继续尝试启动): %s", exc)

    proxy = default_mitm_proxy_url()
    target = (target_url or "").strip() or "https://jp.mercari.com/"

    await mgr.open_session(
        main_key,
        headless=False,
        start_url=target,
        proxy_server=proxy,
        interactive=True,
        restore_tabs=False,
    )

    if not await _is_context_alive(mgr, main_key):
        raise RuntimeError(
            f"主 profile MITM 浏览器启动失败: {main_key}。请检查 Edge / Playwright 状态后重试。"
        )


async def shutdown_mitm_leases() -> None:
    """进程退出前调用:关闭仍驻留的主 profile 浏览器,清空租借状态。"""
    async with _ensure_leases_guard():
        items = list(_leases.items())

    mgr = get_web_drive_manager()
    for aid, state in items:
        if state.lock is None:
            continue
        async with state.lock:
            if state.started:
                main_key = meilu_account_key(int(aid))
                try:
                    await mgr.close_session(main_key, force=True)
                except Exception as exc:
                    log.debug(
                        "[mitm-lease] shutdown 关闭浏览器失败 account_id=%s: %s", aid, exc
                    )
                state.started = False
            state.refs = 0

    async with _ensure_leases_guard():
        _leases.clear()


@asynccontextmanager
async def mitm_automation_browser(
    account_id: int,
    *,
    start_url: str,
) -> AsyncIterator[Tuple[EdgeWebDriveManager, str]]:
    """
    上下文管理器:为单次 MITM 操作租借账号主 profile 浏览器(同账号自动复用)。

    yield ``(mgr, main_key)``;退出时仅 refs--,不再自动关闭浏览器
    (与 /meilu-accounts 一致,由用户决定何时关闭)。
    """
    aid = int(account_id)
    main_key = meilu_account_key(aid)
    mgr = get_web_drive_manager()
    state = await _get_lease(aid)

    target_url = (start_url or "").strip()

    async with state.lock:  # type: ignore[union-attr]
        state.refs += 1

        try:
            need_launch = not state.started
            if not need_launch:
                # 浏览器可能已被用户手动关掉 / 进程异常退出
                alive = await _is_context_alive(mgr, main_key)
                if not alive:
                    log.info(
                        "[mitm-lease] account_id=%d 主浏览器已不存活,重新启动",
                        aid,
                    )
                    state.started = False
                    need_launch = True

            if need_launch:
                await _launch_with_mitm(
                    mgr=mgr,
                    account_id=aid,
                    main_key=main_key,
                    target_url=target_url,
                )
                state.started = True
            else:
                # 复用:reload 到本次目标页(start_url 为空时则停留在原页面)
                if target_url:
                    try:
                        await mgr.reload_active_tab(main_key, target_url)
                        log.debug(
                            "[mitm-lease] 复用主浏览器 account_id=%d → %s",
                            aid,
                            target_url,
                        )
                    except Exception as exc:
                        log.warning(
                            "[mitm-lease] 复用 reload 失败,强制重启浏览器 account_id=%d: %s",
                            aid,
                            exc,
                        )
                        try:
                            await mgr.close_session(main_key, force=True)
                        except Exception:
                            pass
                        state.started = False
                        await _launch_with_mitm(
                            mgr=mgr,
                            account_id=aid,
                            main_key=main_key,
                            target_url=target_url,
                        )
                        state.started = True
        except BaseException:
            state.refs -= 1
            raise

    try:
        yield mgr, main_key
    finally:
        async with state.lock:  # type: ignore[union-attr]
            state.refs -= 1
            if state.refs < 0:
                state.refs = 0
            # 不再自动延迟关闭:浏览器由用户手动关闭或进程退出时清理


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

    形参名 ``auto_key`` 系历史命名,实际可传任意会话 key
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
