# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..models.meilu_account import MeiluAccountModel

router = APIRouter(prefix="/api/meilu-accounts", tags=["meilu-accounts"])

ALLOWED_STATUS = {"active", "disabled"}


class MeiluAccountCreate(PydanticModel):
    account_name: str
    login_id: str
    login_password: Optional[str] = None
    status: str = "active"
    remark: Optional[str] = None


class MeiluAccountUpdate(PydanticModel):
    account_name: Optional[str] = None
    login_id: Optional[str] = None
    login_password: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None


def _validate_status(status: str):
    if status not in ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail="账号状态错误")


def _norm_required_text(value: str, field_name: str) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail=f"{field_name}不能为空")
    return text


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
    item = MeiluAccountModel(
        account_name=_norm_required_text(data.account_name, "账号名称"),
        login_id=_norm_required_text(data.login_id, "登录账号"),
        login_password=(data.login_password or "").strip() or None,
        status=data.status,
        remark=data.remark,
    )
    if not item.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return item.to_dict()


@router.put("/{aid}")
def update_meilu_account(aid: int, data: MeiluAccountUpdate):
    item = MeiluAccountModel.find_by_id(id=aid)
    if not item:
        raise HTTPException(status_code=404, detail="账号不存在")

    if data.account_name is not None:
        item.account_name = _norm_required_text(data.account_name, "账号名称")
    if data.login_id is not None:
        item.login_id = _norm_required_text(data.login_id, "登录账号")
    if data.login_password is not None:
        item.login_password = data.login_password.strip() or None
    if data.status is not None:
        _validate_status(data.status)
        item.status = data.status
    if data.remark is not None:
        item.remark = data.remark

    if not item.save():
        raise HTTPException(status_code=500, detail="更新失败")
    return item.to_dict()


@router.delete("/{aid}")
def delete_meilu_account(aid: int):
    item = MeiluAccountModel.find_by_id(id=aid)
    if not item:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not item.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}
