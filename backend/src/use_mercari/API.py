# -*- coding: utf-8 -*-
"""
Mercari 操作相关 API 路由

层级蓝图注册：
- 从 src/API.py 接收前缀 /mercariV2/src
- 完整 URL 格式: /mercariV2/src/use_mercari/<endpoint>
"""

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel as PydanticModel

from ..web_drive.core.account_serial_queue import (
    GLOBAL_QUEUE_KEY,
    queue_key_for_meilu_account,
    resolve_meilu_account_id,
    run_meilu_serial_async,
)
from .sync_data import (
    batch_refresh_orders_info,
    history_sync_precheck,
    sync_new_data,
    sync_open_orders,
)
from .sync_progress import (
    clear_sync_progress,
    get_sync_progress,
)

router = APIRouter(prefix="/use_mercari", tags=["use-mercari"])

# 与 listing_post_progress 相同的安全字符集，避免路径注入
_SYNC_JOB_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,128}$")


class SyncOrdersRequest(PydanticModel):
    account_id: Optional[int] = None
    progress_job_id: Optional[str] = None


@router.post("/sync-new-data")
async def api_sync_new_data(data: SyncOrdersRequest):
    """
    订单页「更新列表」：WebDriver 打开取引中一覧 + MITM 截获 trading 列表；仅增量入库尚未存在的出售中单，倒序写入。
    """
    jid = (data.progress_job_id or "").strip() or None
    if jid and not _SYNC_JOB_ID_RE.fullmatch(jid):
        raise HTTPException(status_code=400, detail="invalid progress_job_id")
    try:
        aid = resolve_meilu_account_id(data.account_id)
        result = await run_meilu_serial_async(
            queue_key_for_meilu_account(aid),
            lambda: sync_new_data(account_id=aid, progress_job_id=jid),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"同步失败: {exc}") from exc
    finally:
        if jid:
            clear_sync_progress(jid)

    return {"success": True, "data": result}


@router.post("/batch-refresh-info")
async def api_batch_refresh_info(data: SyncOrdersRequest):
    """
    订单页「更新状态」：逐条打开取引页并由 MITM 截获 transaction_evidences/get 回填（与单行刷新一致）。
    account_id：可选；指定则只处理该账号 seller_id 对应的订单。
    """
    jid = (data.progress_job_id or "").strip() or None
    if jid and not _SYNC_JOB_ID_RE.fullmatch(jid):
        raise HTTPException(status_code=400, detail="invalid progress_job_id")
    try:
        if data.account_id is not None:
            qk = queue_key_for_meilu_account(int(data.account_id))
            result = await run_meilu_serial_async(
                qk,
                lambda: batch_refresh_orders_info(
                    account_id=int(data.account_id),
                    progress_job_id=jid,
                ),
            )
        else:
            result = await run_meilu_serial_async(
                GLOBAL_QUEUE_KEY,
                lambda: batch_refresh_orders_info(
                    account_id=None,
                    progress_job_id=jid,
                ),
            )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"批量刷新失败: {exc}") from exc
    finally:
        if jid:
            clear_sync_progress(jid)

    return {"success": True, "data": result}


@router.get("/sync-progress/{job_id}")
def api_orders_sync_progress(job_id: str):
    """更新列表 / 更新状态执行过程中轮询当前步骤（与 POST body.progress_job_id 对应）。"""
    jid = (job_id or "").strip()
    if not _SYNC_JOB_ID_RE.fullmatch(jid):
        raise HTTPException(status_code=400, detail="invalid job_id")
    row = get_sync_progress(jid)
    if not row:
        return {"success": True, "data": {"step": None, "label_zh": None, "ts": None}}
    return {"success": True, "data": row}


@router.get("/history-sync-precheck")
def api_history_sync_precheck(account_id: Optional[int] = Query(None)):
    """
    「获取历史数据」前置校验：若 orders 中已有 data_user = 该账号卖家 ID 的数据，返回 allowed=false。
    """
    try:
        data = history_sync_precheck(account_id=account_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"校验失败: {exc}") from exc
    return {"success": True, "data": data}


@router.post("/sync-orders")
async def sync_orders(data: SyncOrdersRequest):
    """
    触发 Mercari 订单同步（出售中 trading + 已售完 sold_out 历史），写入同一订单表。

    - account_id: 指定煤炉账号 ID，不传则自动选取第一个 active 账号。
    - 卖家ID: 从煤炉账号配置中读取（不再由接口传入）。
    """
    try:
        aid = resolve_meilu_account_id(data.account_id)
        result = await run_meilu_serial_async(
            queue_key_for_meilu_account(aid),
            lambda: sync_open_orders(account_id=aid),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"同步失败: {exc}") from exc

    return {"success": True, "data": result}
