# -*- coding: utf-8 -*-
"""
代办事项（Mercari /todos 页 services/todolist/v1/list 返回项）本地缓存表。

字段与 backend/test_json/待办/req.json 中 data[] 单项对齐：
- 顶层 uuid / kind / title / message / photo_url / photo_type / status
- args 是 JSON 字符串：解析出 item_id / item_name / sender_id 单独建索引
- intent 是 JSON 字符串：原样保留 intent_json
- created / updated 是 RFC3339 字符串：转毫秒存放，便于排序与去重
"""

from typing import Any, Dict, List

from ..base_model import BaseModel


class TodoItemModel(BaseModel):
    """代办事项"""

    @classmethod
    def get_table_name(cls) -> str:
        return "todo_items"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "id": {
                "type": "INTEGER",
                "primary_key": True,
                "autoincrement": True,
                "not_null": True,
            },
            "account_id": {
                "type": "INTEGER",
                "not_null": True,
                "default": None,
            },
            "uuid": {
                "type": "TEXT",
                "not_null": True,
                "default": None,
            },
            "kind": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "title": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "message": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "photo_url": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "photo_type": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "status": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "args_json": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "intent_json": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "item_id": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "item_name": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "sender_id": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            "mercari_created": {
                "type": "INTEGER",
                "not_null": False,
                "default": None,
            },
            "mercari_updated": {
                "type": "INTEGER",
                "not_null": False,
                "default": None,
            },
            "is_delete": {
                "type": "INTEGER",
                "not_null": True,
                "default": 0,
            },
            "synced_at": {
                "type": "INTEGER",
                "not_null": False,
                "default": None,
            },
        }

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "idx_todo_items_account_uuid",
                "columns": ["account_id", "uuid"],
                "unique": True,
            },
            {"name": "idx_todo_items_account_kind", "columns": ["account_id", "kind"]},
            {"name": "idx_todo_items_item_id", "columns": ["item_id"]},
            {"name": "idx_todo_items_mercari_updated", "columns": ["mercari_updated"]},
        ]
