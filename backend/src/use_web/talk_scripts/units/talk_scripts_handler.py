# -*- coding: utf-8 -*-
"""话术表处理器：全局共享的客服话术 / 常用回复模板的增删改查 + 使用计数。"""

from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel as PydanticModel

from ....auth import require_auth
from ....db_manage.database import DatabaseManager
from ....db_manage.models.talk_script import TalkScriptModel

db = DatabaseManager()


class ScriptBody(PydanticModel):
    title: str
    content: str
    category: Optional[str] = None
    sort_order: Optional[int] = 0


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _serialize(s: TalkScriptModel) -> dict:
    return s.to_dict()


def _clean(body: ScriptBody) -> dict:
    title = (body.title or "").strip()
    content = (body.content or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="话术标题不能为空")
    if not content:
        raise HTTPException(status_code=400, detail="话术内容不能为空")
    category = (body.category or "").strip() or None
    try:
        sort_order = int(body.sort_order or 0)
    except (TypeError, ValueError):
        sort_order = 0
    return {"title": title, "content": content, "category": category, "sort_order": sort_order}


def list_scripts(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    _claims: dict = Depends(require_auth),
):
    """返回话术列表（按 sort_order 升序、id 降序）。支持按分类筛选 / 关键字搜索。"""
    where = ""
    clauses = []
    params: list = []
    if category and category.strip():
        clauses.append("COALESCE(category, '') = ?")
        params.append(category.strip())
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        clauses.append("(title LIKE ? OR content LIKE ? OR COALESCE(category, '') LIKE ?)")
        params.extend([kw, kw, kw])
    if clauses:
        where = " AND ".join(clauses)
    rows = TalkScriptModel.find_all(
        where=where,
        params=tuple(params),
        order_by="sort_order ASC, id DESC",
    )
    return {"items": [_serialize(r) for r in rows], "total": len(rows)}


def list_categories(_claims: dict = Depends(require_auth)):
    """返回去重后的分类列表（供前端筛选用）。"""
    rows = db.execute_query(
        "SELECT DISTINCT category FROM [talk_scripts] "
        "WHERE category IS NOT NULL AND TRIM(category) != '' ORDER BY category ASC"
    )
    return {"categories": [r[0] for r in rows if r[0]]}


def create_script(body: ScriptBody, _claims: dict = Depends(require_auth)):
    data = _clean(body)
    script = TalkScriptModel(
        title=data["title"],
        content=data["content"],
        category=data["category"],
        sort_order=data["sort_order"],
        use_count=0,
        created_at=_now(),
        updated_at=_now(),
    )
    if not script.save():
        raise HTTPException(status_code=500, detail="新增失败")
    return _serialize(script)


def update_script(sid: int, body: ScriptBody, _claims: dict = Depends(require_auth)):
    script = TalkScriptModel.find_by_id(id=sid)
    if not script:
        raise HTTPException(status_code=404, detail="话术不存在")
    data = _clean(body)
    script.title = data["title"]
    script.content = data["content"]
    script.category = data["category"]
    script.sort_order = data["sort_order"]
    script.updated_at = _now()
    if not script.save():
        raise HTTPException(status_code=500, detail="更新失败")
    return _serialize(script)


def delete_script(sid: int, _claims: dict = Depends(require_auth)):
    script = TalkScriptModel.find_by_id(id=sid)
    if not script:
        raise HTTPException(status_code=404, detail="话术不存在")
    if not script.delete():
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}


def mark_used(sid: int, _claims: dict = Depends(require_auth)):
    """复制话术时调用：使用次数 +1。"""
    affected = db.execute_update(
        "UPDATE [talk_scripts] SET use_count = COALESCE(use_count, 0) + 1 WHERE id = ?",
        (sid,),
    )
    if affected <= 0:
        raise HTTPException(status_code=404, detail="话术不存在")
    script = TalkScriptModel.find_by_id(id=sid)
    return {"use_count": script.use_count if script else None}
