# -*- coding: utf-8 -*-
"""按条码/暗号/まとめ商品标题反查库存 ID"""
from __future__ import annotations

from typing import List, Optional, Tuple
from ....db_manage.database import DatabaseManager
from ...mgmt_id_cipher import parse_trailing_cipher_mgmt_tokens
from ._common import _BUNDLE_LINE_RE, _BUNDLE_PHRASE_A, _BUNDLE_PHRASE_B, _BUNDLE_SECTION_HEADER, _BUNDLE_TRAILING_STATE_RE, _normalize_match_text, _split_mercari_item_ids


def _inventory_id_exists(inv_id: int) -> bool:
    db = DatabaseManager()
    r = db.execute_query(
        "SELECT 1 FROM [inventory] WHERE [id] = ? LIMIT 1",
        (int(inv_id),),
    )
    return bool(r)

def _inventory_id_by_barcode(barcode: str) -> Optional[int]:
    """按条形码精确匹配（与库存表 TRIM 后比较）。"""
    bc = (barcode or "").strip()
    if not bc:
        return None
    db = DatabaseManager()
    r = db.execute_query(
        "SELECT [id] FROM [inventory] WHERE TRIM(IFNULL([barcode], '')) = ? LIMIT 1",
        (bc,),
    )
    if not r or r[0][0] is None:
        return None
    try:
        return int(r[0][0])
    except (TypeError, ValueError):
        return None

def _is_bundle_order_description(text: Optional[str]) -> bool:
    s = str(text or "").strip()
    if not s:
        return False
    return _BUNDLE_PHRASE_A in s and _BUNDLE_PHRASE_B in s and _BUNDLE_SECTION_HEADER in s

def _extract_bundle_product_titles(text: Optional[str]) -> List[str]:
    s = str(text or "")
    if not s:
        return []
    lines = s.splitlines()
    titles: List[str] = []
    in_section = False
    for raw_line in lines:
        line = str(raw_line or "").strip()
        if not in_section:
            if _BUNDLE_SECTION_HEADER in line:
                in_section = True
            continue
        if not line:
            if titles:
                break
            continue
        m = _BUNDLE_LINE_RE.match(line)
        if not m:
            if titles:
                break
            continue
        title = (m.group(1) or "").strip()
        title = _BUNDLE_TRAILING_STATE_RE.sub("", title).strip()
        if title:
            titles.append(title)
    return titles

def _resolve_inventory_id_by_bundle_title(title: str) -> Optional[int]:
    query_title = str(title or "").strip()
    if not query_title:
        return None
    db = DatabaseManager()
    rows = db.execute_query(
        """
        SELECT
            o.[item_id],
            TRIM(IFNULL(o.[name], '')),
            IFNULL(o.[listing_description], '')
        FROM [on_sale_items] o
        WHERE COALESCE(o.[is_delete], 0) = 0
          AND TRIM(IFNULL(o.[item_id], '')) != ''
          AND TRIM(IFNULL(o.[name], '')) != ''
        """,
    )
    if not rows:
        return None

    target_norm = _normalize_match_text(query_title)
    exact_matches: List[Tuple[str, str]] = []
    fuzzy_matches: List[Tuple[str, str]] = []
    for item_id_raw, name_raw, desc_raw in rows:
        item_id = str(item_id_raw or "").strip()
        if not item_id:
            continue
        name = str(name_raw or "").strip()
        name_norm = _normalize_match_text(name)
        if not name_norm:
            continue
        desc = str(desc_raw or "")
        if name_norm == target_norm:
            exact_matches.append((item_id, desc))
        elif target_norm and (target_norm in name_norm or name_norm in target_norm):
            fuzzy_matches.append((item_id, desc))

    matches = exact_matches if exact_matches else fuzzy_matches
    if not matches:
        return None

    # 优先：用 on_sale_items.listing_description 末行 5 进制暗号直接定位 inventory.id。
    # 暗号 → inventory.id 是出品时编码的强绑定，比 mercari_item_id 反查更可靠，
    # 且不依赖库存行是否回写过 mercari_item_id。
    for _item_id, desc in matches:
        for mid, _qty in parse_trailing_cipher_mgmt_tokens(desc):
            if _inventory_id_exists(mid):
                return mid

    # 回退：按 mercari_item_id 反查 inventory。
    item_ids = [iid for iid, _desc in matches]
    inv_rows = db.execute_query(
        """
        SELECT [id], [mercari_item_id]
        FROM [inventory]
        WHERE TRIM(IFNULL([mercari_item_id], '')) != ''
        """,
    )
    inv_by_mid = {}
    for inv_id_raw, mids_raw in inv_rows:
        try:
            inv_id = int(inv_id_raw)
        except (TypeError, ValueError):
            continue
        for mid in _split_mercari_item_ids(mids_raw):
            inv_by_mid.setdefault(mid, []).append(inv_id)

    matched_inv_ids: List[int] = []
    for item_id in item_ids:
        for key in (item_id, item_id[1:] if item_id.startswith("m") else f"m{item_id}"):
            for inv_id in inv_by_mid.get(key, []):
                matched_inv_ids.append(inv_id)

    if not matched_inv_ids:
        return None
    # 只取一个稳定结果，避免一次标题映射多库存造成误扣减。
    return sorted(set(matched_inv_ids))[0]
