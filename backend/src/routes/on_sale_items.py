# -*- coding: utf-8 -*-
from typing import Dict, Optional, Set

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel

from ..db_manage.database import DatabaseManager
from ..db_manage.models.on_sale_item import OnSaleItemModel
from ..operation_mercari.on_sale_item_detail_sync import fetch_detail_and_sync_inventory
from ..operation_mercari.on_sale_items_sync import sync_on_sale_items_from_mercari
from ..operation_mercari.sync_data import resolve_account_id_by_seller_id

router = APIRouter(prefix="/api/on-sale-items", tags=["on-sale-items"])


def _seller_name_by_seller_id(seller_ids: Set[str]) -> Dict[str, str]:
    """按 seller_id 从 meilu_accounts 取展示名（account_name），键为 TRIM 后的 seller_id。"""
    ids = {str(s).strip() for s in seller_ids if s is not None and str(s).strip()}
    if not ids:
        return {}
    db = DatabaseManager()
    lst = list(ids)
    ph = ",".join(["?"] * len(lst))
    sql = f"""
        SELECT TRIM(COALESCE([seller_id], '')), [account_name], [status], [id]
        FROM [meilu_accounts]
        WHERE TRIM(COALESCE([seller_id], '')) IN ({ph})
        ORDER BY CASE WHEN [status] = 'active' THEN 0 ELSE 1 END, [id] ASC
    """
    rows = db.execute_query(sql, tuple(lst))
    out: Dict[str, str] = {}
    for sid, aname, _status, _id in rows:
        if sid and sid not in out:
            out[sid] = (aname or "").strip()
    return out


def _attach_seller_name(items: list) -> None:
    if not items:
        return
    sid_set = {str(i.get("seller_id") or "").strip() for i in items}
    name_map = _seller_name_by_seller_id(sid_set)
    for row in items:
        sid = str(row.get("seller_id") or "").strip()
        row["seller_name"] = name_map.get(sid) or None


class SyncOnSaleRequest(PydanticModel):
    account_id: Optional[int] = None


class FetchOnSaleDetailRequest(PydanticModel):
    """items/get 拉取详情并尝试同步库存；account_id 不传则按在售行的 seller_id 匹配 active 账号。"""
    item_id: str
    account_id: Optional[int] = None


@router.get("")
def list_on_sale_items(
    keyword: Optional[str] = None,
    seller_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    data = OnSaleItemModel.find_list(
        keyword=keyword,
        seller_id=seller_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    _attach_seller_name(data.get("items") or [])
    return data


@router.post("/sync")
def sync_on_sale(data: SyncOnSaleRequest):
    """
    先按卖家删除本地 on_sale_items 缓存，再从煤炉拉取在售列表（items/get_items，
    status=on_sale,stop 等，见 on_sale_list.build_on_sale_list_url）写入 on_sale_items；须配置 dpop_on_sale_list。
    """
    try:
        result = sync_on_sale_items_from_mercari(account_id=data.account_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"同步失败: {exc}") from exc
    return {"success": True, "data": result}


@router.post("/fetch-detail")
def fetch_on_sale_item_detail(data: FetchOnSaleDetailRequest):
    """
    GET api.mercari.jp/items/get（完整 include_* 查询串），须配置 dpop_item_get_info。
    解析 data.description 中的「管理ID / 管理番号 / バーコード」，匹配库存后写入 mercari_item_id、on_sale_quantity。
    """
    item_id = (data.item_id or "").strip()
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id 不能为空")

    account_id = data.account_id
    if account_id is None:
        rows = OnSaleItemModel.find_all(
            where="TRIM([item_id]) = TRIM(?)",
            params=(item_id,),
            limit=1,
        )
        seller_id = None
        if rows:
            seller_id = str(rows[0].seller_id or "").strip() or None
        if seller_id:
            account_id = resolve_account_id_by_seller_id(seller_id)
        if account_id is None:
            raise HTTPException(
                status_code=400,
                detail="请传 account_id，或在在售列表中存在该商品且卖家已绑定 active 煤炉账号（seller_id）",
            )

    try:
        payload = fetch_detail_and_sync_inventory(item_id, account_id=account_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取详情失败: {exc}") from exc

    return {"success": True, "data": payload}
