# -*- coding: utf-8 -*-
"""合并购买请求详情同步入口（HTTP 层）。"""

import re
from typing import Any, Dict

from fastapi import HTTPException

from ....use_mercari.get_notifications.bundle_purchase_sync import (
    _resolve_account_id,
    sync_bundle_purchase_from_mercari,
)
from ....use_mercari.sync.sync_progress import clear_sync_progress
from ....web_drive.core.account_serial_queue import (
    queue_key_for_mercari_account,
    run_mercari_serial_async,
)
from .bundle_purchase_models import BundlePurchaseSyncRequest


_JOB_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,128}$")


async def sync_bundle_purchase(req: BundlePurchaseSyncRequest) -> Dict[str, Any]:
    """打开 bundle_offer 页捕获响应并入库；按账号串行避免浏览器抢占。"""
    bid = (req.bundle_id or "").strip()
    if not bid:
        raise HTTPException(status_code=400, detail="bundle_id 不能为空")
    try:
        aid = _resolve_account_id(req.account_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    jid = (req.progress_job_id or "").strip() or None
    if jid and not _JOB_ID_RE.fullmatch(jid):
        raise HTTPException(status_code=400, detail="invalid progress_job_id")

    try:
        stats = await run_mercari_serial_async(
            queue_key_for_mercari_account(aid),
            lambda: sync_bundle_purchase_from_mercari(
                bundle_id=bid,
                account_id=aid,
                notification_id=req.notification_id,
                progress_job_id=jid,
            ),
        )
    finally:
        if jid:
            clear_sync_progress(jid)
    return stats
