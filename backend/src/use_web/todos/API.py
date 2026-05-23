# -*- coding: utf-8 -*-
"""代办事项 API 路由（对应前端 /todos 页面）。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web/todos
- 完整 URL 示例:
    GET  /mercariV2/src/use_web/todos
    POST /mercariV2/src/use_web/todos/sync
    GET  /mercariV2/src/use_web/todos/kinds
"""

from typing import Optional

from fastapi import APIRouter

from .units.todos_query import list_kinds, list_todos
from .units.todos_sync import sync_todos

router = APIRouter()


def _list_todos_endpoint(
    account_id: Optional[int] = None,
    kind: Optional[str] = None,
    keyword: Optional[str] = None,
    include_deleted: bool = False,
    page: int = 1,
    page_size: int = 20,
):
    return list_todos(
        account_id=account_id,
        kind=kind,
        keyword=keyword,
        include_deleted=include_deleted,
        page=page,
        page_size=page_size,
    )


def _list_kinds_endpoint():
    return {"kinds": list_kinds()}


router.add_api_route("", _list_todos_endpoint, methods=["GET"])
router.add_api_route("/kinds", _list_kinds_endpoint, methods=["GET"])
router.add_api_route("/sync", sync_todos, methods=["POST"])
