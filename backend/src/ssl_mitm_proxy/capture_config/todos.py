# -*- coding: utf-8 -*-
"""待办相关响应文件：todolist / shipping_info / transaction_messages / shipping_classes"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from ..paths import ssl_mitm_data_dir
from ._core import _lock


# ============ 待办事项 services/todolist/v1/list ============
# 请求路径不含 seller_id，多账号通过 run_mercari_serial_async 串行隔离；
# 单一 latest 文件即可，同步函数进入时 clear、抓取后 read。

def todolist_response_path() -> str:
    return os.path.join(ssl_mitm_data_dir(), "todolist_latest_response.json")

def clear_todolist_response_file() -> None:
    p = todolist_response_path()
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_todolist_response(payload: Dict[str, Any]) -> None:
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = todolist_response_path()
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_todolist_response() -> Optional[Dict[str, Any]]:
    path = todolist_response_path()
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

# ============ 交易详情：shipping/get_info（按 transaction_evidence_id 但用 latest 即可） ============
# 同 todolist：浏览器在 run_mercari_serial_async 内串行，单一 latest 文件就够。

def shipping_info_response_path() -> str:
    return os.path.join(ssl_mitm_data_dir(), "shipping_info_latest_response.json")

def clear_shipping_info_response_file() -> None:
    p = shipping_info_response_path()
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_shipping_info_response(payload: Dict[str, Any]) -> None:
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = shipping_info_response_path()
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_shipping_info_response() -> Optional[Dict[str, Any]]:
    path = shipping_info_response_path()
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

# ============ 交易详情：transaction_messages/get_messages ============

def transaction_messages_response_path() -> str:
    return os.path.join(ssl_mitm_data_dir(), "transaction_messages_latest_response.json")

def clear_transaction_messages_response_file() -> None:
    p = transaction_messages_response_path()
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_transaction_messages_response(payload: Dict[str, Any]) -> None:
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = transaction_messages_response_path()
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_transaction_messages_response() -> Optional[Dict[str, Any]]:
    path = transaction_messages_response_path()
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

# ============ 发货尺寸：shipping/get_shipping_classes ============

def shipping_classes_response_path() -> str:
    return os.path.join(ssl_mitm_data_dir(), "shipping_classes_latest_response.json")

def clear_shipping_classes_response_file() -> None:
    p = shipping_classes_response_path()
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_shipping_classes_response(payload: Dict[str, Any]) -> None:
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = shipping_classes_response_path()
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_shipping_classes_response() -> Optional[Dict[str, Any]]:
    path = shipping_classes_response_path()
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
