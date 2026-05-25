# -*- coding: utf-8 -*-
"""通用煤炉同步进度（内存）：供前端轮询展示「从煤炉同步」当前步骤。

与 web_drive/listing/units/listing_progress.py 同模式：按 job_id 写入步骤标签，
前端通过对应 GET /…/sync-progress/{job_id} 端点拉取展示。

供多个同步入口共享（在售商品、待办、通知）；同一进程内 job_id 唯一即可。
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

_store: Dict[str, Dict[str, Any]] = {}


def set_sync_progress(job_id: str, step: str, label_zh: str) -> None:
    if not job_id:
        return
    _store[job_id] = {
        "step": step,
        "label_zh": label_zh,
        "ts": time.time(),
    }


def get_sync_progress(job_id: str) -> Optional[Dict[str, Any]]:
    if not job_id:
        return None
    row = _store.get(job_id)
    return dict(row) if row else None


def clear_sync_progress(job_id: str) -> None:
    if job_id:
        _store.pop(job_id, None)


def make_sync_reporter(job_id: Optional[str]) -> Callable[[str, str], None]:
    """生成 (step, label_zh) → 写入内存的回调；job_id 为空时返回 no-op。"""
    jid = (job_id or "").strip() or None

    def report(step: str, label_zh: str) -> None:
        if jid:
            set_sync_progress(jid, step, label_zh)

    return report
