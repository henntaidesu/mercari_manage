# -*- coding: utf-8 -*-
"""
代办事项查询：分页 + 多条件过滤；联表 meilu_accounts 取 account_name 用于前端显示。
"""

from typing import Any, Dict, List, Optional

from ....db_manage.database import DatabaseManager


_LIST_COLS = (
    "id",
    "account_id",
    "uuid",
    "kind",
    "title",
    "message",
    "photo_url",
    "photo_type",
    "status",
    "args_json",
    "intent_json",
    "item_id",
    "item_name",
    "sender_id",
    "mercari_created",
    "mercari_updated",
    "is_delete",
    "synced_at",
)


def list_todos(
    account_id: Optional[int] = None,
    kind: Optional[str] = None,
    keyword: Optional[str] = None,
    include_deleted: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    分页列出本地 ``todo_items``，附 ``account_name``。

    - ``include_deleted=False``（默认）只显示未完成（``is_delete=0``）
    - ``keyword`` 匹配 title / message / item_id / item_name
    """
    db = DatabaseManager()
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 20), 200))

    where = ["1=1"]
    params: List[Any] = []
    if not include_deleted:
        where.append("COALESCE(t.[is_delete], 0) = 0")
    if account_id is not None:
        where.append("t.[account_id] = ?")
        params.append(int(account_id))
    if kind:
        where.append("t.[kind] = ?")
        params.append(str(kind).strip())
    if keyword:
        kw = f"%{str(keyword).strip()}%"
        where.append(
            "(IFNULL(t.[title], '') LIKE ? "
            "OR IFNULL(t.[message], '') LIKE ? "
            "OR IFNULL(t.[item_id], '') LIKE ? "
            "OR IFNULL(t.[item_name], '') LIKE ?)"
        )
        params.extend([kw, kw, kw, kw])

    where_sql = " AND ".join(where)
    total = db.execute_query(
        f"SELECT COUNT(*) FROM [todo_items] t WHERE {where_sql}",
        tuple(params),
    )[0][0]

    sel_cols = ", ".join(f"t.[{c}]" for c in _LIST_COLS) + ", a.[account_name] AS account_name"
    offset = (page - 1) * page_size
    rows = db.execute_query(
        f"""
        SELECT {sel_cols}
        FROM [todo_items] t
        LEFT JOIN [meilu_accounts] a ON a.[id] = t.[account_id]
        WHERE {where_sql}
        ORDER BY COALESCE(t.[is_delete], 0) ASC,
                 COALESCE(t.[mercari_updated], t.[mercari_created], 0) DESC,
                 t.[id] DESC
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
    """返回所有出现过的 kind（前端做下拉用，含已删行也算）。"""
    db = DatabaseManager()
    rows = db.execute_query(
        "SELECT DISTINCT [kind] FROM [todo_items] "
        "WHERE [kind] IS NOT NULL AND TRIM([kind]) != '' ORDER BY [kind] ASC"
    )
    return [r[0] for r in rows if r and r[0]]
