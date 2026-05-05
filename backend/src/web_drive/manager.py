# -*- coding: utf-8 -*-
"""
按 account_key 使用独立 user_data_dir 启动 Microsoft Edge（Playwright channel=msedge），
Cookie 与站点数据随目录持久化；不同账号对应不同子浏览器配置目录。
"""

from __future__ import annotations

import asyncio
import os
import shutil
from typing import Any, Dict, List, Optional

from .paths import profile_dir_for, profiles_root, validate_account_key

_manager: Optional["EdgeWebDriveManager"] = None


def get_web_drive_manager() -> "EdgeWebDriveManager":
    global _manager
    if _manager is None:
        _manager = EdgeWebDriveManager()
    return _manager


class EdgeWebDriveManager:
    """管理多账号 Edge 持久化会话（每账号独立 profile 目录）。"""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._playwright: Any = None
        self._contexts: Dict[str, Any] = {}

    @staticmethod
    async def _navigate_one_tab(
        context: Any,
        start_url: str,
        *,
        wait_until: str = "domcontentloaded",
    ) -> None:
        """只保留一个标签并打开 start_url。

        Edge 持久化 profile 的「继续浏览上次页面」可能在 launch 后异步再开标签，
        仅关掉 pages[1:] 仍会出现两个相同页面；因此先关掉启动时所有页再 new_page，
        并在 goto 后短循环关闭晚到的恢复标签。
        """
        for p in list(context.pages):
            try:
                await p.close()
            except Exception:
                pass
        page = await context.new_page()
        await page.goto(start_url, wait_until=wait_until)
        for _ in range(12):
            extra = [p for p in context.pages if p is not page]
            if not extra:
                break
            for p in extra:
                try:
                    await p.close()
                except Exception:
                    pass
            await asyncio.sleep(0.15)

    async def _ensure_playwright(self) -> Any:
        if self._playwright is None:
            try:
                from playwright.async_api import async_playwright
            except ImportError as exc:
                raise RuntimeError(
                    "未安装 playwright，请在 backend 目录执行: pip install playwright && playwright install msedge"
                ) from exc
            self._playwright = await async_playwright().start()
        return self._playwright

    @staticmethod
    def _purge_non_auth_cache(user_data_dir: str) -> None:
        """清理浏览器运行期缓存，尽量保留登录态相关数据（cookies/local storage/indexeddb）。"""
        if not user_data_dir or not os.path.isdir(user_data_dir):
            return

        targets = [
            os.path.join(user_data_dir, "Default", "Cache"),
            os.path.join(user_data_dir, "Default", "Code Cache"),
            os.path.join(user_data_dir, "Default", "GPUCache"),
            os.path.join(user_data_dir, "Default", "DawnCache"),
            os.path.join(user_data_dir, "Default", "DawnGraphiteCache"),
            os.path.join(user_data_dir, "Default", "DawnWebGPUCache"),
            os.path.join(user_data_dir, "Default", "Service Worker", "CacheStorage"),
            os.path.join(user_data_dir, "Default", "Media Cache"),
            os.path.join(user_data_dir, "GrShaderCache"),
            os.path.join(user_data_dir, "ShaderCache"),
        ]
        for p in targets:
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
            except Exception:
                # 清理失败不影响浏览器启动
                pass

        # 这类文件不影响登录态，但可减少站点缓存/状态噪音
        files = [
            os.path.join(user_data_dir, "Default", "Network Action Predictor"),
            os.path.join(user_data_dir, "Default", "Network Action Predictor-journal"),
        ]
        for f in files:
            try:
                if os.path.isfile(f):
                    os.remove(f)
            except Exception:
                pass

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
        """仅列出仍存活的上下文；已手动关闭的条目由下次 open_session 时从缓存剔除。"""
        out: List[Dict[str, Any]] = []
        for key, ctx in list(self._contexts.items()):
            if not self._is_context_alive(ctx):
                continue
            try:
                pages = len(ctx.pages)
            except Exception:
                continue
            out.append(
                {
                    "account_key": key,
                    "profile_dir": os.path.join(profiles_root(), key),
                    "open_pages": pages,
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
    ) -> Dict[str, Any]:
        key = validate_account_key(account_key)
        async with self._lock:
            for k in list(self._contexts.keys()):
                c = self._contexts.get(k)
                if c is not None and not self._is_context_alive(c):
                    self._contexts.pop(k, None)

            ctx = self._contexts.get(key)

            if ctx is not None:
                if start_url:
                    try:
                        await self._navigate_one_tab(ctx, start_url)
                    except Exception:
                        self._contexts.pop(key, None)
                        ctx = None
                else:
                    return {
                        "account_key": key,
                        "already_running": True,
                        "profile_dir": profile_dir_for(key),
                        "profiles_root": profiles_root(),
                    }

            if ctx is not None:
                return {
                    "account_key": key,
                    "already_running": True,
                    "profile_dir": profile_dir_for(key),
                    "profiles_root": profiles_root(),
                }

            pw = await self._ensure_playwright()
            udir = profile_dir_for(key)
            launch_kw: Dict[str, Any] = {
                "user_data_dir": udir,
                "channel": "msedge",
                "headless": headless,
                "viewport": {"width": 1280, "height": 800},
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    # 减轻启动时再拉起「上次会话」标签（配合 _navigate_one_tab 收敛）
                    "--disable-session-crashed-bubble",
                    "--disable-infobars",
                ],
            }
            ps = (proxy_server or "").strip()
            if ps:
                launch_kw["proxy"] = {"server": ps}
                # 本地 mitmproxy 动态签发站点证书，未将 mitm CA 导入系统前 Edge 会报 ERR_CERT_AUTHORITY_INVALID
                launch_kw["ignore_https_errors"] = True
            try:
                self._purge_non_auth_cache(udir)
                context = await pw.chromium.launch_persistent_context(**launch_kw)
            except Exception as exc:
                raise RuntimeError(
                    f"启动 Edge 失败（请确认已安装 Microsoft Edge，并已执行 playwright install msedge）: {exc}"
                ) from exc

            self._contexts[key] = context
            if start_url:
                await self._navigate_one_tab(context, start_url)

            return {
                "account_key": key,
                "already_running": False,
                "profile_dir": udir,
                "profiles_root": profiles_root(),
                "proxy_server": ps or None,
            }

    async def close_session(self, account_key: str) -> Dict[str, Any]:
        key = validate_account_key(account_key)
        async with self._lock:
            ctx = self._contexts.pop(key, None)
            if ctx is None:
                return {"account_key": key, "closed": False}
            try:
                if self._is_context_alive(ctx):
                    await ctx.close()
            except Exception:
                pass
            return {"account_key": key, "closed": True}

    async def click_xpath(
        self,
        account_key: str,
        xpath: str,
        *,
        timeout_ms: int = 20000,
    ) -> Dict[str, Any]:
        key = validate_account_key(account_key)
        xp = (xpath or "").strip()
        if not xp:
            raise ValueError("xpath 不能为空")
        async with self._lock:
            ctx = self._contexts.get(key)
            if ctx is None or not self._is_context_alive(ctx):
                raise RuntimeError(f"会话未运行: {key}")
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            locator = page.locator(f"xpath={xp}")
            await locator.first.wait_for(state="visible", timeout=timeout_ms)
            await locator.first.click(timeout=timeout_ms)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            except Exception:
                pass
            return {"account_key": key, "clicked": True, "xpath": xp}

    async def open_new_tab(
        self,
        account_key: str,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 30000,
    ) -> Dict[str, Any]:
        key = validate_account_key(account_key)
        u = (url or "").strip()
        if not u:
            raise ValueError("url 不能为空")
        async with self._lock:
            ctx = self._contexts.get(key)
            if ctx is None or not self._is_context_alive(ctx):
                raise RuntimeError(f"会话未运行: {key}")
            page = await ctx.new_page()
            await page.goto(u, wait_until=wait_until, timeout=timeout_ms)
            return {"account_key": key, "opened": True, "url": u}

    async def shutdown(self) -> None:
        async with self._lock:
            for key in list(self._contexts.keys()):
                ctx = self._contexts.pop(key, None)
                if ctx is not None:
                    try:
                        await ctx.close()
                    except Exception:
                        pass
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
