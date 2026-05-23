# -*- coding: utf-8 -*-
"""库存出入库交易接口。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web/transactions
- 完整 URL 示例: GET /mercariV2/src/use_web/transactions
"""
from fastapi import APIRouter

from .units.transactions_handler import create_transaction, list_transactions

router = APIRouter()

router.add_api_route("", list_transactions, methods=["GET"])
router.add_api_route("", create_transaction, methods=["POST"])
