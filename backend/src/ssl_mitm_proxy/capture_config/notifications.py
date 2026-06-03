# -*- coding: utf-8 -*-
"""通知相关响应文件：notification / bundle_purchase / aggregated_desired_prices"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from ..paths import ssl_mitm_data_dir
from ._core import _lock, _safe_bundle_id, canonical_mercari_item_id


# ============ お知らせ：services/notification/v1/list ============
# 与 todolist 相同的设计：单一 latest 文件，同步函数进入时 clear、抓取后 read；
# 多账号通过 run_mercari_serial_async 串行隔离。

def notification_response_path() -> str:
    return os.path.join(ssl_mitm_data_dir(), "notification_latest_response.json")

def clear_notification_response_file() -> None:
    p = notification_response_path()
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_notification_response(payload: Dict[str, Any]) -> None:
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = notification_response_path()
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_notification_response() -> Optional[Dict[str, Any]]:
    path = notification_response_path()
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

def bundle_purchase_response_path(bundle_id: str) -> str:
    bid = _safe_bundle_id(bundle_id)
    return os.path.join(ssl_mitm_data_dir(), f"bundle_purchase_response_{bid}.json")

def clear_bundle_purchase_response_file(bundle_id: str) -> None:
    p = bundle_purchase_response_path(bundle_id)
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_bundle_purchase_response(bundle_id: str, payload: Dict[str, Any]) -> None:
    bid = _safe_bundle_id(bundle_id)
    if not bid:
        return
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = bundle_purchase_response_path(bid)
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_bundle_purchase_response(bundle_id: str) -> Optional[Dict[str, Any]]:
    path = bundle_purchase_response_path(bundle_id)
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

# ============ 降价请求(値下げ依頼)：/v2/aggregatedDesiredPriceItems/{item_id} ============
# 按 item_id 分文件，避免多商品并发覆盖。


def aggregated_desired_prices_response_path(item_id: str) -> str:
    cid = canonical_mercari_item_id(item_id)
    return os.path.join(
        ssl_mitm_data_dir(), f"aggregated_desired_prices_response_{cid}.json"
    )

def clear_aggregated_desired_prices_response_file(item_id: str) -> None:
    p = aggregated_desired_prices_response_path(item_id)
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_aggregated_desired_prices_response(
    item_id: str, payload: Dict[str, Any]
) -> None:
    cid = canonical_mercari_item_id(item_id)
    if not cid:
        return
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = aggregated_desired_prices_response_path(cid)
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_aggregated_desired_prices_response(item_id: str) -> Optional[Dict[str, Any]]:
    path = aggregated_desired_prices_response_path(item_id)
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
