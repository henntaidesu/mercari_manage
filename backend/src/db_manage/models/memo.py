# -*- coding: utf-8 -*-
"""备忘录 / 站内信表模型

用户之间互相留言；接收方可标记为已读。
"""

from typing import Dict, Any, List
from ..base_model import BaseModel


class MemoModel(BaseModel):
    """备忘录 / 站内信"""

    @classmethod
    def get_table_name(cls) -> str:
        return "memos"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            'id': {
                'type': 'INTEGER',
                'primary_key': True,
                'autoincrement': True,
                'not_null': True,
            },
            'sender_id': {
                'type': 'INTEGER',
                'not_null': True,
                'default': None,
            },
            'receiver_id': {
                'type': 'INTEGER',
                'not_null': True,
                'default': None,
            },
            'title': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            'content': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
            },
            'is_read': {
                'type': 'INTEGER',
                'not_null': True,
                'default': 0,
            },
            'read_at': {
                'type': 'DATETIME',
                'not_null': False,
                'default': None,
            },
            'created_at': {
                'type': 'DATETIME',
                'not_null': False,
                'default': 'CURRENT_TIMESTAMP',
            },
        }

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {'name': 'idx_memos_receiver', 'columns': ['receiver_id', 'is_read']},
            {'name': 'idx_memos_sender', 'columns': ['sender_id']},
            {'name': 'idx_memos_created_at', 'columns': ['created_at']},
        ]
