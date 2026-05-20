# -*- coding: utf-8 -*-
"""应用级系统操作：重启后端服务等。"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)


async def graceful_cleanup_before_exit() -> None:
    """与 main.py shutdown 事件一致：关闭浏览器、MITM 等。"""
    try:
        from src.web_drive import get_web_drive_manager, shutdown_serial_executors
        from src.ssl_mitm_proxy.runner import stop_mitm_proxy

        shutdown_serial_executors(wait=False)
        await get_web_drive_manager().shutdown()
        stop_mitm_proxy()
    except Exception as exc:
        logger.warning("重启前清理资源失败: %s", exc)


def _build_restart_argv() -> list[str]:
    """构造重启子进程的命令行（兼容 PyInstaller、python -m uvicorn、mercari_server.py）。"""
    if getattr(sys, "frozen", False):
        return [sys.executable]

    argv0 = (sys.argv[0] if sys.argv else "").replace("\\", "/")
    if "uvicorn" in argv0 and argv0.endswith("__main__.py") and len(sys.argv) >= 2:
        return [sys.executable, "-m", "uvicorn", *sys.argv[1:]]
    if argv0.endswith("mercari_server.py"):
        return [sys.executable, *sys.argv]
    if len(sys.argv) > 1:
        return [sys.executable, *sys.argv[1:]]
    return [sys.executable]


def _spawn_replacement_process() -> None:
    argv = _build_restart_argv()
    cwd = os.getcwd()
    logger.info("启动新进程: %s (cwd=%s)", argv, cwd)

    kwargs: dict = {"cwd": cwd, "close_fds": True}
    if sys.platform == "win32":
        flags = 0
        for name in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP"):
            flags |= getattr(subprocess, name, 0)
        if flags:
            kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
        kwargs["stdin"] = subprocess.DEVNULL
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL

    subprocess.Popen(argv, **kwargs)


async def schedule_system_restart(*, delay_seconds: float = 1.0) -> None:
    """延迟后清理资源、拉起新进程并退出当前进程。"""
    await asyncio.sleep(delay_seconds)
    await graceful_cleanup_before_exit()
    _spawn_replacement_process()
    os._exit(0)
