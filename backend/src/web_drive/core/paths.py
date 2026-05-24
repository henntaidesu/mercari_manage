# -*- coding: utf-8 -*-
"""Edge 持久化用户数据目录（Cookie / LocalStorage 等随 profile 落盘）。"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

from src.app_paths import backend_root_str

log = logging.getLogger(__name__)

_ACCOUNT_KEY_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def backend_root() -> str:
    return backend_root_str()


def profiles_root() -> str:
    override = (os.environ.get("WEB_DRIVE_PROFILES_DIR") or "").strip()
    if override:
        return os.path.abspath(override)
    return os.path.join(backend_root(), "data", "web_drive_profiles")


def validate_account_key(account_key: str) -> str:
    s = (account_key or "").strip()
    if not _ACCOUNT_KEY_RE.match(s):
        raise ValueError(
            "account_key 须为 1～64 位，仅允许字母、数字、下划线、连字符（用于隔离不同子浏览器配置）"
        )
    return s


def profile_dir_for(account_key: str) -> str:
    key = validate_account_key(account_key)
    root = profiles_root()
    path = os.path.join(root, key)
    os.makedirs(path, exist_ok=True)
    return path


def meilu_account_key(account_id: int) -> str:
    """账号主 profile（用户手动登录 + MITM 自动化共用，登录态由 Edge 持久化 cookie 自动维护）。"""
    return f"meilu_{int(account_id)}"


def meilu_id_from_account_key(account_key: str) -> Optional[int]:
    key = (account_key or "").strip()
    if not key.startswith("meilu_"):
        return None
    try:
        return int(key[6:])
    except ValueError:
        return None
