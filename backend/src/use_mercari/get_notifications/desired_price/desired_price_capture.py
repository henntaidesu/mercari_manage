# -*- coding: utf-8 -*-
"""
打开 jp.mercari.com/item/{item_id}/desired_price 页面，等待 MITM 截获两个响应:

1. ``api.mercari.jp/v2/aggregatedDesiredPriceItems/{item_id}`` -> 降价请求列表
2. ``api.mercari.jp/items/get?id={item_id}`` -> 商品详情(用于补充商品名/价格/图片等)

提供解析函数把两份响应聚合成前端需要的扁平结构。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from functools import partial
from typing import Any, Dict, List, Optional

from ....ssl_mitm_proxy.capture_config import (
    read_aggregated_desired_prices_response,
    read_item_get_response,
)
from ....web_drive.core.manager import EdgeWebDriveManager
from ....web_drive.core.mitm_session import wait_mitm_capture

log = logging.getLogger(__name__)

DESIRED_PRICE_PAGE_URL_TPL = "https://jp.mercari.com/item/{item_id}/desired_price"

_PAGE_TIMEOUT_SEC = 45
_RFC3339_FRAC_RE = re.compile(r"\.(\d+)")


def build_desired_price_page_url(item_id: str) -> str:
    return DESIRED_PRICE_PAGE_URL_TPL.format(item_id=str(item_id).strip())


def _parse_rfc3339_to_ms(raw: Optional[str]) -> Optional[int]:
    s = (raw or "").strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    s = _RFC3339_FRAC_RE.sub(lambda m: "." + m.group(1)[:6], s)
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except (ValueError, OverflowError):
        return None


def _to_int_or_none(val: Any) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        try:
            return int(val)
        except (ValueError, OverflowError):
            return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except (ValueError, OverflowError):
            return None


def extract_primary_offer(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """aggregatedDesiredPriceItems 响应中提取第一条降价请求(主请求)。"""
    if not isinstance(body, dict):
        return None
    arr = body.get("aggregatedDesiredPrices")
    if not isinstance(arr, list) or not arr:
        return None
    first = arr[0]
    if not isinstance(first, dict):
        return None
    buyer = first.get("buyer") if isinstance(first.get("buyer"), dict) else {}
    return {
        "offer_name": (str(first.get("name") or "").strip() or None),
        "offer_type": (str(first.get("type") or "").strip() or None),
        "offered_price": _to_int_or_none(first.get("price")),
        "buyer_id": (str(buyer.get("userId") or "").strip() or None),
        "buyer_username": (str(buyer.get("username") or "").strip() or None),
        "buyer_photo": (str(buyer.get("profileImageUri") or "").strip() or None),
        "buyer_score": _to_int_or_none(buyer.get("score")),
        "buyer_reviews_count": _to_int_or_none(buyer.get("reviewsCount")),
        "create_time": _parse_rfc3339_to_ms(first.get("createTime")),
        "expire_time": _parse_rfc3339_to_ms(first.get("expireTime")),
    }


def extract_item_summary(item_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """items/get 响应 -> 商品基本字段。"""
    if not isinstance(item_body, dict):
        return None
    data = item_body.get("data")
    if not isinstance(data, dict):
        return None
    thumbs = data.get("thumbnails") if isinstance(data.get("thumbnails"), list) else []
    photos = data.get("photos") if isinstance(data.get("photos"), list) else []
    return {
        "item_name": (str(data.get("name") or "").strip() or None),
        "item_photo": (
            thumbs[0] if thumbs else (photos[0] if photos else None)
        ),
        "item_price": _to_int_or_none(data.get("price")),
        "item_status": (str(data.get("status") or "").strip() or None),
        "raw_item_data": data,
    }


def build_offer_list(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """整理完整的 offers 列表给前端展示(多条买家请求时)。"""
    out: List[Dict[str, Any]] = []
    if not isinstance(body, dict):
        return out
    for raw in body.get("aggregatedDesiredPrices") or []:
        if not isinstance(raw, dict):
            continue
        buyer = raw.get("buyer") if isinstance(raw.get("buyer"), dict) else {}
        out.append(
            {
                "name": raw.get("name"),
                "type": raw.get("type"),
                "price": _to_int_or_none(raw.get("price")),
                "create_time_ms": _parse_rfc3339_to_ms(raw.get("createTime")),
                "expire_time_ms": _parse_rfc3339_to_ms(raw.get("expireTime")),
                "buyer_id": buyer.get("userId"),
                "buyer_username": buyer.get("username"),
                "buyer_photo": buyer.get("profileImageUri"),
                "buyer_score": _to_int_or_none(buyer.get("score")),
                "buyer_reviews_count": _to_int_or_none(buyer.get("reviewsCount")),
            }
        )
    return out


async def capture_desired_price_via_mitm_session(
    mgr: EdgeWebDriveManager,
    auto_key: str,
    *,
    item_id: str,
    since_ms: int,
) -> Dict[str, Any]:
    """轮询截获 MITM 写入的 aggregatedDesiredPriceItems 响应,顺带读 items/get。

    调用方需在打开浏览器**之前**先 clear 对应文件并取 ``since_ms=int(time.time()*1000)``。

    返回 dict:
        {
            "desired_price_body": dict,        # aggregatedDesiredPriceItems 响应体
            "items_get_body": dict | None,     # items/get 响应体(已有就附带)
        }
    """
    iid = str(item_id or "").strip()
    if not iid:
        raise ValueError("item_id 不能为空")

    start_url = build_desired_price_page_url(iid)
    data = await wait_mitm_capture(
        mgr=mgr,
        auto_key=auto_key,
        start_url=start_url,
        read_response=partial(read_aggregated_desired_prices_response, iid),
        since_ms=since_ms,
        wait_seconds=_PAGE_TIMEOUT_SEC,
        error_detail=f"v2/aggregatedDesiredPriceItems/{iid}",
    )
    body = data.get("body") if isinstance(data, dict) else None
    if not isinstance(body, dict):
        log.warning("[desired_price] 响应体异常 item_id=%s", iid)
        body = {}

    items_get_payload = read_item_get_response(iid)
    items_get_body: Optional[Dict[str, Any]] = None
    if isinstance(items_get_payload, dict):
        inner = items_get_payload.get("body")
        if isinstance(inner, dict):
            items_get_body = inner

    offers_n = len(body.get("aggregatedDesiredPrices") or [])
    log.info(
        "[desired_price] 抓取完成 item_id=%s offers=%d items_get=%s",
        iid,
        offers_n,
        "yes" if items_get_body else "no",
    )
    return {"desired_price_body": body, "items_get_body": items_get_body}
