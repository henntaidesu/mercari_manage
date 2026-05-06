# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..db_manage.database import DatabaseManager
from ..db_manage.models.warehouse import WarehouseModel

router = APIRouter(prefix="/api/warehouses", tags=["warehouses"])
db = DatabaseManager()


class WarehouseCreate(PydanticModel):
    name: str
    warehouse: Optional[str] = "默认仓库"
    location: Optional[str] = None
    description: Optional[str] = None


class WarehouseUpdate(PydanticModel):
    name: Optional[str] = None
    warehouse: Optional[str] = None
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
    wh_key = WarehouseModel.normalize_warehouse_key(data.warehouse)
    if WarehouseModel.find_by_warehouse_and_name(wh_key, data.name):
        raise HTTPException(status_code=400, detail="该仓库下货架名称已存在")
    wh = WarehouseModel(
        name=data.name,
        warehouse=wh_key,
        location=data.location,
        description=data.description
    )
    if not wh.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return _serialize(wh)


@router.put("/{wid}")
def update_warehouse(wid: int, data: WarehouseUpdate):
    wh = WarehouseModel.find_by_id(id=wid)
    if not wh:
        raise HTTPException(status_code=404, detail="仓库不存在")
    next_name = data.name if data.name is not None else wh.name
    next_wh = WarehouseModel.normalize_warehouse_key(
        data.warehouse if data.warehouse is not None else wh.warehouse
    )
    other = WarehouseModel.find_by_warehouse_and_name(next_wh, next_name)
    if other and other.id != wid:
        raise HTTPException(status_code=400, detail="该仓库下货架名称已存在")
    if data.name is not None:
        wh.name = data.name
    if data.warehouse is not None:
        wh.warehouse = WarehouseModel.normalize_warehouse_key(data.warehouse)
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
    has_tx = db.execute_query(
        "SELECT 1 FROM [transactions] WHERE warehouse_id = ? OR target_warehouse_id = ? LIMIT 1",
        (wid, wid),
    )
    if has_tx:
        raise HTTPException(status_code=400, detail="仓库存在出入库记录，无法删除")
    wh.delete()
    return {"message": "删除成功"}
