# -*- coding: utf-8 -*-
"""
待办事项 →「处理」按钮：打开 https://jp.mercari.com/transaction/<item_id>，
通过 **MITM 抓两个关键 API** 还原交易详情字段（不再做 DOM 爬取）：

- GET ``api.mercari.jp/shipping/get_info?transaction_evidence_id=...``
  → 商品名、发送方法、发送元、shipment 状态
- GET ``api.mercari.jp/transaction_messages/get_messages?item_id=...``
  → 买家·卖家消息流（含用户名、时间）

直接使用账号主 profile ``mercari_{id}`` 打开浏览器（与 /mercari-accounts 「打开浏览器」
一致，登录态由 Edge 持久化 cookie 自动维护，不再用 ``__auto`` 副本 + seed cookie）。
浏览器在抓取后 **保持打开**，方便用户在原生页面上手动操作。
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ...db_manage.models.todo_item import TodoItemModel
from ...ssl_mitm_proxy.capture_config import (
    clear_shipping_info_response_file,
    clear_transaction_messages_response_file,
    read_shipping_info_response,
    read_transaction_messages_response,
)
from ...web_drive.core.manager import EdgeWebDriveManager, get_web_drive_manager
from ...web_drive.core.mitm_session import (
    _raise_login_required_for,
    login_redirect_state_for,
    mitm_automation_browser,
)
from ...web_drive.core.paths import mercari_account_key, mercari_id_from_account_key
from ..get_order.get_in_progress_order.get_order_info import apply_item_info_to_order
from ..sync_progress import make_sync_reporter

log = logging.getLogger(__name__)


# 「待发货」待办：处理时需打开持久化的有头浏览器（前台可见），便于用户在浏览器内
# 亲自核对/操作发货。kind 命中下列集合，或标题为「発送をしてください」即视为待发货。
_WAIT_SHIPPING_KINDS = frozenset(
    {
        "WaitShippingCard",
        "WaitShippingPoint",
        "WaitShippingCarrier",
        "TransactionWaitShippingFunds",
    }
)
_WAIT_SHIPPING_TITLE = "発送をしてください"


def _is_wait_shipping_todo(todo: Any) -> bool:
    kind = (getattr(todo, "kind", "") or "").strip()
    title = (getattr(todo, "title", "") or "").strip()
    return kind in _WAIT_SHIPPING_KINDS or title == _WAIT_SHIPPING_TITLE


# 等待两个 API 都被 MITM 截获的总超时（页面加载 + JS 渲染 + API 往返）
_WAIT_TIMEOUT_SEC = 30
# 期间每隔多少秒重新 navigate 一次（兜底：偶发未触发 API）
_RELOAD_INTERVAL_SEC = 20.0


async def _wait_for_both_captures(
    *,
    mgr: EdgeWebDriveManager,
    auto_key: str,
    start_url: str,
    since_ms: int,
    timeout: int = _WAIT_TIMEOUT_SEC,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """同一轮询循环里等两个文件，避免互相干扰的 reload。

    每次迭代都会检查实时登录跳转监听器是否触发；命中则提前抛
    ``MercariLoginRequiredError``，不再等满 timeout。
    """
    aid_for_login = mercari_id_from_account_key(auto_key)
    deadline = time.monotonic() + timeout
    next_reload = time.monotonic() + _RELOAD_INTERVAL_SEC
    shipping: Optional[Dict[str, Any]] = None
    messages: Optional[Dict[str, Any]] = None
    while time.monotonic() < deadline:
        if aid_for_login is not None and login_redirect_state_for(aid_for_login):
            _raise_login_required_for(aid_for_login)
        if shipping is None:
            d = read_shipping_info_response()
            if d and int(d.get("ts") or 0) >= since_ms:
                shipping = d
        if messages is None:
            d = read_transaction_messages_response()
            if d and int(d.get("ts") or 0) >= since_ms:
                messages = d
        if shipping is not None and messages is not None:
            return shipping, messages
        if time.monotonic() >= next_reload:
            next_reload += _RELOAD_INTERVAL_SEC
            try:
                await mgr.reload_active_tab(auto_key, start_url)
            except Exception as exc:
                log.debug("[txdetail] reload 失败（忽略）：%s", exc)
        await asyncio.sleep(0.35)
    if aid_for_login is not None and login_redirect_state_for(aid_for_login):
        _raise_login_required_for(aid_for_login)
    return shipping, messages


def _compose_sender_address(origin: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(origin, dict):
        return None
    parts: List[str] = []
    postcode = str(origin.get("postcode") or "").strip()
    if len(postcode) == 7:
        parts.append(f"〒{postcode[:3]}-{postcode[3:]}")
    elif postcode:
        parts.append(f"〒{postcode}")
    region_line = "".join(
        [
            str(origin.get("prefecture") or "").strip(),
            str(origin.get("city") or "").strip(),
        ]
    )
    if region_line:
        parts.append(region_line)
    a1 = str(origin.get("address1") or "").strip()
    a2 = str(origin.get("address2") or "").strip()
    if a1:
        parts.append(a1)
    if a2:
        parts.append(a2)
    family = str(origin.get("family_name") or "").strip()
    first = str(origin.get("first_name") or "").strip()
    name = " ".join([s for s in (family, first) if s])
    if name:
        parts.append(f"{name} 様")
    tel = str(origin.get("telephone") or "").strip()
    if tel:
        parts.append(tel)
    return "\n".join(parts) if parts else None


def _parse_shipping_info(payload: Optional[Dict[str, Any]], local_sender_id: Optional[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "product_name": None,
        "shipping_method_name": None,
        "current_shipping_status": None,
        "sender_address": None,
        "shipment_status": None,
        "has_size_location_btn": False,
        "has_change_method_btn": False,
    }
    if not isinstance(payload, dict):
        return out
    body = payload.get("body") or {}
    data = body.get("data") or {}
    if not isinstance(data, dict):
        return out

    # 商品名：优先 data.item.name，回退 data.name（部分接口直接挂在 data 上）
    item = data.get("item") or {}
    if isinstance(item, dict) and item.get("name"):
        out["product_name"] = str(item.get("name")).strip() or None
    elif data.get("name"):
        out["product_name"] = str(data.get("name")).strip() or None

    method = (data.get("shipping_method_name") or "").strip()
    if method:
        out["shipping_method_name"] = method
        out["current_shipping_status"] = f"{method}で発送する"

    shipment = data.get("shipment") or {}
    if isinstance(shipment, dict):
        st = (str(shipment.get("status") or "")).strip().lower()
        if st:
            out["shipment_status"] = st
        # 仅当待发货（fillin / shipping）时才可点这两个按钮
        out["has_change_method_btn"] = st in ("fillin", "shipping")
        out["has_size_location_btn"] = (
            st in ("fillin", "shipping") and bool(shipment.get("is_origin_updatable"))
        )
        out["sender_address"] = _compose_sender_address(shipment.get("origin"))

    return out


def _parse_messages(
    payload: Optional[Dict[str, Any]],
    local_sender_id: Optional[str],
) -> Dict[str, Any]:
    """返回 {messages, buyer_name}"""
    out: Dict[str, Any] = {"messages": [], "buyer_name": None}
    if not isinstance(payload, dict):
        return out
    body = payload.get("body") or {}
    data = body.get("data") or []
    if not isinstance(data, list):
        return out

    buyer_uid: Optional[str] = None
    if local_sender_id:
        buyer_uid = str(local_sender_id).strip() or None

    # 按 created 升序
    items = sorted(
        [m for m in data if isinstance(m, dict)],
        key=lambda m: int(m.get("created") or 0),
    )
    for m in items:
        user = m.get("user") or {}
        uid_raw = m.get("user_id") if m.get("user_id") is not None else user.get("id")
        uid = str(uid_raw).strip() if uid_raw is not None else ""
        is_buyer = bool(buyer_uid) and uid == buyer_uid
        body_text = (m.get("body") or "").strip()
        if not body_text and not user.get("name"):
            continue
        msg_id_raw = m.get("id")
        msg_id = str(msg_id_raw).strip() if msg_id_raw is not None else ""
        reaction = (m.get("reaction") or "").strip()
        out["messages"].append(
            {
                "id": msg_id or None,
                "from": (user.get("name") or "").strip() or None,
                "text": body_text,
                "at": _format_ts(m.get("created")),
                "is_buyer": is_buyer,
                "user_id": uid or None,
                "reaction": reaction or None,
            }
        )
        if is_buyer and not out["buyer_name"]:
            out["buyer_name"] = (user.get("name") or "").strip() or None

    # 兜底：若没拿到买家名，取第一条非空 user.name
    if not out["buyer_name"]:
        for m in out["messages"]:
            if m.get("from"):
                out["buyer_name"] = m["from"]
                break
    return out


def _format_ts(unix_seconds: Any) -> Optional[str]:
    try:
        n = int(unix_seconds)
        if n <= 0:
            return None
        dt = datetime.fromtimestamp(n, tz=timezone.utc).astimezone()
        return dt.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OverflowError):
        return None


async def fetch_transaction_detail(
    todo_id: int,
    *,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """打开有头浏览器到 transaction 页 → MITM 等两个 API → 解析返回。"""
    report = make_sync_reporter(progress_job_id)
    report("resolve_todo", "正在准备煤炉账号…")
    todo = TodoItemModel.find_by_id(id=int(todo_id))
    if not todo:
        raise ValueError(f"待办事项 id={todo_id} 不存在")

    item_id = (todo.item_id or "").strip()
    if not item_id:
        raise ValueError("该待办无关联 item_id，无法打开交易页")

    aid = int(todo.account_id)
    local_sender_id = (todo.sender_id or "").strip() or None
    url = f"https://jp.mercari.com/transaction/{item_id}"
    log.info("[txdetail] 打开交易页 account_id=%s url=%s", aid, url)

    # ── Step 1: 清空 latest 响应文件 + 取 since_ms ──
    clear_shipping_info_response_file()
    clear_transaction_messages_response_file()
    since_ms = int(time.time() * 1000)

    # ── Step 2: 用账号主 profile 经 MITM 打开交易页（与 /orders 更新列表同模式，
    #            cookie 由 Edge 持久化自动维护；浏览器留给后续 followup op 复用，
    #            队列空闲自动关闭由路由层 suppress_idle_close=True 关闭）──
    # 待发货待办：强制有头 + 前台可见的持久化浏览器，便于用户在浏览器内亲自核对发货；
    # 其余类型沿用默认（由 WEB_DRIVE_AUTOMATION_HEADLESS 决定，通常无头静默）。
    is_wait_shipping = _is_wait_shipping_todo(todo)
    headless_override = False if is_wait_shipping else None
    minimized_override = False if is_wait_shipping else None
    if is_wait_shipping:
        log.info("[txdetail] 待发货待办 → 打开有头持久化浏览器 account_id=%s", aid)

    report("open_browser", f"正在打开交易页（{item_id}）…")
    async with mitm_automation_browser(
        aid,
        start_url=url,
        headless=headless_override,
        minimized=minimized_override,
    ) as (mgr, main_key):
        report("wait_captures", "等待 shipping_info 与 transaction_messages 截获…")
        shipping, messages = await _wait_for_both_captures(
            mgr=mgr,
            auto_key=main_key,
            start_url=url,
            since_ms=since_ms,
        )

    if shipping is None and messages is None:
        log.warning("[txdetail] 两个 API 均未截获 todo_id=%s", todo_id)
    elif shipping is None:
        log.warning("[txdetail] shipping/get_info 未截获 todo_id=%s", todo_id)
    elif messages is None:
        log.warning("[txdetail] transaction_messages/get_messages 未截获 todo_id=%s", todo_id)

    report("parse_response", "正在解析截获的取引详情…")
    shipping_part = _parse_shipping_info(shipping, local_sender_id)
    messages_part = _parse_messages(messages, local_sender_id)
    report("done", "交易详情已就绪")

    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "item_id": item_id,
        "url": url,
        "captured": {
            "shipping_info": shipping is not None,
            "transaction_messages": messages is not None,
        },
        **shipping_part,
        **messages_part,
    }


# 取引消息回复 textarea 的 placeholder 在不同代办类型下不一样：
# - 默认（WaitShipping*）：「なにか分からないことがあれば質問してみましょう。」
# - 待回复（IncomingMessage）：「このたびはご購入ありがとうございます。商品の発送まで今しばらくお待ちください。」
# 任一命中即可，所以用 CSS OR 选择器一次抓两个。
_REPLY_TEXTAREA_PLACEHOLDERS = (
    "なにか分からないことがあれば質問してみましょう。",
    "このたびはご購入ありがとうございます。商品の発送まで今しばらくお待ちください。",
)
_REPLY_SEND_BUTTON_TEXT = "取引メッセージを送る"

_REVIEW_TEXTAREA_PLACEHOLDER = "例) このたびはお取引ありがとうございました。"
_REVIEW_SUBMIT_BUTTON_TEXT = "購入者を評価して取引完了する"
_REVIEW_CONFIRM_BUTTON_TEXT = "取引を完了する"
_REVIEW_COMPLETED_TEXT = "取引が完了しました"


async def send_transaction_message(
    todo_id: int,
    text: str,
    *,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """在已开的主 profile 浏览器内填回复并点击「取引メッセージを送る」。

    要求 ``fetch_transaction_detail`` 已先打开过对应账号的交易页（否则会话不存在/不在目标 URL）。
    """
    report = make_sync_reporter(progress_job_id)
    report("resolve_todo", "正在准备发送消息…")
    todo = TodoItemModel.find_by_id(id=int(todo_id))
    if not todo:
        raise ValueError(f"待办事项 id={todo_id} 不存在")
    item_id = (todo.item_id or "").strip()
    if not item_id:
        raise ValueError("该待办无关联 item_id")
    body = (text or "").strip()
    if not body:
        raise ValueError("消息内容不能为空")

    aid = int(todo.account_id)
    mgr = get_web_drive_manager()
    auto_key = mercari_account_key(aid)

    report("attach_browser", "正在连接已打开的浏览器交易页…")
    try:
        page = await mgr.active_tab_page(auto_key)
    except Exception as exc:
        raise RuntimeError("浏览器未打开或已关闭，请先点「处理」打开交易页") from exc

    report("locate_textarea", "正在定位回复输入框…")
    # 找到回复 textarea：按多种 placeholder 取 OR 选择器，谁先可见就用谁
    selector = ", ".join(
        f'textarea[placeholder="{p}"]' for p in _REPLY_TEXTAREA_PLACEHOLDERS
    )
    textarea = page.locator(selector)
    try:
        await textarea.first.wait_for(state="visible", timeout=8000)
    except Exception as exc:
        raise RuntimeError(
            f"未找到回复输入框（placeholder 不匹配任何已知模板；当前 URL: {page.url}）"
        ) from exc

    report("fill_text", "正在填入回复内容…")
    await textarea.first.fill(body)

    report("click_send", "正在点击「取引メッセージを送る」…")
    # 找到「取引メッセージを送る」按钮（按文本）
    btn = page.get_by_role("button", name=_REPLY_SEND_BUTTON_TEXT)
    try:
        await btn.first.wait_for(state="visible", timeout=4000)
    except Exception:
        # fallback：直接 :has-text
        btn = page.locator(f'button:has-text("{_REPLY_SEND_BUTTON_TEXT}")')
        try:
            await btn.first.wait_for(state="visible", timeout=2000)
        except Exception as exc:
            raise RuntimeError(
                f"未找到「{_REPLY_SEND_BUTTON_TEXT}」按钮（当前 URL: {page.url}）"
            ) from exc

    await btn.first.click()
    log.info(
        "[txdetail] 已点击发送消息 account_id=%s item_id=%s text_len=%s",
        aid,
        item_id,
        len(body),
    )

    # 待回复（IncomingMessage）类型：发送即视为待办完成
    # → 等 1.5s 让 send API 落地 → 软删 todo + 关浏览器（不再次刷新）
    kind = (todo.kind or "").strip()
    completed = False
    if kind == "IncomingMessage":
        report("finalize", "已发送，正在收尾并关闭浏览器…")
        await asyncio.sleep(1.5)
        try:
            todo.is_delete = 1
            todo.synced_at = int(time.time() * 1000)
            todo.save()
            log.info("[reply] IncomingMessage 已软删 todo_id=%s", todo_id)
        except Exception as exc:
            log.warning("[reply] 软删 todo 失败: %s", exc)
        try:
            await mgr.close_session(auto_key, force=True)
            log.info("[reply] IncomingMessage 已关闭主浏览器 account_id=%s", aid)
        except Exception as exc:
            log.warning("[reply] 关浏览器失败: %s", exc)
        completed = True

    report("done", "回复已发送")
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "item_id": item_id,
        "sent": True,
        "completed": completed,
        "text_len": len(body),
    }


# ====================================================================
# 选择商品尺寸与发送地
# ====================================================================

_SIZE_SELECT_BUTTON_TEXT = "商品サイズと発送場所を選択する"
_CHANGE_METHOD_BUTTON_TEXT = "発送方法を変更する"
_SELECT_NEXT_BUTTON_TEXT = "選択して次へ"
_SELECT_FINISH_BUTTON_TEXT = "選択して完了する"
# ゆうパケットポスト / ゆうパケットポストmini 完了後、交易ページに出る「2次元コードを読み取る」
_SCAN_QR_BUTTON_TEXT = "2次元コードを読み取る"
# /qr_code_scanner 上の撮影開始ボタン（カメラ無効時は disabled）
_SCAN_START_BUTTON_TEXT = "QRコードをスキャンする"
# 読み取り成功後の交易ページ上の発送確定 UI
_SCAN_OK_TEXT = "読み取りが正しく完了しました"
# 確認用チェックボックスのラベル候補（シール/専用箱など発送方法で文言が変わるため複数許容）
_SHIP_CONFIRM_CHECKBOX_TEXTS = (
    "ご依頼主様控えを切り取りました",
    "梱包した商品に発送用シールを貼りました",
)
_NOTIFY_SHIP_BUTTON_TEXT = "商品を発送したので、発送通知をする"
_SHIPPED_CONFIRM_BUTTON_TEXT = "発送しました"
# 二次确认後、页面が再読込され発送完了になると表示される文言
_SHIP_SUCCESS_TEXT = "購入者の受取をお待ちください"

# ─── 远程摄像头注入 ───────────────────────────────────────────────
# 服务器没有摄像头：在 QR スキャナページに入る前に、navigator.mediaDevices の
# getUserMedia / enumerateDevices を差し替え、canvas.captureStream() を「カメラ」として返す。
# 客户端（管理 UI を開いているユーザー端末）のカメラ映像を window.__pushCameraFrame(dataUrl,w,h)
# で逐次この canvas に描画 → スキャナはあたかもローカルカメラがあるかのように QR を読み取る。
_FAKE_CAMERA_JS = r"""
(() => {
  try {
    if (window.__remoteCamInstalled) return true;
    window.__remoteCamInstalled = true;
    var canvas = document.createElement('canvas');
    canvas.width = 640; canvas.height = 480;
    var ctx = canvas.getContext('2d');
    ctx.fillStyle = '#111'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    var stream = null;
    window.__remoteCamCanvas = canvas;
    window.__pushCameraFrame = function (dataUrl, w, h) {
      try {
        if (!dataUrl) return false;
        var img = new Image();
        img.onload = function () {
          try {
            if (w && h && (canvas.width !== w || canvas.height !== h)) {
              canvas.width = w; canvas.height = h;
            }
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          } catch (e) {}
        };
        img.src = dataUrl;
        return true;
      } catch (e) { return false; }
    };
    function getStream() {
      if (!stream) { stream = canvas.captureStream(30); }
      return stream;
    }
    if (!navigator.mediaDevices) { try { navigator.mediaDevices = {}; } catch (e) {} }
    var md = navigator.mediaDevices;
    if (md) {
      var origGUM = md.getUserMedia ? md.getUserMedia.bind(md) : null;
      md.getUserMedia = function (constraints) {
        if (constraints && constraints.video) {
          try { return Promise.resolve(getStream()); } catch (e) { return Promise.reject(e); }
        }
        return origGUM ? origGUM(constraints) : Promise.reject(new Error('no media'));
      };
      var origEnum = md.enumerateDevices ? md.enumerateDevices.bind(md) : null;
      md.enumerateDevices = function () {
        var fake = { deviceId: 'remote-virtual-cam', kind: 'videoinput', label: 'Remote Camera', groupId: 'remote' };
        fake.toJSON = function () { return this; };
        if (origEnum) {
          return origEnum().then(function (list) {
            var others = (list || []).filter(function (d) { return d.kind !== 'videoinput'; });
            return [fake].concat(others);
          }).catch(function () { return [fake]; });
        }
        return Promise.resolve([fake]);
      };
    }
    return true;
  } catch (e) { return false; }
})();
"""


async def start_select_shipping_class(
    todo_id: int,
    *,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """点 transaction 页的「商品サイズと発送場所を選択する」按钮 → 等浏览器跳到 /shipping_class。

    尺寸列表由前端硬编码（按 shipping_method_name 区分），不再依赖 MITM 抓取。
    """
    report = make_sync_reporter(progress_job_id)
    report("resolve_todo", "正在准备…")
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
        raise RuntimeError("浏览器未打开或已关闭，请先点「处理」打开交易页") from exc

    report("locate_button", "正在定位「商品サイズと発送場所を選択する」按钮…")
    btn = page.get_by_role("button", name=_SIZE_SELECT_BUTTON_TEXT)
    try:
        await btn.first.wait_for(state="visible", timeout=4000)
    except Exception:
        btn = page.locator(f'button:has-text("{_SIZE_SELECT_BUTTON_TEXT}")')
        try:
            await btn.first.wait_for(state="visible", timeout=2000)
        except Exception as exc:
            raise RuntimeError(
                f"未找到「{_SIZE_SELECT_BUTTON_TEXT}」按钮（当前 URL: {page.url}）"
            ) from exc
    report("click_button", "正在点击按钮，等待跳转到 /shipping_class…")
    await btn.first.click()
    log.info("[shipping] 已点击「%s」 account_id=%s", _SIZE_SELECT_BUTTON_TEXT, aid)

    # 等浏览器跳到 /shipping_class（用户后续在我们 dialog 内选 size）
    try:
        await page.wait_for_url("**/shipping_class*", timeout=8000)
    except Exception:
        log.warning("[shipping] 未观察到 /shipping_class 导航（可能已经在该页）")

    report("done", "已进入「商品サイズと発送場所」选择页")
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "clicked": True,
    }


_FACILITY_XPATHS = {
    "post_office": '//*[@id="main"]/div/form/div[1]/div/div[1]/div/div[1]',
    "lawson": '//*[@id="main"]/div/form/div[1]/div/div[1]/div/div[2]',
}


async def _click_scan_qr_and_open_scanner(
    page: Any,
    *,
    item_id: str,
    report,
) -> bool:
    """交易ページに戻った後「2次元コードを読み取る」を押して /qr_code_scanner へ遷移。

    成功で True。ボタンが無い（既に発送済み等）場合は False を返す。
    """
    # 完了する後、交易ページ /transaction/{item_id} に戻るのを待つ
    try:
        await page.wait_for_url("**/transaction/*", timeout=10000)
    except Exception:
        log.warning("[shipping] 完了後に交易ページへ戻る遷移を観測できず (URL: %s)", page.url)
    # SPA 再描画待ち
    await asyncio.sleep(0.6)

    # 远程摄像头注入：服务器无摄像头 → 把「客户端推送的帧」当作本地摄像头喂给 QR スキャナ。
    # ・add_init_script: ハードナビゲーション（新ドキュメント）に効く
    # ・evaluate: SPA ソフトナビ（同一ドキュメント内でルート遷移）に効く
    # スキャナページがマウント時に enumerateDevices を見るため、遷移「前」に仕込む。
    try:
        await page.add_init_script(_FAKE_CAMERA_JS)
    except Exception as exc:
        log.debug("[qrcam] add_init_script 失敗: %s", exc)
    try:
        await page.evaluate(_FAKE_CAMERA_JS)
    except Exception as exc:
        log.debug("[qrcam] evaluate 注入失敗: %s", exc)

    report("click_scan_qr", "正在点击「2次元コードを読み取る」…")
    scan_btn = page.get_by_role("button", name=_SCAN_QR_BUTTON_TEXT)
    try:
        await scan_btn.first.wait_for(state="visible", timeout=6000)
    except Exception:
        scan_btn = page.locator(f'button:has-text("{_SCAN_QR_BUTTON_TEXT}")')
        try:
            await scan_btn.first.wait_for(state="visible", timeout=4000)
        except Exception:
            log.warning(
                "[shipping] 「%s」ボタンが見つからず (URL: %s)",
                _SCAN_QR_BUTTON_TEXT,
                page.url,
            )
            return False
    await scan_btn.first.click()
    log.info("[shipping] 已点击「%s」", _SCAN_QR_BUTTON_TEXT)
    try:
        await page.wait_for_url("**/qr_code_scanner*", timeout=8000)
    except Exception:
        log.warning("[shipping] /qr_code_scanner への遷移を観測できず (URL: %s)", page.url)

    # スキャナ到達後：念のため再注入（ソフトナビ後でも window に効くよう）し、
    # 撮影開始ボタン「QRコードをスキャンする」が有効なら押してカメラを起動させる。
    await asyncio.sleep(0.6)
    try:
        await page.evaluate(_FAKE_CAMERA_JS)
    except Exception:
        pass
    try:
        start_btn = page.get_by_role("button", name=_SCAN_START_BUTTON_TEXT)
        if await start_btn.count() == 0:
            start_btn = page.locator(f'button:has-text("{_SCAN_START_BUTTON_TEXT}")')
        if await start_btn.count() > 0:
            b = start_btn.first
            if await b.is_visible() and await b.is_enabled():
                await b.click()
                log.info("[qrcam] 已点击「%s」启动摄像头", _SCAN_START_BUTTON_TEXT)
    except Exception as exc:
        log.debug("[qrcam] 開始ボタン押下スキップ: %s", exc)
    return True


async def push_remote_camera_frame(
    todo_id: int,
    *,
    frame: str = "",
    width: int = 0,
    height: int = 0,
) -> Dict[str, Any]:
    """客户端摄像头帧 → 注入到有头浏览器的「虚拟摄像头」canvas（QR スキャナ用）。

    返回值同时携带扫描状态，供前端判断是否停止推流：
      - ``on_scanner``: 仍在 /qr_code_scanner（继续推流）
      - ``done``: 已离开扫描页回到 /transaction/（读取成功）
      - ``pushed``: 本帧是否成功写入页面 canvas
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

    url = ""
    try:
        url = (page.url or "").strip()
    except Exception:
        url = ""
    on_scanner = "/qr_code_scanner" in url
    done = (not on_scanner) and "/transaction/" in url

    pushed = False
    if frame and on_scanner:
        try:
            pushed = bool(
                await page.evaluate(
                    "(a) => (typeof window.__pushCameraFrame === 'function')"
                    " ? window.__pushCameraFrame(a.f, a.w, a.h) : false",
                    {"f": frame, "w": int(width or 0), "h": int(height or 0)},
                )
            )
        except Exception as exc:
            log.debug("[qrcam] フレーム注入失敗: %s", exc)

    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "on_scanner": on_scanner,
        "done": done,
        "url": url,
        "pushed": pushed,
    }


