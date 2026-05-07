# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel

from ..db_manage.models.cost_expense import CostExpenseModel
from ..db_manage.models.cost_record import CostRecordModel

router = APIRouter(prefix="/api/cost-expenses", tags=["cost-expenses"])
ALLOWED_TYPES = {"快递费", "包装材料"}


class CostExpenseCreate(PydanticModel):
    type: Optional[str] = None
    item_name: str
    quantity: int
    unit_price: int
    owner: Optional[str] = None
    record_time: Optional[int] = None


class CostExpenseUpdate(PydanticModel):
    type: Optional[str] = None
    item_name: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[int] = None
    owner: Optional[str] = None
    record_time: Optional[int] = None


def _validate_required_text(value: Optional[str], field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{field_name}不能为空")
    return cleaned


def _validate_positive_int(value: Optional[int], field_name: str) -> int:
    if value is None or int(value) <= 0:
        raise HTTPException(status_code=400, detail=f"{field_name}必须大于0")
    return int(value)


def _validate_type(value: Optional[str]) -> str:
    cost_type = _validate_required_text(value, "类型")
    if cost_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="类型仅支持：快递费、包装材料")
    return cost_type


def _default_london_ts() -> int:
    return int(datetime.now(ZoneInfo("Europe/London")).timestamp())


def _find_packaging_item_latest(item_name: str):
    rows = CostRecordModel.find_all(
        where="type = ? AND item_name = ?",
        params=("packaging", item_name),
        order_by="cost_date DESC, id DESC",
        limit=1,
    )
    return rows[0] if rows else None


def _validate_packaging_stock(item_name: str, quantity: int):
    source = _find_packaging_item_latest(item_name)
    if not source:
        raise HTTPException(status_code=400, detail="库存包材中不存在该物品名称")
    stock_qty = int(source.quantity or 0)
    if stock_qty < quantity:
        raise HTTPException(status_code=400, detail=f"库存包材数量不足，当前仅剩 {stock_qty}")


def _sync_expense_type_from_source(item_name: str) -> str:
    source = _find_packaging_item_latest(item_name)
    if not source:
        raise HTTPException(status_code=400, detail="库存包材中不存在该物品名称")
    source_type = (source.type or "").strip()
    if source_type == "packaging":
        return "包装材料"
    if source_type == "shipping":
        return "快递费"
    # 库存包材模块目前只允许包装类；这里做兜底保护
    raise HTTPException(status_code=400, detail="该物品在库存包材中的类型不支持同步")


@router.get("")
def list_cost_expenses(
    type: Optional[str] = None,
    owner: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
):
    where_parts = ["1=1"]
    params = []
    if type:
        if type.strip() not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="类型仅支持：快递费、包装材料")
        where_parts.append("[type] = ?")
        params.append(type.strip())
    if owner:
        where_parts.append("[owner] = ?")
        params.append(owner.strip())
    if start_time is not None:
        where_parts.append("[record_time] >= ?")
        params.append(int(start_time))
    if end_time is not None:
        where_parts.append("[record_time] <= ?")
        params.append(int(end_time))

    where_clause = " AND ".join(where_parts)
    total = CostExpenseModel.count(where=where_clause, params=tuple(params))
    rows = CostExpenseModel.find_all(
        where=where_clause,
        params=tuple(params),
        order_by="record_time DESC, id DESC",
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [row.to_dict() for row in rows],
    }


@router.post("")
def create_cost_expense(data: CostExpenseCreate):
    item_name = _validate_required_text(data.item_name, "物品名称")
    expense_quantity = _validate_positive_int(data.quantity, "数量")
    _validate_packaging_stock(item_name, expense_quantity)
    source = _find_packaging_item_latest(item_name)
    if not source:
        raise HTTPException(status_code=400, detail="库存包材中不存在该物品名称")
    source_original_quantity = int(source.quantity or 0)
    synced_type = _sync_expense_type_from_source(item_name)
    row = CostExpenseModel(
        type=synced_type,
        item_name=item_name,
        quantity=expense_quantity,
        unit_price=_validate_positive_int(data.unit_price, "单价"),
        owner=(data.owner or "").strip() or None,
        record_time=int(data.record_time) if data.record_time is not None else _default_london_ts(),
    )
    source.quantity = source_original_quantity - expense_quantity
    if not source.save():
        raise HTTPException(status_code=500, detail="自动扣减库存包材失败")
    if not row.save():
        source.quantity = source_original_quantity
        source.save()
        raise HTTPException(status_code=500, detail="保存失败")
    return row.to_dict()


@router.put("/{cid}")
def update_cost_expense(cid: int, data: CostExpenseUpdate):
    row = CostExpenseModel.find_by_id(id=cid)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    next_item_name = _validate_required_text(
        data.item_name if data.item_name is not None else row.item_name,
        "物品名称",
    )
    next_quantity = _validate_positive_int(
        data.quantity if data.quantity is not None else row.quantity,
        "数量",
    )
    _validate_packaging_stock(next_item_name, next_quantity)
    next_synced_type = _sync_expense_type_from_source(next_item_name)

    row.type = next_synced_type
    if data.item_name is not None:
        row.item_name = _validate_required_text(data.item_name, "物品名称")
    if data.quantity is not None:
        row.quantity = _validate_positive_int(data.quantity, "数量")
    if data.unit_price is not None:
        row.unit_price = _validate_positive_int(data.unit_price, "单价")
    if data.owner is not None:
        row.owner = data.owner.strip() or None
    if data.record_time is not None:
        row.record_time = int(data.record_time)

    if not row.save():
        raise HTTPException(status_code=500, detail="更新失败")
    return row.to_dict()


@router.delete("/{cid}")
def delete_cost_expense(cid: int):
    row = CostExpenseModel.find_by_id(id=cid)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    if not row.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}
