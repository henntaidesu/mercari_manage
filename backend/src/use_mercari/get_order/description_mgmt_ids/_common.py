# -*- coding: utf-8 -*-
"""管理ID/暗号 解析共享：正则常量 / OutboundToken / 文本与数字小工具"""
from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple


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

def _normalize_int_id(value: Any) -> Optional[int]:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None
