# -*- coding: utf-8 -*-
"""
Mercari 统一请求调度模块

职责：
1. 直接从数据库读取煤炉账号请求头信息（避免通过 HTTP 接口访问引发鉴权问题）
2. 将数据库中存储的字段名映射为标准 HTTP 请求头
3. 提供 send_request(...) 统一接口，支持 GET / POST；DPoP 按 dpop_for 选用 dpop_list、dpop_info、dpop_on_sale_list、dpop_item_get_info（见各模块注释）
4. 每次发起 Mercari 请求前随机休眠 1.0～3.0 秒，降低请求频率

SSL：默认校验证书。若出现 CERTIFICATE_VERIFY_FAILED / self-signed certificate in chain（常见于公司代理、
Charles 等 MITM），可设置环境变量 MERCARI_REQUESTS_VERIFY：
  - 0 / false / no / off — 关闭校验（仅建议本机调试）
  - 绝对路径 — 指向合并后的 CA 证书文件（.pem），供 requests 校验代理根证书
未设置时与 requests 默认行为一致（verify=True）。
"""

import os
import random
import time

import requests
import urllib3
from typing import Any, Dict, Literal, Optional, Union

from ..db_manage.models.meilu_account import MeiluAccountModel

# items/get_items、出售中/履歴列表等：DPoP 用 dpop_list（或旧键 dpop）
DPOP_FOR_ITEMS_LIST: Literal["list"] = "list"
# GET transaction_evidences/get?_datetime_format=U&item_id=…（订单详情回填）：仅 dpop_info，不可回退
DPOP_FOR_ITEM_INFO: Literal["info"] = "info"
# GET items/get_items 在售列表（status=on_sale,stop 等）：仅 dpop_on_sale_list（须针对完整查询串生成）
DPOP_FOR_ON_SALE_LIST: Literal["on_sale_list"] = "on_sale_list"
# GET items/get?id=…&include_*=…（单件商品详情）：仅 dpop_item_get_info
DPOP_FOR_ITEM_GET_INFO: Literal["item_get_info"] = "item_get_info"

DpopFor = Literal["list", "info", "on_sale_list", "item_get_info"]

# 数据库字段名 -> 标准 HTTP 请求头名 映射（DPoP 由 _dpop_header_value + dpop_for 单独注入）
_HEADER_FIELD_MAP: Dict[str, str] = {
    "accept":          "Accept",
    "x_app_type":      "X-App-Type",
    "authorization":   "Authorization",
    "priority":        "Priority",
    "accept_language": "Accept-Language",
    "accept_encoding": "Accept-Encoding",
    "user_agent":      "User-Agent",
    "x_app_version":   "X-App-Version",
    "x_platform":      "X-Platform",
    "x_mcc":           "X-Mcc",
}


def _requests_verify() -> Union[bool, str]:
    """供 requests 的 verify 参数：True / False / CA 文件路径。见模块文档 MERCARI_REQUESTS_VERIFY。"""
    raw = (os.environ.get("MERCARI_REQUESTS_VERIFY") or "").strip()
    if not raw:
        return True
    low = raw.lower()
    if low in ("0", "false", "no", "off"):
        return False
    if os.path.isfile(raw):
        return raw
    return True


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


def _dpop_header_value(value: Dict[str, Any], dpop_for: DpopFor) -> str:
    """
    从账号 value 中解析发往 HTTP 头 DPoP 的 JWT 字符串。

    Mercari 侧 DPoP 与请求 URL（及方法）绑定。
    list=dpop_list：items/get_items（如订单用 trading）等。
    info=仅 dpop_info：GET transaction_evidences/get，空则抛错。
    on_sale_list=仅 dpop_on_sale_list：GET items/get_items（在售 status=on_sale,stop 等完整 URL），空则抛错。
    item_get_info=仅 dpop_item_get_info：GET items/get（单件详情完整 URL），空则抛错。
    """
    if dpop_for == "info":
        return (value.get("dpop_info") or "").strip()
    if dpop_for == "on_sale_list":
        return (value.get("dpop_on_sale_list") or "").strip()
    if dpop_for == "item_get_info":
        return (value.get("dpop_item_get_info") or "").strip()
    return (value.get("dpop_list") or value.get("dpop") or "").strip()


