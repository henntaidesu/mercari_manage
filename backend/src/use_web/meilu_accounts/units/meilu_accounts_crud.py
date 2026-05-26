# -*- coding: utf-8 -*-
"""煤炉账号管理 CRUD 端点：列表 / 创建 / 更新 / 删除。"""
import json
from typing import Optional

from fastapi import HTTPException

from ....db_manage.models.meilu_account import MeiluAccountModel
from .meilu_accounts_helpers import (
    _item_api_dict,
    _norm_auto_fetch,
    _norm_headers_dict,
    _norm_pause_window,
    _norm_required_text,
    _norm_seller_id,
    _normalize_is_open,
    _validate_status,
)
from .meilu_accounts_models import MeiluAccountCreate, MeiluAccountUpdate


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


def _value_json_for_create(data: MeiluAccountCreate) -> str:
    raw = data.value
    if not raw or not isinstance(raw, dict):
        return json.dumps({}, ensure_ascii=False)
    if not any(str(v or "").strip() for v in raw.values()):
        return json.dumps({}, ensure_ascii=False)
    headers = _norm_headers_dict(raw)
    return json.dumps(headers, ensure_ascii=False)


def create_meilu_account(data: MeiluAccountCreate):
    _validate_status(data.status)
    value_json = _value_json_for_create(data)
    name = _norm_required_text(data.account_name, "账号名称")
    lid = (data.login_id or "").strip() or name
    io, fi, li, os_, td, nt = _norm_auto_fetch(
        _normalize_is_open(data.is_open),
        data.fetch_interval,
        _normalize_is_open(data.auto_fetch_order_list),
        _normalize_is_open(data.auto_fetch_on_sale),
        _normalize_is_open(data.auto_fetch_todos),
        _normalize_is_open(data.auto_fetch_notifications),
    )
    pause_s, pause_e = _norm_pause_window(data.pause_start_time, data.pause_end_time)
    item = MeiluAccountModel(
        account_name=name,
        login_id=lid,
        seller_id=_norm_seller_id(data.seller_id),
        login_password=None,
        value=value_json,
        status=data.status,
        remark=data.remark,
        is_open=io,
        fetch_interval=fi,
        auto_fetch_order_list=li,
        auto_fetch_on_sale=os_,
        auto_fetch_todos=td,
        auto_fetch_notifications=nt,
        pause_start_time=pause_s,
        pause_end_time=pause_e,
    )
    if not item.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return _item_api_dict(item)


def update_meilu_account(aid: int, data: MeiluAccountUpdate):
    item = MeiluAccountModel.find_by_id(id=aid)
    if not item:
        raise HTTPException(status_code=404, detail="账号不存在")

    if data.account_name is not None:
        item.account_name = _norm_required_text(data.account_name, "账号名称")
    if data.login_id is not None:
        item.login_id = (data.login_id or "").strip() or item.account_name
    if data.seller_id is not None:
        item.seller_id = _norm_seller_id(data.seller_id)
    if data.status is not None:
        _validate_status(data.status)
        item.status = data.status
    if data.remark is not None:
        item.remark = data.remark
    if data.value is not None:
        headers = _norm_headers_dict(data.value)
        item.value = json.dumps(headers, ensure_ascii=False)
    if (
        data.is_open is not None
        or data.fetch_interval is not None
        or data.auto_fetch_order_list is not None
        or data.auto_fetch_on_sale is not None
        or data.auto_fetch_todos is not None
        or data.auto_fetch_notifications is not None
    ):
        prev_open = _normalize_is_open(item.is_open)
        io = _normalize_is_open(data.is_open) if data.is_open is not None else prev_open
        fi = data.fetch_interval if data.fetch_interval is not None else item.fetch_interval
        li = _normalize_is_open(getattr(item, "auto_fetch_order_list", 0))
        if data.auto_fetch_order_list is not None:
            li = _normalize_is_open(data.auto_fetch_order_list)
        os_ = _normalize_is_open(getattr(item, "auto_fetch_on_sale", 0))
        if data.auto_fetch_on_sale is not None:
            os_ = _normalize_is_open(data.auto_fetch_on_sale)
        td = _normalize_is_open(getattr(item, "auto_fetch_todos", 0))
        if data.auto_fetch_todos is not None:
            td = _normalize_is_open(data.auto_fetch_todos)
        nt = _normalize_is_open(getattr(item, "auto_fetch_notifications", 0))
        if data.auto_fetch_notifications is not None:
            nt = _normalize_is_open(data.auto_fetch_notifications)
        io, fi, li, os_, td, nt = _norm_auto_fetch(io, fi, li, os_, td, nt)
        item.is_open = io
        item.fetch_interval = fi
        item.auto_fetch_order_list = li
        item.auto_fetch_on_sale = os_
        item.auto_fetch_todos = td
        item.auto_fetch_notifications = nt
        if io == 0:
            item.auto_fetch_last_at = None
        elif prev_open == 0 and io == 1:
            item.auto_fetch_last_at = None

    if data.pause_start_time is not None or data.pause_end_time is not None:
        new_start = (
            data.pause_start_time
            if data.pause_start_time is not None
            else getattr(item, "pause_start_time", None)
        )
        new_end = (
            data.pause_end_time
            if data.pause_end_time is not None
            else getattr(item, "pause_end_time", None)
        )
        pause_s, pause_e = _norm_pause_window(new_start, new_end)
        item.pause_start_time = pause_s
        item.pause_end_time = pause_e

    if not item.save():
        raise HTTPException(status_code=500, detail="更新失败")
    return _item_api_dict(item)


def delete_meilu_account(aid: int):
    item = MeiluAccountModel.find_by_id(id=aid)
    if not item:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not item.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}
