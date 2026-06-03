# -*- coding: utf-8 -*-
"""EdgeWebDriveManager 主类：组合各 Mixin + 单例工厂。"""
from __future__ import annotations

import threading
from typing import Dict, Optional
from ._mixin_lifecycle import _LifecycleMixin
from ._mixin_sessions import _SessionsMixin
from ._mixin_tabs import _TabsMixin


class EdgeWebDriveManager(_LifecycleMixin, _SessionsMixin, _TabsMixin):
    """管理多账号 Edge 持久化会话（每账号独立 profile 目录）。"""

    # 同一 profile 目录只能被一个线程「关→开」；否则 Windows 下易出现 SingletonLock / 句柄未释放，
    # Edge 瞬间退出（exitCode≈21）并报 Target ... has been closed。
    _profile_outer_locks: Dict[str, threading.Lock] = {}
    _profile_outer_locks_guard = threading.Lock()


    def __init__(self) -> None:
        self._tls = threading.local()




_manager: Optional["EdgeWebDriveManager"] = None


def get_web_drive_manager() -> "EdgeWebDriveManager":
    global _manager
    if _manager is None:
        _manager = EdgeWebDriveManager()
    return _manager
