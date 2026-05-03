# -*- coding: utf-8 -*-
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import List, Optional
from ..db_manage.models.order import OrderModel
from ..operation_mercari.sync_data import resolve_account_id_by_seller_id
from ..operation_mercari.get_order.get_in_progress_order.get_order_info import apply_item_info_to_order

router = APIRouter(prefix="/api/orders", tags=["orders"])

# 订单 status 仅使用煤炉侧取值（与 items 列表 / 取引详情一致）
ORDER_STATUSES = frozenset(
    {
        "pending",
        "trading",
        "wait_payment",
        "wait_shipping",
        "wait_review",
        "done",
        "sold_out",
        "cancelled",
        "cancel_request",
    }
)
ALL_ORDER_STATUSES = ORDER_STATUSES


def _encode_thumbnails(urls: Optional[List[str]]) -> Optional[str]:
    if not urls:
        return None
    out = [str(u).strip() for u in urls if u is not None and str(u).strip()]
    return json.dumps(out, ensure_ascii=False) if out else None


class OrderCreate(PydanticModel):
    order_no: str
    order_date: int
    order_updated_at: Optional[int] = None
    purchase_time: Optional[int] = None
    customer_name: Optional[str] = None
    data_user: Optional[str] = None
    status: str = "pending"
    amount: int
    service_fee: Optional[int] = None
    net_income: Optional[int] = None
    carrier_display_name: Optional[str] = None
    request_class_display_name: Optional[str] = None
    shipping_fee: Optional[int] = None
    tracking_no: Optional[str] = None
    transaction_evidence_id: Optional[int] = None
    remark: Optional[str] = None
    description: Optional[str] = None
    thumbnails: Optional[List[str]] = None


class RefreshOrderInfoBody(PydanticModel):
    """单行刷新：transaction_evidences/get 回填，需指定卖家 ID 以选择对应煤炉账号。"""

    order_no: str
    data_user: str


class OrderUpdate(PydanticModel):
    order_no: Optional[str] = None
    order_date: Optional[int] = None
    order_updated_at: Optional[int] = None
    purchase_time: Optional[int] = None
    customer_name: Optional[str] = None
    data_user: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[int] = None
    service_fee: Optional[int] = None
    net_income: Optional[int] = None
    carrier_display_name: Optional[str] = None
    request_class_display_name: Optional[str] = None
    shipping_fee: Optional[int] = None
    tracking_no: Optional[str] = None
    transaction_evidence_id: Optional[int] = None
    remark: Optional[str] = None
    description: Optional[str] = None
    thumbnails: Optional[List[str]] = None


def _validate_status_query(status: Optional[str]) -> None:
    """列表/统计筛选：仅允许煤炉订单状态。"""
    if status is None or not str(status).strip():
        return
    s = str(status).strip()
    if s not in ALL_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="订单状态错误")


def _validate_order_status(status: str):
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
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    today_start_ts: Optional[int] = None,
    today_end_ts: Optional[int] = None,
):
    """当前筛选条件下的全表汇总（金额、手续费、快递费、净收益及行数），不受分页影响。

    筛选购入时间区间：start_ts / end_ts 为 Unix 秒（与列表一致，建议由前端按本地自然日 0 点～当日结束换算）。
    可选 today_start_ts / today_end_ts（同为 Unix 秒，本地「今天」起止）：在相同 keyword、status 下汇总「今日购入」，
    不受 start_ts/end_ts 影响。
    """
    _validate_status_query(status)
    out = OrderModel.aggregate_sums(
        keyword=keyword,
        status=status,
        start_ts=start_ts,
        end_ts=end_ts,
    )
    if today_start_ts is not None and today_end_ts is not None:
        t = OrderModel.aggregate_sums(
            keyword=keyword,
            status=status,
            start_ts=int(today_start_ts),
            end_ts=int(today_end_ts),
        )
        out["today_total_count"] = t["total_count"]
        out["today_sum_amount"] = t["sum_amount"]
        out["today_sum_service_fee"] = t["sum_service_fee"]
        out["today_sum_shipping_fee"] = t["sum_shipping_fee"]
        out["today_sum_net_income"] = t["sum_net_income"]
    return out