async def confirm_shipping_selection(
    todo_id: int,
    class_text: str,
    facility: Optional[str] = None,
    *,
    scan_qr: bool = False,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """在 /shipping_class 页选 size → 次へ → 在 /shipping_facilities 页按需点 facility → 完了する。

    ``facility``：
      - ``None``：不点 facility（用于 POST_BOX 唯一选项的 size，页面会自动选好）
      - ``"post_office"`` / ``"lawson"``：按对应 XPath 点击卡片
    """
    report = make_sync_reporter(progress_job_id)
    report("resolve_todo", "正在准备…")
    todo = TodoItemModel.find_by_id(id=int(todo_id))
    if not todo:
        raise ValueError(f"待办事项 id={todo_id} 不存在")
    aid = int(todo.account_id)
    class_text = (class_text or "").strip()
    if not class_text:
        raise ValueError("class_text 不能为空")
    facility = (facility or "").strip().lower() or None
    if facility is not None and facility not in _FACILITY_XPATHS:
        raise ValueError(f"facility 取值非法：{facility}")

    mgr = get_web_drive_manager()
    auto_key = mercari_account_key(aid)
    report("attach_browser", "正在连接已打开的浏览器…")
    try:
        page = await mgr.active_tab_page(auto_key)
    except Exception as exc:
        raise RuntimeError("浏览器未打开或已关闭") from exc

    # ── Step 1: 按精确文本匹配点击 size ──
    report("select_size", f"正在选择尺寸「{class_text}」…")
    size_loc = page.get_by_text(class_text, exact=True).first
    try:
        await size_loc.wait_for(state="visible", timeout=8000)
    except Exception as exc:
        raise RuntimeError(
            f"未找到尺寸选项「{class_text}」（当前 URL: {page.url}）"
        ) from exc
    await size_loc.click()
    log.info("[shipping] 已选择尺寸「%s」 account_id=%s", class_text, aid)
    await asyncio.sleep(0.2)

    # ── Step 2: 点「選択して次へ」──
    report("click_next", "正在点击「選択して次へ」…")
    next_btn = page.get_by_role("button", name=_SELECT_NEXT_BUTTON_TEXT)
    try:
        await next_btn.first.wait_for(state="visible", timeout=4000)
    except Exception:
        next_btn = page.locator(f'button:has-text("{_SELECT_NEXT_BUTTON_TEXT}")')
        await next_btn.first.wait_for(state="visible", timeout=4000)
    await next_btn.first.click()
    log.info("[shipping] 已点击「%s」 account_id=%s", _SELECT_NEXT_BUTTON_TEXT, aid)

    # ── Step 3: 等浏览器跳到 /shipping_facilities ──
    report("wait_facilities", "等待跳转到 /shipping_facilities…")
    try:
        await page.wait_for_url("**/shipping_facilities*", timeout=10000)
    except Exception:
        log.warning("[shipping] 未观察到 /shipping_facilities 导航 (当前 URL: %s)", page.url)

    # ── Step 4: 按需点 facility 卡片 ──
    if facility is not None:
        report("select_facility", f"正在选择发货地（{facility}）…")
        xpath_expr = _FACILITY_XPATHS[facility]
        fac_loc = page.locator(f"xpath={xpath_expr}")
        try:
            await fac_loc.first.wait_for(state="visible", timeout=8000)
        except Exception as exc:
            raise RuntimeError(
                f"未找到发货地卡片（facility={facility}，XPath={xpath_expr}，当前 URL: {page.url}）"
            ) from exc
        await fac_loc.first.click()
        log.info("[shipping] 已点击发货地 facility=%s", facility)
        await asyncio.sleep(0.2)
    else:
        log.info("[shipping] 无需选择 facility（auto_finish），直接点完了")

    # ── Step 5: 点「選択して完了する」──
    report("click_finish", "正在点击「選択して完了する」…")
    finish_btn = page.get_by_role("button", name=_SELECT_FINISH_BUTTON_TEXT)
    try:
        await finish_btn.first.wait_for(state="visible", timeout=6000)
    except Exception:
        finish_btn = page.locator(f'button:has-text("{_SELECT_FINISH_BUTTON_TEXT}")')
        try:
            await finish_btn.first.wait_for(state="visible", timeout=4000)
        except Exception as exc:
            raise RuntimeError(
                f"未找到「{_SELECT_FINISH_BUTTON_TEXT}」按钮（当前 URL: {page.url}）"
            ) from exc
    await finish_btn.first.click()
    log.info("[shipping] 已点击「%s」 account_id=%s", _SELECT_FINISH_BUTTON_TEXT, aid)

    # ── Step 6: ゆうパケットポスト系は完了後そのまま QR スキャナへ ──
    qr_scanner_open = False
    if scan_qr:
        item_id = (todo.item_id or "").strip()
        qr_scanner_open = await _click_scan_qr_and_open_scanner(
            page, item_id=item_id, report=report,
        )

    report("done", "已完成发货尺寸与发货地选择")
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "class_text": class_text,
        "facility": facility,
        "success": True,
        "qr_scanner_open": qr_scanner_open,
    }


