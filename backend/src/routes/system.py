# -*- coding: utf-8 -*-
"""系统管理：重启应用服务等。"""

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

from ..system_service import schedule_system_restart

router = APIRouter(prefix="/api/system", tags=["system"])


class RestartOut(BaseModel):
    success: bool = True
    message: str


@router.post("/restart", response_model=RestartOut)
async def restart_system():
    """
    重启 mercari 后端进程（关闭 WebDrive / MITM 后拉起新进程）。
    前端在收到响应后稍等再刷新页面。
    """
    asyncio.create_task(schedule_system_restart(delay_seconds=1.0))
    return RestartOut(message="系统正在重启，请约 10 秒后刷新页面")
