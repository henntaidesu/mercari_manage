# -*- coding: utf-8 -*-
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import List, Optional
from ..db_manage.models.order import OrderModel

router = APIRouter(prefix="/api/orders", tags=["orders"])

ALLOWED_STATUS = {"to_pack", "to_ship", "sent", "signed", "confirmed"}
# 与煤炉同步后的状态，编辑保存时允许保留
MERCARI_STATUSES = {
    "trading",
    "wait_payment",
    "wait_shipping",
    "wait_review",
    "done",
    "sold_out",
    "cancelled",
    "cancel_request",
    "pending",
}
ALL_ORDER_STATUSES = ALLOWED_STATUS | MERCARI_STATUSES


def _encode_thumbnails(urls: Optional[List[str]]) -> Optional[str]:
    if not urls:
        return None
    out = [str(u).strip() for u in urls if u is not None and str(u).strip()]
    return json.dumps(out, ensure_ascii=False) if out else None


class OrderCreate(PydanticModel):
    order_no: str
    order_date: str
    order_updated_at: Optional[str] = None
    customer_name: Optional[str] = None
    status: str = "to_pack"
    amount: float
    service_fee: Optional[float] = None
    net_income: Optional[float] = None
    carrier_display_name: Optional[str] = None
    request_class_display_name: Optional[str] = None
    shipping_fee: Optional[float] = None
    tracking_no: Optional[str] = None
    transaction_evidence_id: Optional[int] = None
    remark: Optional[str] = None
    thumbnails: Optional[List[str]] = None


class OrderUpdate(PydanticModel):
    order_no: Optional[str] = None
    order_date: Optional[str] = None
    order_updated_at: Optional[str] = None
    customer_name: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    service_fee: Optional[float] = None
    net_income: Optional[float] = None
    carrier_display_name: Optional[str] = None
    request_class_display_name: Optional[str] = None
    shipping_fee: Optional[float] = None
    tracking_no: Optional[str] = None
    transaction_evidence_id: Optional[int] = None
    remark: Optional[str] = None
    thumbnails: Optional[List[str]] = None


def _validate_status(status: str):
    if status not in ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail="订单状态错误")


def _validate_status_update(status: str):
    if status not in ALL_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="订单状态错误")


def _normalize_order_no(order_no: str) -> str:
    val = (order_no or "").strip()
    if not val:
        raise HTTPException(status_code=400, detail="订单号不能为空")
    return val


@router.get("/stats")
def order_stats(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """当前筛选条件下的全表汇总（金额、手续费、快递费、净收益及行数），不受分页影响。"""
    if status:
        _validate_status(status)
    return OrderModel.aggregate_sums(
        keyword=keyword,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )


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
    ou = (data.order_updated_at or "").strip() or None
    item = OrderModel(
        order_no=order_no,
        order_date=data.order_date,
        order_updated_at=ou,
        customer_name=(data.customer_name or "").strip() or None,
        status=data.status,
        amount=data.amount,
        service_fee=data.service_fee,
        net_income=data.net_income,
        carrier_display_name=(data.carrier_display_name or "").strip() or None,
        request_class_display_name=(data.request_class_display_name or "").strip() or None,
        shipping_fee=data.shipping_fee,
        tracking_no=(data.tracking_no or "").strip() or None,
        transaction_evidence_id=data.transaction_evidence_id,
        remark=data.remark,
        thumbnails=_encode_thumbnails(data.thumbnails),
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
    if "order_updated_at" in data.model_fields_set:
        item.order_updated_at = (data.order_updated_at or "").strip() or None
    if data.customer_name is not None:
        item.customer_name = data.customer_name.strip() or None
    if data.status is not None:
        _validate_status_update(data.status)
        item.status = data.status
    if data.amount is not None:
        if data.amount <= 0:
            raise HTTPException(status_code=400, detail="金额必须大于0")
        item.amount = data.amount
    if "service_fee" in data.model_fields_set:
        item.service_fee = data.service_fee
    if "net_income" in data.model_fields_set:
        item.net_income = data.net_income
    if "carrier_display_name" in data.model_fields_set:
        item.carrier_display_name = (data.carrier_display_name or "").strip() or None
    if "request_class_display_name" in data.model_fields_set:
        item.request_class_display_name = (data.request_class_display_name or "").strip() or None
    if "shipping_fee" in data.model_fields_set:
        item.shipping_fee = data.shipping_fee
    if "tracking_no" in data.model_fields_set:
        item.tracking_no = (data.tracking_no or "").strip() or None
    if "transaction_evidence_id" in data.model_fields_set:
        item.transaction_evidence_id = data.transaction_evidence_id
    if "remark" in data.model_fields_set:
        item.remark = (data.remark or "").strip() or None
    if "thumbnails" in data.model_fields_set:
        item.thumbnails = _encode_thumbnails(data.thumbnails)

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
