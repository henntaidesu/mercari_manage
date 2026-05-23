# -*- coding: utf-8 -*-
"""有头交互会话：记录 / 恢复已打开的标签页 URL。"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .paths import profile_dir_for

log = logging.getLogger(__name__)

_SNAPSHOT_NAME = "interactive_tabs.snapshot.json"
_SKIP_URL_PREFIXES = (
    "about:",
    "chrome://",
    "edge://",
    "devtools://",
    "chrome-error://",
)


def snapshot_path(account_key: str) -> str:
    return os.path.join(profile_dir_for(account_key), _SNAPSHOT_NAME)


def _is_meaningful_url(url: str) -> bool:
    u = (url or "").strip()
    if not u:
        return False
    low = u.lower()
    return not any(low.startswith(p) for p in _SKIP_URL_PREFIXES)


async def collect_tabs_from_context(context: Any) -> Dict[str, Any]:
    """从 Playwright BrowserContext 收集标签 URL；活动页取 pages[-1]。"""
    tabs: List[str] = []
    active_index = 0
    pages = list(getattr(context, "pages", []) or [])
    active_page = pages[-1] if pages else None

    for p in pages:
        try:
            u = (p.url or "").strip()
        except Exception:
            u = ""
        if _is_meaningful_url(u):
            tabs.append(u)

    if active_page is not None:
        try:
            active_url = (active_page.url or "").strip()
        except Exception:
            active_url = ""
        if _is_meaningful_url(active_url) and active_url in tabs:
            active_index = tabs.index(active_url)
        elif tabs:
            active_index = len(tabs) - 1

    return {"tabs": tabs, "active_index": active_index}


def load_snapshot(account_key: str) -> Optional[Dict[str, Any]]:
    path = snapshot_path(account_key)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        log.warning("读取标签快照失败 %s: %s", path, exc)
        return None
    if not isinstance(data, dict):
        return None
    tabs = data.get("tabs")
    if not isinstance(tabs, list):
        return None
    clean = [str(u).strip() for u in tabs if _is_meaningful_url(str(u))]
    if not clean:
        return None
    active = data.get("active_index", len(clean) - 1)
    try:
        active_i = int(active)
    except (TypeError, ValueError):
        active_i = len(clean) - 1
    active_i = max(0, min(active_i, len(clean) - 1))
    return {"tabs": clean, "active_index": active_i, "saved_at": data.get("saved_at")}


def save_snapshot(account_key: str, payload: Dict[str, Any]) -> None:
    tabs = payload.get("tabs") or []
    if not tabs:
        return
    path = snapshot_path(account_key)
    body = {
        "tabs": tabs,
        "active_index": int(payload.get("active_index", len(tabs) - 1)),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as exc:
        log.warning("写入标签快照失败 %s: %s", path, exc)


async def save_snapshot_from_context(account_key: str, context: Any) -> bool:
    data = await collect_tabs_from_context(context)
    if not data.get("tabs"):
        return False
    save_snapshot(account_key, data)
    return True


async def restore_tabs_to_context(
    context: Any,
    account_key: str,
    *,
    fallback_url: str,
) -> Dict[str, Any]:
    """
    按快照恢复标签；无快照时打开 fallback_url 单标签。
    先按快照 new_page 再关闭 launch 时的旧标签，避免 0 标签时 new_page 失败。
    """
    import asyncio

    snap = load_snapshot(account_key)
    if not snap:
        await _open_single_tab(context, fallback_url)
        return {"restored": False, "tab_count": 1, "source": "fallback"}

    tabs: List[str] = snap["tabs"]
    active_index: int = snap["active_index"]

    # Edge/Chromium 在 0 标签时 new_page 常会失败（Target.createTarget），须先开新页再关旧页。
    await asyncio.sleep(0.35)
    pages_before = list(context.pages)

    opened: List[Any] = []
    for url in tabs:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        except Exception as exc:
            log.warning("恢复标签失败 account=%s url=%s: %s", account_key, url, exc)
        opened.append(page)

    if not opened:
        await _open_single_tab(context, fallback_url)
        return {"restored": False, "tab_count": 1, "source": "fallback_after_fail"}

    for p in pages_before:
        try:
            await p.close()
        except Exception:
            pass
    for _ in range(12):
        extra = [p for p in context.pages if p not in opened]
        if not extra:
            break
        for p in extra:
            try:
                await p.close()
            except Exception:
                pass
        await asyncio.sleep(0.15)

    idx = max(0, min(active_index, len(opened) - 1))
    try:
        await opened[idx].bring_to_front()
    except Exception:
        pass

    return {
        "restored": True,
        "tab_count": len(opened),
        "active_index": idx,
        "source": "snapshot",
    }


async def _open_single_tab(context: Any, url: str) -> None:
    """单标签打开 URL（与 manager._navigate_one_tab 行为一致，避免循环导入）。"""
    import asyncio

    pages_before = list(context.pages)
    page = await context.new_page()
    for p in pages_before:
        try:
            await p.close()
        except Exception:
            pass
    await page.goto(url, wait_until="domcontentloaded")
    for _ in range(12):
        extra = [p for p in context.pages if p is not page]
        if not extra:
            break
        for p in extra:
            try:
                await p.close()
            except Exception:
                pass
        await asyncio.sleep(0.15)
