# -*- coding: utf-8 -*-
"""订单管理 Pydantic 模型集合。"""
from pydantic import BaseModel as PydanticModel
from typing import List, Optional


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


class OrderPackagingWaiveBody(PydanticModel):
    order_no: str


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


class OutboundStockOutBody(PydanticModel):
    remark: Optional[str] = None


class OutboundLineBindInventoryBody(PydanticModel):
    """将未匹配到库存的出库明细行手动关联到某条库存（仅允许 inventory_id 为空时）。"""

    inventory_id: int
    quantity: Optional[int] = None


class ManualOutboundLineCreateBody(PydanticModel):
    order_no: str
    inventory_id: int
    quantity: int = 1
    management_id: Optional[str] = None
    remark: Optional[str] = None


class ManualOutboundLineItem(PydanticModel):
    inventory_id: int
    quantity: int = 1
    management_id: Optional[str] = None


class ManualOutboundLinesBatchCreateBody(PydanticModel):
    order_no: str
    lines: List[ManualOutboundLineItem]
    remark: Optional[str] = None
