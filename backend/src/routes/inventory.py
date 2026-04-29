# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..models.inventory import InventoryModel

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


class InventoryUpdate(PydanticModel):
    min_quantity: Optional[int] = None


@router.get("/summary")
def get_summary():
    return InventoryModel.get_summary()


@router.get("")
def list_inventory(warehouse_id: Optional[int] = None, low_stock: Optional[bool] = None):
    return InventoryModel.find_detail_list(warehouse_id=warehouse_id, low_stock=low_stock)


@router.put("/{iid}")
def update_inventory(iid: int, data: InventoryUpdate):
    inv = InventoryModel.find_by_id(id=iid)
    if not inv:
        raise HTTPException(status_code=404, detail="库存记录不存在")
    if data.min_quantity is not None:
        inv.min_quantity = data.min_quantity
    inv.save()
    return inv.to_dict()
