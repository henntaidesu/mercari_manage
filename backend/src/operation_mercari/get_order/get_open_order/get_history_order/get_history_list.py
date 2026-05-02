# -*- coding: utf-8 -*-
"""
获取 Mercari 已售完（sold_out）历史订单列表并同步到本地订单管理表。

调用接口:
  GET https://api.mercari.jp/items/get_items
  参数: order_by=desc & seller_id=<seller_id> & sort_type=updated
        & status=sold_out & with_auction=true & with_enhanced_hints=false
        & with_impression_boost=false

数据映射与 get_order_list 相同，复用其 _item_to_order_data / _upsert_order。
"""

from typing import Any, Dict, List, Optional

from ....mercari_req_scheduling import DPOP_FOR_ITEMS_LIST, send_request
from ..get_order_info import apply_item_info_to_order
from ..get_order_list import _item_to_order_data, _upsert_order

_API_URL = "https://api.mercari.jp/items/get_items"
_API_PARAMS = (
    "order_by=desc"
    "&sort_type=updated"
    "&status=sold_out"
    "&with_auction=true"
    "&with_enhanced_hints=false"
    "&with_impression_boost=false"
)


def fetch_and_sync_history_orders(
    seller_id: int,
    account_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    从 Mercari API 获取已售完订单列表，并同步到本地订单管理表（与交易中订单同表）。

    :param seller_id:  Mercari 卖家 ID（从账号配置读取后传入）。
    :param account_id: 指定请求头账号 ID。
    :return: 同步结果统计字典。
    """
    url = f"{_API_URL}?{_API_PARAMS}&seller_id={seller_id}"

    response = send_request(
        "GET", url, account_id=account_id, dpop_for=DPOP_FOR_ITEMS_LIST
    )

    if response.get("result") != "OK":
        raise RuntimeError(f"历史订单 API 返回异常: {response}")

    items: List[Dict[str, Any]] = response.get("data") or []
    meta: Dict[str, Any] = response.get("meta") or {}

    stats = {
        "total": len(items),
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "info_enriched": 0,
        "info_errors": [],
    }

    for item in items:
        try:
            order_data = _item_to_order_data(item, seller_id=seller_id)
            result = _upsert_order(order_data)
            stats[result] += 1
            iid = item.get("id")
            if iid and result in ("inserted", "updated"):
                err = apply_item_info_to_order(str(iid), account_id=account_id)
                if err is None:
                    stats["info_enriched"] += 1
                else:
                    stats["info_errors"].append({"item_id": iid, "error": err})
        except Exception as exc:
            stats["errors"].append({"item_id": item.get("id"), "error": str(exc)})

    stats["has_next"] = meta.get("has_next", False)
    stats["total_item_count"] = meta.get("total_item_count", len(items))

    print(
        f"[history_orders] 同步完成: "
        f"共 {stats['total']} 条, "
        f"新增 {stats['inserted']}, "
        f"更新 {stats['updated']}, "
        f"跳过 {stats['skipped']}, "
        f"错误 {len(stats['errors'])}, "
        f"info 回填 {stats['info_enriched']}, "
        f"info 失败 {len(stats['info_errors'])}"
    )
    if stats["info_errors"]:
        fe = stats["info_errors"][0]
        print(f"  [history_orders] info 失败示例: item_id={fe.get('item_id')!r} -> {fe.get('error')!r}")
    return stats
