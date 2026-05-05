# -*- coding: utf-8 -*-
"""
在售商品列表：从 Mercari items/get_items 拉取后，执行“新增/更新 + 软删除标记”同步。

使用在售专用 URL（status=on_sale,stop 等）与 DPoP_OnSale-List（dpop_on_sale_list），
见 get_on_sale.on_sale_list.fetch_on_sale_list_items。
金额入库：日元整数，价格向下取整（math.floor）。
"""

import json
import math
import time
from typing import Any, Dict, List, Optional

from .get_order.get_on_sale.on_sale_list import fetch_on_sale_list_items
from .sync_data import _resolve_account_and_seller
from ..db_manage.models.on_sale_item import OnSaleItemModel


def _opt_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _price_yen_floor(v: Any) -> int:
    try:
        return int(math.floor(float(v or 0)))
    except (TypeError, ValueError):
        return 0


def mercari_list_item_to_row(item: Dict[str, Any], seller_id: str) -> Optional[Dict[str, Any]]:
    """
    将 list.json 结构的单条 item 转为 on_sale_items 行字典。
    """
    iid = str(item.get("id") or "").strip()
    if not iid:
        return None

    ntiers = item.get("item_category_ntiers") or {}
    if not isinstance(ntiers, dict):
        ntiers = {}
    parents = item.get("parent_categories_ntiers")
    parents_json = None
    if isinstance(parents, list):
        parents_json = json.dumps(parents, ensure_ascii=False)
    ship = item.get("shipping_from_area") or {}
    if not isinstance(ship, dict):
        ship = {}
    imp = item.get("impression_boost_state") or {}
    if not isinstance(imp, dict):
        imp = {}

    thumbs = item.get("thumbnails")
    thumbs_json = None
    if isinstance(thumbs, list):
        thumbs_json = json.dumps(thumbs, ensure_ascii=False)

    auction = item.get("auction_info")
    auction_json = None
    if isinstance(auction, dict):
        auction_json = json.dumps(auction, ensure_ascii=False)

    return {
        "item_id": iid,
        "seller_id": str(seller_id).strip(),
        "status": (str(item.get("status")).strip() if item.get("status") is not None else None) or None,
        "name": (str(item.get("name")) if item.get("name") is not None else None) or None,
        "price": _price_yen_floor(item.get("price")),
        "thumbnails": thumbs_json,
        "item_root_category_id": _opt_int(item.get("root_category_id")),
        "num_likes": int(item.get("num_likes") or 0),
        "num_comments": int(item.get("num_comments") or 0),
        "created": _opt_int(item.get("created")),
        "updated": _opt_int(item.get("updated")),
        "category_id": _opt_int(ntiers.get("id")),
        "category_name": (str(ntiers.get("name")).strip() if ntiers.get("name") else None) or None,
        "parent_category_id": _opt_int(ntiers.get("parent_category_id")),
        "parent_category_name": (str(ntiers.get("parent_category_name")).strip() if ntiers.get("parent_category_name") else None) or None,
        "category_root_id": _opt_int(ntiers.get("root_category_id")),
        "category_root_name": (str(ntiers.get("root_category_name")).strip() if ntiers.get("root_category_name") else None) or None,
        "parent_categories_json": parents_json,
        "shipping_from_area_id": _opt_int(ship.get("id")),
        "shipping_from_area_name": (str(ship.get("name")).strip() if ship.get("name") else None) or None,
        "shipping_method_id": _opt_int(item.get("shipping_method_id")),
        "pager_id": _opt_int(item.get("pager_id")),
        "liked": 1 if item.get("liked") else 0,
        "item_pv": int(item.get("item_pv") or 0),
        "recent_item_pv": int(item.get("recent_item_pv") or 0),
        "search_impression": _opt_int(item.get("search_impression")),
        "recent_search_impression": _opt_int(item.get("recent_search_impression")),
        "is_no_price": 1 if item.get("is_no_price") else 0,
        "impression_boost_status": (str(imp.get("status")).strip() if imp.get("status") is not None else None) or None,
        "auction_info_json": auction_json,
        "synced_at": int(time.time()),
    }


def upsert_on_sale_item_row(row: Dict[str, Any]) -> str:
    """按 item_id upsert，返回 inserted / updated。"""
    iid = row.get("item_id")
    if not iid:
        return "skipped"
    rows = OnSaleItemModel.find_all(
        where="[item_id] = ?", params=(iid,), limit=1
    )
    if rows:
        o = rows[0]
        for k, v in row.items():
            if k == "item_id":
                continue
            setattr(o, k, v)
        o.save()
        return "updated"
    rec = OnSaleItemModel(**row)
    rec.save()
    return "inserted"


def sync_on_sale_items_from_mercari(account_id: Optional[int] = None) -> Dict[str, Any]:
    """
    从煤炉拉取在售列表（items/get_items，on_sale,stop）并同步本地：
    - 列表中存在：按 item_id 新增/更新，且 is_delete=0
    - 本地存在但新列表中不存在：标记 is_delete=1（软删除）
    """
    aid, sid = _resolve_account_and_seller(account_id)
    seller_key = str(int(sid))
    items, meta = fetch_on_sale_list_items(seller_id=sid, account_id=aid)
    incoming_ids = {
        str(it.get("id") or "").strip()
        for it in items
        if str(it.get("id") or "").strip()
    }
    existed_rows = OnSaleItemModel.find_all(
        where="TRIM([seller_id]) = TRIM(?)",
        params=(seller_key,),
    )
    existed_id_set = {str(r.item_id or "").strip() for r in existed_rows if str(r.item_id or "").strip()}
    soft_deleted_ids = existed_id_set - incoming_ids
    marked_deleted = 0
    restored = 0
    err_list: List[Dict[str, str]] = []
    stats: Dict[str, Any] = {
        "seller_id": seller_key,
        "api_item_count": len(items),
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "marked_deleted": 0,
        "restored": 0,
        "errors": err_list,
    }

    for item in items:
        try:
            row = mercari_list_item_to_row(item, seller_key)
            if not row:
                stats["skipped"] += 1
                continue
            row["is_delete"] = 0
            before = OnSaleItemModel.find_all(where="[item_id] = ?", params=(row["item_id"],), limit=1)
            was_deleted = bool(before and int(getattr(before[0], "is_delete", 0) or 0) == 1)
            r = upsert_on_sale_item_row(row)
            if r == "inserted":
                stats["inserted"] += 1
            elif r == "updated":
                stats["updated"] += 1
                if was_deleted:
                    restored += 1
            else:
                stats["skipped"] += 1
        except Exception as exc:
            err_list.append({"item_id": str(item.get("id", "")), "error": str(exc)})

    if soft_deleted_ids:
        placeholders = ",".join(["?"] * len(soft_deleted_ids))
        sql = (
            "UPDATE [on_sale_items] "
            "SET [is_delete] = 1, [synced_at] = ? "
            f"WHERE TRIM([seller_id]) = TRIM(?) AND TRIM([item_id]) IN ({placeholders}) "
            "AND COALESCE([is_delete], 0) = 0"
        )
        params = (int(time.time()), seller_key, *sorted(soft_deleted_ids))
        marked_deleted = OnSaleItemModel().db.execute_update(sql, params)

    stats["marked_deleted"] = marked_deleted
    stats["restored"] = restored
    stats["has_next"] = meta.get("has_next", False)
    stats["total_item_count"] = meta.get("total_item_count", len(items))
    return stats
