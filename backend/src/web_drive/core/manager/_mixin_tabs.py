# -*- coding: utf-8 -*-
"""EdgeWebDriveManager 标签页与交互：导航 / 刷新 / 点击 / 新开标签"""
from __future__ import annotations

import asyncio
from typing import Any, Dict
from ..paths import validate_account_key


class _TabsMixin:

    @staticmethod
    async def _navigate_one_tab(
        context: Any,
        start_url: str,
        *,
        wait_until: str = "domcontentloaded",
    ) -> None:
        """只保留一个标签并打开 start_url。

        Edge 持久化 profile 的「继续浏览上次页面」可能在 launch 后异步再开标签，
        仅关掉 pages[1:] 仍会出现两个相同页面；因此需要收敛到单标签。

        注意：不能先关掉全部页面再 new_page。Chromium/Edge 在「0 个标签」状态下
        常会触发 Target.createTarget: Failed to open a new tab。应始终在仍有标签时
        先 new_page，再关闭此前所有页面（不复用旧 Page）。
        """
        pages_before = list(context.pages)
        page = await context.new_page()
        for p in pages_before:
            try:
                await p.close()
            except Exception:
                pass
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


    async def reload_active_tab(
        self,
        account_key: str,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 60000,
    ) -> None:
        """刷新目标会话当前标签页（MITM 等待超时前重试拉取 API）。"""
        key = validate_account_key(account_key)
        u = (url or "").strip()
        if not u:
            return
        s = self._prepare_async()
        async with s.lock:  # type: ignore[union-attr]
            ctx = s.contexts.get(key)
            if ctx is None or not self._is_context_alive(ctx):
                return
            page = ctx.pages[-1] if ctx.pages else await ctx.new_page()
            await page.goto(u, wait_until=wait_until, timeout=timeout_ms)


    async def active_tab_page(self, account_key: str) -> Any:
        """返回会话当前活动标签页（与 ``reload_active_tab`` 选取规则一致）。"""
        key = validate_account_key(account_key)
        s = self._prepare_async()
        async with s.lock:  # type: ignore[union-attr]
            ctx = s.contexts.get(key)
            if ctx is None or not self._is_context_alive(ctx):
                raise RuntimeError(f"会话不可用或无活动页: {key}")
            return ctx.pages[-1] if ctx.pages else await ctx.new_page()


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
        s = self._prepare_async()
        async with s.lock:  # type: ignore[union-attr]
            ctx = s.contexts.get(key)
            if ctx is None or not self._is_context_alive(ctx):
                raise RuntimeError(f"会话未运行: {key}")
            # 始终操作最后打开的标签页：
            # Step2 click → pages[-1]=取引中(open_new_tab后) → 点进交易详情
            # Step4 click → pages[-1]=出品一覧(open_new_tab后) → 点进商品详情
            page = ctx.pages[-1] if ctx.pages else await ctx.new_page()
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
        s = self._prepare_async()
        async with s.lock:  # type: ignore[union-attr]
            ctx = s.contexts.get(key)
            if ctx is None or not self._is_context_alive(ctx):
                raise RuntimeError(f"会话未运行: {key}")
            page = await ctx.new_page()
            await page.goto(u, wait_until=wait_until, timeout=timeout_ms)
            return {"account_key": key, "opened": True, "url": u}
