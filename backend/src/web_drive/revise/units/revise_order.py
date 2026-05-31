# -*- coding: utf-8 -*-
"""
Mercari 在售商品修改：用账号主 profile 经 MITM 打开编辑页，填写「标题/价格/商品说明」
并点击「変更する」提交，完成后打开出品一覧同步本地列表（浏览器由队列空闲超时关闭）。

流程（与删除同模式，cookie 由 Edge 持久化自动维护）：
  1. ``mitm_automation_browser(account_id, start_url=edit_url)`` 进入账号主 profile ``mercari_{id}``
  2. 填写 标题(input[name=name]) / 价格(input[name=price]) / 商品说明(textarea[name=description])
  3. 点击「変更する」(button[data-testid=edit-button]) 提交
  4. 打开出品一覧，MITM 截获 items/get_items 并同步本地
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from ...listing.units.post_to_macket import (
    DEFAULT_ELEMENT_TIMEOUT_MS,
    DEFAULT_PAGE_LOAD_TIMEOUT_MS,
)
from ...delete.units.delete_order import (
    build_sell_edit_url,
    mercari_item_path_segment,
    _page_for_session,
)
from ....use_mercari.sync_progress import make_sync_reporter

log = logging.getLogger(__name__)

NAME_INPUT_SELECTOR = 'input[name="name"]'
PRICE_INPUT_SELECTOR = 'input[name="price"]'
# 可见的说明输入框（排除自动高度镜像用的只读 textarea）
DESC_TEXTAREA_SELECTOR = 'textarea[name="description"]:not([readonly])'
# 「変更する」提交按钮
SUBMIT_BTN_SELECTOR = 'button[data-testid="edit-button"]'


async def _fill_value(page: Any, selector: str, value: str, *, element_timeout_ms: int) -> None:
    """清空并填入输入框（React 受控组件，Playwright fill 会派发 input 事件）。"""
    loc = page.locator(selector).first
    await loc.wait_for(state="visible", timeout=element_timeout_ms)
    await loc.scroll_into_view_if_needed()
    await loc.fill("")
    await loc.fill(value)


async def revise_mercari_item(
    manager: Any,
    account_key: str,
    *,
    item_id: str,
    name: Optional[str] = None,
    price: Optional[int] = None,
    description: Optional[str] = None,
    proxy_server: Optional[str] = None,  # noqa: ARG001 — MITM 由 mitm_automation_browser 统一配置
    page_load_timeout_ms: int = DEFAULT_PAGE_LOAD_TIMEOUT_MS,
    element_timeout_ms: int = DEFAULT_ELEMENT_TIMEOUT_MS,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    使用账号主 profile ``mercari_{id}`` 经 MITM 打开编辑页修改商品并同步在售列表；
    上下文退出后浏览器由 ``account_serial_queue`` 在队列空闲超时后自动关闭。

    仅填写传入的字段（name / price / description 任意组合）。
    ``progress_job_id`` 配合通用 ``sync_progress``：每个阶段写入中文步骤供前端轮询。
    """
    from ...core.manager import EdgeWebDriveManager
    from ...core.mitm_session import mitm_automation_browser
    from ...core.paths import mercari_account_key, mercari_id_from_account_key
    from ....use_mercari.get_order.get_on_sale.on_sale_list import (
        LISTINGS_PAGE_URL,
        sync_on_sale_from_listings_browser_page,
    )
    from ....use_mercari.sync_data import _resolve_account_and_seller
    from ....ssl_mitm_proxy.capture_config import clear_on_sale_list_response_file

    report = make_sync_reporter(progress_job_id)

    if not isinstance(manager, EdgeWebDriveManager):
        raise TypeError("manager 须为 EdgeWebDriveManager 实例")

    seg = mercari_item_path_segment(item_id)
    if not seg:
        raise ValueError("item_id 不能为空")

    account_id = mercari_id_from_account_key(account_key)
    if account_id is None:
        raise ValueError(f"无效的 account_key: {account_key}")

    name_val = (name or "").strip()
    desc_val = description if description is not None else None
    price_val: Optional[int] = None
    if price is not None:
        try:
            price_val = int(price)
        except (TypeError, ValueError):
            price_val = None

    if not name_val and desc_val is None and price_val is None:
        raise ValueError("没有需要修改的字段")

    report("resolve_account", "正在准备煤炉账号…")
    _aid, seller_id = _resolve_account_and_seller(account_id)
    seller_key = str(int(seller_id))
    auto_key = mercari_account_key(account_id)
    edit_url = build_sell_edit_url(item_id)

    clear_on_sale_list_response_file(seller_key)

    log.info(
        "[revise_mercari_item] account=%s auto=%s item=%s url=%s",
        account_key,
        auto_key,
        seg,
        edit_url,
    )

    result: Dict[str, Any] = {
        "account_key": account_key,
        "browser_key": auto_key,
        "item_id": seg,
        "edit_url": edit_url,
        "filled": [],
        "revise_confirmed": False,
        "sync": None,
        "browser_closed": False,
    }

    report("open_edit_page", f"正在打开编辑页（{seg}）…")
    async with mitm_automation_browser(
        account_id,
        start_url=edit_url,
    ) as (mgr, browser_key):
        page = await _page_for_session(mgr, browser_key)

        try:
            await page.wait_for_load_state("networkidle", timeout=page_load_timeout_ms)
        except Exception:
            try:
                await page.wait_for_load_state(
                    "domcontentloaded", timeout=page_load_timeout_ms
                )
            except Exception:
                pass

        report("fill_form", "正在填写商品信息…")
        if name_val:
            await _fill_value(
                page, NAME_INPUT_SELECTOR, name_val, element_timeout_ms=element_timeout_ms
            )
            result["filled"].append("name")
        if price_val is not None:
            await _fill_value(
                page, PRICE_INPUT_SELECTOR, str(price_val), element_timeout_ms=element_timeout_ms
            )
            result["filled"].append("price")
        if desc_val is not None:
            await _fill_value(
                page, DESC_TEXTAREA_SELECTOR, desc_val, element_timeout_ms=element_timeout_ms
            )
            result["filled"].append("description")

        await page.wait_for_timeout(500)

        capture_since_ms = int(time.time() * 1000)
        report("submit", "正在提交修改「変更する」…")
        submit_btn = page.locator(SUBMIT_BTN_SELECTOR).first
        await submit_btn.wait_for(state="visible", timeout=element_timeout_ms)
        await submit_btn.scroll_into_view_if_needed()
        await submit_btn.click(timeout=element_timeout_ms)
        result["revise_confirmed"] = True

        try:
            await page.wait_for_load_state(
                "domcontentloaded", timeout=page_load_timeout_ms
            )
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        report("sync_listings", "修改已提交，正在打开出品一覧并同步列表…")
        try:
            await page.goto(LISTINGS_PAGE_URL, wait_until="domcontentloaded")
        except Exception:
            pass

        sync_stats = await sync_on_sale_from_listings_browser_page(
            mgr,
            browser_key,
            int(seller_id),
            page,
            capture_since_ms=capture_since_ms,
            timeout=max(90, element_timeout_ms // 1000),
        )
        result["sync"] = sync_stats

    result["browser_closed"] = True
    report("done", "修改完成并已同步列表")
    log.info(
        "[revise_mercari_item] 完成并已关闭浏览器 account=%s item=%s filled=%s",
        account_key,
        seg,
        result["filled"],
    )
    return result
