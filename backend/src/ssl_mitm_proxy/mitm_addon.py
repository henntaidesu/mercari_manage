# -*- coding: utf-8 -*-
"""mitmproxy 插件：拦截 items/get_items（trading）并写入 items_get_items_capture.json"""

from __future__ import annotations

import os
import sys
import time

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mitmproxy import http  # noqa: E402

from src.ssl_mitm_proxy.capture_config import (  # noqa: E402
    atomic_write_capture_file,
    headers_to_value_dict,
    parse_items_get_items,
)


class ItemsGetItemsCapture:
    def request(self, flow: http.HTTPFlow) -> None:
        try:
            req = flow.request
            host = req.host or ""
            path = req.path or ""
            url = req.pretty_url or ""
            try:
                qraw = req.query
                if isinstance(qraw, bytes):
                    qstr = qraw.decode("utf-8", "replace")
                else:
                    qstr = str(qraw or "")
            except Exception:
                qstr = ""
            meta = parse_items_get_items(url, path, host, qstr)
            if not meta:
                return
            value_headers = headers_to_value_dict(req.headers)
            if not value_headers:
                return
            payload = {
                "ts": int(time.time() * 1000),
                "seller_id": meta["seller_id"],
                "url": meta.get("full_url") or url,
                "value_patch": value_headers,
            }
            atomic_write_capture_file(payload)
        except Exception:
            pass


addons = [ItemsGetItemsCapture()]
