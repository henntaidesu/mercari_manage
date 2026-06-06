# -*- coding: utf-8 -*-
"""煤炉账号管理 CRUD 端点：列表 / 创建 / 更新 / 删除。"""
import json
from typing import Optional

from fastapi import HTTPException

from ....db_manage.models.mercari_account import MercariAccountModel
from .mercari_accounts_helpers import (
    _item_api_dict,
    _norm_headers_dict,
    _norm_interval,
    _norm_pause_window,
    _norm_required_text,
    _norm_seller_id,
    _normalize_is_open,
    _validate_status,
)
from .mercari_accounts_models import (
    AUTO_FETCH_TASK_KEYS,
    MercariAccountCreate,
    MercariAccountUpdate,
)


def list_mercari_accounts(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    if status:
        _validate_status(status)
    return MercariAccountModel.find_detail_list(
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size,
    )


def _value_json_for_create(data: MercariAccountCreate) -> str:
    raw = data.value
    if not raw or not isinstance(raw, dict):
        return json.dumps({}, ensure_ascii=False)
    if not any(str(v or "").strip() for v in raw.values()):
        return json.dumps({}, ensure_ascii=False)
    headers = _norm_headers_dict(raw)
    return json.dumps(headers, ensure_ascii=False)


def create_mercari_account(data: MercariAccountCreate):
    _validate_status(data.status)
    value_json = _value_json_for_create(data)
    name = _norm_required_text(data.account_name, "账号名称")
    lid = (data.login_id or "").strip() or name
    # 每项独立间隔：非空即开启该项；is_open 由是否有任一项开启派生（无总开关）
    intervals = {
        k: _norm_interval(getattr(data, f"auto_fetch_{k}_interval"))
        for k in AUTO_FETCH_TASK_KEYS
    }
    is_open = 1 if any(intervals.values()) else 0
    # 自动上架（售出即补挂）账号级开关：保留用户选择
    rl = 1 if _normalize_is_open(data.auto_fetch_relist) else 0
    pause_s, pause_e = _norm_pause_window(data.pause_start_time, data.pause_end_time)
    kwargs = dict(
        account_name=name,
        login_id=lid,
        seller_id=_norm_seller_id(data.seller_id),
        login_password=None,
        value=value_json,
        status=data.status,
        remark=data.remark,
        is_open=is_open,
        fetch_interval=None,
        auto_fetch_relist=rl,
        pause_start_time=pause_s,
        pause_end_time=pause_e,
    )
    for k in AUTO_FETCH_TASK_KEYS:
        iv = intervals[k]
        kwargs[f"auto_fetch_{k}"] = 1 if iv else 0
        kwargs[f"auto_fetch_{k}_interval"] = iv
    item = MercariAccountModel(**kwargs)
    if not item.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return _item_api_dict(item)


def update_mercari_account(aid: int, data: MercariAccountUpdate):
    item = MercariAccountModel.find_by_id(id=aid)
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
    # 每项独立间隔：只要本次提交带了任一 *_interval 字段就按项重算
    intervals_present = any(
        getattr(data, f"auto_fetch_{k}_interval") is not None
        for k in AUTO_FETCH_TASK_KEYS
    )
    if intervals_present:
        for k in AUTO_FETCH_TASK_KEYS:
            raw = getattr(data, f"auto_fetch_{k}_interval")
            cur = getattr(item, f"auto_fetch_{k}_interval", None)
            # raw 为 None 表示本次未携带该项，保留原值；否则规范化（空串=关闭）
            new_iv = _norm_interval(raw) if raw is not None else (cur or None)
            prev_on = bool((cur or "").strip())
            now_on = bool(new_iv)
            setattr(item, f"auto_fetch_{k}_interval", new_iv)
            setattr(item, f"auto_fetch_{k}", 1 if now_on else 0)
            # 新开启（关→开）或关闭时清空该项上次时间：开启后尽快执行、关闭后不残留节流
            if (now_on and not prev_on) or not now_on:
                setattr(item, f"auto_fetch_{k}_last_at", None)
        item.is_open = 1 if any(
            bool((getattr(item, f"auto_fetch_{k}_interval", None) or "").strip())
            for k in AUTO_FETCH_TASK_KEYS
        ) else 0

    # 自动上架账号级开关：独立于各同步项，保留用户选择
    if data.auto_fetch_relist is not None:
        item.auto_fetch_relist = 1 if _normalize_is_open(data.auto_fetch_relist) else 0

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


def delete_mercari_account(aid: int):
    item = MercariAccountModel.find_by_id(id=aid)
    if not item:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not item.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}
