# -*- coding: utf-8 -*-
"""
Mercari 单笔订单详情：transaction_evidences/get（按 item_id），回填 orders 字段。
  若传入 expected_seller_id，校验 data.seller_id 一致。
  remark <- item_name；description <- description；purchase_time <- created（UTC 存库）；
  承运：shipping_class_carrier_display_name；运费：seller_shipping_fee / buyer_shipping_fee；
  手续费：售价 price 的 10%（自行计算）；净收益：运费合计 > 0 时为 price − 手续费 − 运费。
"""

import datetime
import json
from typing import Any, Dict, Optional
from urllib.parse import quote

from ...mercari_req_scheduling import DPOP_FOR_ITEM_INFO, send_request
from ....db_manage.models.order import OrderModel

_TRANSACTION_EVIDENCE_GET_PATH = "https://api.mercari.jp/transaction_evidences/get"


def build_transaction_evidence_url(item_id: str) -> str:
    qid = quote(str(item_id).strip(), safe="")
    return f"{_TRANSACTION_EVIDENCE_GET_PATH}?_datetime_format=U&item_id={qid}"


def _mercari_response_ok(resp: Any) -> bool:
    """判定业务响应是否成功（兼容无 result 字段、大小写）。"""
    if not isinstance(resp, dict):
        return False
    rc = resp.get("result")
    if rc is None:
        return isinstance(resp.get("data"), dict)
    return str(rc).strip().upper() == "OK"


def _unix_to_utc_str(ts: Any) -> Optional[str]:
    """Unix 秒 -> UTC 存库串 YYYY-MM-DD HH:MM:SS。"""
    try:
        return datetime.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return None


def _mercari_error_hint(resp: Any) -> str:
    if not isinstance(resp, dict):
        return str(resp)
    try:
        return json.dumps(resp, ensure_ascii=False)
    except Exception:
        return str(resp)


def _tracking_no_from_evidence(te: Any, d: Dict[str, Any]) -> Optional[str]:
    """从嵌套 transaction_evidence 或扁平 data 解析快递单号。"""
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


def _float_str_or_num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_item_info(item_id: str, account_id: Optional[int] = None) -> Dict[str, Any]:
    """GET transaction_evidences/get，返回完整 JSON（含 result / data）。"""
    url = build_transaction_evidence_url(item_id)
    return send_request(
        "GET",
        url,
        account_id=account_id,
        dpop_for=DPOP_FOR_ITEM_INFO,
        timeout=60,
    )


def extract_order_info_fields(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 transaction_evidences/get 响应解析写入 orders 的字段。
    data 为取引凭证对象（见 test_json/出售中/info.json）。
    """
    d = response.get("data")
    if not isinstance(d, dict):
        return {}

    price = float(d.get("price") or 0)
    # 手续费：按售价（金额）10% 计算，不用接口 payment_fee
    fee_f: Optional[float] = round(price * 0.1, 2) if price > 0 else None

    carrier_raw = (d.get("shipping_class_carrier_display_name") or "").strip()
    carrier_display_name: Optional[str] = carrier_raw or None

    ss = _float_str_or_num(d.get("seller_shipping_fee"))
    bs = _float_str_or_num(d.get("buyer_shipping_fee"))
    ship_parts = [x for x in (ss, bs) if x is not None]
    shipping_fee: Optional[float] = None
    if ship_parts:
        shipping_fee = sum(ship_parts)

    net_income: Optional[float] = None
    if shipping_fee is not None and shipping_fee > 0 and fee_f is not None:
        net_income = round(price - float(fee_f) - float(shipping_fee), 2)

    te = d.get("transaction_evidence") if isinstance(d.get("transaction_evidence"), dict) else {}
    tracking_no = _tracking_no_from_evidence(te, d)

    transaction_evidence_id: Optional[int] = None
    raw_id = d.get("id")
    if raw_id is not None:
        try:
            transaction_evidence_id = int(raw_id)
        except (TypeError, ValueError):
            transaction_evidence_id = None

    status_val: Optional[str] = None
    st = d.get("status")
    if st is not None and str(st).strip():
        status_val = str(st).strip()

    order_updated_at_str = _unix_to_utc_str(d.get("updated"))
    # 购入时间：取引创建时刻（与前端「购入时间」字段对应）
    purchase_time_str = _unix_to_utc_str(d.get("created"))

    name_raw = d.get("item_name")
    remark_val = str(name_raw).strip() if name_raw is not None else ""

    desc_raw = d.get("description")
    description_val = str(desc_raw).strip() if desc_raw is not None else ""

    buyer_id = d.get("buyer_id")
    customer_name_val = (
        str(int(buyer_id)).strip()
        if buyer_id is not None and str(buyer_id).strip() != ""
        else None
    )

    return {
        "service_fee": fee_f,
        "net_income": net_income,
        "carrier_display_name": carrier_display_name,
        "request_class_display_name": None,
        "shipping_fee": shipping_fee,
        "tracking_no": tracking_no,
        "transaction_evidence_id": transaction_evidence_id,
        "status": status_val,
        "order_updated_at": order_updated_at_str,
        "purchase_time": purchase_time_str,
        "amount": price,
        "remark": remark_val if remark_val else None,
        "description": description_val if description_val else None,
        "customer_name": customer_name_val,
    }


def apply_item_info_to_order(
    item_id: str,
    account_id: Optional[int] = None,
    expected_seller_id: Optional[str] = None,
) -> Optional[str]:
    """
    拉取 transaction_evidences/get 并写入已存在订单（order_no == item_id）。
    expected_seller_id：校验 data.seller_id 与该卖家 ID 一致。
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

    if expected_seller_id is not None:
        exp = str(expected_seller_id).strip()
        if exp:
            dat = resp.get("data")
            if isinstance(dat, dict):
                sid = dat.get("seller_id")
                if sid is None or str(sid).strip() != exp:
                    return "seller_mismatch"

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
    if fields.get("status"):
        o.status = fields["status"]
    if fields.get("order_updated_at"):
        o.order_updated_at = fields["order_updated_at"]
    if fields.get("purchase_time"):
        o.purchase_time = fields["purchase_time"]
    if fields.get("amount") is not None:
        o.amount = float(fields["amount"])
    if fields.get("remark") is not None:
        o.remark = fields["remark"]
    if fields.get("description") is not None:
        o.description = fields["description"]
    if fields.get("customer_name"):
        o.customer_name = fields["customer_name"]

    if not o.save():
        return "save_failed"
    return None
