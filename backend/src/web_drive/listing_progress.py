# -*- coding: utf-8 -*-
"""出品自动化进度（内存）：供前端轮询展示当前步骤。"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

_store: Dict[str, Dict[str, Any]] = {}


def set_listing_progress(job_id: str, step: str, label_zh: str) -> None:
    if not job_id:
        return
    _store[job_id] = {
        "step": step,
        "label_zh": label_zh,
        "ts": time.time(),
    }


def get_listing_progress(job_id: str) -> Optional[Dict[str, Any]]:
    if not job_id:
        return None
    row = _store.get(job_id)
    return dict(row) if row else None


def clear_listing_progress(job_id: str) -> None:
    if job_id:
        _store.pop(job_id, None)
