# -*- coding: utf-8 -*-
"""在售数量计算与库存 on_sale_quantity 重算/增减/清理"""

import re
from typing import Any, Dict, List, Optional
from ....db_manage.models.on_sale_item import OnSaleItemModel
from ....db_manage.database import DatabaseManager
from ....ssl_mitm_proxy.capture_config import canonical_mercari_item_id


_MERCARI_ID_SEP_RE = re.compile(r"[\n,，、\s]+")

def _split_mercari_item_ids(raw: Any) -> List[str]:
    s = str(raw or "").strip()
    if not s:
        return []
    out: List[str] = []
    seen = set()
    for part in _MERCARI_ID_SEP_RE.split(s):
        t = str(part or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out

def _is_active_on_sale(status: Optional[str], is_delete: int = 0) -> bool:
    """仅 status=on_sale 且未软删除，视为在售。"""
    s = (status or "").strip()
    return int(is_delete or 0) == 0 and s == "on_sale"

def _mercari_id_lookup_keys(item_id: str) -> List[str]:
    """查询 on_sale_items 时兼容 m 前缀与纯数字。"""
    keys: List[str] = []
    seen = set()
    for raw in (str(item_id or "").strip(), canonical_mercari_item_id(item_id)):
        if not raw or raw in seen:
            continue
        seen.add(raw)
        keys.append(raw)
    return keys

def count_active_on_sale_for_mercari_ids(mids: List[str]) -> int:
    """
    统计 mercari_item_id 列表中仍为「出售中」的条数（与库存页二级表过滤规则一致）。
    """
    if not mids:
        return 0
    query_keys: List[str] = []
    seen_q = set()
    for mid in mids:
        for k in _mercari_id_lookup_keys(mid):
            if k not in seen_q:
                seen_q.add(k)
                query_keys.append(k)
    if not query_keys:
        return 0
    rows = OnSaleItemModel.find_all_by_item_ids(query_keys)
    active_keys = set()
    for row in rows:
        if not _is_active_on_sale(row.get("status"), int(row.get("is_delete") or 0)):
            continue
        iid = str(row.get("item_id") or "").strip()
        if not iid:
            continue
        for k in _mercari_id_lookup_keys(iid):
            active_keys.add(k)
    count = 0
    seen_mid = set()
    for mid in mids:
        t = str(mid or "").strip()
        if not t or t in seen_mid:
            continue
        seen_mid.add(t)
        if any(k in active_keys for k in _mercari_id_lookup_keys(t)):
            count += 1
    return count

def recalculate_and_persist_inventory_on_sale_quantity(inventory_id: int) -> int:
    """按 mercari_item_id 与 on_sale_items 重算并写回 inventory.on_sale_quantity。"""
    iid = int(inventory_id)
    db = DatabaseManager()
    row = db.execute_query(
        "SELECT [mercari_item_id], [on_sale_quantity] FROM [inventory] WHERE [id] = ? LIMIT 1",
        (iid,),
    )
    if not row:
        return 0
    mids = _split_mercari_item_ids(row[0][0])
    qty = count_active_on_sale_for_mercari_ids(mids)
    old = int(row[0][1] or 0)
    if qty != old:
        db.execute_update(
            "UPDATE [inventory] SET [on_sale_quantity] = ? WHERE [id] = ?",
            (qty, iid),
        )
    return qty

def enrich_inventory_rows_on_sale_quantity(rows: List[dict]) -> None:
    """修正 API 返回的在售数，使其与展开二级表（仅 status=on_sale）一致。"""
    if not rows:
        return
    inv_mids: Dict[int, List[str]] = {}
    query_keys: List[str] = []
    seen_q: set[str] = set()
    for d in rows:
        iid = int(d.get("id") or 0)
        mids = _split_mercari_item_ids(d.get("mercari_item_id"))
        if mids:
            inv_mids[iid] = mids
            for mid in mids:
                for k in _mercari_id_lookup_keys(mid):
                    if k not in seen_q:
                        seen_q.add(k)
                        query_keys.append(k)
    active_keys: set[str] = set()
    if query_keys:
        for row in OnSaleItemModel.find_all_by_item_ids(query_keys):
            if not _is_active_on_sale(row.get("status"), int(row.get("is_delete") or 0)):
                continue
            iid = str(row.get("item_id") or "").strip()
            for k in _mercari_id_lookup_keys(iid):
                active_keys.add(k)

    def _mid_active(mid: str) -> bool:
        return any(k in active_keys for k in _mercari_id_lookup_keys(mid))

    db = DatabaseManager()
    for d in rows:
        iid = int(d.get("id") or 0)
        mids = inv_mids.get(iid, [])
        old_qty = int(d.get("on_sale_quantity") or 0)
        if not mids:
            qty = 0
        else:
            seen_mid: set[str] = set()
            qty = 0
            for mid in mids:
                t = str(mid or "").strip()
                if not t or t in seen_mid:
                    continue
                seen_mid.add(t)
                if _mid_active(t):
                    qty += 1
        d["on_sale_quantity"] = qty
        if qty != old_qty and iid > 0:
            db.execute_update(
                "UPDATE [inventory] SET [on_sale_quantity] = ? WHERE [id] = ?",
                (qty, iid),
            )

def _apply_inventory_on_sale_delta_by_item_ids(item_ids: set[str], delta: int) -> int:
    """
    按煤炉 item_id 批量调整 inventory.on_sale_quantity（支持正负），返回影响行数。
    说明：inventory.mercari_item_id 可能是一行多 ID，需拆分匹配。
    """
    if not item_ids or delta == 0:
        return 0
    db = DatabaseManager()
    rows = db.execute_query(
        """
        SELECT [id], [mercari_item_id], [on_sale_quantity]
        FROM [inventory]
        WHERE TRIM(IFNULL([mercari_item_id], '')) != ''
        """
    )
    affected = 0
    wanted = {str(x).strip() for x in item_ids if str(x).strip()}
    if not wanted:
        return 0
    for iid_raw, mids_raw, osq_raw in rows:
        mids = _split_mercari_item_ids(mids_raw)
        if not mids:
            continue
        overlap = any(mid in wanted for mid in mids)
        if not overlap:
            continue
        old_qty = int(osq_raw or 0)
        next_qty = old_qty + int(delta)
        if next_qty < 0:
            next_qty = 0
        if next_qty == old_qty:
            continue
        changed = db.execute_update(
            "UPDATE [inventory] SET [on_sale_quantity] = ? WHERE [id] = ?",
            (next_qty, int(iid_raw)),
        )
        affected += int(changed or 0)
    return affected

def _join_mercari_item_ids(ids: List[str]) -> Optional[str]:
    arr = []
    seen = set()
    for v in ids:
        t = str(v or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        arr.append(t)
    return "、".join(arr) if arr else None

def _strip_mercari_item_ids_from_inventory(strip_ids: set[str]) -> int:
    """
    从 inventory.mercari_item_id 中移除指定煤炉商品 ID（同步后非出售中、或已从 API 消失时），
    供库存页二级列表不再展示已下架/非出售中链接。与 _apply_inventory_on_sale_delta 配合：先调数量再调本函数。
    """
    if not strip_ids:
        return 0
    wanted_drop: set[str] = set()
    for x in strip_ids:
        s = str(x).strip()
        if not s:
            continue
        wanted_drop.add(s)
        c = canonical_mercari_item_id(s)
        if c:
            wanted_drop.add(c)

    def should_remove(mid: str) -> bool:
        t = str(mid or "").strip()
        if not t:
            return False
        if t in wanted_drop:
            return True
        ct = canonical_mercari_item_id(t)
        return bool(ct and ct in wanted_drop)

    db = DatabaseManager()
    rows = db.execute_query(
        """
        SELECT [id], [mercari_item_id], [on_sale_quantity]
        FROM [inventory]
        WHERE TRIM(IFNULL([mercari_item_id], '')) != ''
        """
    )
    updated = 0
    for iid_raw, mids_raw, osq_raw in rows:
        mids = _split_mercari_item_ids(mids_raw)
        if not mids:
            continue
        next_mids = [m for m in mids if not should_remove(m)]
        if len(next_mids) == len(mids):
            continue
        next_text = _join_mercari_item_ids(next_mids)
        inv_id = int(iid_raw)
        db.execute_update(
            """
            UPDATE [inventory]
            SET [mercari_item_id] = ?
            WHERE [id] = ?
            """,
            (next_text, inv_id),
        )
        recalculate_and_persist_inventory_on_sale_quantity(inv_id)
        updated += 1
    return updated
