# -*- coding: utf-8 -*-
"""成本支出（包材/快递费）处理器：Pydantic 请求模型。"""

from typing import Optional

from pydantic import BaseModel as PydanticModel


class CostExpenseCreate(PydanticModel):
    type: Optional[str] = None
    item_name: str
    quantity: int
    unit_price: int
    owner: Optional[str] = None
    order_no: Optional[str] = None
    record_time: Optional[int] = None


class CostExpenseUpdate(PydanticModel):
    type: Optional[str] = None
    item_name: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[int] = None
    owner: Optional[str] = None
    order_no: Optional[str] = None
    record_time: Optional[int] = None
