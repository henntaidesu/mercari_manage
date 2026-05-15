# -*- coding: utf-8 -*-
"""
Mercari 在售商品删除：打开编辑页并点击删除确认。

流程：
  1. 打开 https://jp.mercari.com/sell/edit/{item_id}
  2. 点击「この商品を削除する」
  3. 二次确认弹窗中点击「削除する」
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .post_to_macket import (
    DEFAULT_ELEMENT_TIMEOUT_MS,
    DEFAULT_PAGE_LOAD_TIMEOUT_MS,
    _click_by_texts,
)

log = logging.getLogger(__name__)

SELL_EDIT_URL_TPL = "https://jp.mercari.com/sell/edit/{item_seg}"

DELETE_ENTRY_TEXT = "この商品を削除する"
DELETE_CONFIRM_TEXT = "削除する"
DELETE_DIALOG_TESTID = "deletion-dialog"
DELETE_DIALOG_ACTION_TESTID = "dialog-action-button"
DELETE_DIALOG_TITLE_TEXT = "この商品を削除しますか？"


def mercari_item_path_segment(item_id: str) -> str:
    """煤炉商品路径段：API 多为 m 开头，纯数字时补 m。"""
    raw = (item_id or "").strip()
    if not raw:
        return ""
    return raw if raw.startswith("m") else f"m{raw}"


def build_sell_edit_url(item_id: str) -> str:
    seg = mercari_item_path_segment(item_id)
    if not seg:
        raise ValueError("item_id 不能为空")
    return SELL_EDIT_URL_TPL.format(item_seg=seg)


async def _click_delete_confirm_in_dialog(
    page: Any,
    *,
    element_timeout_ms: int,
) -> None:
    """
    在二次确认弹窗（data-testid=deletion-dialog）内点击「削除する」。
    优先 [data-testid=dialog-action-button] button，再按弹窗内文案兜底。
    """
    dialog = page.locator(f'[data-testid="{DELETE_DIALOG_TESTID}"]')
    await dialog.wait_for(state="visible", timeout=element_timeout_ms)

    # 可选：确认标题已出现，避免点到其它层叠 UI
    try:
        title_loc = dialog.get_by_text(DELETE_DIALOG_TITLE_TEXT, exact=False).first
        await title_loc.wait_for(state="visible", timeout=element_timeout_ms)
    except Exception:
        log.info("[delete_mercari_item] 未检测到弹窗标题，继续尝试点击确认按钮")

    last_exc: Optional[BaseException] = None
    for factory in (
        lambda: dialog.locator(
            f'[data-testid="{DELETE_DIALOG_ACTION_TESTID}"] button'
        ).first,
        lambda: dialog.get_by_role("button", name=DELETE_CONFIRM_TEXT),
        lambda: dialog.locator(f'button:has-text("{DELETE_CONFIRM_TEXT}")'),
    ):
        try:
            loc = factory()
            await loc.wait_for(state="visible", timeout=element_timeout_ms)
            await loc.scroll_into_view_if_needed()
            await loc.click(timeout=element_timeout_ms)
            log.info(
                "[delete_mercari_item] 已在 deletion-dialog 内点击「%s」",
                DELETE_CONFIRM_TEXT,
            )
            return
        except Exception as exc:
            last_exc = exc
            continue

    raise last_exc if last_exc else RuntimeError(
        f"未在删除确认弹窗内找到「{DELETE_CONFIRM_TEXT}」按钮"
    )


async def delete_mercari_item(
    manager: Any,
    account_key: str,
    *,
    item_id: str,
    proxy_server: Optional[str] = None,
    page_load_timeout_ms: int = DEFAULT_PAGE_LOAD_TIMEOUT_MS,
    element_timeout_ms: int = DEFAULT_ELEMENT_TIMEOUT_MS,
) -> Dict[str, Any]:
    """
    使用 WebDrive 打开商品编辑页并执行删除。
    """
    from ..manager import EdgeWebDriveManager

    if not isinstance(manager, EdgeWebDriveManager):
        raise TypeError("manager 须为 EdgeWebDriveManager 实例")

    seg = mercari_item_path_segment(item_id)
    if not seg:
        raise ValueError("item_id 不能为空")

    edit_url = build_sell_edit_url(item_id)

    ps = (proxy_server or "").strip()
    if not ps:
        try:
            from ...ssl_mitm_proxy.runner import default_mitm_proxy_url

            ps = default_mitm_proxy_url()
        except Exception:
            ps = "http://127.0.0.1:8890"

    log.info("[delete_mercari_item] account=%s item=%s url=%s", account_key, seg, edit_url)

    await manager.open_session(
        account_key,
        headless=False,
        start_url=edit_url,
        proxy_server=ps,
        interactive=True,
    )

    s = manager._prepare_async()
    async with s.lock:  # type: ignore[union-attr]
        ctx = s.contexts.get(account_key)
        if ctx is None or not manager._is_context_alive(ctx):
            raise RuntimeError(f"会话启动失败: {account_key}")
        page = ctx.pages[-1] if ctx.pages else await ctx.new_page()

    try:
        await page.wait_for_load_state("networkidle", timeout=page_load_timeout_ms)
    except Exception:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=page_load_timeout_ms)
        except Exception:
            pass

    result: Dict[str, Any] = {
        "account_key": account_key,
        "item_id": seg,
        "edit_url": edit_url,
        "url_before_delete": page.url,
        "delete_entry_clicked": False,
        "delete_confirmed": False,
        "url_after_delete": None,
    }

    await _click_by_texts(
        page,
        (DELETE_ENTRY_TEXT,),
        element_timeout_ms=element_timeout_ms,
        log_prefix="[delete_mercari_item]",
    )
    result["delete_entry_clicked"] = True

    await _click_delete_confirm_in_dialog(
        page,
        element_timeout_ms=element_timeout_ms,
    )
    result["delete_confirmed"] = True

    # 等待弹窗关闭
    try:
        await page.locator(f'[data-testid="{DELETE_DIALOG_TESTID}"]').wait_for(
            state="hidden",
            timeout=element_timeout_ms,
        )
    except Exception:
        pass

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=page_load_timeout_ms)
    except Exception:
        pass

    try:
        await page.wait_for_url(
            lambda u: "sell/edit" not in (u or "").lower(),
            timeout=element_timeout_ms,
        )
    except Exception:
        log.info("[delete_mercari_item] 删除后未检测到离开编辑页，可能仍停留在当前 URL")

    result["url_after_delete"] = page.url
    log.info(
        "[delete_mercari_item] 完成 account=%s item=%s url_after=%s",
        account_key,
        seg,
        result["url_after_delete"],
    )
    return result
