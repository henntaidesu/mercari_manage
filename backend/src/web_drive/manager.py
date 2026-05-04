# -*- coding: utf-8 -*-
"""
按 account_key 使用独立 user_data_dir 启动 Microsoft Edge（Playwright channel=msedge），
Cookie 与站点数据随目录持久化；不同账号对应不同子浏览器配置目录。
"""

from __future__ import annotations

import asyncio
import os
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

    def list_sessions(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for key, ctx in self._contexts.items():
            try:
                pages = len(ctx.pages) if ctx else 0
            except Exception:
                pages = 0
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
    ) -> Dict[str, Any]:
        key = validate_account_key(account_key)
        async with self._lock:
            if key in self._contexts:
                ctx = self._contexts[key]
                if start_url:
                    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                    await page.goto(start_url, wait_until="domcontentloaded")
                return {
                    "account_key": key,
                    "already_running": True,
                    "profile_dir": profile_dir_for(key),
                    "profiles_root": profiles_root(),
                }

            pw = await self._ensure_playwright()
            udir = profile_dir_for(key)
            try:
                context = await pw.chromium.launch_persistent_context(
                    user_data_dir=udir,
                    channel="msedge",
                    headless=headless,
                    viewport={"width": 1280, "height": 800},
                    args=["--disable-blink-features=AutomationControlled"],
                )
            except Exception as exc:
                raise RuntimeError(
                    f"启动 Edge 失败（请确认已安装 Microsoft Edge，并已执行 playwright install msedge）: {exc}"
                ) from exc

            self._contexts[key] = context
            if start_url:
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(start_url, wait_until="domcontentloaded")

            return {
                "account_key": key,
                "already_running": False,
                "profile_dir": udir,
                "profiles_root": profiles_root(),
            }

    async def close_session(self, account_key: str) -> Dict[str, Any]:
        key = validate_account_key(account_key)
        async with self._lock:
            ctx = self._contexts.pop(key, None)
            if ctx is None:
                return {"account_key": key, "closed": False}
            await ctx.close()
            return {"account_key": key, "closed": True}

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