def build_headers(
    account_id: Optional[int] = None,
    dpop_for: DpopFor = "list",
) -> Dict[str, str]:
    """
    根据账号信息构建标准 HTTP 请求头字典。

    :param account_id: 指定账号 ID；为 None 时自动选取 active 账号。
    :param dpop_for:   \"list\"：dpop_list；
                       \"info\"：仅 dpop_info，空则抛错；
                       \"on_sale_list\"：仅 dpop_on_sale_list（在售商品列表 URL），空则抛错；
                       \"item_get_info\"：仅 dpop_item_get_info（GET items/get 单件详情 URL），空则抛错。
    :return: 可直接传给 requests 的请求头字典。
    """
    account = _fetch_active_account(account_id)
    value: Dict[str, str] = account.get("value") or {}

    headers: Dict[str, str] = {}
    for field_key, header_name in _HEADER_FIELD_MAP.items():
        val = (value.get(field_key) or "").strip()
        if val:
            headers[header_name] = val

    dpop_jwt = _dpop_header_value(value, dpop_for)
    if dpop_for == "info" and not dpop_jwt:
        raise RuntimeError(
            f"账号 '{account.get('account_name')}' 缺少 dpop_info："
            "订单详情（transaction_evidences/get）须使用针对该 URL 的 DPoP，请补全 dpop_info 字段"
        )
    if dpop_for == "on_sale_list" and not dpop_jwt:
        raise RuntimeError(
            f"账号 '{account.get('account_name')}' 缺少 dpop_on_sale_list："
            "在售商品列表（items/get_items，status=on_sale,stop 等）须单独配置 DPoP_OnSale-List（dpop_on_sale_list）"
        )
    if dpop_for == "item_get_info" and not dpop_jwt:
        raise RuntimeError(
            f"账号 '{account.get('account_name')}' 缺少 dpop_item_get_info："
            "单件商品详情（GET items/get?id=…）须单独配置 DPoP_ItemGet-Info（dpop_item_get_info）"
        )
    if dpop_jwt:
        headers["DPoP"] = dpop_jwt

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
    dpop_for: DpopFor = "list",
) -> Dict[str, Any]:
    """
    统一网络请求入口。

    :param method:        请求类型，"GET" 或 "POST"（大小写均可）。
    :param url:           请求目标 URL。
    :param json_body:     POST 请求体（JSON 对象），GET 请求时忽略。
    :param account_id:    指定使用的账号 ID；为 None 时自动选取 active 账号。
    :param extra_headers: 额外请求头，会覆盖账号默认头中的同名字段。
    :param timeout:       请求超时秒数，默认 30 秒。
    :param dpop_for:      同 build_headers；on_sale_list / item_get_info 时须配置对应 dpop 字段。
    :return:              响应 JSON 反序列化后的字典。
    注意: 发请求前会随机 sleep [1.0, 3.0] 秒。
    :raises ValueError:   method 不为 GET / POST 时抛出。
    :raises RuntimeError: 请求失败或响应非 JSON 时抛出。
    """
    headers = build_headers(account_id, dpop_for=dpop_for)
    if extra_headers:
        headers.update(extra_headers)

    method_upper = method.upper()
    verify = _requests_verify()
    if verify is False:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    time.sleep(random.uniform(1.0, 3.0))
    try:
        if method_upper == "GET":
            response = requests.get(
                url, headers=headers, timeout=timeout, verify=verify
            )
        elif method_upper == "POST":
            response = requests.post(
                url,
                headers=headers,
                json=json_body,
                timeout=timeout,
                verify=verify,
            )
        else:
            raise ValueError(f"不支持的请求类型: {method}，仅支持 GET / POST")

        response.raise_for_status()
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else ""
        raise RuntimeError(
            f"HTTP 请求失败 [{method_upper} {url}]: {exc.response.status_code} {body}"
        ) from exc
    except requests.RequestException as exc:
        # 异常信息放前，避免长 URL 占满日志；便于对接口返回 502 时看到根因（超时/SSL/代理/DNS）
        hint = ""
        es = f"{type(exc).__name__}: {exc}"
        if "CERTIFICATE_VERIFY_FAILED" in es or "SSL" in es.upper():
            hint = "（若本机走代理/抓包，可设环境变量 MERCARI_REQUESTS_VERIFY=0 或指向 CA 文件，见 mercari_req_scheduling 模块注释）"
        elif "timed out" in es.lower() or "timeout" in es.lower():
            hint = f"（当前 timeout={timeout}s，仍失败多为网络不可达或需代理访问 api.mercari.jp）"
        raise RuntimeError(f"网络请求异常: {es}{hint} | {method_upper} {url}") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"响应非 JSON 格式 [{method_upper} {url}]: {response.text}") from exc
