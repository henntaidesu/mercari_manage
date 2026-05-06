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
                'default': None,
            },
            'warehouse': {
                'type': 'TEXT',
                'not_null': False,
                'default': '默认仓库',
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
        return [
            {
                'name': 'idx_warehouses_warehouse_name',
                'columns': ['warehouse', 'name'],
                'unique': True,
            },
        ]

    @classmethod
    def normalize_warehouse_key(cls, warehouse: Any) -> str:
        if warehouse is None:
            return '默认仓库'
        t = str(warehouse).strip()
        return t if t else '默认仓库'

    @classmethod
    def find_by_name(cls, name: str):
        """根据货架名称查找（仍可能有同名跨仓库，谨慎使用）"""
        result = cls.find_all("name = ?", (name,), limit=1)
        return result[0] if result else None

    @classmethod
    def find_by_warehouse_and_name(cls, warehouse: Any, name: str):
        """同一仓库下货架名称唯一"""
        wh = cls.normalize_warehouse_key(warehouse)
        result = cls.find_all(
            "COALESCE(NULLIF(TRIM([warehouse]), ''), '默认仓库') = ? AND [name] = ?",
            (wh, name),
            limit=1,
        )
        return result[0] if result else None

    @classmethod
    def get_stats(cls, warehouse_id: int) -> Dict[str, int]:
        """获取仓库统计（基于 transactions 计算净库存）"""
        db = cls().db
        total_qty = db.execute_query(
            """
            SELECT COALESCE(SUM(
                CASE
                    WHEN type = 'in' AND warehouse_id = ? THEN quantity
                    WHEN type = 'out' AND warehouse_id = ? THEN -quantity
                    WHEN type = 'transfer' AND warehouse_id = ? THEN -quantity
                    WHEN type = 'transfer' AND target_warehouse_id = ? THEN quantity
                    ELSE 0
                END
            ), 0)
            FROM [transactions]
            """,
            (warehouse_id, warehouse_id, warehouse_id, warehouse_id)
        )
        product_types = db.execute_query(
            """
            SELECT COUNT(*) FROM (
                SELECT product_id,
                       SUM(
                           CASE
                               WHEN type = 'in' AND warehouse_id = ? THEN quantity
                               WHEN type = 'out' AND warehouse_id = ? THEN -quantity
                               WHEN type = 'transfer' AND warehouse_id = ? THEN -quantity
                               WHEN type = 'transfer' AND target_warehouse_id = ? THEN quantity
                               ELSE 0
                           END
                       ) AS net_qty
                FROM [transactions]
                GROUP BY product_id
                HAVING net_qty > 0
            ) t
            """,
            (warehouse_id, warehouse_id, warehouse_id, warehouse_id)
        )
        return {
            'total_quantity': total_qty[0][0] if total_qty else 0,
            'product_types': product_types[0][0] if product_types else 0,
        }
