# -*- coding: utf-8 -*-
"""お知らせ通知同步入口（HTTP 层）。"""

import re
from typing import Any, Dict

from fastapi import HTTPException

from ....use_mercari.get_notifications.notification_sync import (
    _resolve_account_id,
    sync_notifications_from_mercari,
)
from ....use_mercari.sync_progress import (
    clear_sync_progress,
    get_sync_progress,
)
from ....web_drive.core.account_serial_queue import (
    queue_key_for_meilu_account,
    run_meilu_serial_async,
)
from .notifications_models import SyncNotificationsRequest


# 与 listing_post_progress 相同的安全字符集，避免路径注入
_SYNC_JOB_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,128}$")


async def sync_notifications(req: SyncNotificationsRequest) -> Dict[str, Any]:
    """从煤炉同步当前账号的お知らせ通知；按账号串行避免浏览器抢占。

    ``progress_job_id`` 与 GET /use_web/notifications/sync-progress/{job_id} 配合，
    供前端轮询当前步骤展示全屏等待框。
    """
    jid = (req.progress_job_id or "").strip() or None
    if jid and not _SYNC_JOB_ID_RE.fullmatch(jid):
        raise HTTPException(status_code=400, detail="invalid progress_job_id")

    try:
        aid = _resolve_account_id(req.account_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        stats = await run_meilu_serial_async(
            queue_key_for_meilu_account(aid),
            lambda: sync_notifications_from_mercari(
                account_id=aid,
                progress_job_id=jid,
            ),
        )
    finally:
        if jid:
            clear_sync_progress(jid)
    return stats


def notifications_sync_progress(job_id: str):
    """通知同步执行过程中轮询当前步骤（与 POST body.progress_job_id 对应）。"""
    jid = (job_id or "").strip()
    if not _SYNC_JOB_ID_RE.fullmatch(jid):
        raise HTTPException(status_code=400, detail="invalid job_id")
    row = get_sync_progress(jid)
    if not row:
        return {"success": True, "data": {"step": None, "label_zh": None, "ts": None}}
    return {"success": True, "data": row}
