# -*- coding: utf-8 -*-
"""话术表模型

全局共享的客服话术 / 常用回复模板。可按分类分组、手动排序，并统计复制使用次数。
"""

from typing import Dict, Any, List
from ..base_model import BaseModel


class TalkScriptModel(BaseModel):
    """话术 / 常用回复模板（全局共享）"""

    @classmethod
    def get_table_name(cls) -> str:
        return "talk_scripts"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            'id': {
                'type': 'INTEGER',
                'primary_key': True,
                'autoincrement': True,
                'not_null': True,
            },
            'title': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
            },
            'content': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
            },
            'category': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            'sort_order': {
                'type': 'INTEGER',
                'not_null': True,
                'default': 0,
            },
            'use_count': {
                'type': 'INTEGER',
                'not_null': True,
                'default': 0,
            },
            'created_at': {
                'type': 'DATETIME',
                'not_null': False,
                'default': 'CURRENT_TIMESTAMP',
            },
            'updated_at': {
                'type': 'DATETIME',
                'not_null': False,
                'default': None,
            },
        }

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {'name': 'idx_talk_scripts_category', 'columns': ['category']},
            {'name': 'idx_talk_scripts_sort', 'columns': ['sort_order']},
        ]
