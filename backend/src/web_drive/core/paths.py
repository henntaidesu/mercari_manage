# -*- coding: utf-8 -*-
"""Edge 持久化用户数据目录（Cookie / LocalStorage 等随 profile 落盘）。"""

from __future__ import annotations

import logging
import os
import re
import shutil
from typing import List, Optional

from src.app_paths import backend_root_str

log = logging.getLogger(__name__)

_ACCOUNT_KEY_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_MEILU_LISTING_SUFFIX = "__listing"

# 从主 profile 复制到 ``meilu_{id}__listing``，把煤炉登录态带过去
# （主窗口打开时部分文件可能被锁，跳过即可）
_AUTH_SEED_REL_PATHS: List[str] = [
    os.path.join("Default", "Cookies"),
    os.path.join("Default", "Cookies-journal"),
    os.path.join("Default", "Login Data"),
    os.path.join("Default", "Login Data For Account"),
    os.path.join("Default", "Login Data-journal"),
    os.path.join("Default", "Login Data For Account-journal"),
    os.path.join("Default", "Preferences"),
    os.path.join("Default", "Secure Preferences"),
    os.path.join("Default", "Network"),
    os.path.join("Default", "Local Storage"),
    os.path.join("Default", "Session Storage"),
    os.path.join("Default", "IndexedDB"),
]


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


def meilu_listing_key(account_id: int) -> str:
    """库存出品自动化：独立有头 profile，与 ``meilu_{id}`` 主窗口并行。"""
    return f"meilu_{int(account_id)}{_MEILU_LISTING_SUFFIX}"


def meilu_id_from_account_key(account_key: str) -> Optional[int]:
    key = (account_key or "").strip()
    if not key.startswith("meilu_"):
        return None
    tail = key[6:]
    if tail.endswith(_MEILU_LISTING_SUFFIX):
        tail = tail[: -len(_MEILU_LISTING_SUFFIX)]
    try:
        return int(tail)
    except ValueError:
        return None


def _seed_profile_auth_files(src_root: str, dst_root: str, *, log_label: str) -> None:
    """将主 profile 登录相关文件复制到目标 profile（目标目录正被占用时可能部分失败，忽略即可）。"""
    os.makedirs(os.path.join(dst_root, "Default"), exist_ok=True)
    for rel in _AUTH_SEED_REL_PATHS:
        src = os.path.join(src_root, rel)
        dst = os.path.join(dst_root, rel)
        if not os.path.exists(src):
            continue
        try:
            if os.path.isdir(src):
                if os.path.isdir(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        except Exception as exc:
            log.debug("seed %s profile skip %s: %s", log_label, rel, exc)


def seed_listing_profile_from_account(account_id: int) -> None:
    """
    将 ``meilu_{id}`` 主 profile 的登录相关文件同步到 ``meilu_{id}__listing``，
    供库存出品有头自动化使用。
    """
    main_key = meilu_account_key(account_id)
    listing_key = meilu_listing_key(account_id)
    _seed_profile_auth_files(
        profile_dir_for(main_key),
        profile_dir_for(listing_key),
        log_label="listing",
    )
