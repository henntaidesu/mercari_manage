# -*- coding: utf-8 -*-
"""
Mercari 单条商品/订单详情 items/get，回填 orders 扩展字段：
  service_fee、carrier_display_name、request_class_display_name、
  shipping_fee（shipping_class.fee）、tracking_no、transaction_evidence_id（transaction_evidence.id）。
  net_income：仅当 shipping_class.fee（快递费）存在且 >0 时计算为
  售价 price − 销售手续费 sales_fee.fee − 快递费；快递费为 0 或缺失时不写入净收益（置 None）。
在 list 同步每条写入后调用 apply_item_info_to_order（含 sync_data.sync_new_data 增量入库）。
"""

import json
from typing import Any, Dict, Optional
from urllib.parse import quote

from ...mercari_req_scheduling import DPOP_FOR_ITEM_INFO, send_request
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


def _tracking_no_from_evidence(te: Any, d: Dict[str, Any]) -> Optional[str]:
    """从 transaction_evidence / data 根节点解析快递单号。"""
    if isinstance(te, dict):
        for key in (
            "tracking_number",
            "tracking_no",
            "carrier_tracking_number",
            "tracking_id",
        ):
            v = te.get(key)
            if v is not None and str(v).strip():
                return str(v).strip()
        for list_key in ("tracking_numbers", "tracking_number_list"):
            nums = te.get(list_key)
            if isinstance(nums, list) and nums:
                first = nums[0]
                if isinstance(first, dict):
                    t = first.get("number") or first.get("tracking_number")
                else:
                    t = first
                if t is not None and str(t).strip():
                    return str(t).strip()
    for key in ("tracking_number", "tracking_no"):
        v = d.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def fetch_item_info(item_id: str, account_id: Optional[int] = None) -> Dict[str, Any]:
    """GET items/get，返回完整 JSON（含 result / data）。"""
    url = build_item_info_url(item_id)
    return send_request("GET", url, account_id=account_id, dpop_for=DPOP_FOR_ITEM_INFO)


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

    sc = d.get("shipping_class") or {}

    carrier_raw = (sc.get("carrier_display_name") or "").strip()
    carrier_display_name: Optional[str] = carrier_raw or None

    rcdn_raw = (sc.get("request_class_display_name") or "").strip()
    request_class_display_name: Optional[str] = rcdn_raw or None

    shipping_fee: Optional[float] = None
    fee_ship = sc.get("fee")
    if fee_ship is not None:
        try:
            shipping_fee = float(fee_ship)
        except (TypeError, ValueError):
            shipping_fee = None

    # 净收益 = 金额 − 手续费 − 快递费；快递费为 0 或缺失时不计算（None）
    net_income: Optional[float] = None
    if shipping_fee is not None and shipping_fee > 0:
        svc = float(fee_f) if fee_f is not None else 0.0
        net_income = price - svc - float(shipping_fee)

    te = d.get("transaction_evidence") or {}
    tracking_no = _tracking_no_from_evidence(te, d)

    transaction_evidence_id: Optional[int] = None
    if isinstance(te, dict) and te.get("id") is not None:
        try:
            transaction_evidence_id = int(te["id"])
        except (TypeError, ValueError):
            transaction_evidence_id = None

    return {
        "service_fee": fee_f,
        "net_income": net_income,
        "carrier_display_name": carrier_display_name,
        "request_class_display_name": request_class_display_name,
        "shipping_fee": shipping_fee,
        "tracking_no": tracking_no,
        "transaction_evidence_id": transaction_evidence_id,
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
    if "net_income" in fields:
        o.net_income = fields["net_income"]
    if fields.get("carrier_display_name"):
        o.carrier_display_name = fields["carrier_display_name"]
    if fields.get("request_class_display_name"):
        o.request_class_display_name = fields["request_class_display_name"]
    if fields.get("shipping_fee") is not None:
        o.shipping_fee = fields["shipping_fee"]
    if fields.get("tracking_no"):
        o.tracking_no = fields["tracking_no"]
    if "transaction_evidence_id" in fields:
        o.transaction_evidence_id = fields["transaction_evidence_id"]

    if not o.save():
        return "save_failed"
    return None
