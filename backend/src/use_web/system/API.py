# -*- coding: utf-8 -*-
"""系统管理 API 模块（对应前端 /system 页面）。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web/system
- 完整 URL 示例: POST /mercariV2/src/use_web/system/restart
- 聚合：系统重启 + 用户管理 + 出品默认值 + SSL MITM 代理控制
"""

from fastapi import APIRouter

from .units.system_handler import RestartOut, restart_system
from .units.users_handler import list_users, create_user, change_password
from .units.app_config_handler import (
    ListingDefaultsOut,
    get_listing_defaults,
    put_listing_defaults,
)
from .units.ssl_mitm_handler import (
    download_ca_cert,
    get_last_capture,
    get_status,
    post_start,
    post_stop,
)

router = APIRouter()

# 系统重启
router.add_api_route("/restart", restart_system, methods=["POST"], response_model=RestartOut)

# 用户管理（System 页面"用户管理"区）
router.add_api_route("/users", list_users, methods=["GET"])
router.add_api_route("/users", create_user, methods=["POST"])
router.add_api_route("/change-password", change_password, methods=["POST"])

# 应用配置（出品默认值）
router.add_api_route("/listing-defaults", get_listing_defaults, methods=["GET"], response_model=ListingDefaultsOut)
router.add_api_route("/listing-defaults", put_listing_defaults, methods=["PUT"], response_model=ListingDefaultsOut)

# SSL MITM 代理控制
router.add_api_route("/ssl-mitm/status", get_status, methods=["GET"])
router.add_api_route("/ssl-mitm/start", post_start, methods=["POST"])
router.add_api_route("/ssl-mitm/stop", post_stop, methods=["POST"])
router.add_api_route("/ssl-mitm/ca-cert", download_ca_cert, methods=["GET"])
router.add_api_route("/ssl-mitm/last-capture", get_last_capture, methods=["GET"])
