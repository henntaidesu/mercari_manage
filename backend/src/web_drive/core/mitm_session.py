# -*- coding: utf-8 -*-
"""
MITM 自动化:按账号维护一个**租借式**有头最小化 Edge 浏览器,同账号多个 MITM
请求复用同一进程,空闲一段时间后才整体关闭。

生命周期:
  ──────────────────────────────────────────────────────────────────────
  T0 第一个请求进入:
     1. 取消该账号挂起的延迟关闭 task(如有)
     2. refs = 0 → 1
     3. 启动新的 ``__auto`` Edge:
        - 确保 MITM 代理已启动
        - 从 ``meilu_{id}`` profile 磁盘 seed Cookie 到 ``meilu_{id}__auto``
        - ``launch_persistent_context(start_url=https://jp.mercari.com/)``
     4. **prewarm**:``await asyncio.sleep(WEB_DRIVE_MITM_PREWARM_SEC, 默认 3.0)``
        让煤炉首页 Set-Cookie / refresh-token 生效
     5. ``reload_active_tab(start_url)`` 跳到调用方真正想要的目标页
     6. yield ``(mgr, auto_key)``

  T1 后续请求进入(refs > 0,浏览器存活):
     1. 取消延迟关闭 task
     2. refs++
     3. ``reload_active_tab(start_url)`` 复用浏览器
     4. yield ``(mgr, auto_key)``

  Tn 请求退出:
     - refs--
     - refs == 0 → schedule 延迟关闭 task
       ``WEB_DRIVE_MITM_IDLE_CLOSE_SEC``(默认 10.0)秒后真正 ``close_session``

  延迟期内若有新请求:
     - cancel 延迟关闭 task → 继续复用
  ──────────────────────────────────────────────────────────────────────

设计动机:
  - 老版每次开/关浏览器,启动开销大、cookie 未充分刷新就跳子页易丢登录态
  - 新版浏览器复用 + 首次启动统一 prewarm,稳定且省时
  - 与上游 ``run_meilu_serial_async`` 同账号 FIFO 队列协作:浏览器在整个队列
    执行期间保持驻留,直到队列空闲足够久才关掉
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, Optional, Tuple

from ...ssl_mitm_proxy.runner import default_mitm_proxy_url, start_mitm_proxy
from .manager import EdgeWebDriveManager, get_web_drive_manager
from .paths import (
    meilu_account_key,
    meilu_automation_key,
    seed_automation_profile_from_account,
)

log = logging.getLogger(__name__)

_MITM_PAGE_RELOAD_INTERVAL_SEC = 20.0
_MERCARI_HOME_URL = "https://jp.mercari.com/"


def _prewarm_sec() -> float:
    """首次启动浏览器后等待 cookie 刷新的秒数,默认 3.0,可由 ``WEB_DRIVE_MITM_PREWARM_SEC`` 覆盖。"""
    raw = (os.environ.get("WEB_DRIVE_MITM_PREWARM_SEC") or "3.0").strip()
    try:
        v = float(raw)
    except ValueError:
        return 3.0
    return v if v >= 0 else 0.0


def _idle_close_sec() -> float:
    """refs 归 0 后延迟关闭的秒数,默认 10.0,可由 ``WEB_DRIVE_MITM_IDLE_CLOSE_SEC`` 覆盖。"""
    raw = (os.environ.get("WEB_DRIVE_MITM_IDLE_CLOSE_SEC") or "10.0").strip()
    try:
        v = float(raw)
    except ValueError:
        return 10.0
    return v if v >= 0 else 0.0


@dataclass
class _MitmLeaseState:
    """每个煤炉账号一份的租借状态。"""

    refs: int = 0
    started: bool = False
    close_task: Optional[asyncio.Task] = None
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


async def _is_auto_context_alive(mgr: EdgeWebDriveManager, auto_key: str) -> bool:
    """检查 __auto profile 在 manager 内的 context 是否仍存活(用户未手动关窗)。"""
    s = mgr._prepare_async()
    async with s.lock:  # type: ignore[union-attr]
        ctx = s.contexts.get(auto_key)
        return ctx is not None and mgr._is_context_alive(ctx)


async def _launch_with_prewarm(
    *,
    mgr: EdgeWebDriveManager,
    account_id: int,
    auto_key: str,
    target_url: str,
) -> None:
    """启动 ``__auto`` Edge,先开煤炉首页等 prewarm 秒数刷新 cookie,再跳到 ``target_url``。"""
    # ── A. MITM 代理 ──
    r = start_mitm_proxy()
    if r.get("error"):
        raise RuntimeError(f"MITM 代理不可用: {r['error']}")

    main_key = meilu_account_key(account_id)
    if mgr.is_interactive_session_running(main_key):
        log.warning(
            "MITM seed 时检测到 %s 有头会话仍在运行,部分 Cookie 文件被 Edge 独占;"
            "如登录态较旧,请先关闭账号管理页的 Edge 窗口以刷盘 Cookie 后再重试。",
            main_key,
        )

    # ── B. seed cookie ──
    try:
        seed_automation_profile_from_account(account_id)
    except Exception as exc:
        log.warning("MITM seed profile 失败 %s(仍尝试用上次磁盘 Cookie 启动): %s", auto_key, exc)

    # ── C. 启动浏览器(start_url 先打开煤炉首页) ──
    proxy = default_mitm_proxy_url()
    await mgr.ensure_session_for_mitm(
        auto_key,
        start_url=_MERCARI_HOME_URL,
        proxy_server=proxy,
        headless=False,
        start_minimized=True,
    )

    if not await _is_auto_context_alive(mgr, auto_key):
        raise RuntimeError(
            f"MITM 浏览器启动失败: {auto_key}。请检查 Edge / Playwright 状态后重试。"
        )

    # ── D. prewarm:等待 cookie / refresh-token 落地 ──
    prewarm = _prewarm_sec()
    if prewarm > 0:
        log.info(
            "[mitm-lease] account_id=%d 已打开首页,prewarm sleep %.1fs 刷新 cookie",
            account_id,
            prewarm,
        )
        await asyncio.sleep(prewarm)

    # ── E. 跳转到调用方真实目标页(若不是首页) ──
    target = (target_url or "").strip()
    if target and target != _MERCARI_HOME_URL:
        try:
            await mgr.reload_active_tab(auto_key, target)
        except Exception as exc:
            log.warning("[mitm-lease] reload 到 start_url 失败 %s: %s", target, exc)


async def _delayed_close(account_id: int, state: _MitmLeaseState, auto_key: str) -> None:
    """空闲 ``WEB_DRIVE_MITM_IDLE_CLOSE_SEC`` 秒后关闭 ``__auto`` 浏览器。被新请求 cancel 即放弃关闭。"""
    delay = _idle_close_sec()
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return

    async with state.lock:  # type: ignore[union-attr]
        if state.refs > 0:
            # 等待期间又有新请求加入(取消失败的边界情况兜底)
            return
        if not state.started:
            state.close_task = None
            return
        mgr = get_web_drive_manager()
        try:
            await mgr.close_session(auto_key, force=True)
            log.info(
                "[mitm-lease] 浏览器空闲 %.1fs 已关闭 account_id=%d key=%s",
                delay,
                account_id,
                auto_key,
            )
        except Exception as exc:
            log.warning(
                "[mitm-lease] 关闭浏览器失败 account_id=%d key=%s: %s",
                account_id,
                auto_key,
                exc,
            )
        state.started = False
        state.close_task = None


async def shutdown_mitm_leases() -> None:
    """进程退出前调用:取消所有挂起的延迟关闭 task,关闭仍驻留的 ``__auto`` 浏览器。"""
    async with _ensure_leases_guard():
        items = list(_leases.items())

    mgr = get_web_drive_manager()
    for aid, state in items:
        if state.lock is None:
            continue
        async with state.lock:
            if state.close_task is not None and not state.close_task.done():
                state.close_task.cancel()
                try:
                    await state.close_task
                except (asyncio.CancelledError, Exception):
                    pass
            state.close_task = None
            if state.started:
                auto_key = meilu_automation_key(int(aid))
                try:
                    await mgr.close_session(auto_key, force=True)
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
    上下文管理器:为单次 MITM 操作租借一个 ``__auto`` 浏览器(同账号自动复用)。

    yield ``(mgr, auto_key)``;退出时仅 refs--,空闲超时后才真正关闭浏览器。
    """
    aid = int(account_id)
    auto_key = meilu_automation_key(aid)
    mgr = get_web_drive_manager()
    state = await _get_lease(aid)

    target_url = (start_url or "").strip()

    # ── 进入:取消 pending 关闭、refs++、按需启动或复用 ──
    async with state.lock:  # type: ignore[union-attr]
        if state.close_task is not None and not state.close_task.done():
            state.close_task.cancel()
            try:
                await state.close_task
            except (asyncio.CancelledError, Exception):
                pass
        state.close_task = None

        state.refs += 1

        try:
            need_launch = not state.started
            if not need_launch:
                # 浏览器可能已被用户手动关掉 / 进程异常退出
                alive = await _is_auto_context_alive(mgr, auto_key)
                if not alive:
                    log.info(
                        "[mitm-lease] account_id=%d 浏览器已不存活,重启 + prewarm",
                        aid,
                    )
                    state.started = False
                    need_launch = True

            if need_launch:
                await _launch_with_prewarm(
                    mgr=mgr,
                    account_id=aid,
                    auto_key=auto_key,
                    target_url=target_url,
                )
                state.started = True
            else:
                # 复用:reload 到本次目标页(start_url 为空时则停留在原页面)
                if target_url:
                    try:
                        await mgr.reload_active_tab(auto_key, target_url)
                        log.debug(
                            "[mitm-lease] 复用浏览器 account_id=%d → %s",
                            aid,
                            target_url,
                        )
                    except Exception as exc:
                        log.warning(
                            "[mitm-lease] 复用 reload 失败,强制重启浏览器 account_id=%d: %s",
                            aid,
                            exc,
                        )
                        # 兜底重启
                        try:
                            await mgr.close_session(auto_key, force=True)
                        except Exception:
                            pass
                        state.started = False
                        await _launch_with_prewarm(
                            mgr=mgr,
                            account_id=aid,
                            auto_key=auto_key,
                            target_url=target_url,
                        )
                        state.started = True
        except BaseException:
            state.refs -= 1
            raise

    # ── yield 阶段:不持锁,允许同账号其它租借在退出时拿锁更新 refs ──
    try:
        yield mgr, auto_key
    finally:
        async with state.lock:  # type: ignore[union-attr]
            state.refs -= 1
            if state.refs <= 0:
                state.refs = 0
                if state.close_task is None or state.close_task.done():
                    state.close_task = asyncio.create_task(
                        _delayed_close(aid, state, auto_key)
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
    轮询 MITM 落盘文件;超时前按间隔刷新当前标签页以再次触发目标 API。

    ``mgr.reload_active_tab`` 始终操作 ``ctx.pages[-1]``;新版 ``mitm_automation_browser``
    在租借期内浏览器保持单标签,因此与旧持久化版本行为一致。
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
        "请确认 MITM 已启动;并先在账号管理页对该账号完成 Mercari 登录后**关闭该窗口**,"
        "以便系统从磁盘 Cookie 启动独立的最小化 Edge 拉取数据。"
    )
