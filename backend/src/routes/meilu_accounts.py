# -*- coding: utf-8 -*-
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional, Dict, Any
from ..db_manage.models.meilu_account import MeiluAccountModel

router = APIRouter(prefix="/api/meilu-accounts", tags=["meilu-accounts"])

ALLOWED_STATUS = {"active", "disabled"}
ALLOWED_FETCH_INTERVALS = frozenset({"10", "30", "60", "3h", "6h", "12h", "24h"})

_HEADER_FIELD_LABELS = [
    ("accept", "Accept"),
    ("x_app_type", "X-App-Type"),
    ("authorization", "Authorization"),
    ("dpop", "DPoP"),
    ("priority", "Priority"),
    ("accept_language", "Accept-Language"),
    ("accept_encoding", "Accept-Encoding"),
    ("user_agent", "User-Agent"),
    ("x_app_version", "X-App-Version"),
    ("x_platform", "X-Platform"),
    ("x_mcc", "X-Mcc"),
]


class MeiluAccountCreate(PydanticModel):
    account_name: str
    value: Dict[str, Any]
    login_id: Optional[str] = None
    status: str = "active"
    remark: Optional[str] = None
    is_open: int = 0
    fetch_interval: Optional[str] = None


class MeiluAccountUpdate(PydanticModel):
    account_name: Optional[str] = None
    login_id: Optional[str] = None
    value: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    remark: Optional[str] = None
    is_open: Optional[int] = None
    fetch_interval: Optional[str] = None


def _validate_status(status: str):
    if status not in ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail="账号状态错误")


def _norm_required_text(value: str, field_name: str) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail=f"{field_name}不能为空")
    return text


def _normalize_is_open(v: Any) -> int:
    if v is True:
        return 1
    if v is False or v is None:
        return 0
    try:
        return 1 if int(v) else 0
    except (TypeError, ValueError):
        return 0


def _norm_auto_fetch(is_open: int, fetch_interval: Optional[str]) -> tuple:
    is_open = 1 if is_open else 0
    if is_open == 0:
        return 0, None
    iv = (fetch_interval or "").strip()
    if iv not in ALLOWED_FETCH_INTERVALS:
        raise HTTPException(status_code=400, detail="开启自动数据获取时，请选择有效的时间间隔")
    return 1, iv


def _norm_headers_dict(d: Optional[dict]) -> dict:
    if not d or not isinstance(d, dict):
        raise HTTPException(status_code=400, detail="请求头 value 必须为 JSON 对象")
    out = {}
    for key, label in _HEADER_FIELD_LABELS:
        raw = d.get(key)
        text = ("" if raw is None else str(raw)).strip()
        if not text:
            raise HTTPException(status_code=400, detail=f"{label}不能为空")
        out[key] = text
    return out


def _item_api_dict(item: MeiluAccountModel) -> dict:
    d = item.to_dict()
    d.pop('login_password', None)
    raw = d.pop('value', None)
    d['value'] = MeiluAccountModel._parse_value_json(raw if isinstance(raw, str) else None)
    d['is_open'] = 1 if d.get('is_open') else 0
    return d


@router.get("")
def list_meilu_accounts(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    if status:
        _validate_status(status)
    return MeiluAccountModel.find_detail_list(
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.post("")
def create_meilu_account(data: MeiluAccountCreate):
    _validate_status(data.status)
    headers = _norm_headers_dict(data.value)
    name = _norm_required_text(data.account_name, "账号名称")
    lid = (data.login_id or "").strip() or name
    io, fi = _norm_auto_fetch(_normalize_is_open(data.is_open), data.fetch_interval)
    item = MeiluAccountModel(
        account_name=name,
        login_id=lid,
        login_password=None,
        value=json.dumps(headers, ensure_ascii=False),
        status=data.status,
        remark=data.remark,
        is_open=io,
        fetch_interval=fi,
    )
    if not item.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return _item_api_dict(item)


@router.put("/{aid}")
def update_meilu_account(aid: int, data: MeiluAccountUpdate):
    item = MeiluAccountModel.find_by_id(id=aid)
    if not item:
        raise HTTPException(status_code=404, detail="账号不存在")

    if data.account_name is not None:
        item.account_name = _norm_required_text(data.account_name, "账号名称")
    if data.login_id is not None:
        item.login_id = (data.login_id or "").strip() or item.account_name
    if data.status is not None:
        _validate_status(data.status)
        item.status = data.status
    if data.remark is not None:
        item.remark = data.remark
    if data.value is not None:
        headers = _norm_headers_dict(data.value)
        item.value = json.dumps(headers, ensure_ascii=False)
    if data.is_open is not None or data.fetch_interval is not None:
        io = _normalize_is_open(data.is_open if data.is_open is not None else item.is_open)
        fi = data.fetch_interval if data.fetch_interval is not None else item.fetch_interval
        io, fi = _norm_auto_fetch(io, fi)
        item.is_open = io
        item.fetch_interval = fi

    if not item.save():
        raise HTTPException(status_code=500, detail="更新失败")
    return _item_api_dict(item)


@router.delete("/{aid}")
def delete_meilu_account(aid: int):
    item = MeiluAccountModel.find_by_id(id=aid)
    if not item:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not item.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}