@router.get("")
def list_orders(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
):
    _validate_status_query(status)
    return OrderModel.find_detail_list(
        keyword=keyword,
        status=status,
        start_ts=start_ts,
        end_ts=end_ts,
        page=page,
        page_size=page_size,
    )


@router.post("/refresh-info")
def refresh_order_info(data: RefreshOrderInfoBody):
    """调用 Mercari transaction_evidences/get，更新状态、金额、说明、手续费、快递费、净收益、承运等字段。"""
    order_no = (data.order_no or "").strip()
    if not order_no:
        raise HTTPException(status_code=400, detail="订单号不能为空")
    du = (data.data_user or "").strip()
    if not du:
        raise HTTPException(status_code=400, detail="卖家ID（data_user）不能为空")

    aid = resolve_account_id_by_seller_id(du)
    if aid is None:
        raise HTTPException(
            status_code=400,
            detail="未找到与该卖家ID绑定的 active 煤炉账号，请在账号管理中配置 seller_id",
        )

    err = apply_item_info_to_order(order_no, account_id=aid, expected_seller_id=du)
    if err == "order_not_found":
        raise HTTPException(status_code=404, detail="本地不存在该订单号")
    if err == "seller_mismatch":
        raise HTTPException(
            status_code=400,
            detail="接口返回的商品不属于该卖家，请检查订单号与卖家ID是否匹配",
        )
    if err and err.startswith("api:"):
        raise HTTPException(status_code=502, detail=err[4:])
    if err and err.startswith("request:"):
        raise HTTPException(status_code=502, detail=err[8:])
    if err == "save_failed":
        raise HTTPException(status_code=500, detail="写入数据库失败")
    if err:
        raise HTTPException(status_code=400, detail=err)

    rows = OrderModel.find_all(where="[order_no] = ?", params=(order_no,), limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="订单不存在")
    return rows[0].to_dict()


@router.post("")
def create_order(data: OrderCreate):
    order_no = _normalize_order_no(data.order_no)
    _validate_order_status(data.status)
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="金额必须大于0")
    ou = data.order_updated_at
    pt = data.purchase_time
    item = OrderModel(
        order_no=order_no,
        order_date=int(data.order_date),
        order_updated_at=None if ou is None else int(ou),
        purchase_time=None if pt is None else int(pt),
        customer_name=(data.customer_name or "").strip() or None,
        data_user=(data.data_user or "").strip() or None,
        status=data.status,
        amount=int(data.amount),
        service_fee=data.service_fee,
        net_income=data.net_income,
        carrier_display_name=(data.carrier_display_name or "").strip() or None,
        request_class_display_name=(data.request_class_display_name or "").strip() or None,
        shipping_fee=data.shipping_fee,
        tracking_no=(data.tracking_no or "").strip() or None,
        transaction_evidence_id=data.transaction_evidence_id,
        remark=data.remark,
        description=data.description,
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
        item.order_date = int(data.order_date)
    if "order_updated_at" in data.model_fields_set:
        v = data.order_updated_at
        item.order_updated_at = None if v is None else int(v)
    if "purchase_time" in data.model_fields_set:
        v = data.purchase_time
        item.purchase_time = None if v is None else int(v)
    if data.customer_name is not None:
        item.customer_name = data.customer_name.strip() or None
    if "data_user" in data.model_fields_set:
        item.data_user = (data.data_user or "").strip() or None
    if data.status is not None:
        _validate_order_status(data.status)
        item.status = data.status
    if data.amount is not None:
        if data.amount <= 0:
            raise HTTPException(status_code=400, detail="金额必须大于0")
        item.amount = int(data.amount)
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
    if "description" in data.model_fields_set:
        item.description = (data.description or "").strip() or None
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
