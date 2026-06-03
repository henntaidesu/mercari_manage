# -*- coding: utf-8 -*-
"""
打开 jp.mercari.com/notifications 页面，等待 MITM 截获 ``services/notification/v1/list`` 响应。

返回扁平 items 列表（聚合所有分页）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ....ssl_mitm_proxy.capture_config import read_notification_response
from ....web_drive.core.manager import EdgeWebDriveManager
from ....web_drive.core.mitm_session import wait_mitm_capture

log = logging.getLogger(__name__)

NOTIFICATIONS_PAGE_URL = "https://jp.mercari.com/notifications"

_PAGE_TIMEOUT_SEC = 45


async def capture_notifications_via_mitm_session(
    mgr: EdgeWebDriveManager,
    auto_key: str,
    *,
    since_ms: int,
) -> List[Dict[str, Any]]:
    """轮询截获 MITM 写入的 notification 响应；仅抓取首页（不翻页）。

    调用方需在打开浏览器**之前**先 ``clear_notification_response_file()``
    并取 ``since_ms=int(time.time()*1000)``，否则浏览器首次请求的响应会被
    本函数误判为旧数据而丢弃。
    """
    data = await wait_mitm_capture(
        mgr=mgr,
        auto_key=auto_key,
        start_url=NOTIFICATIONS_PAGE_URL,
        read_response=read_notification_response,
        since_ms=since_ms,
        wait_seconds=_PAGE_TIMEOUT_SEC,
        error_detail="services/notification/v1/list",
    )
    body = data.get("body") if isinstance(data, dict) else None
    if not isinstance(body, dict):
        log.warning("[notification] 响应体异常，无数据可入库")
        return []
    chunk = body.get("data") or []
    items: List[Dict[str, Any]] = chunk if isinstance(chunk, list) else []
    log.info("[notification] 抓取完成，共 %d 条（仅首页）", len(items))
    return items
