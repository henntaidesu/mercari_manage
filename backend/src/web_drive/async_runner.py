# -*- coding: utf-8 -*-
"""
在线程池 / 同步入口中运行 Playwright 协程。

Windows 上 ``asyncio.run()`` 若在 Playwright 子进程管道未关闭前就销毁 loop，
会在进程退出或 GC 时打印 ``unclosed transport`` / ``I/O operation on closed pipe``。
因此在协程结束后、loop 关闭前显式 ``shutdown()`` 并短暂让出事件循环。
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Coroutine, TypeVar

from .manager import get_web_drive_manager

T = TypeVar("T")

# Windows Proactor 关闭子进程管道时常需略大于 0 的 yield
_WIN_TRANSPORT_DRAIN_SEC = 0.2


async def _run_with_drive_cleanup(coro: Coroutine[Any, Any, T]) -> T:
    try:
        return await coro
    finally:
        try:
            await get_web_drive_manager().shutdown()
        except Exception:
            pass
        if sys.platform == "win32":
            await asyncio.sleep(_WIN_TRANSPORT_DRAIN_SEC)


def run_browser_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    在无运行中 event loop 的线程内执行 ``coro``（典型：FastAPI 同步路由、煤炉串行队列 worker）。

    须在 ``asyncio.get_running_loop()`` 抛出 ``RuntimeError`` 的上下文中调用。
    """
    return asyncio.run(_run_with_drive_cleanup(coro))
