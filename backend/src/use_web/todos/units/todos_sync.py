# -*- coding: utf-8 -*-
"""代办事项同步入口（HTTP 层）。"""

from typing import Any, Dict

from fastapi import HTTPException

from ....use_mercari.get_to_du_list.todolist_sync import (
    _resolve_account_id,
    sync_todos_from_mercari,
)
from ....web_drive.core.account_serial_queue import (
    queue_key_for_meilu_account,
    run_meilu_serial_async,
)
from .todos_models import SyncTodosRequest


async def sync_todos(req: SyncTodosRequest) -> Dict[str, Any]:
    """从煤炉同步当前账号的代办事项；按账号串行避免浏览器抢占。"""
    try:
        aid = _resolve_account_id(req.account_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    stats = await run_meilu_serial_async(
        queue_key_for_meilu_account(aid),
        lambda: sync_todos_from_mercari(account_id=aid),
    )
    return stats
