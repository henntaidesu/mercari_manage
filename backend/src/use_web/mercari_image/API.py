# -*- coding: utf-8 -*-
"""煤炉图片代理 API（跨页面共享，前端 <img> 直接通过 URL 访问，无需 token）。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web
- 端点: GET /mercariV2/src/use_web/mercari-image?u=<encoded url>
"""
from fastapi import APIRouter

from .proxy_handler import proxy_mercari_image

# 公开路由（不要求登录态），与 inventory.image-thumb 同样定位
public_router = APIRouter()
public_router.add_api_route("/mercari-image", proxy_mercari_image, methods=["GET"])
