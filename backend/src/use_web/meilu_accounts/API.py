# -*- coding: utf-8 -*-
"""煤炉账号管理 API 模块。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web/meilu_accounts
- 完整 URL 示例: GET /mercariV2/src/use_web/meilu_accounts/
"""
from fastapi import APIRouter

from .units.meilu_accounts_crud import (
    create_meilu_account,
    delete_meilu_account,
    list_meilu_accounts,
    update_meilu_account,
)
from .units.meilu_accounts_mitm import (
    fetch_auth_via_mitm,
    fetch_seller_id_via_mitm,
)

router = APIRouter()

router.add_api_route("", list_meilu_accounts, methods=["GET"])
router.add_api_route("", create_meilu_account, methods=["POST"])
router.add_api_route("/{aid}", update_meilu_account, methods=["PUT"])
router.add_api_route("/fetch-seller-id-via-mitm", fetch_seller_id_via_mitm, methods=["POST"])
router.add_api_route("/{aid}/fetch-auth-via-mitm", fetch_auth_via_mitm, methods=["POST"])
router.add_api_route("/{aid}", delete_meilu_account, methods=["DELETE"])
