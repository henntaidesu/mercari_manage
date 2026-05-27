# -*- coding: utf-8 -*-
"""备忘录 / 站内信处理器：用户互发留言 + 已读状态 + 附图。"""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, File, HTTPException, UploadFile
from pydantic import BaseModel as PydanticModel

from ....auth import require_auth
from ....db_manage.database import DatabaseManager
from ....db_manage.models.memo import MemoModel
from ...image_storage import (
    delete_image_file,
    is_base64_image,
    save_base64_image,
    save_upload_image,
)

db = DatabaseManager()

MAX_MEMO_IMAGES = 9


class MemoCreate(PydanticModel):
    receiver_id: int
    title: Optional[str] = None
    content: str
    images: Optional[List[str]] = None  # 每项为 /imges/... 路径或 data:image/...;base64,... 数据 URL


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


def _parse_images_json(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        v = json.loads(raw)
        if isinstance(v, list):
            return [str(x) for x in v if x]
    except Exception:
        pass
    return []


def _normalize_image_inputs(items: Optional[List[str]]) -> List[str]:
    if not items:
        return []
    if len(items) > MAX_MEMO_IMAGES:
        raise HTTPException(
            status_code=400, detail=f"最多附 {MAX_MEMO_IMAGES} 张图片"
        )
    out: List[str] = []
    for it in items:
        if not it:
            continue
        s = str(it).strip()
        if not s:
            continue
        if is_base64_image(s):
            try:
                out.append(save_base64_image(s, prefix="memo"))
            except Exception:
                raise HTTPException(
                    status_code=400, detail="图片格式无效或保存失败"
                )
        elif s.startswith("/imges/"):
            out.append(s)
        else:
            raise HTTPException(status_code=400, detail="图片路径无效")
    return out


def _serialize(memo: MemoModel, name_map: dict) -> dict:
    d = memo.to_dict()
    d["sender"] = name_map.get(memo.sender_id)
    d["receiver"] = name_map.get(memo.receiver_id)
    d["is_read"] = bool(memo.is_read)
    d["images"] = _parse_images_json(memo.images_json)
    d.pop("images_json", None)
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
    processed: bool = False,
    page: int = 1,
    page_size: int = 20,
    claims: dict = Depends(require_auth),
):
    me = _current_user_id(claims)
    where = "receiver_id = ?"
    params: list = [me]
    # 收件箱默认只显示待处理项；已处理项在「已处理」标签页单独查看
    if processed:
        where += " AND COALESCE(is_read, 0) = 1"
    else:
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

    image_paths = _normalize_image_inputs(data.images)
    title = (data.title or "").strip() or None
    images_json = (
        json.dumps(image_paths, ensure_ascii=False, separators=(",", ":"))
        if image_paths
        else None
    )
    # 显式写入本地时间，避免依赖模型默认值 'CURRENT_TIMESTAMP'（会被当作字符串字面量写入）
    memo = MemoModel(
        sender_id=me,
        receiver_id=receiver_id,
        title=title,
        content=content,
        images_json=images_json,
        is_read=0,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    if not memo.save():
        # 保存失败时清理已落盘的图片，避免孤儿文件
        for p in image_paths:
            delete_image_file(p)
        raise HTTPException(status_code=500, detail="发送失败")
    name_map = _user_name_map([me, receiver_id])
    return _serialize(memo, name_map)


async def upload_memo_image(
    file: UploadFile = File(...),
    _claims: dict = Depends(require_auth),
):
    """先 multipart 上传落盘，返回 /imges/ 路径，提交备忘录时只传路径。"""
    path = await save_upload_image(file, prefix="memo")
    return {"path": path}


def mark_read(data: MarkReadBody, claims: dict = Depends(require_auth)):
    me = _current_user_id(claims)
    ids = [int(i) for i in (data.ids or []) if int(i) > 0]
    if not ids:
        raise HTTPException(status_code=400, detail="请提供 ids")
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    image_paths = _parse_images_json(memo.images_json)
    if not memo.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    for p in image_paths:
        delete_image_file(p)
    return {"message": "删除成功"}
