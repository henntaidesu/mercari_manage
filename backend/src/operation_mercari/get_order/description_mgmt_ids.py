# -*- coding: utf-8 -*-
"""
从煤炉商品说明（orders.description）中解析待出库标识：

- 「管理ID:57,56,55」「管理番号:59」—— 对应本地 inventory.id
- 「バーコード:6977850080855」或「バーコード:6977850080824,6977850080831」—— 对应 inventory.barcode

支持半角/全角冒号与逗号、顿号、空白分隔；管理 ID 段内支持全角数字；条码段内支持全角数字。
同一说明中多处「管理ID」「バーコード」按在文中出现的先后顺序交错展开。
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple

from ...db_manage.database import DatabaseManager
from ...db_manage.models.order_outbound_line import (
    TERMINAL_ORDER_STATUSES,
    OrderOutboundLineModel,
)

_FW_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")

# 捕获「管理ID」后的数字列表片段（不含前缀）
_MGMT_ID_PATTERN = re.compile(
    r"管理\s*ID\s*[:：]\s*([0-9０-９\s,，、*xX×]+)",
    re.IGNORECASE | re.MULTILINE,
)

# 「管理番号:59」—— 与管理 ID 相同语义，对应 inventory.id
_MGMT_BANGO_PATTERN = re.compile(
    r"管理\s*番号\s*[:：]\s*([0-9０-９\s,，、*xX×]+)",
    re.MULTILINE,
)

# バーコード：后为条码列表（逗号/空白分隔）；条码一般为数字，亦允许字母与常见符号
_BARCODE_PATTERN = re.compile(
    r"バーコード\s*[:：]\s*([0-9A-Za-z０-９\s,，、\-_*xX×]+)",
    re.MULTILINE,
)

# 单条解析结果：(line_kind, value) — line_kind 为 mgmt_id 时 value 为 int；为 barcode 时 value 为 str
OutboundToken = Tuple[str, Any]


def _split_chunks(segment: str) -> List[str]:
    parts: List[str] = []
    for part in re.split(r"[,，、\s]+", segment or ""):
        p = (part or "").strip()
        if p:
            parts.append(p)
    return parts


def _value_and_quantity(token: str) -> Tuple[str, int]:
    """
    支持 token 尾部数量语法：6977850080862*10 / 6977850080862×10 / 6977850080862x10。
    未携带数量时默认 1。
    """
    t = (token or "").translate(_FW_DIGITS).strip()
    if not t:
        return "", 1
    m = re.match(r"^(.*?)(?:\s*[*xX×]\s*(\d+))?$", t)
    if not m:
        return t, 1
    base = (m.group(1) or "").strip()
    qraw = (m.group(2) or "").strip()
    if not qraw:
        return base, 1
    try:
        q = int(qraw)
    except (TypeError, ValueError):
        q = 1
    return base, max(1, q)


def parse_order_description_outbound_tokens_with_quantity(
    text: Optional[str],
) -> List[Tuple[str, Any, int]]:
    """
    按说明文中出现顺序，解析出 (line_kind, value, quantity) 列表。
    line_kind: ``mgmt_id`` | ``barcode``
    """
    if text is None:
        return []
    s = str(text).strip()
    if not s:
        return []

    spans: List[Tuple[int, str, str]] = []
    for m in _MGMT_ID_PATTERN.finditer(s):
        spans.append((m.start(), "mgmt", m.group(1) or ""))
    for m in _MGMT_BANGO_PATTERN.finditer(s):
        spans.append((m.start(), "mgmt", m.group(1) or ""))
    for m in _BARCODE_PATTERN.finditer(s):
        spans.append((m.start(), "barcode", m.group(1) or ""))
    spans.sort(key=lambda x: x[0])

    out: List[Tuple[str, Any, int]] = []
    for _, kind, chunk in spans:
        for part in _split_chunks(chunk):
            base, qty = _value_and_quantity(part)
            if not base:
                continue
            if kind == "mgmt":
                try:
                    n = int(base)
                except (TypeError, ValueError):
                    continue
                out.append(("mgmt_id", n, qty))
            else:
                bc = base.strip()
                if not bc:
                    continue
                out.append(("barcode", bc, qty))
    return out


def parse_order_description_outbound_tokens(text: Optional[str]) -> List[OutboundToken]:
    """
    按说明文中出现顺序，解析出 (line_kind, value) 列表。
    line_kind: ``mgmt_id`` | ``barcode``
    """
    if text is None:
        return []
    s = str(text).strip()
    if not s:
        return []

    out: List[OutboundToken] = []
    for kind, value, qty in parse_order_description_outbound_tokens_with_quantity(s):
        repeat = max(1, int(qty or 1))
        out.extend([(kind, value)] * repeat)
    return out


def parse_management_ids_from_description(text: Optional[str]) -> List[int]:
    """
    仅从说明中解析管理 ID 序列（兼容旧调用；新逻辑见 parse_order_description_outbound_tokens）。
    """
    return [v for k, v in parse_order_description_outbound_tokens(text) if k == "mgmt_id"]


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


def sync_outbound_lines_for_order(order_no: str, description: Optional[str]) -> None:
    """
    根据最新商品说明重写该订单的 order_outbound_lines。
    无「管理ID:」「管理番号:」「バーコード:」或解析结果为空时，仅删除该订单原有明细。
    """
    ono = (order_no or "").strip()
    if not ono:
        return

    OrderOutboundLineModel.delete_all("[order_no] = ?", (ono,))
    tokens = parse_order_description_outbound_tokens_with_quantity(description)
    if not tokens:
        return

    for idx, (kind, val, qty) in enumerate(tokens):
        if kind == "mgmt_id":
            mid = int(val)
            exists = _inventory_id_exists(mid)
            line = OrderOutboundLineModel(
                order_no=ono,
                inventory_id=mid if exists else None,
                management_id=str(mid),
                line_kind="mgmt_id",
                quantity=max(1, int(qty or 1)),
                sort_index=idx,
            )
        else:
            bc = str(val).strip()
            inv_id = _inventory_id_by_barcode(bc)
            line = OrderOutboundLineModel(
                order_no=ono,
                inventory_id=inv_id,
                management_id=bc,
                line_kind="barcode",
                quantity=max(1, int(qty or 1)),
                sort_index=idx,
            )
        line.save()


def sql_pending_outbound_subquery(alias: str = "p") -> str:
    """
    用于 SELECT 中追加列：某库存行在非终态订单中的待出库件数合计。
    """
    ph = ",".join("?" * len(TERMINAL_ORDER_STATUSES))
    return f"""
        COALESCE((
            SELECT SUM(l.quantity)
            FROM [order_outbound_lines] l
            INNER JOIN [orders] o ON o.order_no = l.order_no
            WHERE l.inventory_id = {alias}.[id]
              AND o.status NOT IN ({ph})
        ), 0)
    """


def sql_pending_outbound_params() -> tuple:
    return tuple(TERMINAL_ORDER_STATUSES)
