# -*- coding: utf-8 -*-
"""
Mercari 在售商品列表：GET items/get_items（status=on_sale,stop 与指定查询参数）。

DPoP：须使用账号 JSON 中 ``dpop_on_sale_list``（``DPOP_FOR_ON_SALE_LIST``），
针对下方 ``build_on_sale_list_url`` 生成的完整 URL（含 GET 方法与查询串）绑定。
"""

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from ...mercari_req_scheduling import DPOP_FOR_ON_SALE_LIST, send_request

_API_BASE = "https://api.mercari.jp/items/get_items"


def build_on_sale_list_url(seller_id: int) -> str:
    """
    与抓包一致的查询参数（seller_id 可变，其余固定）。
    """
    params = {
        "order_by": "desc",
        "seller_id": str(int(seller_id)),
        "sort_type": "updated",
        "status": "on_sale,stop",
        "with_action_hints": "false",
        "with_auction": "true",
        "with_enhanced_hints": "true",
        "with_impression_boost": "true",
        "with_total_item_count": "false",
    }
    return f"{_API_BASE}?{urlencode(params)}"


def fetch_on_sale_list_items(
    seller_id: int,
    account_id: Optional[int] = None,
    timeout: int = 60,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    请求在售列表 API，返回 (data 数组, meta)。

    :raises RuntimeError: HTTP/JSON 错误或 result!=OK
    """
    url = build_on_sale_list_url(seller_id)
    response = send_request(
        "GET",
        url,
        account_id=account_id,
        dpop_for=DPOP_FOR_ON_SALE_LIST,
        timeout=timeout,
    )
    if response.get("result") != "OK":
        raise RuntimeError(f"API 返回异常: {response}")

    items: List[Dict[str, Any]] = response.get("data") or []
    meta: Dict[str, Any] = response.get("meta") or {}
    return items, meta
