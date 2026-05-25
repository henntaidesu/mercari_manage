# -*- coding: utf-8 -*-
"""在售同步进度（兼容层）：转发到通用 ``sync_progress``。

保留旧函数名以避免破坏既有调用方；新代码请直接 import ``sync_progress``。
"""
from __future__ import annotations

from .sync_progress import (
    clear_sync_progress as clear_on_sale_sync_progress,
    get_sync_progress as get_on_sale_sync_progress,
    make_sync_reporter as make_on_sale_sync_reporter,
    set_sync_progress as set_on_sale_sync_progress,
)

__all__ = [
    "clear_on_sale_sync_progress",
    "get_on_sale_sync_progress",
    "make_on_sale_sync_reporter",
    "set_on_sale_sync_progress",
]
