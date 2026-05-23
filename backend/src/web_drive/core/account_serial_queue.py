# -*- coding: utf-8 -*-
"""
煤炉浏览器任务串行队列：同一账号（meilu_{id}）或全局批量任务在同一时刻只执行一个，
避免并发点击导致同一 Edge profile / MITM 流程互相打断。

实现：每个队列键对应一个 ``asyncio.Lock``，在 uvicorn 主事件循环上 ``await`` 串行执行，
不再使用 ``ThreadPoolExecutor`` + ``asyncio.run()``，避免阻塞线程与 Windows 管道泄漏。
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Awaitable, Callable, Dict, Optional, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")

_async_locks: Dict[str, asyncio.Lock] = {}
_async_locks_guard: Optional[asyncio.Lock] = None

# 未指定 account_id 的订单批量刷新等「跨账号」任务共用此键，全局串行
GLOBAL_QUEUE_KEY = "meilu_serial_global"


def queue_key_for_meilu_account(account_id: int) -> str:
    return f"meilu_{int(account_id)}"


def default_task_timeout_sec() -> Optional[float]:
    raw = (os.environ.get("MEILU_BROWSER_TASK_TIMEOUT_SEC") or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _locks_guard() -> asyncio.Lock:
    global _async_locks_guard
    if _async_locks_guard is None:
        _async_locks_guard = asyncio.Lock()
    return _async_locks_guard


async def _async_lock_for(queue_key: str) -> asyncio.Lock:
    async with _locks_guard():
        lock = _async_locks.get(queue_key)
        if lock is None:
            lock = asyncio.Lock()
            _async_locks[queue_key] = lock
        return lock


async def run_meilu_serial_async(
    queue_key: str,
    fn: Callable[[], Awaitable[T]],
    *,
    timeout_sec: Optional[float] = None,
) -> T:
    """
    在指定队列键下串行执行异步任务 ``fn()``（先进先出）。

    :param queue_key: 通常 ``queue_key_for_meilu_account(account_id)`` 或 ``GLOBAL_QUEUE_KEY``
    :param timeout_sec: 等待超时秒数；默认读 ``MEILU_BROWSER_TASK_TIMEOUT_SEC``，未设置则无超时
    """
    lock = await _async_lock_for(queue_key)
    async with lock:
        coro = fn()
        to = timeout_sec if timeout_sec is not None else default_task_timeout_sec()
        if to is not None:
            return await asyncio.wait_for(coro, timeout=to)
        return await coro


def resolve_meilu_account_id(account_id: Optional[int]) -> int:
    """与 ``sync_new_data`` 等一致：解析最终使用的煤炉账号主键。"""
    from ..operation_mercari.sync_data import _resolve_account_and_seller

    aid, _ = _resolve_account_and_seller(account_id)
    return int(aid)


def shutdown_serial_executors(*, wait: bool = False) -> None:
    """进程退出时清空队列锁（兼容旧调用名）。"""
    _async_locks.clear()
    log.debug("async serial queue locks cleared (wait=%s)", wait)
