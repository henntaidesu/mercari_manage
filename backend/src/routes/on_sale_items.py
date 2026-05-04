# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel

from ..db_manage.models.on_sale_item import OnSaleItemModel
from ..operation_mercari.on_sale_items_sync import sync_on_sale_items_from_mercari

router = APIRouter(prefix="/api/on-sale-items", tags=["on-sale-items"])


class SyncOnSaleRequest(PydanticModel):
    account_id: Optional[int] = None


@router.get("")
def list_on_sale_items(
    keyword: Optional[str] = None,
    seller_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    return OnSaleItemModel.find_list(
        keyword=keyword,
        seller_id=seller_id,
        status=status,
        page=page,
        page_size=page_size,
    )


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
