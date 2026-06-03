# -*- coding: utf-8 -*-
"""订单相关响应文件：trading_list / sold_out_list / transaction_evidence"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from ..paths import ssl_mitm_data_dir
from ._core import _lock, canonical_mercari_item_id


def trading_list_response_path(seller_id: str) -> str:
    """出售中订单列表：``items/get_items``（status=trading）响应，按 seller_id 分文件。"""
    sid = str(int(str(seller_id).strip()))
    return os.path.join(ssl_mitm_data_dir(), f"items_get_items_trading_response_{sid}.json")

def clear_trading_list_response_file(seller_id: str) -> None:
    p = trading_list_response_path(seller_id)
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_trading_list_response(seller_id: str, payload: Dict[str, Any]) -> None:
    sid = str(int(str(seller_id).strip()))
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = trading_list_response_path(sid)
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_trading_list_response(seller_id: str) -> Optional[Dict[str, Any]]:
    path = trading_list_response_path(seller_id)
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

def sold_out_list_response_path(seller_id: str) -> str:
    """已售完历史：``items/get_items``（status=sold_out）响应，按 seller_id 分文件。"""
    sid = str(int(str(seller_id).strip()))
    return os.path.join(ssl_mitm_data_dir(), f"items_get_items_sold_out_response_{sid}.json")

def clear_sold_out_list_response_file(seller_id: str) -> None:
    p = sold_out_list_response_path(seller_id)
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_sold_out_list_response(seller_id: str, payload: Dict[str, Any]) -> None:
    sid = str(int(str(seller_id).strip()))
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = sold_out_list_response_path(sid)
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_sold_out_list_response(seller_id: str) -> Optional[Dict[str, Any]]:
    path = sold_out_list_response_path(seller_id)
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

def transaction_evidence_response_path(item_id: str) -> str:
    cid = canonical_mercari_item_id(item_id)
    return os.path.join(ssl_mitm_data_dir(), f"transaction_evidences_get_response_{cid}.json")

def clear_transaction_evidence_response_file(item_id: str) -> None:
    p = transaction_evidence_response_path(item_id)
    with _lock:
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass

def atomic_write_transaction_evidence_response(item_id: str, payload: Dict[str, Any]) -> None:
    cid = canonical_mercari_item_id(item_id)
    if not cid:
        return
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = transaction_evidence_response_path(cid)
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

def read_transaction_evidence_response(item_id: str) -> Optional[Dict[str, Any]]:
    path = transaction_evidence_response_path(item_id)
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
