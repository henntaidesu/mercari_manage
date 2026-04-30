# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..models.cost_record import CostRecordModel

router = APIRouter(prefix="/api/cost-records", tags=["cost-records"])

ALLOWED_TYPES = {"purchase", "shipping", "packaging", "operation", "other"}


class CostRecordCreate(PydanticModel):
    cost_date: str
    type: str
    amount: float
    quantity: int
    warehouse_id: Optional[int] = None
    remark: Optional[str] = None
    operator: Optional[str] = "管理员"


class CostRecordUpdate(PydanticModel):
    cost_date: Optional[str] = None
    type: Optional[str] = None
    amount: Optional[float] = None
    quantity: Optional[int] = None
    warehouse_id: Optional[int] = None
    remark: Optional[str] = None
    operator: Optional[str] = None


def _validate_type(cost_type: str):
    if cost_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="成本类型错误")


@router.get("")
def list_cost_records(
    type: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    if type:
        _validate_type(type)
    return CostRecordModel.find_detail_list(
        cost_type=type,
        warehouse_id=warehouse_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.post("")
def create_cost_record(data: CostRecordCreate):
    _validate_type(data.type)
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="金额必须大于0")
    if data.quantity <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于0")
    item = CostRecordModel(
        cost_date=data.cost_date,
        type=data.type,
        amount=data.amount,
        quantity=data.quantity,
        warehouse_id=data.warehouse_id,
        remark=data.remark,
        operator=data.operator,
    )
    if not item.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return item.to_dict()


@router.put("/{cid}")
def update_cost_record(cid: int, data: CostRecordUpdate):
    item = CostRecordModel.find_by_id(id=cid)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在")

    if data.type is not None:
        _validate_type(data.type)
        item.type = data.type
    if data.cost_date is not None:
        item.cost_date = data.cost_date
    if data.amount is not None:
        if data.amount <= 0:
            raise HTTPException(status_code=400, detail="金额必须大于0")
        item.amount = data.amount
    if data.quantity is not None:
        if data.quantity <= 0:
            raise HTTPException(status_code=400, detail="数量必须大于0")
        item.quantity = data.quantity
    if data.warehouse_id is not None:
        item.warehouse_id = data.warehouse_id
    if data.remark is not None:
        item.remark = data.remark
    if data.operator is not None:
        item.operator = data.operator

    if not item.save():
        raise HTTPException(status_code=500, detail="更新失败")
    return item.to_dict()


@router.delete("/{cid}")
def delete_cost_record(cid: int):
    item = CostRecordModel.find_by_id(id=cid)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在")
    if not item.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}
