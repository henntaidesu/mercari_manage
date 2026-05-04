# -*- coding: utf-8 -*-
"""Edge 持久化用户数据目录（Cookie / LocalStorage 等随 profile 落盘）。"""

import os
import re

_ACCOUNT_KEY_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def backend_root() -> str:
    # 本文件位于 backend/src/web_drive/paths.py → 上两级为 backend 根目录
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


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
