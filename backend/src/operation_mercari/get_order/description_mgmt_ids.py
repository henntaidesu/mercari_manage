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
_BUNDLE_PHRASE_A = "こちらはまとめ買い商品です"
_BUNDLE_PHRASE_B = "までに購入してください"
_BUNDLE_SECTION_HEADER = "■ 商品内容"
_BUNDLE_LINE_RE = re.compile(r"^\s*[・･]\s*(.+?)\s*$")
_BUNDLE_TRAILING_STATE_RE = re.compile(r"\s*[【\[].*?[】\]]\s*$")
_MERCARI_ID_SEP_RE = re.compile(r"[\n,，、\s]+")

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


def _is_bundle_order_description(text: Optional[str]) -> bool:
    s = str(text or "").strip()
    if not s:
        return False
    return _BUNDLE_PHRASE_A in s and _BUNDLE_PHRASE_B in s and _BUNDLE_SECTION_HEADER in s


def _normalize_match_text(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").strip()).casefold()


def _split_mercari_item_ids(raw: Any) -> List[str]:
    s = str(raw or "").strip()
    if not s:
        return []
    out: List[str] = []
    seen = set()
    for part in _MERCARI_ID_SEP_RE.split(s):
        token = str(part or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


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
            TRIM(IFNULL(o.[name], ''))
        FROM [on_sale_items] o
        WHERE COALESCE(o.[is_delete], 0) = 0
          AND TRIM(IFNULL(o.[item_id], '')) != ''
          AND TRIM(IFNULL(o.[name], '')) != ''
        """,
    )
    if not rows:
        return None

    target_norm = _normalize_match_text(query_title)
    exact_item_ids: List[str] = []
    fuzzy_item_ids: List[str] = []
    for item_id_raw, name_raw in rows:
        item_id = str(item_id_raw or "").strip()
        if not item_id:
            continue
        name = str(name_raw or "").strip()
        name_norm = _normalize_match_text(name)
        if not name_norm:
            continue
        if name_norm == target_norm:
            exact_item_ids.append(item_id)
        elif target_norm and (target_norm in name_norm or name_norm in target_norm):
            fuzzy_item_ids.append(item_id)

    item_ids = exact_item_ids if exact_item_ids else fuzzy_item_ids
    if not item_ids:
        return None

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


def _normalize_int_id(value: Any) -> Optional[int]:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def refresh_inventory_pending_outbound_qty(inventory_ids: Optional[List[int]] = None) -> None:
    """
    将订单待出库汇总回写到 inventory.pending_outbound_qty：
    - 仅统计非终态订单
    - 仅统计 is_stocked_out != 1 的明细
    """
    db = DatabaseManager()
    inv_ids: List[int] = []
    if inventory_ids:
        seen = set()
        for raw in inventory_ids:
            iid = _normalize_int_id(raw)
            if iid is None or iid in seen:
                continue
            seen.add(iid)
            inv_ids.append(iid)
    if inv_ids:
        ph = ",".join("?" * len(inv_ids))
        db.execute_update(
            f"UPDATE [inventory] SET [pending_outbound_qty] = 0 WHERE [id] IN ({ph})",
            tuple(inv_ids),
        )
        term_ph = ",".join("?" * len(TERMINAL_ORDER_STATUSES))
        bind = tuple(TERMINAL_ORDER_STATUSES) + tuple(inv_ids)
        rows = db.execute_query(
            f"""
            SELECT l.[inventory_id], SUM(COALESCE(l.[quantity], 1)) AS q
            FROM [order_outbound_lines] l
            INNER JOIN [orders] o ON o.[order_no] = l.[order_no]
            WHERE l.[inventory_id] IS NOT NULL
              AND COALESCE(l.[is_stocked_out], 0) = 0
              AND o.[status] NOT IN ({term_ph})
              AND l.[inventory_id] IN ({ph})
            GROUP BY l.[inventory_id]
            """,
            bind,
        )
    else:
        db.execute_update("UPDATE [inventory] SET [pending_outbound_qty] = 0")
        term_ph = ",".join("?" * len(TERMINAL_ORDER_STATUSES))
        rows = db.execute_query(
            f"""
            SELECT l.[inventory_id], SUM(COALESCE(l.[quantity], 1)) AS q
            FROM [order_outbound_lines] l
            INNER JOIN [orders] o ON o.[order_no] = l.[order_no]
            WHERE l.[inventory_id] IS NOT NULL
              AND COALESCE(l.[is_stocked_out], 0) = 0
              AND o.[status] NOT IN ({term_ph})
            GROUP BY l.[inventory_id]
            """,
            tuple(TERMINAL_ORDER_STATUSES),
        )
    for inv_id_raw, qty_raw in rows:
        inv_id = _normalize_int_id(inv_id_raw)
        if inv_id is None:
            continue
        qty = max(0, int(qty_raw or 0))
        db.execute_update(
            "UPDATE [inventory] SET [pending_outbound_qty] = ? WHERE [id] = ?",
            (qty, inv_id),
        )


def sync_outbound_lines_for_order(order_no: str, description: Optional[str]) -> None:
    """
    根据最新商品说明重写该订单的 order_outbound_lines。
    无「管理ID:」「管理番号:」「バーコード:」或解析结果为空时，仅删除该订单原有明细。
    """
    ono = (order_no or "").strip()
    if not ono:
        return

    old_rows = OrderOutboundLineModel.find_all(
        where="[order_no] = ?",
        params=(ono,),
        order_by="sort_index ASC, id ASC",
    )
    old_inv_ids = {
        int(r.inventory_id)
        for r in old_rows
        if r.inventory_id is not None and str(r.inventory_id).strip() != ""
    }
    old_state = {}
    for r in old_rows:
        key = (
            str(r.line_kind or "").strip(),
            str(r.management_id or "").strip(),
            max(1, int(r.quantity or 1)),
            int(r.sort_index or 0),
        )
        old_state[key] = (
            int(r.is_stocked_out or 0),
            int(r.stocked_out_at) if r.stocked_out_at is not None else None,
        )

    OrderOutboundLineModel.delete_all("[order_no] = ?", (ono,))
    tokens = parse_order_description_outbound_tokens_with_quantity(description)
    if not tokens:
        if not _is_bundle_order_description(description):
            refresh_inventory_pending_outbound_qty(list(old_inv_ids))
            return
        titles = _extract_bundle_product_titles(description)
        if not titles:
            refresh_inventory_pending_outbound_qty(list(old_inv_ids))
            return
        touched_inv_ids = set(old_inv_ids)
        for idx, title in enumerate(titles):
            inv_id = _resolve_inventory_id_by_bundle_title(title)
            key = ("bundle_title", title, 1, idx)
            stocked, stocked_at = old_state.get(key, (0, None))
            line = OrderOutboundLineModel(
                order_no=ono,
                inventory_id=inv_id,
                management_id=title,
                line_kind="bundle_title",
                quantity=1,
                sort_index=idx,
                is_stocked_out=stocked,
                stocked_out_at=stocked_at,
            )
            line.save()
            if inv_id is not None:
                touched_inv_ids.add(int(inv_id))
        refresh_inventory_pending_outbound_qty(list(touched_inv_ids))
        return

    touched_inv_ids = set(old_inv_ids)
    for idx, (kind, val, qty) in enumerate(tokens):
        if kind == "mgmt_id":
            mid = int(val)
            exists = _inventory_id_exists(mid)
            key = ("mgmt_id", str(mid), max(1, int(qty or 1)), idx)
            stocked, stocked_at = old_state.get(key, (0, None))
            line = OrderOutboundLineModel(
                order_no=ono,
                inventory_id=mid if exists else None,
                management_id=str(mid),
                line_kind="mgmt_id",
                quantity=max(1, int(qty or 1)),
                sort_index=idx,
                is_stocked_out=stocked,
                stocked_out_at=stocked_at,
            )
        else:
            bc = str(val).strip()
            inv_id = _inventory_id_by_barcode(bc)
            key = ("barcode", bc, max(1, int(qty or 1)), idx)
            stocked, stocked_at = old_state.get(key, (0, None))
            line = OrderOutboundLineModel(
                order_no=ono,
                inventory_id=inv_id,
                management_id=bc,
                line_kind="barcode",
                quantity=max(1, int(qty or 1)),
                sort_index=idx,
                is_stocked_out=stocked,
                stocked_out_at=stocked_at,
            )
        line.save()
        if line.inventory_id is not None:
            touched_inv_ids.add(int(line.inventory_id))
    refresh_inventory_pending_outbound_qty(list(touched_inv_ids))


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
              AND COALESCE(l.is_stocked_out, 0) = 0
              AND o.status NOT IN ({ph})
        ), 0)
    """


def sql_pending_outbound_params() -> tuple:
    return tuple(TERMINAL_ORDER_STATUSES)
