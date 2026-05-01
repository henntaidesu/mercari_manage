# -*- coding: utf-8 -*-
"""
Mercari 单条商品/订单详情 items/get，回填 orders 扩展字段：
  service_fee（手续费）、net_income（收益）、shipping_type（快递类型）、tracking_no（快递单号）。

在 list 同步每条写入后调用 apply_item_info_to_order。
"""

import json
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ...mercari_req_scheduling import send_request
from ....db_manage.models.order import OrderModel

_ITEM_GET_PATH = "https://api.mercari.jp/items/get"
_ITEM_GET_QUERY = (
    "include_auction=false"
    "&include_campaign_achievement_status=false"
    "&include_donation=true"
    "&include_impboost=false"
    "&include_item_attributes=false"
    "&include_item_attributes_sections=false"
    "&include_non_ui_item_attributes=false"
    "&include_offer_coupon_display=false"
    "&include_offer_like_coupon_display=false"
    "&include_product_page_component=false"
)


def build_item_info_url(item_id: str) -> str:
    qid = quote(str(item_id).strip(), safe="")
    return f"{_ITEM_GET_PATH}?id={qid}&{_ITEM_GET_QUERY}"


def _mercari_response_ok(resp: Any) -> bool:
    """判定 items/get 等业务响应是否成功（兼容无 result 字段、大小写）。"""
    if not isinstance(resp, dict):
        return False
    rc = resp.get("result")
    if rc is None:
        return isinstance(resp.get("data"), dict)
    return str(rc).strip().upper() == "OK"


def _mercari_error_hint(resp: Any) -> str:
    if not isinstance(resp, dict):
        return str(resp)[:220]
    try:
        return json.dumps(resp, ensure_ascii=False)[:260]
    except Exception:
        return str(resp)[:220]


def fetch_item_info(item_id: str, account_id: Optional[int] = None) -> Dict[str, Any]:
    """GET items/get，返回完整 JSON（含 result / data）。"""
    url = build_item_info_url(item_id)
    return send_request("GET", url, account_id=account_id)


def extract_order_info_fields(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 items/get 响应中解析写入 orders 的扩展字段。
    data 为接口里的 data 节点（商品详情对象）。
    """
    d = response.get("data")
    if not isinstance(d, dict):
        return {}

    price = float(d.get("price") or 0)
    sf = d.get("sales_fee") or {}
    fee_raw = sf.get("fee")
    fee_f: Optional[float] = None
    if fee_raw is not None:
        try:
            fee_f = float(fee_raw)
        except (TypeError, ValueError):
            fee_f = None

    net_income: Optional[float] = None
    if fee_f is not None:
        net_income = price - fee_f

    sm = d.get("shipping_method") or {}
    sc = d.get("shipping_class") or {}
    parts: List[str] = []
    n1 = (sm.get("name") or "").strip()
    n2 = (sc.get("name") or "").strip()
    if n1:
        parts.append(n1)
    if n2 and n2 != n1:
        parts.append(n2)
    shipping_type = " / ".join(parts) if parts else None

    te = d.get("transaction_evidence") or {}
    tracking_raw = (
        te.get("tracking_number")
        or te.get("tracking_no")
        or d.get("tracking_number")
        or d.get("tracking_no")
    )
    tracking_no: Optional[str] = None
    if tracking_raw is not None and str(tracking_raw).strip():
        tracking_no = str(tracking_raw).strip()

    return {
        "service_fee": fee_f,
        "net_income": net_income,
        "shipping_type": shipping_type,
        "tracking_no": tracking_no,
    }


def apply_item_info_to_order(item_id: str, account_id: Optional[int] = None) -> Optional[str]:
    """
    拉取 items/get 并将扩展字段写入已存在的订单（order_no == item_id）。
    :return: 成功返回 None；失败返回简短错误说明（供统计）。
    """
    item_id = str(item_id or "").strip()
    if not item_id:
        return "empty_item_id"

    try:
        resp = fetch_item_info(item_id, account_id=account_id)
    except Exception as exc:
        return f"request:{exc}"

    if not _mercari_response_ok(resp):
        return f"api:{_mercari_error_hint(resp)}"

    fields = extract_order_info_fields(resp)
    rows = OrderModel.find_all(where="[order_no] = ?", params=(item_id,), limit=1)
    if not rows:
        return "order_not_found"

    o = rows[0]
    if fields.get("service_fee") is not None:
        o.service_fee = fields["service_fee"]
    if fields.get("net_income") is not None:
        o.net_income = fields["net_income"]
    if fields.get("shipping_type"):
        o.shipping_type = fields["shipping_type"]
    if fields.get("tracking_no"):
        o.tracking_no = fields["tracking_no"]

    if not o.save():
        return "save_failed"
    return None
