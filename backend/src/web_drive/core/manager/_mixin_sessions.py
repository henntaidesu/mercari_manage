# -*- coding: utf-8 -*-
"""EdgeWebDriveManager 会话管理：打开 / 关闭 / 列举 / 快照"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional
from ..interactive_tab_state import restore_tabs_to_context, save_snapshot_from_context
from ..paths import profile_dir_for, profiles_root, validate_account_key
from ._config import log, _DriveThreadState, force_headed_debug_enabled


class _SessionsMixin:

    @staticmethod
    def _prune_dead_sessions(s: _DriveThreadState) -> None:
        for k in list(s.contexts.keys()):
            c = s.contexts.get(k)
            if c is not None and _SessionsMixin._is_context_alive(c):
                continue
            s.contexts.pop(k, None)
            s.session_meta.pop(k, None)


    @staticmethod
    def _session_meta(s: _DriveThreadState, key: str) -> Dict[str, bool]:
        return s.session_meta.get(key, {})


    @staticmethod
    def _is_interactive_session(s: _DriveThreadState, key: str) -> bool:
        ctx = s.contexts.get(key)
        if ctx is None or not _SessionsMixin._is_context_alive(ctx):
            return False
        return bool(s.session_meta.get(key, {}).get("interactive"))


    @staticmethod
    def _is_context_alive(ctx: Any) -> bool:
        """用户手动关窗后 Playwright 上下文已关闭，但字典里可能仍留着引用。"""
        if ctx is None:
            return False
        try:
            _ = list(ctx.pages)
            return True
        except Exception:
            return False


    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出当前线程内仍存活的上下文（async 路由=主循环；sync+asyncio.run=线程池线程）。"""
        s = self._ts()
        out: List[Dict[str, Any]] = []
        for key, ctx in list(s.contexts.items()):
            if not self._is_context_alive(ctx):
                continue
            try:
                pages = len(ctx.pages)
            except Exception:
                continue
            meta = self._session_meta(s, key)
            out.append(
                {
                    "account_key": key,
                    "profile_dir": os.path.join(profiles_root(), key),
                    "open_pages": pages,
                    "interactive": bool(meta.get("interactive")),
                    "headless": bool(meta.get("headless")),
                }
            )
        return out


    async def open_session(
        self,
        account_key: str,
        *,
        headless: bool = False,
        start_url: Optional[str] = None,
        proxy_server: Optional[str] = None,
        interactive: Optional[bool] = None,
        restore_tabs: Optional[bool] = None,
        start_minimized: bool = False,
    ) -> Dict[str, Any]:
        """
        :param interactive: 是否为「用户手动可见」会话（影响窗口前台 / 标签恢复行为）。
            默认：``headless=False`` 时为 True，``headless=True`` 时为 False。
        :param restore_tabs: 有头交互会话是否从 ``interactive_tabs.snapshot.json`` 恢复标签；
            默认 interactive 时为 True。
        :param start_minimized: 启动时窗口最小化到任务栏（后台运行，不抢前台）。
            ``headless=True`` 时无效。``interactive=True`` 仍会生效，此时跳过
            ``--start-maximized``，改用 ``--start-minimized``。
        """
        key = validate_account_key(account_key)
        if interactive is None:
            interactive = not headless
        if restore_tabs is None:
            restore_tabs = bool(interactive and not headless)
        async with self._serialize_profile(key):
            return await self._open_session_impl(
                key,
                headless=headless,
                start_url=start_url,
                proxy_server=proxy_server,
                interactive=interactive,
                restore_tabs=bool(restore_tabs),
                start_minimized=bool(start_minimized),
            )


    def is_interactive_session_running(self, account_key: str) -> bool:
        """主 profile（``mercari_{id}``）上是否有用户手动打开的有头会话。"""
        key = validate_account_key(account_key)
        s = self._ts()
        self._prune_dead_sessions(s)
        return self._is_interactive_session(s, key)


    async def snapshot_all_interactive_sessions(self) -> int:
        """将当前线程内所有有头交互会话的标签 URL 写入 profile 快照。返回成功写入的账号数。"""
        s = self._prepare_async()
        saved = 0
        async with s.lock:  # type: ignore[union-attr]
            for key, ctx in list(s.contexts.items()):
                meta = self._session_meta(s, key)
                if not meta.get("interactive") or not self._is_context_alive(ctx):
                    continue
                if await save_snapshot_from_context(key, ctx):
                    saved += 1
        return saved


    async def _open_session_impl(
        self,
        key: str,
        *,
        headless: bool = False,
        start_url: Optional[str] = None,
        proxy_server: Optional[str] = None,
        interactive: bool = False,
        restore_tabs: bool = False,
        start_minimized: bool = False,
        block_images: bool = False,
    ) -> Dict[str, Any]:
        # 全局调试开关：强制有头时，最底层兜底——无论调用方传入什么，一律有头
        if force_headed_debug_enabled() and headless:
            headless = False
        s = self._prepare_async()
        async with s.lock:  # type: ignore[union-attr]
            self._prune_dead_sessions(s)

            ctx = s.contexts.get(key)
            meta = self._session_meta(s, key)

            if ctx is not None and self._is_context_alive(ctx):
                if interactive and not meta.get("interactive"):
                    try:
                        await ctx.close()
                    except Exception:
                        pass
                    s.contexts.pop(key, None)
                    s.session_meta.pop(key, None)
                    ctx = None
            ctx = s.contexts.get(key)
            if ctx is not None and self._is_context_alive(ctx):
                if start_url and not (interactive and restore_tabs):
                    try:
                        await self._navigate_one_tab(ctx, start_url)
                    except Exception:
                        s.contexts.pop(key, None)
                        s.session_meta.pop(key, None)
                        ctx = None
                else:
                    if interactive:
                        await save_snapshot_from_context(key, ctx)
                    out = {
                        "account_key": key,
                        "already_running": True,
                        "profile_dir": profile_dir_for(key),
                        "profiles_root": profiles_root(),
                        "interactive": bool(meta.get("interactive")),
                    }
                    return out

            if ctx is not None and self._is_context_alive(ctx):
                out = {
                    "account_key": key,
                    "already_running": True,
                    "profile_dir": profile_dir_for(key),
                    "profiles_root": profiles_root(),
                    "interactive": bool(meta.get("interactive")),
                }
                return out

            pw = await self._ensure_playwright(s)
            udir = profile_dir_for(key)
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-session-crashed-bubble",
                "--disable-infobars",
            ]
            if interactive and not headless:
                # start_minimized 与 interactive 同时为真:跳过 --start-maximized,
                # 启动后窗口在任务栏最小化(后台运行)。
                if start_minimized:
                    launch_args.append("--start-minimized")
                    launch_args.append("--disable-features=RestoreSession")
                else:
                    launch_args.extend(self._interactive_launch_args())
            elif start_minimized and not headless:
                launch_args.append("--start-minimized")
            if block_images:
                launch_args.append("--blink-settings=imagesEnabled=false")
            launch_kw: Dict[str, Any] = {
                "user_data_dir": udir,
                "channel": "msedge",
                "headless": headless,
                "args": launch_args,
            }
            if interactive and not headless and self._interactive_no_viewport():
                launch_kw["no_viewport"] = True
            else:
                launch_kw["viewport"] = {"width": 1280, "height": 800}
            ps = (proxy_server or "").strip()
            if ps:
                launch_kw["proxy"] = {"server": ps}
                # 本地 mitmproxy 动态签发站点证书，未将 mitm CA 导入系统前 Edge 会报 ERR_CERT_AUTHORITY_INVALID
                launch_kw["ignore_https_errors"] = True

            delays = self._launch_retry_delays_sec()
            last_exc: Optional[BaseException] = None
            context = None
            for attempt, delay_sec in enumerate(delays):
                if delay_sec > 0:
                    await asyncio.sleep(delay_sec)
                try:
                    if attempt == 0:
                        self._purge_non_auth_cache(udir)
                    context = await pw.chromium.launch_persistent_context(**launch_kw)
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
            if context is None:
                raise RuntimeError(
                    f"启动 Edge 失败（请确认已安装 Microsoft Edge，并已执行 playwright install msedge；"
                    f"或关闭其它占用该账号 profile 的 Edge 窗口后重试；已重试 {len(delays)} 次）: {last_exc}"
                ) from last_exc

            await self._apply_image_block_route(context, block_images=block_images)
            s.contexts[key] = context
            s.session_meta[key] = {"interactive": bool(interactive), "headless": bool(headless)}

            # 用户手动关窗 / 浏览器进程退出 → Playwright 触发 context 'close'，
            # 立刻把死引用从注册表移除，下次 open_session 才会重新启动而非误报 already_running
            def _on_context_close(*_args, _key=key, _state=s):
                _state.contexts.pop(_key, None)
                _state.session_meta.pop(_key, None)
                log.info("浏览器会话已关闭（用户关窗 / 进程退出），已从注册表移除: %s", _key)

            try:
                context.on("close", _on_context_close)
            except Exception as exc:
                log.debug("注册 context close 事件失败 %s: %s", key, exc)

            tab_restore: Optional[Dict[str, Any]] = None
            if interactive and restore_tabs:
                fallback = (start_url or "").strip() or "https://jp.mercari.com/"
                tab_restore = await restore_tabs_to_context(
                    context, key, fallback_url=fallback
                )
            elif start_url:
                await self._navigate_one_tab(context, start_url)

            return {
                "account_key": key,
                "already_running": False,
                "profile_dir": udir,
                "profiles_root": profiles_root(),
                "proxy_server": ps or None,
                "interactive": bool(interactive),
                "tab_restore": tab_restore,
            }


    async def _close_session_unlocked(
        self,
        key: str,
        *,
        only_automation: bool = False,
        force: bool = False,
    ) -> Dict[str, Any]:
        s = self._prepare_async()
        closed = False
        async with s.lock:  # type: ignore[union-attr]
            self._prune_dead_sessions(s)
            meta = self._session_meta(s, key)
            if only_automation and not force and meta.get("interactive"):
                return {
                    "account_key": key,
                    "closed": False,
                    "skipped": "interactive",
                }
            ctx = s.contexts.pop(key, None)
            meta_before_close = dict(meta)
            s.session_meta.pop(key, None)
            if ctx is None:
                return {"account_key": key, "closed": False}
            try:
                if self._is_context_alive(ctx):
                    if meta_before_close.get("interactive"):
                        await save_snapshot_from_context(key, ctx)
                    await ctx.close()
                    closed = True
            except Exception:
                pass
        if closed:
            await asyncio.sleep(self._profile_release_delay_sec())
        return {"account_key": key, "closed": closed}


    async def close_session(
        self,
        account_key: str,
        *,
        only_automation: bool = False,
        force: bool = False,
    ) -> Dict[str, Any]:
        key = validate_account_key(account_key)
        async with self._serialize_profile(key):
            return await self._close_session_unlocked(
                key, only_automation=only_automation, force=force
            )
