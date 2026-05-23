# -*- coding: utf-8 -*-
"""分类管理接口。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web/categories
- 完整 URL 示例: GET /mercariV2/src/use_web/categories
"""
from fastapi import APIRouter

from .units.categories_handler import (
    create_category,
    delete_category,
    list_categories,
    update_category,
)

router = APIRouter()

router.add_api_route("", list_categories, methods=["GET"])
router.add_api_route("", create_category, methods=["POST"])
router.add_api_route("/{cid}", update_category, methods=["PUT"])
router.add_api_route("/{cid}", delete_category, methods=["DELETE"])
