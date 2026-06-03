# -*- coding: utf-8 -*-
"""fetch_transaction_detail main flow (shared by wait-shipping/wait-reply + precache)"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional
from ....db_manage.database import DatabaseManager
from ....db_manage.models.todo_item import TodoItemModel
from ....ssl_mitm_proxy.capture_config import clear_shipping_info_response_file, clear_transaction_messages_response_file
from ....web_drive.core.mitm_session import mitm_automation_browser
from ...sync.sync_progress import make_sync_reporter
from ._cache import _clear_qr_image, _persist_transaction_detail
from ._captures import _wait_for_both_captures
from ._common import _WAIT_REPLY_KINDS, _is_wait_shipping_todo, _parse_messages, _parse_shipping_info
from ._qr_facility import _extract_shipping_facility, _qr_code_exists, _save_qr_code_image

log = logging.getLogger(__name__)


async def fetch_transaction_detail(
    todo_id: int,
    *,
    progress_job_id: Optional[str] = None,
    force_headless: bool = False,
) -> Dict[str, Any]:
    """打开有头浏览器到 transaction 页 → MITM 等两个 API → 解析返回。

    ``force_headless``：批量预缓存（「从煤炉同步」后为无缓存的待发货待办补抓详情）场景用。
    待发货待办默认强制有头+前台可见，便于用户手动核对；但同步时若逐条弹出前台浏览器
    会非常干扰，故此参数为 True 时即便待发货也静默无头运行。
    """
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
    if force_headless:
        # 同步后的批量预缓存：即便待发货也静默无头，避免逐条弹出前台浏览器
        headless_override = True
        minimized_override = True
    else:
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
        # 同步发货码（QR 二维码 / らくらく×セブン等返回的条形码，二者通用同一处理）：
        # 交易页若带发货码（含在 App/其他平台已完成发货）→ 抓取保存；
        # 若页面确无发货码（别处取消/重置了发货）→ 后续清除本地已存的，回到选择发送状态。
        synced_qr_url: Optional[str] = None
        synced_facility: Dict[str, str] = {}
        qr_checked = False
        qr_present = False
        try:
            qr_page = await mgr.active_tab_page(main_key)
            qr_present = await _qr_code_exists(qr_page, timeout=3000)
            qr_checked = True
            if qr_present:
                synced_qr_url = await _save_qr_code_image(
                    qr_page, item_id=item_id, todo_id=int(todo_id), timeout=1500
                )
                # 同步「発送場所」信息（标题/说明/图标），供前端在发货码旁展示
                synced_facility = await _extract_shipping_facility(qr_page)
        except Exception as exc:
            log.debug("[txdetail] 同步发货二维码失败 todo_id=%s: %s", todo_id, exc)

    if shipping is None and messages is None:
        log.warning("[txdetail] 两个 API 均未截获 todo_id=%s", todo_id)
    elif shipping is None:
        log.warning("[txdetail] shipping/get_info 未截获 todo_id=%s", todo_id)
    elif messages is None:
        log.warning("[txdetail] transaction_messages/get_messages 未截获 todo_id=%s", todo_id)

    report("parse_response", "正在解析截获的取引详情…")
    shipping_part = _parse_shipping_info(shipping, local_sender_id)
    messages_part = _parse_messages(messages, local_sender_id)

    result = {
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
    # 发货二维码同步：
    #   - 本次抓到 → 用新的
    #   - 页面已加载且确无二维码（别处取消/重置发货）→ 清除本地已存的，回到选择发送状态
    #   - 检查失败/页面未加载（保守）→ 沿用此前已保存的
    page_loaded = (shipping is not None) or (messages is not None)
    if synced_qr_url:
        result["qr_image_url"] = synced_qr_url
        # 发货码存在时，附带本次抓到的发送场所信息（标题/说明/图标）
        if synced_facility:
            result.update(synced_facility)
    elif qr_checked and not qr_present and page_loaded:
        _clear_qr_image(int(todo_id))
        result["qr_image_url"] = None
    else:
        try:
            prev = DatabaseManager().execute_query(
                "SELECT [qr_image_path], [detail_json] FROM [todo_items] WHERE [id]=?",
                (int(todo_id),),
            )
            if prev and prev[0]:
                if prev[0][0]:
                    result["qr_image_url"] = prev[0][0]
                # 保留此前缓存的发送场所信息（_persist_transaction_detail 会整体覆盖）
                if prev[0][1]:
                    try:
                        pd = json.loads(prev[0][1])
                        if isinstance(pd, dict):
                            for k in (
                                "shipping_facility_name",
                                "shipping_facility_desc",
                                "shipping_facility_image_url",
                            ):
                                if pd.get(k) and not result.get(k):
                                    result[k] = pd[k]
                    except Exception:
                        pass
        except Exception:
            pass
    # 缓存有效性判定：只有真正截获到「该类型关键数据」时才写缓存并置 detail_synced_at；
    # 否则跳过——若仍标记为已缓存，则该待办会被永久当作「已缓存的空详情」：前端一直显示
    # 「待抓取」，且 list_uncached_detail_todo_ids 不再返回它，后续「从煤炉同步」批量预缓存
    # 也不会重试。跳过缓存后下次同步会重新抓取。
    #   - 待回复（IncomingMessage）：关键数据是消息流 → 须截获 transaction_messages；
    #   - 其余（含待发货）：截获到 shipping 或 messages 任一即视为本次抓取成功。
    kind = (getattr(todo, "kind", "") or "").strip()
    if kind in _WAIT_REPLY_KINDS:
        capture_ok = messages is not None
    else:
        capture_ok = page_loaded
    if capture_ok:
        _persist_transaction_detail(int(todo_id), result)
    else:
        log.warning(
            "[txdetail] 关键 API 未截获（kind=%s），跳过缓存以便下次同步重试 todo_id=%s",
            kind or "-",
            todo_id,
        )

    report("done", "交易详情已就绪")
    return result
