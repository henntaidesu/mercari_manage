# -*- coding: utf-8 -*-
"""备忘录 / 站内信处理器：用户互发留言 + 已读状态。"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel as PydanticModel

from ....auth import require_auth
from ....db_manage.database import DatabaseManager
from ....db_manage.models.memo import MemoModel

db = DatabaseManager()


class MemoCreate(PydanticModel):
    receiver_id: int
    title: Optional[str] = None
    content: str


class MarkReadBody(PydanticModel):
    ids: Optional[List[int]] = None
    is_read: bool = True


def _current_user_id(claims: dict) -> int:
    uid = int(claims.get("sub") or 0)
    if uid <= 0:
        raise HTTPException(status_code=401, detail="无效的登录凭证")
    return uid


def _user_name_map(user_ids: List[int]) -> dict:
    if not user_ids:
        return {}
    placeholders = ",".join(["?"] * len(user_ids))
    rows = db.execute_query(
        f"SELECT id, username, display_name FROM [users] WHERE id IN ({placeholders})",
        tuple(user_ids),
    )
    return {
        row[0]: {"id": row[0], "username": row[1], "display_name": row[2] or row[1]}
        for row in rows
    }


def _serialize(memo: MemoModel, name_map: dict) -> dict:
    d = memo.to_dict()
    d["sender"] = name_map.get(memo.sender_id)
    d["receiver"] = name_map.get(memo.receiver_id)
    d["is_read"] = bool(memo.is_read)
    return d


def list_users_for_memo(claims: dict = Depends(require_auth)):
    """返回可发送备忘录的用户列表（排除自己 + 已禁用用户）。"""
    me = _current_user_id(claims)
    rows = db.execute_query(
        """
        SELECT id, username, display_name
        FROM [users]
        WHERE id != ? AND COALESCE(is_active, 1) = 1
        ORDER BY id ASC
        """,
        (me,),
    )
    return [
        {"id": r[0], "username": r[1], "display_name": r[2] or r[1]}
        for r in rows
    ]


def list_inbox(
    keyword: Optional[str] = None,
    only_unread: bool = False,
    page: int = 1,
    page_size: int = 20,
    claims: dict = Depends(require_auth),
):
    me = _current_user_id(claims)
    where = "receiver_id = ?"
    params: list = [me]
    if only_unread:
        where += " AND COALESCE(is_read, 0) = 0"
    if keyword:
        kw = f"%{keyword.strip()}%"
        where += " AND (COALESCE(title, '') LIKE ? OR COALESCE(content, '') LIKE ?)"
        params.extend([kw, kw])

    total = MemoModel.count(where=where, params=tuple(params))
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 20), 200))
    offset = (page - 1) * page_size
    rows = MemoModel.find_all(
        where=where,
        params=tuple(params),
        order_by="created_at DESC, id DESC",
        limit=page_size,
        offset=offset,
    )
    user_ids = {r.sender_id for r in rows} | {r.receiver_id for r in rows}
    name_map = _user_name_map(list(user_ids))
    return {
        "items": [_serialize(r, name_map) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def list_sent(
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    claims: dict = Depends(require_auth),
):
    me = _current_user_id(claims)
    where = "sender_id = ?"
    params: list = [me]
    if keyword:
        kw = f"%{keyword.strip()}%"
        where += " AND (COALESCE(title, '') LIKE ? OR COALESCE(content, '') LIKE ?)"
        params.extend([kw, kw])
    total = MemoModel.count(where=where, params=tuple(params))
    page = max(1, int(page or 1))
    page_size = max(1, min(int(page_size or 20), 200))
    offset = (page - 1) * page_size
    rows = MemoModel.find_all(
        where=where,
        params=tuple(params),
        order_by="created_at DESC, id DESC",
        limit=page_size,
        offset=offset,
    )
    user_ids = {r.sender_id for r in rows} | {r.receiver_id for r in rows}
    name_map = _user_name_map(list(user_ids))
    return {
        "items": [_serialize(r, name_map) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def unread_count(claims: dict = Depends(require_auth)):
    me = _current_user_id(claims)
    n = MemoModel.count(
        where="receiver_id = ? AND COALESCE(is_read, 0) = 0",
        params=(me,),
    )
    return {"unread": n}


def create_memo(data: MemoCreate, claims: dict = Depends(require_auth)):
    me = _current_user_id(claims)
    content = (data.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="留言内容不能为空")
    receiver_id = int(data.receiver_id or 0)
    if receiver_id <= 0:
        raise HTTPException(status_code=400, detail="请选择接收用户")
    exists = db.execute_query(
        "SELECT 1 FROM [users] WHERE id = ? AND COALESCE(is_active, 1) = 1 LIMIT 1",
        (receiver_id,),
    )
    if not exists:
        raise HTTPException(status_code=404, detail="接收用户不存在或已禁用")

    title = (data.title or "").strip() or None
    memo = MemoModel(
        sender_id=me,
        receiver_id=receiver_id,
        title=title,
        content=content,
        is_read=0,
    )
    if not memo.save():
        raise HTTPException(status_code=500, detail="发送失败")
    name_map = _user_name_map([me, receiver_id])
    return _serialize(memo, name_map)


def mark_read(data: MarkReadBody, claims: dict = Depends(require_auth)):
    me = _current_user_id(claims)
    ids = [int(i) for i in (data.ids or []) if int(i) > 0]
    if not ids:
        raise HTTPException(status_code=400, detail="请提供 ids")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    placeholders = ",".join(["?"] * len(ids))
    if data.is_read:
        affected = db.execute_update(
            f"UPDATE [memos] SET is_read = 1, read_at = ? "
            f"WHERE receiver_id = ? AND id IN ({placeholders})",
            (now_iso, me, *ids),
        )
    else:
        affected = db.execute_update(
            f"UPDATE [memos] SET is_read = 0, read_at = NULL "
            f"WHERE receiver_id = ? AND id IN ({placeholders})",
            (me, *ids),
        )
    return {"updated": affected}


def mark_all_read(claims: dict = Depends(require_auth)):
    me = _current_user_id(claims)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    affected = db.execute_update(
        "UPDATE [memos] SET is_read = 1, read_at = ? "
        "WHERE receiver_id = ? AND COALESCE(is_read, 0) = 0",
        (now_iso, me),
    )
    return {"updated": affected}


def delete_memo(mid: int, claims: dict = Depends(require_auth)):
    me = _current_user_id(claims)
    memo = MemoModel.find_by_id(id=mid)
    if not memo:
        raise HTTPException(status_code=404, detail="留言不存在")
    if memo.sender_id != me and memo.receiver_id != me:
        raise HTTPException(status_code=403, detail="无权删除该留言")
    if not memo.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}
