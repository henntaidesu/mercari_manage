# -*- coding: utf-8 -*-
"""订单管理共享辅助函数与常量。"""
import json
from typing import List, Optional

from fastapi import HTTPException

from ....db_manage.database import DatabaseManager
from ....db_manage.models.order_outbound_line import OrderOutboundLineModel

db = DatabaseManager()

# 订单 status 仅使用煤炉侧取值（与 items 列表 / 取引详情一致）
ORDER_STATUSES = frozenset(
    {
        "pending",
        "trading",
        "wait_payment",
        "wait_shipping",
        "wait_review",
        "done",
        "sold_out",
        "cancelled",
        "cancel_request",
    }
)
ALL_ORDER_STATUSES = ORDER_STATUSES


def _encode_thumbnails(urls: Optional[List[str]]) -> Optional[str]:
    if not urls:
        return None
    out = [str(u).strip() for u in urls if u is not None and str(u).strip()]
    return json.dumps(out, ensure_ascii=False) if out else None


def _validate_status_query(status: Optional[str]) -> None:
    """列表/统计筛选：仅允许煤炉订单状态。"""
    if status is None or not str(status).strip():
        return
    s = str(status).strip()
    if s not in ALL_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="订单状态错误")


def _validate_order_status(status: str):
    if status not in ALL_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="订单状态错误")


def _normalize_order_no(order_no: str) -> str:
    val = (order_no or "").strip()
    if not val:
        raise HTTPException(status_code=400, detail="订单号不能为空")
    return val


def _inventory_ids_for_order(order_no: str) -> List[int]:
    rows = db.execute_query(
        """
        SELECT DISTINCT [inventory_id]
        FROM [order_outbound_lines]
        WHERE [order_no] = ? AND [inventory_id] IS NOT NULL
        """,
        ((order_no or "").strip(),),
    )
    out: List[int] = []
    for (raw_id,) in rows:
        try:
            n = int(raw_id)
        except (TypeError, ValueError):
            continue
        if n > 0:
            out.append(n)
    return out


def _outbound_line_has_inventory_id(line: OrderOutboundLineModel) -> bool:
    raw = line.inventory_id
    if raw is None:
        return False
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return False
    return n > 0
