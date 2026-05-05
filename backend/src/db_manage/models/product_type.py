# -*- coding: utf-8 -*-
"""
商品类型表模型
"""

from typing import Dict, Any, List
from ..base_model import BaseModel


class ProductTypeModel(BaseModel):
    """商品类型表"""

    @classmethod
    def get_table_name(cls) -> str:
        return "product_types"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            'id': {
                'type': 'INTEGER',
                'primary_key': True,
                'autoincrement': True,
                'not_null': True,
            },
            'name': {
                'type': 'TEXT',
                'not_null': True,
                'unique': True,
                'default': None,
            },
            'description': {
                'type': 'TEXT',
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
        return []

    @classmethod
    def find_by_name(cls, name: str):
        """根据名称查找商品类型"""
        result = cls.find_all("name = ?", (name,), limit=1)
        return result[0] if result else None

    @classmethod
    def get_product_count(cls, product_type_id: int) -> int:
        """获取该类型下的商品数量"""
        db = cls().db
        result = db.execute_query(
            "SELECT COUNT(*) FROM [inventory] WHERE product_type_id = ?", (product_type_id,)
        )
        return result[0][0] if result else 0
