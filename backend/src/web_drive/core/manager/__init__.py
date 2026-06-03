# -*- coding: utf-8 -*-
"""EdgeWebDriveManager 包。

原单文件 ``manager.py`` 已按职责拆分（配置 + 三个 Mixin + 主类）；``__init__``
重新导出对外公开 API，保持 ``from ...core.manager import X`` 旧导入不变。
"""

from ._config import (
    automation_headless_enabled,
    force_headed_debug_enabled,
    set_force_headed_debug,
)
from ._manager_class import EdgeWebDriveManager, get_web_drive_manager

__all__ = [
    "EdgeWebDriveManager",
    "get_web_drive_manager",
    "automation_headless_enabled",
    "force_headed_debug_enabled",
    "set_force_headed_debug",
]
