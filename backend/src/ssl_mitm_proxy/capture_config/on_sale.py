# -*- coding: utf-8 -*-
"""在售相关响应文件：on_sale_list / item_get"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from ..paths import ssl_mitm_data_dir
from ._core import _lock, canonical_mercari_item_id


def on_sale_list_response_path(seller_id: str) -> str:
    """MITM 写入的「在售列表 items/get_items 响应体」按 seller_id 分文件，避免多账号并发覆盖。"""
    sid = str(int(str(seller_id).strip()))
    return os.path.join(ssl_mitm_data_dir(), f"items_get_items_on_sale_response_{sid}.json")

def clear_on_sale_list_response_file(seller_id: str) -> None:
    p = on_sale_list_response_path(seller_id)
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_on_sale_list_response(seller_id: str, payload: Dict[str, Any]) -> None:
    sid = str(int(str(seller_id).strip()))
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = on_sale_list_response_path(sid)
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_on_sale_list_response(seller_id: str) -> Optional[Dict[str, Any]]:
    path = on_sale_list_response_path(seller_id)
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

def item_get_response_path(item_id: str) -> str:
    cid = canonical_mercari_item_id(item_id)
    return os.path.join(ssl_mitm_data_dir(), f"items_get_response_{cid}.json")

def clear_item_get_response_file(item_id: str) -> None:
    p = item_get_response_path(item_id)
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_item_get_response(item_id: str, payload: Dict[str, Any]) -> None:
    cid = canonical_mercari_item_id(item_id)
    if not cid:
        return
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = item_get_response_path(cid)
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_item_get_response(item_id: str) -> Optional[Dict[str, Any]]:
    path = item_get_response_path(item_id)
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
