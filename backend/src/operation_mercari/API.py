# -*- coding: utf-8 -*-
"""
Mercari 操作相关 API 路由

前缀: /api/mercari
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel

from .sync_data import sync_new_data, sync_open_orders

router = APIRouter(prefix="/api/mercari", tags=["mercari"])


class SyncOrdersRequest(PydanticModel):
    account_id: Optional[int] = None


@router.post("/sync-new-data")
def api_sync_new_data(data: SyncOrdersRequest):
    """
    订单页「更新数据」：仅增量入库当前 API 页中尚未存在的出售中订单，倒序写入。
    """
    try:
        result = sync_new_data(account_id=data.account_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"同步失败: {exc}") from exc

    return {"success": True, "data": result}


@router.post("/sync-orders")
def sync_orders(data: SyncOrdersRequest):
    """
    触发 Mercari 订单同步（出售中 trading + 已售完 sold_out 历史），写入同一订单表。

    - account_id: 指定煤炉账号 ID，不传则自动选取第一个 active 账号。
    - 卖家ID: 从煤炉账号配置中读取（不再由接口传入）。
    """
    try:
        result = sync_open_orders(account_id=data.account_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"同步失败: {exc}") from exc

    return {"success": True, "data": result}
