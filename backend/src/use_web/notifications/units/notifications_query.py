# -*- coding: utf-8 -*-
"""
お知らせ通知查询：分页 + 多条件过滤；联表 meilu_accounts 取 account_name。
"""

from typing import Any, Dict, List, Optional

from ....db_manage.database import DatabaseManager


_LIST_COLS = (
    "id",
    "account_id",
    "uuid",
    "kind",
    "message",
    "action_url",
    "photo_url",
    "photo_type",
    "args_json",
    "intent_json",
    "item_id",
    "item_name",
    "item_thumbnail",
    "sender_id",
    "price",
    "bid_price",
    "activity",
    "target_url",
    "mercari_created",
    "is_read",
    "synced_at",
)


def list_notifications(
    account_id: Optional[int] = None,
    kind: Optional[str] = None,
    keyword: Optional[str] = None,
    only_unread: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    分页列出本地 ``notifications``，附 ``account_name``。

    - ``only_unread=True`` 仅显示未读（``is_read=0``）
    - ``keyword`` 匹配 message / item_id / item_name
    """
    db = DatabaseManager()
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 20), 200))

    where = ["1=1"]
    params: List[Any] = []
    if only_unread:
        where.append("COALESCE(n.[is_read], 0) = 0")
    if account_id is not None:
        where.append("n.[account_id] = ?")
        params.append(int(account_id))
    if kind:
        where.append("n.[kind] = ?")
        params.append(str(kind).strip())
    if keyword:
        kw = f"%{str(keyword).strip()}%"
        where.append(
            "(IFNULL(n.[message], '') LIKE ? "
            "OR IFNULL(n.[item_id], '') LIKE ? "
            "OR IFNULL(n.[item_name], '') LIKE ?)"
        )
        params.extend([kw, kw, kw])

    where_sql = " AND ".join(where)
    total = db.execute_query(
        f"SELECT COUNT(*) FROM [notifications] n WHERE {where_sql}",
        tuple(params),
    )[0][0]

    sel_cols = ", ".join(f"n.[{c}]" for c in _LIST_COLS) + ", a.[account_name] AS account_name"
    offset = (page - 1) * page_size
    rows = db.execute_query(
        f"""
        SELECT {sel_cols}
        FROM [notifications] n
        LEFT JOIN [meilu_accounts] a ON a.[id] = n.[account_id]
        WHERE {where_sql}
        ORDER BY COALESCE(n.[mercari_created], 0) DESC, n.[id] DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [page_size, offset]),
    )
    keys = list(_LIST_COLS) + ["account_name"]
    items = [dict(zip(keys, row)) for row in rows]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


def list_kinds() -> List[str]:
    """返回所有出现过的 kind（前端下拉用）。"""
    db = DatabaseManager()
    rows = db.execute_query(
        "SELECT DISTINCT [kind] FROM [notifications] "
        "WHERE [kind] IS NOT NULL AND TRIM([kind]) != '' ORDER BY [kind] ASC"
    )
    return [r[0] for r in rows if r and r[0]]


def mark_read(ids: List[int], is_read: bool = True) -> Dict[str, Any]:
    """批量标记已读/未读，返回受影响行数。"""
    ids_int = [int(i) for i in (ids or []) if isinstance(i, (int, str)) and str(i).strip().lstrip("-").isdigit()]
    if not ids_int:
        return {"updated": 0}
    db = DatabaseManager()
    placeholders = ",".join(["?"] * len(ids_int))
    affected = db.execute_update(
        f"UPDATE [notifications] SET [is_read] = ? WHERE [id] IN ({placeholders})",
        tuple([1 if is_read else 0] + ids_int),
    )
    return {"updated": int(affected or 0)}


def mark_all_read(account_id: Optional[int] = None) -> Dict[str, Any]:
    """把某账号（或全部）未读通知标记为已读。"""
    db = DatabaseManager()
    if account_id is not None:
        affected = db.execute_update(
            "UPDATE [notifications] SET [is_read] = 1 "
            "WHERE [account_id] = ? AND COALESCE([is_read], 0) = 0",
            (int(account_id),),
        )
    else:
        affected = db.execute_update(
            "UPDATE [notifications] SET [is_read] = 1 WHERE COALESCE([is_read], 0) = 0"
        )
    return {"updated": int(affected or 0)}
