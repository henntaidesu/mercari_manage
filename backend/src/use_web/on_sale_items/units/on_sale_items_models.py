# -*- coding: utf-8 -*-
"""在售商品列表处理器：Pydantic 请求模型。"""
from typing import List, Optional

from pydantic import BaseModel as PydanticModel


class SyncOnSaleRequest(PydanticModel):
    account_id: Optional[int] = None
    progress_job_id: Optional[str] = None


class FetchOnSaleDetailRequest(PydanticModel):
    """items/get 拉取详情并尝试同步库存；account_id 不传则按在售行的 seller_id 匹配 active 账号。"""
    item_id: str
    account_id: Optional[int] = None


class FetchOnSaleDetailsBatchRequest(PydanticModel):
    """同一账号下批量 items/get：在 run_meilu_serial_async 内串行执行，避免多请求并发抢占 WebDriver。"""
    item_ids: List[str]
    account_id: Optional[int] = None
