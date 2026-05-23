# -*- coding: utf-8 -*-
"""お知らせ通知 API 路由（对应前端 /notifications 页面）。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web/notifications
- 完整 URL 示例:
    GET  /mercariV2/src/use_web/notifications
    POST /mercariV2/src/use_web/notifications/sync
    GET  /mercariV2/src/use_web/notifications/kinds
    POST /mercariV2/src/use_web/notifications/mark-read
    POST /mercariV2/src/use_web/notifications/mark-all-read
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter

from .units.notifications_models import MarkReadRequest, SyncNotificationsRequest
from .units.notifications_query import (
    list_kinds,
    list_notifications,
    mark_all_read,
    mark_read,
)
from .units.notifications_sync import sync_notifications

router = APIRouter()


def _list_notifications_endpoint(
    account_id: Optional[int] = None,
    kind: Optional[str] = None,
    keyword: Optional[str] = None,
    only_unread: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    return list_notifications(
        account_id=account_id,
        kind=kind,
        keyword=keyword,
        only_unread=only_unread,
        page=page,
        page_size=page_size,
    )


def _list_kinds_endpoint() -> Dict[str, Any]:
    return {"kinds": list_kinds()}


def _mark_read_endpoint(req: MarkReadRequest) -> Dict[str, Any]:
    return mark_read(req.ids, is_read=req.is_read)


def _mark_all_read_endpoint(account_id: Optional[int] = None) -> Dict[str, Any]:
    return mark_all_read(account_id=account_id)


async def _sync_endpoint(req: SyncNotificationsRequest) -> Dict[str, Any]:
    return await sync_notifications(req)


router.add_api_route("", _list_notifications_endpoint, methods=["GET"])
router.add_api_route("/kinds", _list_kinds_endpoint, methods=["GET"])
router.add_api_route("/sync", _sync_endpoint, methods=["POST"])
router.add_api_route("/mark-read", _mark_read_endpoint, methods=["POST"])
router.add_api_route("/mark-all-read", _mark_all_read_endpoint, methods=["POST"])
