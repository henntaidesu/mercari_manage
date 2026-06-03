# -*- coding: utf-8 -*-
"""库存三栏计数器（库存 quantity / 在售 on_sale_quantity / 待出 pending_outbound_qty）的事件驱动转移。

模型（出品 1 件 = 1）：
  · 上架成功：库存 -1，在售 +1
  · 暂停出售(on_sale→stop) / 恢复出售(stop→on_sale)：不变
  · 下架/删除（真正下架，非售出）：在售 -1，库存 +1
  · 售出（在售 ID 被买）：在售 -1，待出 +1
  · 出库/发货：待出 -1

「在售 ↔ 库存」的转移统一由本模块在「在售列表同步」(sync.apply_on_sale_list_sync) 与
「详情绑定」(detail_sync) 两处通过 ``reconcile_listing_counts`` 应用，并以
``on_sale_items.counted_on_sale`` 标记保证幂等（同步重复运行不会重复增减）。

「待出」仍由订单管线派生维护（见 description_mgmt_ids.refresh_inventory_pending_outbound_qty），
本模块不直接增减 pending_outbound_qty。

售出 vs 下架 判别：某 listing 从在售消失（is_delete=1 或 status 不在 on_sale/stop）时，
若其绑定库存存在「未出库的非终态订单行」→ 视为售出（仅释放在售，不回补库存，待出由订单派生）；
否则视为下架（释放在售并回补库存）。账号同步与订单同步先后顺序可能导致短时漂移，
可用 scripts/migrate_inventory_counters.py 重新对账修正。
"""
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional, Set, Tuple

from ..db_manage.database import DatabaseManager
from ..db_manage.models.order_outbound_line import TERMINAL_ORDER_STATUSES
from .on_sale.on_sale_items_sync.inventory_qty import (
    _mercari_id_lookup_keys,
    _split_mercari_item_ids,
)

log = logging.getLogger(__name__)

# 视为「仍挂在售（占用在售名额）」的煤炉状态：含暂停 stop（暂停不释放在售名额）
LISTED_STATUSES: Tuple[str, ...] = ("on_sale", "stop")


def _norm_keys(item_id: str) -> List[str]:
    """item_id 的查询键（兼容 m 前缀与纯数字）。"""
    return _mercari_id_lookup_keys(item_id)


def _adjust_inventory(
    db: DatabaseManager,
    inv_id: int,
    *,
    quantity_delta: int = 0,
    on_sale_delta: int = 0,
) -> bool:
    """对单个库存行应用增量（quantity / on_sale_quantity 均 clamp >= 0）。返回是否实际更新。"""
    if quantity_delta == 0 and on_sale_delta == 0:
        return False
    changed = db.execute_update(
        """
        UPDATE [inventory]
        SET [quantity] = MAX(0, COALESCE([quantity], 0) + ?),
            [on_sale_quantity] = MAX(0, COALESCE([on_sale_quantity], 0) + ?)
        WHERE [id] = ?
        """,
        (int(quantity_delta), int(on_sale_delta), int(inv_id)),
    )
    return bool(changed)


def _set_counted_flag(db: DatabaseManager, item_id: str, flag: int) -> None:
    """按 on_sale_items.item_id 设置 counted_on_sale 标记。"""
    iid = str(item_id or "").strip()
    if not iid:
        return
    db.execute_update(
        "UPDATE [on_sale_items] SET [counted_on_sale] = ? WHERE TRIM([item_id]) = TRIM(?)",
        (int(flag), iid),
    )


def _bound_inventory_map(db: DatabaseManager) -> Dict[str, Set[int]]:
    """构建「煤炉商品 ID（含规范化键）→ 绑定的库存 id 集合」。

    inventory.mercari_item_id 可能一行多 ID（、分隔），逐个拆分匹配。
    """
    rows = db.execute_query(
        """
        SELECT [id], [mercari_item_id]
        FROM [inventory]
        WHERE COALESCE([is_delete], 0) = 0
          AND TRIM(IFNULL([mercari_item_id], '')) != ''
        """
    )
    out: Dict[str, Set[int]] = {}
    for inv_id_raw, mids_raw in rows or []:
        try:
            inv_id = int(inv_id_raw)
        except (TypeError, ValueError):
            continue
        for mid in _split_mercari_item_ids(mids_raw):
            for key in _norm_keys(mid):
                out.setdefault(key, set()).add(inv_id)
    return out


def _inventories_with_pending(db: DatabaseManager, inv_ids: Iterable[int]) -> Set[int]:
    """返回这些库存中「存在未出库的非终态订单行」的库存 id 集合（用于售出 vs 下架判别）。"""
    ids = sorted({int(i) for i in inv_ids if i is not None})
    if not ids:
        return set()
    inv_ph = ",".join("?" * len(ids))
    term_ph = ",".join("?" * len(TERMINAL_ORDER_STATUSES))
    rows = db.execute_query(
        f"""
        SELECT DISTINCT l.[inventory_id]
        FROM [order_outbound_lines] l
        INNER JOIN [orders] o ON o.[order_no] = l.[order_no]
        WHERE l.[inventory_id] IN ({inv_ph})
          AND COALESCE(l.[is_stocked_out], 0) = 0
          AND o.[status] NOT IN ({term_ph})
        """,
        tuple(ids) + tuple(TERMINAL_ORDER_STATUSES),
    )
    out: Set[int] = set()
    for (iid,) in rows or []:
        try:
            out.add(int(iid))
        except (TypeError, ValueError):
            continue
    return out


