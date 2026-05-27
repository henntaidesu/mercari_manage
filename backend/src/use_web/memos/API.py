# -*- coding: utf-8 -*-
"""备忘录 / 站内信 API 路由（对应前端 /memos 页面）。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web/memos
- 完整 URL 示例:
    GET    /mercariV2/src/use_web/memos/inbox
    GET    /mercariV2/src/use_web/memos/sent
    GET    /mercariV2/src/use_web/memos/users
    GET    /mercariV2/src/use_web/memos/unread-count
    POST   /mercariV2/src/use_web/memos
    POST   /mercariV2/src/use_web/memos/mark-read
    POST   /mercariV2/src/use_web/memos/mark-all-read
    DELETE /mercariV2/src/use_web/memos/{mid}
"""

from fastapi import APIRouter

from .units.memos_handler import (
    create_memo,
    delete_memo,
    list_inbox,
    list_sent,
    list_users_for_memo,
    mark_all_read,
    mark_read,
    unread_count,
)

router = APIRouter()

router.add_api_route("/inbox", list_inbox, methods=["GET"])
router.add_api_route("/sent", list_sent, methods=["GET"])
router.add_api_route("/users", list_users_for_memo, methods=["GET"])
router.add_api_route("/unread-count", unread_count, methods=["GET"])
router.add_api_route("", create_memo, methods=["POST"])
router.add_api_route("/mark-read", mark_read, methods=["POST"])
router.add_api_route("/mark-all-read", mark_all_read, methods=["POST"])
router.add_api_route("/{mid}", delete_memo, methods=["DELETE"])
