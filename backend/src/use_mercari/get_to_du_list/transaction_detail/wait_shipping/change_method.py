# -*- coding: utf-8 -*-
"""wait-shipping: change shipping method / revise after code"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from .....db_manage.models.todo_item import TodoItemModel
from .....web_drive.core.manager import get_web_drive_manager
from .....web_drive.core.mitm_session import mitm_automation_browser
from .....web_drive.core.paths import mercari_account_key
from ....sync.sync_progress import make_sync_reporter
from .._cache import _clear_qr_image
from .._common import _is_wait_shipping_todo

log = logging.getLogger(__name__)


_CHANGE_METHOD_BUTTON_TEXT = "発送方法を変更する"

# /shipping_method 页：配送方式 radio 的 name 与确认按钮文本
_CHANGE_METHOD_RADIO_NAME = "shippingClass"

_CHANGE_METHOD_SUBMIT_TEXT = "変更する"

async def _click_change_method_entry(page: Any, *, timeout_ms: int = 8000) -> bool:
    """点击交易页的「発送方法を変更する」入口。

    この要素は ``<a data-location="...change_shipping_method_button">`` という
    リンク（role=link）であり ``<button>`` ではない。data-location を最優先に、
    link/button/テキストへ順に回落しつつ、可視要素のみをクリックする。
    """
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        candidates = [
            page.locator('[data-location*="change_shipping_method_button"]'),
            page.get_by_role("link", name=_CHANGE_METHOD_BUTTON_TEXT),
            page.get_by_role("button", name=_CHANGE_METHOD_BUTTON_TEXT),
            page.locator(f'a:has-text("{_CHANGE_METHOD_BUTTON_TEXT}")'),
            page.locator(f'button:has-text("{_CHANGE_METHOD_BUTTON_TEXT}")'),
        ]
        for loc in candidates:
            try:
                n = await loc.count()
            except Exception:
                n = 0
            for i in range(n):
                el = loc.nth(i)
                try:
                    if await el.is_visible():
                        await el.scroll_into_view_if_needed(timeout=1500)
                        await el.click()
                        return True
                except Exception:
                    continue
        await asyncio.sleep(0.3)
    return False

async def click_change_shipping_method(
    todo_id: int,
    *,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """点 transaction 页的「発送方法を変更する」（导航到修改发送方式页；后续由用户在浏览器内手动）。"""
    report = make_sync_reporter(progress_job_id)
    report("resolve_todo", "正在准备…")
    todo = TodoItemModel.find_by_id(id=int(todo_id))
    if not todo:
        raise ValueError(f"待办事项 id={todo_id} 不存在")
    aid = int(todo.account_id)
    item_id = (todo.item_id or "").strip()
    if not item_id:
        raise ValueError("该待办无关联 item_id，无法打开交易页")
    url = f"https://jp.mercari.com/transaction/{item_id}"

    # 点「处理」不再自动开浏览器，因此本操作需自行确保浏览器已打开并停在交易页。
    is_wait_shipping = _is_wait_shipping_todo(todo)
    headless_override = False if is_wait_shipping else None
    minimized_override = False if is_wait_shipping else None
    report("open_browser", f"正在打开交易页（{item_id}）…")
    async with mitm_automation_browser(
        aid,
        start_url=url,
        headless=headless_override,
        minimized=minimized_override,
    ) as (mgr, auto_key):
        page = await mgr.active_tab_page(auto_key)

        report("locate_button", "正在定位「発送方法を変更する」…")
        # 注意：交易页的「発送方法を変更する」是 <a> 链接（role=link），不是 <button>。
        # 因此 get_by_role("button") / button:has-text 都匹配不到。优先用稳定的 data-location，
        # 再回落到 link/button/任意可点元素的文本匹配，并做可视+轮询。
        if not await _click_change_method_entry(page):
            raise RuntimeError(
                f"未找到「{_CHANGE_METHOD_BUTTON_TEXT}」入口（当前 URL: {page.url}）"
            )
        report("click_button", "正在点击「発送方法を変更する」…")
        log.info("[shipping] 已点击「%s」 account_id=%s", _CHANGE_METHOD_BUTTON_TEXT, aid)

        # 等待跳转到 /shipping_method 并抓取可选配送方式（radio）
        try:
            await page.wait_for_url("**/shipping_method*", timeout=8000)
        except Exception:
            log.warning("[shipping] /shipping_method への遷移を観測できず (URL: %s)", page.url)
        # 等待配送方式 radio 渲染出现（页面完全加载），最多 5s；再固定停顿 3s 确保
        # SSR 水合/异步渲染完成后再抓取，避免「未获取到可选的配送方式」。
        report("wait_methods", "正在等待配送方式列表加载…")
        try:
            await page.locator(f'input[name="{_CHANGE_METHOD_RADIO_NAME}"]').first.wait_for(
                state="attached", timeout=5000
            )
        except Exception:
            log.warning(
                "[shipping] /shipping_method 配送方式 radio 未在预期时间内出现 (URL: %s)",
                page.url,
            )
        await asyncio.sleep(3.0)
        options = await _scrape_shipping_method_options(page)
        # 首次抓取为空（渲染滞后）则再等待并重试一次
        if not options:
            await asyncio.sleep(1.5)
            options = await _scrape_shipping_method_options(page)
    report("done", "已跳转修改发送方式页")
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "clicked": True,
        "options": options,
    }

# 已发行二维码后修改发货方式：交易页上的「商品サイズや発送方法を修正する」按钮
_REVISE_SLIP_BUTTON_TEXT = "商品サイズや発送方法を修正する"

_REVISE_SLIP_BUTTON_LOCATION = "transaction:publish:change_shipping_button"

async def _click_dialog_change_confirm(page: Any) -> bool:
    """点二次确认弹窗的行动按钮：优先 data-testid，回落 dialog 内「変更する/修正する」文本。"""
    try:
        b = page.locator('[data-testid="dialog-action-button"]')
        await b.first.wait_for(state="visible", timeout=5000)
        await b.first.click()
        return True
    except Exception:
        pass
    for text in (_CHANGE_METHOD_SUBMIT_TEXT, "修正する"):
        try:
            b = page.locator(f'[role="dialog"] button:has-text("{text}")')
            if await b.count() > 0 and await b.first.is_visible():
                await b.first.click()
                return True
        except Exception:
            pass
    return False

async def revise_shipping_after_qr(
    todo_id: int,
    *,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """已发行二维码后修改发货方式：点「商品サイズや発送方法を修正する」→ 二次确认「変更する」
    → 清除已保存的二维码，恢复到可重新选择尺寸/发货方式的状态。"""
    report = make_sync_reporter(progress_job_id)
    report("resolve_todo", "正在准备…")
    todo = TodoItemModel.find_by_id(id=int(todo_id))
    if not todo:
        raise ValueError(f"待办事项 id={todo_id} 不存在")
    aid = int(todo.account_id)
    item_id = (todo.item_id or "").strip()
    if not item_id:
        raise ValueError("该待办无关联 item_id，无法打开交易页")
    url = f"https://jp.mercari.com/transaction/{item_id}"

    is_wait_shipping = _is_wait_shipping_todo(todo)
    headless_override = False if is_wait_shipping else None
    minimized_override = False if is_wait_shipping else None
    report("open_browser", f"正在打开交易页（{item_id}）…")
    async with mitm_automation_browser(
        aid,
        start_url=url,
        headless=headless_override,
        minimized=minimized_override,
    ) as (mgr, auto_key):
        page = await mgr.active_tab_page(auto_key)

        report("locate_revise", "正在定位「商品サイズや発送方法を修正する」…")
        clicked = False
        loc = page.locator(f'[data-location="{_REVISE_SLIP_BUTTON_LOCATION}"] button')
        try:
            await loc.first.wait_for(state="visible", timeout=8000)
            await loc.first.click()
            clicked = True
        except Exception:
            btn = page.get_by_role("button", name=_REVISE_SLIP_BUTTON_TEXT)
            try:
                await btn.first.wait_for(state="visible", timeout=4000)
                await btn.first.click()
                clicked = True
            except Exception:
                btn2 = page.locator(f'button:has-text("{_REVISE_SLIP_BUTTON_TEXT}")')
                try:
                    if await btn2.count() > 0 and await btn2.first.is_visible():
                        await btn2.first.click()
                        clicked = True
                except Exception:
                    pass
        if not clicked:
            raise RuntimeError(
                f"未找到「{_REVISE_SLIP_BUTTON_TEXT}」按钮（当前 URL: {page.url}）"
            )
        log.info("[shipping] 已点击「%s」 account_id=%s", _REVISE_SLIP_BUTTON_TEXT, aid)

        # 二次确认弹窗 → 点「変更する」
        report("confirm_revise", "正在确认「変更する」…")
        await asyncio.sleep(0.4)
        if not await _click_dialog_change_confirm(page):
            log.warning("[shipping] 二次确认「変更する」未出现或已自动提交 (URL: %s)", page.url)
        # 等回到交易页（修正后回到可重新选择尺寸/方式的状态）
        try:
            await page.wait_for_url("**/transaction/*", timeout=8000)
        except Exception:
            pass
        await asyncio.sleep(0.6)

    # 清除已保存的二维码（DB + 本地文件 + detail_json）
    _clear_qr_image(int(todo_id))
    report("done", "已修正发货方式并清除二维码")
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "clicked": True,
        "qr_image_url": None,
    }

async def _scrape_shipping_method_options(page: Any) -> List[Dict[str, Any]]:
    """抓取 /shipping_method 页配送方式 radio 选项（label / value / 是否已选中）。"""
    try:
        opts = await page.evaluate(
            """(name) => {
                const radios = Array.from(document.querySelectorAll('input[name="' + name + '"]'));
                return radios.map((r) => {
                    let label = r.getAttribute('aria-label') || '';
                    if (!label) {
                        const lc = r.closest('label');
                        if (lc) label = (lc.textContent || '').trim();
                    }
                    return {
                        value: r.getAttribute('value') || '',
                        label: label,
                        data_location: r.getAttribute('data-location') || '',
                        checked: r.getAttribute('aria-checked') === 'true' || r.checked === true,
                    };
                });
            }""",
            _CHANGE_METHOD_RADIO_NAME,
        )
        return [o for o in (opts or []) if (o or {}).get("label")]
    except Exception as exc:
        log.debug("[change-method] 配送方式の取得に失敗: %s", exc)
        return []

async def confirm_change_shipping_method(
    todo_id: int,
    method_value: str = "",
    *,
    method_label: str = "",
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """在 /shipping_method 页选中指定配送方式（按 value 优先，回落 aria-label/文本）并点「変更する」。"""
    report = make_sync_reporter(progress_job_id)
    todo = TodoItemModel.find_by_id(id=int(todo_id))
    if not todo:
        raise ValueError(f"待办事项 id={todo_id} 不存在")
    aid = int(todo.account_id)
    mgr = get_web_drive_manager()
    auto_key = mercari_account_key(aid)
    report("attach_browser", "正在连接已打开的浏览器…")
    try:
        page = await mgr.active_tab_page(auto_key)
    except Exception as exc:
        raise RuntimeError("浏览器未打开或已关闭，请先点「処理」打开交易页") from exc

    val = str(method_value or "").strip()
    lbl = str(method_label or "").strip()

    report("select_method", "正在选择配送方式…")
    selected = False
    if val:
        try:
            loc = page.locator(
                f'input[name="{_CHANGE_METHOD_RADIO_NAME}"][value="{val}"]'
            )
            if await loc.count() > 0:
                await loc.first.check(force=True)
                selected = True
        except Exception as exc:
            log.debug("[change-method] value 选中失败: %s", exc)
    if not selected and lbl:
        try:
            loc = page.locator(
                f'input[name="{_CHANGE_METHOD_RADIO_NAME}"][aria-label="{lbl}"]'
            )
            if await loc.count() > 0:
                await loc.first.check(force=True)
                selected = True
        except Exception as exc:
            log.debug("[change-method] aria-label 选中失败: %s", exc)
    if not selected and lbl:
        try:
            await page.get_by_text(lbl, exact=False).first.click()
            selected = True
        except Exception as exc:
            log.debug("[change-method] 文本点击失败: %s", exc)
    if not selected:
        raise RuntimeError("未找到对应的配送方式选项")

    await asyncio.sleep(0.3)
    report("click_submit", "正在点击「変更する」…")
    clicked = False
    submit = page.get_by_role("button", name=_CHANGE_METHOD_SUBMIT_TEXT)
    try:
        if (
            await submit.count() > 0
            and await submit.first.is_visible()
            and await submit.first.is_enabled()
        ):
            await submit.first.click()
            clicked = True
    except Exception as exc:
        log.debug("[change-method] role 按钮点击失败: %s", exc)
    if not clicked:
        sub2 = page.locator(f'button:has-text("{_CHANGE_METHOD_SUBMIT_TEXT}")')
        try:
            await sub2.first.wait_for(state="visible", timeout=3000)
            await sub2.first.click()
            clicked = True
        except Exception as exc:
            raise RuntimeError(f"未找到「{_CHANGE_METHOD_SUBMIT_TEXT}」按钮") from exc

    # 二次确认弹窗：点击第一次「変更する」后会弹出确认 dialog，里面还有一个「変更する」
    # （data-testid="dialog-action-button"），需要再点一次才会真正提交。
    report("confirm_submit", "正在确认「変更する」…")
    try:
        confirm_btn = page.locator('[data-testid="dialog-action-button"]')
        await confirm_btn.first.wait_for(state="visible", timeout=4000)
        await confirm_btn.first.click()
        log.info("[shipping] 已点击二次确认「%s」 account_id=%s", _CHANGE_METHOD_SUBMIT_TEXT, aid)
    except Exception:
        # 回落：在 dialog/footer 区域里按文本找第二个「変更する」
        try:
            dlg_submit = page.locator(
                f'[role="dialog"] button:has-text("{_CHANGE_METHOD_SUBMIT_TEXT}")'
            )
            if await dlg_submit.count() > 0 and await dlg_submit.first.is_visible():
                await dlg_submit.first.click()
                log.info("[shipping] 已点击二次确认（回落） account_id=%s", aid)
        except Exception as exc:
            log.debug("[change-method] 二次确认未出现或已自动提交: %s", exc)

    # 等待回到 transaction 详情页（离开 /shipping_method）
    try:
        await page.wait_for_url("**/transaction/*", timeout=8000)
    except Exception:
        log.warning("[shipping] 変更後 transaction への遷移を観測できず (URL: %s)", page.url)
    log.info("[shipping] 已变更配送方式 value=%s label=%s account_id=%s", val, lbl, aid)
    report("done", "配送方式已变更")
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "success": True,
        "method_value": val,
        "method_label": lbl,
    }