def _load_listing_states(
    db: DatabaseManager, item_ids: Iterable[str]
) -> Dict[str, Dict[str, object]]:
    """按 item_id 读取 on_sale_items 的 status / is_delete / counted_on_sale（未软删的最新一条）。

    返回 {规范化键: {item_id, status, is_delete, counted}}。同一商品多键都会指向同一状态。
    """
    cleaned: List[str] = []
    seen: Set[str] = set()
    for raw in item_ids:
        for key in _norm_keys(raw):
            if key not in seen:
                seen.add(key)
                cleaned.append(key)
    if not cleaned:
        return {}
    ph = ",".join("?" * len(cleaned))
    rows = db.execute_query(
        f"""
        SELECT [item_id], [status], COALESCE([is_delete], 0), COALESCE([counted_on_sale], 0)
        FROM [on_sale_items]
        WHERE TRIM([item_id]) IN ({ph})
        ORDER BY [id] DESC
        """,
        tuple(cleaned),
    )
    out: Dict[str, Dict[str, object]] = {}
    for item_id, status, is_delete, counted in rows or []:
        state = {
            "item_id": str(item_id or "").strip(),
            "status": (str(status or "").strip() or None),
            "is_delete": int(is_delete or 0),
            "counted": int(counted or 0),
        }
        for key in _norm_keys(str(item_id or "")):
            out.setdefault(key, state)
    return out


def reconcile_listing_counts(item_ids: Iterable[str]) -> Dict[str, int]:
    """对给定煤炉商品 ID 集合，依据 on_sale_items 当前状态与绑定库存，将「在售/库存」计数对齐。

    幂等：凭 on_sale_items.counted_on_sale 标记，仅在「应计入」状态翻转时增减。
      · counted 0 → 应计入(未软删 + status∈on_sale/stop + 已绑定存在库存)：上架 → 库存-1, 在售+1，标记=1
      · counted 1 → 不应计入：该 listing 退出
          - 绑定库存存在未出库的非终态订单行 → 售出：仅 在售-1（待出由订单派生），标记=0
          - 否则 → 下架：在售-1, 库存+1，标记=0
      · 其余（暂停/恢复、未绑定、状态不变）：不动

    返回统计 {listed_inc, delisted, sold_released}。
    """
    db = DatabaseManager()
    states = _load_listing_states(db, item_ids)
    if not states:
        return {"listed_inc": 0, "delisted": 0, "sold_released": 0}

    bound_map = _bound_inventory_map(db)

    # 先收集所有「需要判别售出」的候选库存，批量查 pending，避免逐条查询
    candidate_invs: Set[int] = set()
    # 去重：按 item_id 唯一处理（多键指向同一 state）
    unique_states: Dict[str, Dict[str, object]] = {}
    for state in states.values():
        iid = str(state.get("item_id") or "").strip()
        if iid:
            unique_states[iid] = state

    for iid, state in unique_states.items():
        counted = int(state.get("counted") or 0)
        if counted == 1:
            for key in _norm_keys(iid):
                candidate_invs |= bound_map.get(key, set())
    pending_invs = _inventories_with_pending(db, candidate_invs)

    stats = {"listed_inc": 0, "delisted": 0, "sold_released": 0}

    for iid, state in unique_states.items():
        status = state.get("status")
        is_delete = int(state.get("is_delete") or 0)
        counted = int(state.get("counted") or 0)

        bound: Set[int] = set()
        for key in _norm_keys(iid):
            bound |= bound_map.get(key, set())

        should_count = (
            is_delete == 0
            and (status in LISTED_STATUSES)
            and bool(bound)
        )

        if should_count and counted == 0:
            # 上架：每个绑定库存 库存-1, 在售+1
            for inv_id in bound:
                _adjust_inventory(db, inv_id, quantity_delta=-1, on_sale_delta=+1)
            _set_counted_flag(db, iid, 1)
            stats["listed_inc"] += len(bound)
        elif not should_count and counted == 1:
            # 退出在售：逐个绑定库存释放在售；售出不回补库存，下架回补库存
            for inv_id in bound:
                if inv_id in pending_invs:
                    _adjust_inventory(db, inv_id, on_sale_delta=-1)
                    stats["sold_released"] += 1
                else:
                    _adjust_inventory(db, inv_id, quantity_delta=+1, on_sale_delta=-1)
                    stats["delisted"] += 1
            _set_counted_flag(db, iid, 0)
        # 其余情形：暂停/恢复（counted 保持 1）、未绑定（counted 保持 0）等，不动

    if stats["listed_inc"] or stats["delisted"] or stats["sold_released"]:
        log.info("[inventory_counters] reconcile %s -> %s", list(unique_states.keys()), stats)
    return stats
