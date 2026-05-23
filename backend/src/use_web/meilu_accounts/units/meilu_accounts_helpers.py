# -*- coding: utf-8 -*-
"""煤炉账号管理共享辅助函数：校验、规范化、序列化输出。"""
from typing import Any, Optional

from fastapi import HTTPException

from ....db_manage.models.meilu_account import MeiluAccountModel
from .meilu_accounts_models import (
    ALLOWED_FETCH_INTERVALS,
    ALLOWED_STATUS,
    _HEADER_FIELD_LABELS,
)


def _validate_status(status: str):
    if status not in ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail="账号状态错误")


def _norm_required_text(value: str, field_name: str) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail=f"{field_name}不能为空")
    return text


def _norm_seller_id(value: Optional[str]) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return None
    if not text.isdigit():
        raise HTTPException(status_code=400, detail="卖家ID必须为数字")
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


def _norm_auto_fetch(
    is_open: int,
    fetch_interval: Optional[str],
    order_status: int,
    order_list: int,
    on_sale: int,
    todos: int = 0,
) -> tuple:
    """
    规范化自动同步：总开关关闭时清空间隔与子任务；
    开启时须合法间隔且至少一项子任务为 1。
    """
    io = 1 if is_open else 0
    if io == 0:
        return 0, None, 0, 0, 0, 0
    iv = (fetch_interval or "").strip()
    if iv not in ALLOWED_FETCH_INTERVALS:
        raise HTTPException(status_code=400, detail="开启自动数据获取时，请选择有效的时间间隔")
    st = 1 if order_status else 0
    li = 1 if order_list else 0
    os_ = 1 if on_sale else 0
    td = 1 if todos else 0
    if not (st or li or os_ or td):
        raise HTTPException(status_code=400, detail="开启自动数据获取时，请至少选择一项同步任务")
    return 1, iv, st, li, os_, td


def _norm_headers_dict(d: Optional[dict]) -> dict:
    if not d or not isinstance(d, dict):
        raise HTTPException(status_code=400, detail="请求头 value 必须为 JSON 对象")
    # 旧版仅存 dpop：视为 dpop_list；仅有一条 DPoP 时 dpop_info 可暂与 list 相同
    d = dict(d)
    if not (str(d.get("dpop_list") or "").strip()) and (str(d.get("dpop") or "").strip()):
        d["dpop_list"] = str(d["dpop"]).strip()
    out = {}
    for key, label in _HEADER_FIELD_LABELS:
        raw = d.get(key)
        text = ("" if raw is None else str(raw)).strip()
        # 订单详情 / 在售列表 / 单件详情 等专用 DPoP：可选；不填则调用对应接口时再报错提示补全
        if key in ("dpop_info", "dpop_on_sale_list", "dpop_item_get_info"):
            out[key] = text
            continue
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
    d['auto_fetch_order_status'] = 1 if d.get('auto_fetch_order_status') else 0
    d['auto_fetch_order_list'] = 1 if d.get('auto_fetch_order_list') else 0
    d['auto_fetch_on_sale'] = 1 if d.get('auto_fetch_on_sale') else 0
    d['auto_fetch_todos'] = 1 if d.get('auto_fetch_todos') else 0
    return d
