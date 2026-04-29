# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..models.warehouse import WarehouseModel
from ..models.inventory import InventoryModel

router = APIRouter(prefix="/api/warehouses", tags=["warehouses"])


class WarehouseCreate(PydanticModel):
    name: str
    location: Optional[str] = None
    description: Optional[str] = None


class WarehouseUpdate(PydanticModel):
    name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


def _serialize(wh: WarehouseModel) -> dict:
    d = wh.to_dict()
    d.update(WarehouseModel.get_stats(wh.id))
    return d


@router.get("")
def list_warehouses():
    return [_serialize(w) for w in WarehouseModel.find_all(order_by="id ASC")]


@router.post("")
def create_warehouse(data: WarehouseCreate):
    if WarehouseModel.find_by_name(data.name):
        raise HTTPException(status_code=400, detail="仓库名称已存在")
    wh = WarehouseModel(name=data.name, location=data.location, description=data.description)
    if not wh.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return _serialize(wh)


@router.put("/{wid}")
def update_warehouse(wid: int, data: WarehouseUpdate):
    wh = WarehouseModel.find_by_id(id=wid)
    if not wh:
        raise HTTPException(status_code=404, detail="仓库不存在")
    if data.name is not None:
        wh.name = data.name
    if data.location is not None:
        wh.location = data.location
    if data.description is not None:
        wh.description = data.description
    wh.save()
    return _serialize(wh)


@router.delete("/{wid}")
def delete_warehouse(wid: int):
    wh = WarehouseModel.find_by_id(id=wid)
    if not wh:
        raise HTTPException(status_code=404, detail="仓库不存在")
    has_stock = InventoryModel.find_all("warehouse_id = ? AND quantity > 0", (wid,), limit=1)
    if has_stock:
        raise HTTPException(status_code=400, detail="仓库存在库存，无法删除")
    InventoryModel.delete_all("warehouse_id = ?", (wid,))
    wh.delete()
    return {"message": "删除成功"}
