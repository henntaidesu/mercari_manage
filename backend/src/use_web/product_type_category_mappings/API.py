# -*- coding: utf-8 -*-
"""商品类型与类目映射管理。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web/product_type_category_mappings
- 完整 URL 示例: GET /mercariV2/src/use_web/product_type_category_mappings/<endpoint>
"""

from fastapi import APIRouter

from .units.product_type_category_mappings_handler import (
    create_mapping,
    delete_mapping,
    list_mappings,
    update_mapping,
)

router = APIRouter()

router.add_api_route("", list_mappings, methods=["GET"])
router.add_api_route("", create_mapping, methods=["POST"])
router.add_api_route("/{pk_mapping_id}", update_mapping, methods=["PUT"])
router.add_api_route("/{mapping_id}", delete_mapping, methods=["DELETE"])
