# -*- coding: utf-8 -*-
"""
Mercari 单件商品详情：GET https://api.mercari.jp/items/get?id=…&include_*=…

HTTP 头 DPoP：须使用账号 JSON 中 ``dpop_item_get_info``（与 transaction_evidences 的 dpop_info 分离），
须针对本模块生成的完整 URL（含查询串）与 GET 方法生成绑定。
"""

from typing import Any, Dict, Optional
from urllib.parse import quote

from ..mercari_req_scheduling import DPOP_FOR_ITEM_GET_INFO, send_request

_ITEM_GET_BASE = "https://api.mercari.jp/items/get"
# 与 App / 测试样例一致的查询参数（顺序固定便于抓包对照）
_ITEM_GET_SUFFIX = (
    "include_auction=true"
    "&include_campaign_achievement_status=false"
    "&include_donation=true"
    "&include_impboost=true"
    "&include_item_attributes=true"
    "&include_item_attributes_sections=true"
    "&include_non_ui_item_attributes=true"
    "&include_offer_coupon_display=true"
    "&include_offer_like_coupon_display=false"
    "&include_product_page_component=true"
)


def build_mercari_item_get_url(item_id: str) -> str:
    raw = str(item_id or "").strip()
    if not raw:
        raise ValueError("item_id 不能为空")
    qid = quote(raw, safe="")
    return f"{_ITEM_GET_BASE}?id={qid}&{_ITEM_GET_SUFFIX}"


def fetch_mercari_item_get(item_id: str, account_id: Optional[int] = None) -> Dict[str, Any]:
    """
    GET items/get，返回完整 JSON（含 result / data）。

    DPoP：仅 ``dpop_item_get_info``；缺失时 ``build_headers`` 抛 ``RuntimeError``。
    """
    url = build_mercari_item_get_url(item_id)
    return send_request(
        "GET",
        url,
        account_id=account_id,
        dpop_for=DPOP_FOR_ITEM_GET_INFO,
        timeout=60,
    )
