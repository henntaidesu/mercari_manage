# -*- coding: utf-8 -*-
"""
监控 api.mercari.jp 的 items/get_items（status=trading）请求，将头写入配置文件。

配置文件：backend/ssl_mitm/items_get_items_capture.json（由 mitm 插件原子写入）
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .paths import ssl_mitm_data_dir

_lock = threading.Lock()

# 与 meilu 账号 value 中字段名一致；DPoP HTTP 头 → dpop_list
HEADER_MAP_TO_VALUE = (
    ("authorization", "authorization"),
    ("dpop", "dpop_list"),
    ("dpop-list", "dpop_list"),
    ("user-agent", "user_agent"),
    ("accept", "accept"),
    ("accept-language", "accept_language"),
    ("accept-encoding", "accept_encoding"),
    ("priority", "priority"),
    ("x-platform", "x_platform"),
    ("x-app-version", "x_app_version"),
    ("sec-ch-ua", "sec_ch_ua"),
    ("sec-ch-ua-mobile", "sec_ch_ua_mobile"),
    ("sec-ch-ua-platform", "sec_ch_ua_platform"),
    ("origin", "origin"),
    ("referer", "referer"),
    ("sec-fetch-site", "sec_fetch_site"),
    ("sec-fetch-mode", "sec_fetch_mode"),
    ("sec-fetch-dest", "sec_fetch_dest"),
)


def capture_json_path() -> str:
    return os.path.join(ssl_mitm_data_dir(), "items_get_items_capture.json")


def session_marker_path(account_id: int) -> str:
    return os.path.join(ssl_mitm_data_dir(), f"capture_marker_{account_id}.txt")


def write_session_marker_ms(account_id: int, ts_ms: int) -> None:
    os.makedirs(ssl_mitm_data_dir(), exist_ok=True)
    p = session_marker_path(account_id)
    with open(p, "w", encoding="utf-8") as f:
        f.write(str(ts_ms))


def read_session_marker_ms(account_id: int) -> Optional[int]:
    p = session_marker_path(account_id)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return int((f.read() or "0").strip())
    except (ValueError, OSError):
        return None


def clear_session_marker(account_id: int) -> None:
    p = session_marker_path(account_id)
    try:
        if os.path.isfile(p):
            os.remove(p)
    except OSError:
        pass


def parse_items_get_items(
    flow_url: str, path: str, host: str, raw_query: str = ""
) -> Optional[Dict[str, Any]]:
    """若匹配 api.mercari.jp items/get_items 且 status=trading，则返回 seller_id / full_url。"""
    h = (host or "").lower().strip()
    if "api.mercari.jp" not in h:
        return None
    pth = path or ""
    if "items/get_items" not in pth and "items/get_items" not in (flow_url or ""):
        return None
    try:
        u = (flow_url or "").strip()
        if not u.startswith("http"):
            q = f"?{raw_query}" if raw_query else ""
            u = f"https://{h}{pth}{q}"
        qd = parse_qs(urlparse(u).query)
        sid_list = qd.get("seller_id") or qd.get("sellerId") or []
        sid = (sid_list[0] or "").strip() if sid_list else ""
        status_vals = [(x or "").strip().lower() for x in qd.get("status", [])]
        if not status_vals or "trading" not in status_vals:
            return None
        if not sid.isdigit():
            return None
        return {"seller_id": sid, "full_url": u}
    except Exception:
        return None


def headers_to_value_dict(flow_headers: Any) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for hk, vk in HEADER_MAP_TO_VALUE:
        raw = None
        try:
            raw = flow_headers.get(hk)
        except Exception:
            raw = None
        if raw is None:
            try:
                for k in list(flow_headers.keys()):
                    kn = k.decode("utf-8", "replace") if isinstance(k, bytes) else str(k)
                    if kn.lower() == hk.lower():
                        raw = flow_headers.get(kn)
                        break
            except Exception:
                pass
        if raw is None:
            continue
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        val = str(raw).strip()
        if val:
            out[vk] = val
    if out.get("dpop_list") and not out.get("dpop_info"):
        out["dpop_info"] = out["dpop_list"]
    return out


def atomic_write_capture_file(payload: Dict[str, Any]) -> None:
    d = ssl_mitm_data_dir()
    os.makedirs(d, exist_ok=True)
    path = capture_json_path()
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)


def read_capture_file() -> Optional[Dict[str, Any]]:
    path = capture_json_path()
    if not os.path.isfile(path):
        return None
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

