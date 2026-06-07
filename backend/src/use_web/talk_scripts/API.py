# -*- coding: utf-8 -*-
"""话术表 API 路由（对应前端 /system/talk-scripts 页面）。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web/talk-scripts
- 完整 URL 示例:
    GET    /mercariV2/src/use_web/talk-scripts
    GET    /mercariV2/src/use_web/talk-scripts/categories
    POST   /mercariV2/src/use_web/talk-scripts
    PUT    /mercariV2/src/use_web/talk-scripts/{sid}
    DELETE /mercariV2/src/use_web/talk-scripts/{sid}
    POST   /mercariV2/src/use_web/talk-scripts/{sid}/use
"""

from fastapi import APIRouter

from .units.talk_scripts_handler import (
    create_script,
    delete_script,
    list_categories,
    list_scripts,
    mark_used,
    update_script,
)

router = APIRouter()

router.add_api_route("", list_scripts, methods=["GET"])
router.add_api_route("/categories", list_categories, methods=["GET"])
router.add_api_route("", create_script, methods=["POST"])
router.add_api_route("/{sid}", update_script, methods=["PUT"])
router.add_api_route("/{sid}", delete_script, methods=["DELETE"])
router.add_api_route("/{sid}/use", mark_used, methods=["POST"])
