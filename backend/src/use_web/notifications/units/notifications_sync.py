# -*- coding: utf-8 -*-
"""お知らせ通知同步入口（HTTP 层）。"""

from typing import Any, Dict

from fastapi import HTTPException

from ....use_mercari.get_notifications.notification_sync import (
    _resolve_account_id,
    sync_notifications_from_mercari,
)
from ....web_drive.core.account_serial_queue import (
    queue_key_for_meilu_account,
    run_meilu_serial_async,
)
from .notifications_models import SyncNotificationsRequest


async def sync_notifications(req: SyncNotificationsRequest) -> Dict[str, Any]:
    """从煤炉同步当前账号的お知らせ通知；按账号串行避免浏览器抢占。"""
    try:
        aid = _resolve_account_id(req.account_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    stats = await run_meilu_serial_async(
        queue_key_for_meilu_account(aid),
        lambda: sync_notifications_from_mercari(account_id=aid),
    )
    return stats
