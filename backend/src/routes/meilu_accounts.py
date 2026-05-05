# -*- coding: utf-8 -*-
import asyncio
import json
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel as PydanticModel, Field

from ..db_manage.models.meilu_account import MeiluAccountModel
from ..ssl_mitm_proxy.capture_config import (
    clear_session_marker,
    read_capture_file,
    write_session_marker_ms,
)
from ..ssl_mitm_proxy.runner import default_mitm_proxy_url, start_mitm_proxy
from ..web_drive import get_web_drive_manager

router = APIRouter(prefix="/api/meilu-accounts", tags=["meilu-accounts"])

ALLOWED_STATUS = {"active", "disabled"}
ALLOWED_FETCH_INTERVALS = frozenset({"10", "30", "60", "3h", "6h", "12h", "24h"})

# 与 jp.mercari.com Web 抓包一致；可选：在售列表 / 单件详情专用 DPoP
_HEADER_FIELD_LABELS = [
    ("x_platform", "X-Platform"),
    ("authorization", "Authorization"),
    ("sec_ch_ua_platform", "Sec-CH-UA-Platform"),
    ("accept_language", "Accept-Language"),
    ("sec_ch_ua", "Sec-CH-UA"),
    ("sec_ch_ua_mobile", "Sec-CH-UA-Mobile"),
    ("dpop_list", "DPoP_List"),
    ("dpop_info", "DPoP_Info"),
    ("dpop_on_sale_list", "DPoP_OnSale-List"),
    ("dpop_item_get_info", "DPoP_ItemGet-Info"),
    ("user_agent", "User-Agent"),
    ("accept", "Accept"),
    ("origin", "Origin"),
    ("sec_fetch_site", "Sec-Fetch-Site"),
    ("sec_fetch_mode", "Sec-Fetch-Mode"),
    ("sec_fetch_dest", "Sec-Fetch-Dest"),
    ("referer", "Referer"),
    ("accept_encoding", "Accept-Encoding"),
    ("priority", "Priority"),
]


class MeiluAccountCreate(PydanticModel):
    account_name: str
    value: Dict[str, Any]
    login_id: Optional[str] = None
    seller_id: Optional[str] = None
    status: str = "active"
    remark: Optional[str] = None
    is_open: int = 0
    fetch_interval: Optional[str] = None


class MeiluAccountUpdate(PydanticModel):
    account_name: Optional[str] = None
    login_id: Optional[str] = None
    seller_id: Optional[str] = None
    value: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    remark: Optional[str] = None
    is_open: Optional[int] = None
    fetch_interval: Optional[str] = None


class FetchAuthViaMitmBody(PydanticModel):
    """通过 MITM 抓取 items/get_items（trading）请求头并写回账号。"""

    wait_seconds: int = Field(120, ge=30, le=300)
    open_browser: bool = True


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


def _apply_mitm_patch_to_account(item: MeiluAccountModel, patch: Dict[str, Any]) -> None:
    """将 MITM 写入的 value_patch 合并进现有 value，再经 _norm_headers_dict 校验。"""
    cur = MeiluAccountModel._parse_value_json(item.value)
    for k, v in (patch or {}).items():
        if v is not None and str(v).strip():
            cur[str(k)] = str(v).strip()
    if cur.get("dpop_list") and not (cur.get("dpop_info") or "").strip():
        cur["dpop_info"] = cur["dpop_list"]
    normalized = _norm_headers_dict(cur)
    item.value = json.dumps(normalized, ensure_ascii=False)


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
        seller_id=_norm_seller_id(data.seller_id),
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
    if data.is_open is not None or data.fetch_interval is not None:
        io = _normalize_is_open(data.is_open if data.is_open is not None else item.is_open)
        fi = data.fetch_interval if data.fetch_interval is not None else item.fetch_interval
        io, fi = _norm_auto_fetch(io, fi)
        item.is_open = io
        item.fetch_interval = fi

    if not item.save():
        raise HTTPException(status_code=500, detail="更新失败")
    return _item_api_dict(item)


@router.post("/{aid}/fetch-auth-via-mitm")
async def fetch_auth_via_mitm(
    aid: int,
    body: Optional[FetchAuthViaMitmBody] = Body(default=None),
):
    """
    启动 MITM（若未运行）、可选带代理打开 Edge，等待捕获
    ``api.mercari.jp/items/get_items?...&status=trading`` 后合并 Authorization、
    DPoP→dpop_list 等到账号，并写入 ``ssl_mitm/items_get_items_capture.json``。
    """
    cfg = body or FetchAuthViaMitmBody()
    r = start_mitm_proxy()
    if r.get("error"):
        raise HTTPException(status_code=500, detail=r["error"])

    item = MeiluAccountModel.find_by_id(id=aid)
    if not item:
        raise HTTPException(status_code=404, detail="账号不存在")
    sid = _norm_seller_id(item.seller_id)
    if not sid:
        raise HTTPException(status_code=400, detail="请先填写卖家 ID（须与请求中 seller_id 一致）")

    t0 = int(time.time() * 1000)
    write_session_marker_ms(aid, t0)
    try:
        if cfg.open_browser:
            mgr = get_web_drive_manager()
            await mgr.close_session(f"meilu_{aid}")
            await mgr.open_session(
                f"meilu_{aid}",
                headless=False,
                start_url="https://jp.mercari.com/mypage/listings",
                proxy_server=default_mitm_proxy_url(),
            )

        deadline = time.monotonic() + cfg.wait_seconds
        cap = None
        while time.monotonic() < deadline:
            data = read_capture_file()
            if data and str(data.get("seller_id") or "").strip() == sid:
                if int(data.get("ts") or 0) >= t0:
                    cap = data
                    break
            await asyncio.sleep(0.9)

        if not cap:
            raise HTTPException(
                status_code=408,
                detail="超时未捕获到请求：请安装 MITM 根证书（/api/ssl-mitm/ca-cert），"
                "开启本流程后请在浏览器打开会产生「取引中」列表的请求（items/get_items & status=trading）。",
            )

        patch = cap.get("value_patch") or {}
        if not patch:
            raise HTTPException(status_code=500, detail="捕获数据为空")

        _apply_mitm_patch_to_account(item, patch)
        if not item.save():
            raise HTTPException(status_code=500, detail="保存失败")
        return {"success": True, "data": _item_api_dict(item), "capture_meta": {"url": cap.get("url"), "ts": cap.get("ts")}}
    finally:
        clear_session_marker(aid)


@router.delete("/{aid}")
def delete_meilu_account(aid: int):
    item = MeiluAccountModel.find_by_id(id=aid)
    if not item:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not item.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}
