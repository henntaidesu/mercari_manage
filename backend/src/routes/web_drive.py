# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel, Field

from ..web_drive import get_web_drive_manager, profiles_root

router = APIRouter(prefix="/api/web-drive", tags=["web-drive"])


class OpenSessionBody(PydanticModel):
    """启动指定账号的 Edge 子浏览器（独立 profile，Cookie 持久化在服务端目录）。"""

    account_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    headless: bool = False
    start_url: Optional[str] = None


class CloseSessionBody(PydanticModel):
    account_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )


@router.get("/profiles-root")
def get_profiles_root():
    """返回当前 profile 根目录（环境变量 WEB_DRIVE_PROFILES_DIR 可覆盖）。"""
    return {"profiles_root": profiles_root()}


@router.get("/sessions")
async def list_sessions():
    return {"sessions": get_web_drive_manager().list_sessions()}


@router.post("/sessions/open")
async def open_session(body: OpenSessionBody):
    try:
        return {"success": True, "data": await get_web_drive_manager().open_session(
            body.account_key,
            headless=body.headless,
            start_url=body.start_url,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sessions/close")
async def close_session(body: CloseSessionBody):
    try:
        return {"success": True, "data": await get_web_drive_manager().close_session(body.account_key)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
