# -*- coding: utf-8 -*-
"""
获取 Mercari 出售中（trading）订单列表并同步到本地订单管理表。

调用接口:
  GET https://api.mercari.jp/items/get_items
  参数: order_by=desc & seller_id=<seller_id> & sort_type=updated
        & status=trading & with_auction=true & with_enhanced_hints=false
        & with_impression_boost=true & with_total_item_count=true

数据映射（item -> orders 表）:
  order_no         <- item["id"]                    (唯一单号, 如 m12550594804)
  order_date       <- item["created"] Unix 秒（原始时间戳）
  order_updated_at <- item["updated"] Unix 秒（最后更新时间）
  customer_name    <- str(item["buyer"]["id"])      （仅存买家用户 ID）
  data_user        <- str(seller_id)                （卖家用户 ID，与请求参数 seller_id 一致）
  status           <- item["transaction_evidence"]["status"]（如 wait_shipping）
  amount           <- item["price"]
  remark           <- item["name"]                  (商品名称)
  thumbnails       <- item["thumbnails"]            (URL 列表 JSON 存库)
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from ...mercari_req_scheduling import DPOP_FOR_ITEMS_LIST, send_request
from ....db_manage.models.order import OrderModel
from .get_order_info import apply_item_info_to_order

_API_URL = "https://api.mercari.jp/items/get_items"
_API_PARAMS = (
    "order_by=desc"
    "&sort_type=updated"
    "&status=trading"
    "&with_auction=true"
    "&with_enhanced_hints=false"
    "&with_impression_boost=true"
    "&with_total_item_count=true"
)


def _unix_seconds(ts: Any) -> int:
    """API 原始 Unix 秒；解析失败则用当前时间秒。"""
    try:
        return int(ts)
    except (TypeError, ValueError, OSError):
        return int(time.time())


def _norm_thumbnails_json(raw: Any) -> Optional[str]:
    """将 API thumbnails 规范为 JSON 字符串；空则 None。"""
    if raw is None:
        return None
    if not isinstance(raw, list):
        return None
    urls = [str(u).strip() for u in raw if u is not None and str(u).strip()]
    if not urls:
        return None
    return json.dumps(urls, ensure_ascii=False)


def _item_to_order_data(
    item: Dict[str, Any], seller_id: Optional[int] = None
) -> Dict[str, Any]:
    """将 API 返回的单条 item 映射为 OrderModel 所需字段字典。"""
    buyer = item.get("buyer") or {}
    te = item.get("transaction_evidence") or {}
    buyer_id = buyer.get("id")
    buyer_id_str = "" if buyer_id is None else str(buyer_id).strip()
    data_user = None if seller_id is None else str(int(seller_id))

    return {
        "order_no":         item.get("id", ""),
        "order_date":       _unix_seconds(item.get("created")),
        "order_updated_at": _unix_seconds(item.get("updated")),
        "customer_name":    buyer_id_str or None,
        "data_user":        data_user,
        "status":           te.get("status") or item.get("status", "trading"),
        "amount":           float(item.get("price") or 0),
        "remark":           item.get("name", ""),
        "thumbnails":       _norm_thumbnails_json(item.get("thumbnails")),
    }


def _upsert_order(order_data: Dict[str, Any]) -> str:
    """
    将单条订单写入数据库。
    - 若 order_no 已存在则更新状态、金额、备注等可变字段。
    - 若不存在则插入新记录。
    返回 "inserted" / "updated" / "skipped"。
    """
    order_no = order_data.get("order_no", "")
    if not order_no:
        return "skipped"

    existing: Optional[OrderModel] = None
    rows = OrderModel.find_all(where="[order_no] = ?", params=(order_no,), limit=1)
    if rows:
        existing = rows[0]

    if existing is None:
        record = OrderModel(**order_data)
        record.save()
        return "inserted"

    # 更新可变字段
    existing.status            = order_data["status"]
    existing.amount            = order_data["amount"]
    existing.customer_name     = order_data["customer_name"]
    existing.data_user         = order_data.get("data_user")
    existing.remark            = order_data["remark"]
    existing.order_date        = order_data["order_date"]
    existing.order_updated_at  = order_data.get("order_updated_at")
    existing.thumbnails        = order_data.get("thumbnails")
    existing.save()
    return "updated"


def fetch_open_order_items(
    seller_id: int,
    account_id: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    仅请求 Mercari 出售中（trading）列表，不写数据库。
    与 fetch_and_sync_open_orders 使用同一 URL / 参数。
    """
    url = f"{_API_URL}?{_API_PARAMS}&seller_id={seller_id}"

    response = send_request(
        "GET", url, account_id=account_id, dpop_for=DPOP_FOR_ITEMS_LIST
    )

    if response.get("result") != "OK":
        raise RuntimeError(f"API 返回异常: {response}")

    items: List[Dict[str, Any]] = response.get("data") or []
    meta: Dict[str, Any] = response.get("meta") or {}
    return items, meta


def fetch_and_sync_open_orders(
    seller_id: int,
    account_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    从 Mercari API 获取出售中订单列表，并同步到本地订单管理表。

    :param seller_id:  Mercari 卖家 ID（从账号配置读取后传入）。
    :param account_id: 指定请求头账号 ID；为 None 时自动选取 active 账号。
    :return: 同步结果统计字典，包含 total / inserted / updated / skipped / errors。
    """
    items: List[Dict[str, Any]]
    meta: Dict[str, Any]
    items, meta = fetch_open_order_items(seller_id=seller_id, account_id=account_id)

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
        f"[open_orders] 同步完成: "
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
        print(f"  [open_orders] info 失败示例: item_id={fe.get('item_id')!r} -> {fe.get('error')!r}")
    return stats

