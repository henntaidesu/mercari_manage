# -*- coding: utf-8 -*-
"""Web 自动化：按账号隔离的 Microsoft Edge 持久化会话（Cookie 随 profile 保存）。"""

from .manager import EdgeWebDriveManager, get_web_drive_manager
from .paths import profile_dir_for, profiles_root, validate_account_key

__all__ = [
    "EdgeWebDriveManager",
    "get_web_drive_manager",
    "profile_dir_for",
    "profiles_root",
    "validate_account_key",
]