async def capture_qr_scanner_frame(todo_id: int) -> Dict[str, Any]:
    """QR スキャナ（/qr_code_scanner）を開いている有頭ブラウザの現在タブを
    JPEG スクリーンショットで取得し、base64 で返す（管理 UI へミラー表示用）。

    返り値:
      - ``frame``: data URI 文字列（``data:image/jpeg;base64,...``）。取得不可なら None
      - ``on_scanner``: 現在 /qr_code_scanner 上にいるか
      - ``done``: スキャン完了（/qr_code_scanner を離れ /transaction/ に戻った）
      - ``url``: 現在 URL
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

    url = ""
    try:
        url = (page.url or "").strip()
    except Exception:
        url = ""
    on_scanner = "/qr_code_scanner" in url
    # スキャナを開いた後にスキャナを離れて transaction に戻った＝読み取り成功とみなす
    done = (not on_scanner) and "/transaction/" in url

    frame = None
    try:
        import base64

        # 摄像头/取景框のみを切り出す（ページ全体・ヘッダ・余白は不要）。
        # 取れない時のみページ全体にフォールバック。
        shot = None
        for sel in ('[data-testid="qr-code-scanner-from-camera"]', "#video"):
            try:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    shot = await loc.first.screenshot(type="jpeg", quality=55)
                    break
            except Exception:
                continue
        if shot is None:
            shot = await page.screenshot(type="jpeg", quality=55)
        frame = "data:image/jpeg;base64," + base64.b64encode(shot).decode("ascii")
    except Exception as exc:
        log.debug("[qrscan] スクリーンショット取得失敗: %s", exc)

    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "frame": frame,
        "on_scanner": on_scanner,
        "done": done,
        "url": url,
    }


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


async def _click_visible_button_by_text(page: Any, text: str, *, timeout_ms: int = 8000) -> bool:
    """可視かつ有効な「text」ボタンを探してクリック（モーダル内のボタンも対象）。

    role=button → ``button:has-text`` の順で候補を集め、**非表示の複製（portal/template）を
    避けるため可視・有効なものだけ**をクリックする。出現するまで短間隔でポーリング。
    """
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        for loc in (
            page.get_by_role("button", name=text),
            page.locator(f'button:has-text("{text}")'),
        ):
            try:
                n = await loc.count()
            except Exception:
                n = 0
            for i in range(n):
                b = loc.nth(i)
                try:
                    if await b.is_visible() and await b.is_enabled():
                        await b.click()
                        return True
                except Exception:
                    continue
        await asyncio.sleep(0.3)
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
    mgr = get_web_drive_manager()
    auto_key = mercari_account_key(aid)
    report("attach_browser", "正在连接已打开的浏览器…")
    try:
        page = await mgr.active_tab_page(auto_key)
    except Exception as exc:
        raise RuntimeError("浏览器未打开或已关闭") from exc

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

    # ── Step 4: 数据発送＋页面再読込を待つ。「購入者の受取をお待ちください」が出れば成功 ──
    report("waiting_reload", "已发送，正在等待页面刷新与发送完成…")
    await asyncio.sleep(3)  # クリック後の送信・再読込待ち（要件）
    shipped_ok = False
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            text = await page.inner_text("body")
        except Exception:
            text = ""
        if _SHIP_SUCCESS_TEXT in text:
            shipped_ok = True
            break
        await asyncio.sleep(0.5)
    if shipped_ok:
        log.info("[postship] 检测到「%s」 发送成功 todo=%s", _SHIP_SUCCESS_TEXT, todo_id)
    else:
        log.warning(
            "[postship] 未检测到「%s」(可能仍在处理)。URL: %s",
            _SHIP_SUCCESS_TEXT, page.url,
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


async def submit_transaction_review(
    todo_id: int,
    text: str,
    *,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """在已打开的浏览器（取引評価页）填评价文本 + 点「購入者を評価して取引完了する」。

    页面上 ``良かった`` 通常默认选中，不需要再点。
    """
    report = make_sync_reporter(progress_job_id)
    report("resolve_todo", "正在准备评价提交…")
    todo = TodoItemModel.find_by_id(id=int(todo_id))
    if not todo:
        raise ValueError(f"待办事项 id={todo_id} 不存在")
    body = (text or "").strip()
    if not body:
        raise ValueError("评价文本不能为空")

    aid = int(todo.account_id)
    item_id = (todo.item_id or "").strip()
    mgr = get_web_drive_manager()
    auto_key = mercari_account_key(aid)
    report("attach_browser", "正在连接已打开的浏览器…")
    try:
        page = await mgr.active_tab_page(auto_key)
    except Exception as exc:
        raise RuntimeError("浏览器未打开或已关闭，请先点「处理」打开交易页") from exc

    # 找到评价 textarea（按 placeholder）
    report("fill_review", "正在填入评价文本…")
    textarea = page.locator(
        f'textarea[placeholder="{_REVIEW_TEXTAREA_PLACEHOLDER}"]'
    )
    try:
        await textarea.first.wait_for(state="visible", timeout=8000)
    except Exception as exc:
        raise RuntimeError(
            f"未找到评价输入框（placeholder 不匹配；当前 URL: {page.url}）"
        ) from exc
    await textarea.first.fill(body)
    log.info("[review] 已填入评价文本 text_len=%s", len(body))

    # 找到「購入者を評価して取引完了する」按钮
    report("click_submit", "正在点击「購入者を評価して取引完了する」…")
    btn = page.get_by_role("button", name=_REVIEW_SUBMIT_BUTTON_TEXT)
    try:
        await btn.first.wait_for(state="visible", timeout=4000)
    except Exception:
        btn = page.locator(f'button:has-text("{_REVIEW_SUBMIT_BUTTON_TEXT}")')
        try:
            await btn.first.wait_for(state="visible", timeout=2000)
        except Exception as exc:
            raise RuntimeError(
                f"未找到「{_REVIEW_SUBMIT_BUTTON_TEXT}」按钮（当前 URL: {page.url}）"
            ) from exc
    await btn.first.click()
    log.info(
        "[review] 已点击「%s」 account_id=%s",
        _REVIEW_SUBMIT_BUTTON_TEXT,
        aid,
    )

    # 二次确认弹窗：「購入者を評価して取引を完了しますか？」→ 点「取引を完了する」
    report("confirm_dialog", "正在点击二次确认「取引を完了する」…")
    await asyncio.sleep(0.3)
    confirm_btn = page.get_by_role("button", name=_REVIEW_CONFIRM_BUTTON_TEXT)
    try:
        await confirm_btn.first.wait_for(state="visible", timeout=6000)
    except Exception:
        confirm_btn = page.locator(f'button:has-text("{_REVIEW_CONFIRM_BUTTON_TEXT}")')
        try:
            await confirm_btn.first.wait_for(state="visible", timeout=3000)
        except Exception as exc:
            raise RuntimeError(
                f"未找到二次确认按钮「{_REVIEW_CONFIRM_BUTTON_TEXT}」（当前 URL: {page.url}）"
            ) from exc
    await confirm_btn.first.click()
    log.info(
        "[review] 已点击二次确认「%s」 account_id=%s",
        _REVIEW_CONFIRM_BUTTON_TEXT,
        aid,
    )

    # 等页面刷新 + 检测「取引が完了しました」文案
    report("wait_completed", "等待煤炉返回「取引が完了しました」…")
    completed = False
    try:
        completed_loc = page.get_by_text(_REVIEW_COMPLETED_TEXT, exact=False).first
        await completed_loc.wait_for(state="visible", timeout=15000)
        completed = True
        log.info("[review] 检测到「%s」 account_id=%s", _REVIEW_COMPLETED_TEXT, aid)
    except Exception:
        log.warning(
            "[review] 15s 内未检测到「%s」（可能已完成但页面文案变化；当前 URL: %s）",
            _REVIEW_COMPLETED_TEXT,
            page.url,
        )

    order_refresh_error: Optional[str] = None
    if completed:
        report("finalize", "评价完成，正在收尾并刷新订单…")
        # 软删除本地 todo（页面已结案，对应煤炉端 todolist 也会下次同步剔除）
        try:
            todo.is_delete = 1
            todo.synced_at = int(time.time() * 1000)
            todo.save()
            log.info("[review] 已软删除 todo_id=%s", todo_id)
        except Exception as exc:
            log.warning("[review] 软删除 todo 失败: %s", exc)

        # 关浏览器
        try:
            await mgr.close_session(auto_key, force=True)
            log.info("[review] 已关闭主浏览器 account_id=%s", aid)
        except Exception as exc:
            log.warning("[review] 关浏览器失败: %s", exc)

        # 刷新订单信息（按 item_id 等于 order_no 查 orders 表，回填 transaction_evidences 字段）
        if item_id:
            try:
                order_refresh_error = await apply_item_info_to_order(item_id, account_id=aid)
                if order_refresh_error:
                    log.warning("[review] 订单刷新返回错误: %s", order_refresh_error)
                else:
                    log.info("[review] 订单刷新完成 item_id=%s", item_id)
            except Exception as exc:
                order_refresh_error = f"exception:{exc}"
                log.warning("[review] 订单刷新异常: %s", exc)
        else:
            log.warning("[review] todo 无 item_id，跳过订单刷新")

    report("done", "评价已提交")
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "item_id": item_id,
        "submitted": True,
        "confirmed": True,
        "completed": completed,
        "order_refresh_error": order_refresh_error,
        "text_len": len(body),
    }


# ====================================================================
# 取引メッセージのリアクション（emoji 反应）
# ====================================================================

# Mercari 取引メッセージの定型リアクション一覧
# Mercari picker 内 5 个 emoji 是按位置渲染的 ``<button><img/></button>``，没有 aria-label
# 也没有稳定的文本，只能按 ``button:nth-of-type(N)`` 定位。
# ``index`` 与煤炉 picker 的 1-based XPath（button[1]..button[5]）对应：
#   button[1] = 心  / button[2] = 微笑 / button[3] = 笑 / button[4] = 合掌 / button[5] = 祝
SUPPORTED_REACTIONS: Dict[str, Dict[str, Any]] = {
    "heart": {"emoji": "❤️", "index": 0, "label": "好き"},
    "smile": {"emoji": "😊", "index": 1, "label": "笑顔"},
    "laugh": {"emoji": "😆", "index": 2, "label": "笑い"},
    "pray": {"emoji": "🙏", "index": 3, "label": "ありがとう"},
    "party": {"emoji": "🎉", "index": 4, "label": "お祝い"},
}


async def send_message_reaction_by_index(
    todo_id: int,
    reaction_index: int,
    reaction: str,
    *,
    message_id: Optional[str] = None,
    progress_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """按「页面上第 reaction_index 个 add-reaction-button」定位并点击反应表情。

    前端调用时根据 ``messages.filter(is_buyer=true).indexOf(targetMessage)`` 计算 ``reaction_index``。
    """
    report = make_sync_reporter(progress_job_id)
    report("resolve_todo", "正在准备发送反应表情…")
    todo = TodoItemModel.find_by_id(id=int(todo_id))
    if not todo:
        raise ValueError(f"待办事项 id={todo_id} 不存在")
    if reaction_index < 0:
        raise ValueError("reaction_index 不能小于 0")
    reaction_key = (reaction or "").strip().lower()
    if reaction_key not in SUPPORTED_REACTIONS:
        raise ValueError(f"reaction 取值非法：{reaction}（仅支持 {list(SUPPORTED_REACTIONS)}）")
    rinfo = SUPPORTED_REACTIONS[reaction_key]
    emoji_char = rinfo["emoji"]
    emoji_idx = int(rinfo["index"])

    aid = int(todo.account_id)
    mgr = get_web_drive_manager()
    auto_key = mercari_account_key(aid)

    report("attach_browser", "正在连接已打开的浏览器交易页…")
    try:
        page = await mgr.active_tab_page(auto_key)
    except Exception as exc:
        raise RuntimeError("浏览器未打开或已关闭，请先点「处理」打开交易页") from exc

    # ── Step 1: 找到第 reaction_index 个「add-reaction-button」并点击 ──
    # 注：``[data-testid="add-reaction-button"]`` 只在买家消息卡片下渲染，所以这个 N
    # 直接对应「买家消息中第 N 条」，无论页面上买家/卖家消息交错怎样排列都成立。
    report("click_add_reaction", "正在点击「+」反应按钮…")
    add_btns = page.locator('[data-testid="add-reaction-button"]')
    try:
        await add_btns.first.wait_for(state="visible", timeout=6000)
    except Exception as exc:
        raise RuntimeError(
            f"未找到任何「+」反应按钮（可能该交易没有买家消息或页面未加载完；当前 URL: {page.url}）"
        ) from exc
    total = await add_btns.count()
    if reaction_index >= total:
        raise RuntimeError(
            f"reaction_index={reaction_index} 越界（页面共 {total} 个反应按钮）"
        )
    target_btn = add_btns.nth(reaction_index)
    try:
        await target_btn.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass
    await target_btn.click()
    log.info(
        "[reaction] 已点击 add-reaction-button index=%s account_id=%s todo_id=%s",
        reaction_index,
        aid,
        todo_id,
    )

    # ── Step 2: 在同一条消息卡片内定位 picker 的第 emoji_idx 个 emoji 按钮 ──
    # 煤炉的 picker 是 5 个 ``<button><img/></button>``，没有稳定 aria-label
    # 也没有可读文本，只能按位置取。这些 button 都嵌在 ``[data-testid="ds4-comment"]``
    # 卡片内部（XPath: .../div[3]/div/button[N]/img），因此用「卡片祖先 + 直接子级 img」过滤。
    report("pick_emoji", f"正在选择 emoji（{emoji_char}）…")
    await asyncio.sleep(0.3)
    parent_comment = target_btn.locator('xpath=ancestor::*[@data-testid="ds4-comment"][1]')
    # ``button:has(> img)`` 排除掉 add-reaction-button（其子节点是 svg 不是 img）
    # 也排除掉头像（头像是 <a> + <picture><img>，不是 <button>）
    emoji_btns = parent_comment.locator('button:has(> img)')
    try:
        await emoji_btns.first.wait_for(state="visible", timeout=4000)
    except Exception as exc:
        raise RuntimeError(
            f"未找到 emoji picker 按钮（点击「+」后弹出层未出现；当前 URL: {page.url}）"
        ) from exc

    total_emojis = await emoji_btns.count()
    if total_emojis < len(SUPPORTED_REACTIONS):
        log.warning(
            "[reaction] picker emoji 数量不匹配（页面 %s 个 / 预期 %s 个）",
            total_emojis,
            len(SUPPORTED_REACTIONS),
        )
    if emoji_idx >= total_emojis:
        raise RuntimeError(
            f"emoji 索引 {emoji_idx} 越界（picker 共 {total_emojis} 个 emoji）"
        )

    await emoji_btns.nth(emoji_idx).click()
    log.info(
        "[reaction] 已点击 emoji=%s key=%s index=%s account_id=%s",
        emoji_char,
        reaction_key,
        emoji_idx,
        aid,
    )
    await asyncio.sleep(0.5)

    report("done", "反应表情已发送")
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "reaction_index": reaction_index,
        "reaction": reaction_key,
        "emoji": emoji_char,
        "emoji_index": emoji_idx,
        "message_id": message_id,
        "sent": True,
    }


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

    mgr = get_web_drive_manager()
    auto_key = mercari_account_key(aid)
    report("attach_browser", "正在连接已打开的浏览器…")
    try:
        page = await mgr.active_tab_page(auto_key)
    except Exception as exc:
        raise RuntimeError("浏览器未打开或已关闭，请先点「处理」打开交易页") from exc

    report("locate_button", "正在定位「発送方法を変更する」按钮…")
    btn = page.get_by_role("button", name=_CHANGE_METHOD_BUTTON_TEXT)
    try:
        await btn.first.wait_for(state="visible", timeout=4000)
    except Exception:
        btn = page.locator(f'button:has-text("{_CHANGE_METHOD_BUTTON_TEXT}")')
        try:
            await btn.first.wait_for(state="visible", timeout=2000)
        except Exception as exc:
            raise RuntimeError(
                f"未找到「{_CHANGE_METHOD_BUTTON_TEXT}」按钮（当前 URL: {page.url}）"
            ) from exc
    report("click_button", "正在点击「発送方法を変更する」…")
    await btn.first.click()
    log.info("[shipping] 已点击「%s」 account_id=%s", _CHANGE_METHOD_BUTTON_TEXT, aid)
    report("done", "已跳转修改发送方式页")
    return {
        "todo_id": int(todo_id),
        "account_id": aid,
        "clicked": True,
    }
