# -*- coding: utf-8 -*-
"""系统管理：通过 restart.bat 重启应用。"""

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..system_service import resolve_restart_bat, schedule_restart_via_bat

router = APIRouter(prefix="/api/system", tags=["system"])


class RestartOut(BaseModel):
    success: bool = True
    message: str


@router.post("/restart", response_model=RestartOut)
async def restart_system():
    """
    调用同目录或仓库根目录的 restart.bat 重启服务。
    不使用进程内拉起新 Python/uvicorn，停服与起服均由 bat 完成。
    """
    bat = resolve_restart_bat()
    if bat is None:
        raise HTTPException(
            status_code=503,
            detail="未找到 restart.bat。请将 restart.bat 放在 mercari-server.exe 同目录或仓库根目录。",
        )
    asyncio.create_task(schedule_restart_via_bat(delay_seconds=0.8))
    return RestartOut(message="正在通过 restart.bat 重启，请约 10 秒后刷新页面")
