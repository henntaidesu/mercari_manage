# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..db_manage.models.order import OrderModel

router = APIRouter(prefix="/api/orders", tags=["orders"])

ALLOWED_STATUS = {"to_pack", "to_ship", "sent", "signed", "confirmed"}


class OrderCreate(PydanticModel):
    order_no: str
    order_date: str
    customer_name: Optional[str] = None
    status: str = "to_pack"
    amount: float
    remark: Optional[str] = None


class OrderUpdate(PydanticModel):
    order_no: Optional[str] = None
    order_date: Optional[str] = None
    customer_name: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    remark: Optional[str] = None


def _validate_status(status: str):
    if status not in ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail="订单状态错误")


def _normalize_order_no(order_no: str) -> str:
    val = (order_no or "").strip()
    if not val:
        raise HTTPException(status_code=400, detail="订单号不能为空")
    return val


@router.get("")
def list_orders(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    if status:
        _validate_status(status)
    return OrderModel.find_detail_list(
        keyword=keyword,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.post("")
def create_order(data: OrderCreate):
    order_no = _normalize_order_no(data.order_no)
    _validate_status(data.status)
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="金额必须大于0")
    item = OrderModel(
        order_no=order_no,
        order_date=data.order_date,
        customer_name=(data.customer_name or "").strip() or None,
        status=data.status,
        amount=data.amount,
        remark=data.remark,
    )
    if not item.save():
        raise HTTPException(status_code=400, detail="保存失败，订单号可能重复")
    return item.to_dict()


@router.put("/{oid}")
def update_order(oid: int, data: OrderUpdate):
    item = OrderModel.find_by_id(id=oid)
    if not item:
        raise HTTPException(status_code=404, detail="订单不存在")

    if data.order_no is not None:
        item.order_no = _normalize_order_no(data.order_no)
    if data.order_date is not None:
        item.order_date = data.order_date
    if data.customer_name is not None:
        item.customer_name = data.customer_name.strip() or None
    if data.status is not None:
        _validate_status(data.status)
        item.status = data.status
    if data.amount is not None:
        if data.amount <= 0:
            raise HTTPException(status_code=400, detail="金额必须大于0")
        item.amount = data.amount
    if data.remark is not None:
        item.remark = data.remark

    if not item.save():
        raise HTTPException(status_code=400, detail="更新失败，订单号可能重复")
    return item.to_dict()


@router.delete("/{oid}")
def delete_order(oid: int):
    item = OrderModel.find_by_id(id=oid)
    if not item:
        raise HTTPException(status_code=404, detail="订单不存在")
    if not item.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}
