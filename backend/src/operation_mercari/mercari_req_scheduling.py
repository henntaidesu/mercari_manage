# -*- coding: utf-8 -*-
"""
Mercari 统一请求调度模块

职责：
1. 直接从数据库读取煤炉账号请求头信息（避免通过 HTTP 接口访问引发鉴权问题）
2. 将数据库中存储的字段名映射为标准 HTTP 请求头
3. 提供 send_request(method, url, json_body) 统一接口，支持 GET / POST
4. 每次发起 Mercari 请求前随机休眠 1.0～3.0 秒，降低请求频率
"""

import random
import time

import requests
from typing import Any, Dict, Optional

from ..db_manage.models.meilu_account import MeiluAccountModel

# 数据库字段名 -> 标准 HTTP 请求头名 映射
_HEADER_FIELD_MAP: Dict[str, str] = {
    "accept":          "Accept",
    "x_app_type":      "X-App-Type",
    "authorization":   "Authorization",
    "dpop":            "DPoP",
    "priority":        "Priority",
    "accept_language": "Accept-Language",
    "accept_encoding": "Accept-Encoding",
    "user_agent":      "User-Agent",
    "x_app_version":   "X-App-Version",
    "x_platform":      "X-Platform",
    "x_mcc":           "X-Mcc",
}


def _fetch_active_account(account_id: Optional[int] = None) -> Dict[str, Any]:
    """
    直接从数据库获取煤炉账号信息。

    :param account_id: 指定账号 ID；为 None 时自动选取第一个 active 账号。
    :return: 账号记录字典（含解析后的 value 字段）。
    :raises RuntimeError: 找不到可用账号时抛出。
    """
    if account_id is not None:
        record = MeiluAccountModel.find_by_id(id=account_id)
        if not record:
            raise RuntimeError(f"未找到 ID={account_id} 的煤炉账号")
        d = record.to_dict()
        d['value'] = MeiluAccountModel._parse_value_json(
            d['value'] if isinstance(d.get('value'), str) else None
        )
        return d

    # 自动选取第一个 active 账号
    records = MeiluAccountModel.find_all(
        where="[status] = ?",
        params=("active",),
        order_by="id ASC",
        limit=1,
    )
    if not records:
        raise RuntimeError("数据库中无可用的 active 状态煤炉账号，请先在账号管理页面添加账号")

    d = records[0].to_dict()
    d['value'] = MeiluAccountModel._parse_value_json(
        d['value'] if isinstance(d.get('value'), str) else None
    )
    return d


def build_headers(account_id: Optional[int] = None) -> Dict[str, str]:
    """
    根据账号信息构建标准 HTTP 请求头字典。

    :param account_id: 指定账号 ID；为 None 时自动选取 active 账号。
    :return: 可直接传给 requests 的请求头字典。
    """
    account = _fetch_active_account(account_id)
    value: Dict[str, str] = account.get("value") or {}

    headers: Dict[str, str] = {}
    for field_key, header_name in _HEADER_FIELD_MAP.items():
        val = (value.get(field_key) or "").strip()
        if val:
            headers[header_name] = val

    if not headers.get("Authorization"):
        raise RuntimeError(f"账号 '{account.get('account_name')}' 缺少 Authorization 字段，请完善请求头配置")

    return headers


def send_request(
    method: str,
    url: str,
    json_body: Optional[Dict[str, Any]] = None,
    account_id: Optional[int] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    统一网络请求入口。

    :param method:        请求类型，"GET" 或 "POST"（大小写均可）。
    :param url:           请求目标 URL。
    :param json_body:     POST 请求体（JSON 对象），GET 请求时忽略。
    :param account_id:    指定使用的账号 ID；为 None 时自动选取 active 账号。
    :param extra_headers: 额外请求头，会覆盖账号默认头中的同名字段。
    :param timeout:       请求超时秒数，默认 30 秒。
    :return:              响应 JSON 反序列化后的字典。
    注意: 发请求前会随机 sleep [1.0, 3.0] 秒。
    :raises ValueError:   method 不为 GET / POST 时抛出。
    :raises RuntimeError: 请求失败或响应非 JSON 时抛出。
    """
    headers = build_headers(account_id)
    if extra_headers:
        headers.update(extra_headers)

    method_upper = method.upper()
    time.sleep(random.uniform(1.0, 3.0))
    try:
        if method_upper == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method_upper == "POST":
            response = requests.post(url, headers=headers, json=json_body, timeout=timeout)
        else:
            raise ValueError(f"不支持的请求类型: {method}，仅支持 GET / POST")

        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"HTTP 请求失败 [{method_upper} {url}]: {exc.response.status_code} {exc.response.text[:200]}"
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"网络请求异常 [{method_upper} {url}]: {exc}") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"响应非 JSON 格式 [{method_upper} {url}]: {response.text[:200]}") from exc
