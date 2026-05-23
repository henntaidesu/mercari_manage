# -*- coding: utf-8 -*-
"""登录 API 模块（对应前端 /login 页面）。

层级蓝图注册：
- 从 use_web/API.py 接收前缀 /mercariV2/src/use_web/login
- 完整 URL 示例: POST /mercariV2/src/use_web/login/
- 启动事件：首次运行自动种子默认管理员账号（admin / admin）
"""

from fastapi import APIRouter

from .units.login_handler import login, startup_seed_user

router = APIRouter()

router.add_api_route("", login, methods=["POST"])

# 默认管理员种子事件
router.on_event("startup")(startup_seed_user)
