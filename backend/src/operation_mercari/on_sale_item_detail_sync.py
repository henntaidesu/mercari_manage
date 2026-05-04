# -*- coding: utf-8 -*-
"""
在售商品 items/get 详情 → 解析说明中的管理番号 / バーコード → 回写 inventory.mercari_item_id、on_sale_quantity。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..db_manage.database import DatabaseManager
from .get_order.description_mgmt_ids import (
    _inventory_id_by_barcode,
    _inventory_id_exists,
    parse_order_description_outbound_tokens,
)
from .get_order.mercari_item_get import fetch_mercari_item_get


def _mercari_response_ok(resp: Any) -> bool:
    if not isinstance(resp, dict):
        return False
    rc = resp.get("result")
    if rc is None:
        return isinstance(resp.get("data"), dict)
    return str(rc).strip().upper() == "OK"


def _on_sale_quantity_from_status(status: Optional[str]) -> int:
    """煤炉 status=on_sale（出售中）计 1 件在售；暂停/交易中/已售等均为 0。"""
    s = (status or "").strip()
    return 1 if s == "on_sale" else 0


def _normalize_mercari_item_id(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    t = str(raw).strip()
    return t or None


def resolve_inventory_id_from_listing_description(text: Optional[str]) -> Optional[int]:
    """
    按说明文中出现顺序，找第一个可映射到本地库存的标识：
    管理 ID / 管理番号 → inventory.id；バーコード → inventory.barcode。
    """
    tokens: List[Tuple[str, Any]] = parse_order_description_outbound_tokens(text)
    for kind, val in tokens:
        if kind == "mgmt_id":
            mid = int(val)
            if _inventory_id_exists(mid):
                return mid
        else:
            bc = str(val).strip()
            inv_id = _inventory_id_by_barcode(bc)
            if inv_id is not None:
                return inv_id
    return None


def extract_mgmt_barcode_hints(text: Optional[str]) -> Dict[str, Any]:
    """便于前端展示：从说明中抽取的管理番号（数字串）与条码串列表（不要求已存在于库）。"""
    tokens = parse_order_description_outbound_tokens(text)
    mgmt: List[int] = []
    barcodes: List[str] = []
    for kind, val in tokens:
        if kind == "mgmt_id":
            mgmt.append(int(val))
        else:
            barcodes.append(str(val).strip())
    return {"management_numbers": mgmt, "barcodes": barcodes}


def fetch_detail_and_sync_inventory(
    item_id: str,
    account_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    拉取 items/get，并尝试将 data.id 与在售数量写入匹配到的库存行。

    :return: { api: 原始响应, sync: { updated, inventory_id, mercari_item_id, on_sale_quantity, message } }
    """
    resp = fetch_mercari_item_get(item_id, account_id=account_id)
    sync: Dict[str, Any] = {
        "updated": False,
        "inventory_id": None,
        "mercari_item_id": None,
        "on_sale_quantity": None,
        "message": None,
    }

    if not _mercari_response_ok(resp):
        sync["message"] = "煤炉接口返回非 OK"
        return {"api": resp, "sync": sync}

    data = resp.get("data")
    if not isinstance(data, dict):
        sync["message"] = "响应缺少 data"
        return {"api": resp, "sync": sync}

    desc = data.get("description")
    inv_id = resolve_inventory_id_from_listing_description(
        desc if isinstance(desc, str) else None
    )
    mid_api = _normalize_mercari_item_id(data.get("id"))
    status = data.get("status")
    on_sale_qty = _on_sale_quantity_from_status(status if isinstance(status, str) else None)

    hints = extract_mgmt_barcode_hints(desc if isinstance(desc, str) else None)
    sync["parsed_hints"] = hints

    if inv_id is None:
        sync["message"] = (
            "说明中未找到可关联的库存（需「管理ID」「管理番号」对应已存在的库存 id，"
            "或「バーコード」对应已存在的库存条码）"
        )
        return {"api": resp, "sync": sync}

    if not mid_api:
        sync["message"] = "响应中缺少商品 id"
        return {"api": resp, "sync": sync}

    db = DatabaseManager()
    try:
        db.execute_update(
            """
            UPDATE [inventory]
            SET [mercari_item_id] = ?, [on_sale_quantity] = ?
            WHERE [id] = ?
            """,
            (mid_api, on_sale_qty, int(inv_id)),
        )
    except Exception as exc:
        sync["message"] = f"写入库存失败: {exc}"
        return {"api": resp, "sync": sync}

    sync["updated"] = True
    sync["inventory_id"] = int(inv_id)
    sync["mercari_item_id"] = mid_api
    sync["on_sale_quantity"] = on_sale_qty
    sync["message"] = "已同步煤炉商品 ID 与在售数量"
    return {"api": resp, "sync": sync}
