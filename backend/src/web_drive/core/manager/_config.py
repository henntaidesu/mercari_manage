# -*- coding: utf-8 -*-
"""manager 包：全局调试开关 / 无头判定 / 线程级浏览器状态。"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional



log = logging.getLogger(__name__)




# ── 全局调试开关：强制所有自动化浏览器有头（DEBUG）──
# True  = 无视环境变量与各处 headless=True 入参，全部以「有头」启动，方便肉眼调试；
# False = 走正常无头逻辑（默认）。
# 由 main.py 在启动时通过 set_force_headed_debug() 设定。
_FORCE_HEADED_DEBUG = False




def set_force_headed_debug(enabled: bool) -> None:
    """设置全局「强制有头调试」开关（main.py 启动时调用）。"""
    global _FORCE_HEADED_DEBUG
    _FORCE_HEADED_DEBUG = bool(enabled)




def force_headed_debug_enabled() -> bool:
    """是否开启了「强制有头调试」。开启时所有自动化浏览器一律有头。"""
    return _FORCE_HEADED_DEBUG




def automation_headless_enabled() -> bool:
    """所有自动化任务（除 /mercari-accounts 用户手动外）是否切真·无头浏览器。

    通过 ``WEB_DRIVE_AUTOMATION_HEADLESS`` 环境变量控制，**默认 1（无头静默）**：
    除前端「打开浏览器」外，所有调用 WebDrive 的自动化都不在前台显示。
    生效范围：系统启动预热、MITM 自动化（数据获取/出品/删除/改价）、煤炉账号 MITM 抓取；
    不生效范围：``/use_web/web-drive/sessions/open``（前端 /mercari-accounts 手动按钮，恒有头）。

    设 ``WEB_DRIVE_AUTOMATION_HEADLESS=0`` 可改回有头+最小化（调试观察浏览器用）。

    另：``set_force_headed_debug(True)``（见 main.py 全局开关）会强制返回 False（有头）。
    """
    if _FORCE_HEADED_DEBUG:
        return False
    v = (os.environ.get("WEB_DRIVE_AUTOMATION_HEADLESS") or "1").strip().lower()
    return v in ("1", "true", "yes", "on")




class _DriveThreadState:
    """单个 OS 线程内的浏览器状态（Lock / Playwright / 会话表）。"""

    __slots__ = ("lock", "playwright", "playwright_loop", "contexts", "session_meta")

    def __init__(self) -> None:
        self.lock: Optional[asyncio.Lock] = None
        self.playwright: Any = None
        self.playwright_loop: Optional[asyncio.AbstractEventLoop] = None
        self.contexts: Dict[str, Any] = {}
        # account_key -> {"interactive": bool, "headless": bool}
        self.session_meta: Dict[str, Dict[str, bool]] = {}
