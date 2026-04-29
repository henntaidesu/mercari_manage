# -*- coding: utf-8 -*-
"""
仓库表模型
"""

from typing import Dict, Any, List
from ..base_model import BaseModel


class WarehouseModel(BaseModel):
    """仓库表"""

    @classmethod
    def get_table_name(cls) -> str:
        return "warehouses"

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
            'location': {
                'type': 'TEXT',
                'not_null': False,
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
        """根据名称查找仓库"""
        result = cls.find_all("name = ?", (name,), limit=1)
        return result[0] if result else None

    @classmethod
    def get_stats(cls, warehouse_id: int) -> Dict[str, int]:
        """获取仓库的库存统计"""
        db = cls().db
        total_qty = db.execute_query(
            "SELECT COALESCE(SUM(quantity), 0) FROM [inventory] WHERE warehouse_id = ?",
            (warehouse_id,)
        )
        product_types = db.execute_query(
            "SELECT COUNT(*) FROM [inventory] WHERE warehouse_id = ?",
            (warehouse_id,)
        )
        return {
            'total_quantity': total_qty[0][0] if total_qty else 0,
            'product_types': product_types[0][0] if product_types else 0,
        }
