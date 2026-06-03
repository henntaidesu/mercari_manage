# -*- coding: utf-8 -*-
"""wait-shipping: post-ship confirm + finalize"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Dict, Optional
from .....db_manage.models.todo_item import TodoItemModel
from .....web_drive.core.manager import get_web_drive_manager
from .....web_drive.core.mitm_session import mitm_automation_browser
from .....web_drive.core.paths import mercari_account_key
from ....sync.sync_progress import make_sync_reporter
from .._common import _is_wait_shipping_todo
from .._ui import _click_visible_button_by_text
from .qr_scan import _SCAN_OK_TEXT

log = logging.getLogger(__name__)


# 確認用チェックボックスのラベル候補（シール/専用箱など発送方法で文言が変わるため複数許容）
_SHIP_CONFIRM_CHECKBOX_TEXTS = (
    "ご依頼主様控えを切り取りました",
    "梱包した商品に発送用シールを貼りました",
)

_NOTIFY_SHIP_BUTTON_TEXT = "商品を発送したので、発送通知をする"

_SHIPPED_CONFIRM_BUTTON_TEXT = "発送しました"

# 二次确认後、页面が再読込され発送完了になると表示される文言
_SHIP_SUCCESS_TEXT = "購入者の受取をお待ちください"

async def read_post_shipping_confirm_info(todo_id: int) -> Dict[str, Any]:
    """QR 読み取り成功後、交易ページに表示される確認情報を読み取って返す。

    返り値:
      - ``ok``: 「読み取りが正しく完了しました」が表示されているか
      - ``confirm_code``: ポスト発送確認符号（例: BE08TF）
      - ``tracking_no``: 追跡番号（例: 647528803213）
    """
    todo = TodoItemModel.find_by_id(id=int(todo_id))
    if not todo:
        raise ValueError(f"待办事项 id={todo_id} 不存在")
    aid = int(todo.account_id)
    mgr = get_web_drive_manager()
    auto_key = mercari_account_key(aid)
    try:
        page = await mgr.active_tab_page(auto_key)
    except Exception as exc:
        raise RuntimeError("浏览器未打开或已关闭") from exc

    # SPA 再描画待ち（スキャン直後に取ると未反映の場合がある）
    text = ""
    for _ in range(12):
        try:
            text = await page.inner_text("body")
        except Exception:
            text = ""
        if _SCAN_OK_TEXT in text or "発送確認符号" in text or "追跡番号" in text:
            break
        await asyncio.sleep(0.4)

    ok = _SCAN_OK_TEXT in text
    confirm_code = None
    m = re.search(r"発送確認符号[\s:：]*([A-Za-z0-9]+)", text)
    if m:
        confirm_code = m.group(1)
    tracking_no = None
    m = re.search(r"追跡番号[\s:：]*([0-9\-]+)", text)
    if m:
        tracking_no = m.group(1)

    log.info(
        "[postship] 読み取り情報 ok=%s code=%s tracking=%s todo=%s",
        ok, confirm_code, tracking_no, todo_id,
    )
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "ok": ok,
        "confirm_code": confirm_code,
        "tracking_no": tracking_no,
    }

async def _tick_ship_confirm_checkboxes(page: Any) -> int:
    """発送確認ページのチェックボックスにチェックを入れる（複数文言・構造に対応）。

    1) ラベル文言を含む要素の祖先 ``<label>`` をクリック（無ければその要素を直接クリック）
    2) 取りこぼした ``input[type=checkbox]`` を force でチェック
    戻り値: チェック/クリックできた数。
    """
    ticked = 0
    for label_text in _SHIP_CONFIRM_CHECKBOX_TEXTS:
        try:
            loc = page.get_by_text(label_text, exact=False)
            if await loc.count() == 0:
                continue
        except Exception:
            continue
        clicked = False
        # チェックボックスの toggle 範囲＝<label>。あればそれをクリック
        try:
            lbl = loc.first.locator("xpath=ancestor-or-self::label[1]")
            if await lbl.count() > 0:
                await lbl.first.click(timeout=3000)
                clicked = True
        except Exception:
            clicked = False
        if not clicked:
            try:
                await loc.first.click(timeout=3000)
                clicked = True
            except Exception:
                clicked = False
        if clicked:
            ticked += 1
            log.info("[postship] チェック「%s」", label_text)
            await asyncio.sleep(0.2)

    # 取りこぼし対策：未チェックの checkbox を force でチェック
    try:
        cbs = page.locator('input[type="checkbox"]')
        cnt = await cbs.count()
        for i in range(cnt):
            cb = cbs.nth(i)
            try:
                if not await cb.is_checked():
                    await cb.check(force=True, timeout=1500)
                    ticked += 1
                    log.info("[postship] force-checked checkbox[%d]", i)
            except Exception:
                pass
    except Exception:
        pass
    return ticked

async def _has_tracking_number(page: Any, *, body_text: Optional[str] = None) -> bool:
    """交易页是否出现「送り状番号」(发货后才有的追跡番号)。

    らくらくメルカリ便で「発送通知をする」→ 再読込後に「送り状番号」が表示される＝発送成功。
    优先用稳定的 ``data-partner-id="tracking-number"`` 元素；回落到正文文本匹配。
    """
    try:
        loc = page.locator('[data-partner-id="tracking-number"]')
        if await loc.count() > 0 and await loc.first.is_visible():
            return True
    except Exception:
        pass
    try:
        text = body_text if body_text is not None else await page.inner_text("body")
        return "送り状番号" in (text or "")
    except Exception:
        return False

async def finalize_post_shipping(
    todo_id: int,
    *,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """ユーザーの二次確認後：確認チェック → 発送通知 → 「発送しました」を順にクリック。"""
    report = make_sync_reporter(progress_job_id)
    report("resolve_todo", "正在准备发货确认…")
    todo = TodoItemModel.find_by_id(id=int(todo_id))
    if not todo:
        raise ValueError(f"待办事项 id={todo_id} 不存在")
    aid = int(todo.account_id)
    item_id = (todo.item_id or "").strip()
    if not item_id:
        raise ValueError("该待办无关联 item_id，无法打开交易页")
    url = f"https://jp.mercari.com/transaction/{item_id}"

    # 点「确认发送」不依赖已打开的浏览器：mitm_automation_browser 已开则复用并 reload
    # 到交易页，未开则自动启动（待发货走有头）；退出不关闭，保持持久化浏览器。
    is_wait_shipping = _is_wait_shipping_todo(todo)
    headless_override = False if is_wait_shipping else None
    minimized_override = False if is_wait_shipping else None
    report("open_browser", f"正在打开交易页（{item_id}）…")
    ticked = 0
    confirmed = False
    shipped_ok = False
    success_signal = ""
    async with mitm_automation_browser(
        aid,
        start_url=url,
        headless=headless_override,
        minimized=minimized_override,
    ) as (mgr, auto_key):
        page = await mgr.active_tab_page(auto_key)

        # ── Step 1: 確認チェックボックスにチェック（「ご依頼主様控えを切り取りました」等） ──
        report("check_confirm", "正在勾选确认项…")
        ticked = await _tick_ship_confirm_checkboxes(page)
        if ticked == 0:
            log.warning(
                "[postship] 確認チェックボックスが見つからず（当前 URL: %s）。"
                "そのまま発送通知ボタンを試行します。",
                page.url,
            )
        await asyncio.sleep(0.2)

        # ── Step 2: 「商品を発送したので、発送通知をする」 ──
        report("click_notify", "正在点击「発送通知をする」…")
        if not await _click_visible_button_by_text(page, _NOTIFY_SHIP_BUTTON_TEXT, timeout_ms=8000):
            raise RuntimeError(
                f"未找到/未能点击「{_NOTIFY_SHIP_BUTTON_TEXT}」按钮（当前 URL: {page.url}）"
            )
        log.info("[postship] 点击「%s」", _NOTIFY_SHIP_BUTTON_TEXT)

        # ── Step 3: 二次确认ダイアログ「発送しました」 ──
        # 通知ボタン押下後にモーダルが開く。アニメーション完了を待ってから、
        # 可視・有効なボタンだけをクリック（非表示の複製を踏まないように）
        report("click_shipped", "正在点击二次确认「発送しました」…")
        await asyncio.sleep(0.6)
        confirmed = await _click_visible_button_by_text(
            page, _SHIPPED_CONFIRM_BUTTON_TEXT, timeout_ms=8000,
        )
        if confirmed:
            log.info("[postship] 点击二次确认「%s」 完成发货通知", _SHIPPED_CONFIRM_BUTTON_TEXT)
        else:
            log.warning(
                "[postship] 二次确认「%s」按钮未出现/未能点击。URL: %s",
                _SHIPPED_CONFIRM_BUTTON_TEXT, page.url,
            )

        # ── Step 4: 数据発送＋页面再読込を待つ。発送成功の判定 ──
        #   - ゆうゆう/汎用：「購入者の受取をお待ちください」が出れば成功
        #   - らくらくメルカリ便：発送通知後にページ再読込で「送り状番号」(ヤマト追跡番号)が
        #     表示されれば成功（発送前は出ない）。data-partner-id="tracking-number" を優先。
        report("waiting_reload", "已发送，正在等待页面刷新与发送完成…")
        await asyncio.sleep(3)  # クリック後の送信・再読込待ち（要件）
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                text = await page.inner_text("body")
            except Exception:
                text = ""
            if _SHIP_SUCCESS_TEXT in text:
                shipped_ok = True
                success_signal = _SHIP_SUCCESS_TEXT
                break
            # らくらくメルカリ便：送り状番号(追跡番号)が出れば発送完了とみなす
            if await _has_tracking_number(page, body_text=text):
                shipped_ok = True
                success_signal = "送り状番号"
                break
            await asyncio.sleep(0.5)
        if shipped_ok:
            log.info("[postship] 检测到成功标志「%s」 发送成功 todo=%s", success_signal, todo_id)
        else:
            log.warning(
                "[postship] 未检测到发送成功标志（购入者受取待ち/送り状番号）(可能仍在处理)。URL: %s",
                page.url,
            )

    # ── Step 5: 成功确认后才软删除本地 todo（列表から消す） ──
    if shipped_ok:
        try:
            todo.is_delete = 1
            todo.synced_at = int(time.time() * 1000)
            todo.save()
            log.info("[postship] 已软删除 todo_id=%s", todo_id)
        except Exception as exc:
            log.warning("[postship] 软删除 todo 失败: %s", exc)

    report("done", "已完成发货通知" if shipped_ok else "已发送（未检测到完成文案）")
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "success": bool(shipped_ok),
        "checkboxes_ticked": ticked,
        "shipped_confirmed": confirmed,
        "shipped_ok": shipped_ok,
    }
