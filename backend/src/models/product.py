# -*- coding: utf-8 -*-
"""
商品表模型
"""

from typing import Dict, Any, List, Optional
from ..base_model import BaseModel


class ProductModel(BaseModel):
    """商品表（图片以 Base64 格式存储于 image 字段）"""

    @classmethod
    def get_table_name(cls) -> str:
        return "inventory"

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
                'not_null': False,
                'default': None,
            },
            'barcode': {
                'type': 'TEXT',
                'not_null': False,
                'unique': True,
                'default': None,
            },
            'sku': {
                'type': 'TEXT',
                'not_null': False,
                'unique': True,
                'default': None,
            },
            'category_id': {
                'type': 'INTEGER',
                'not_null': False,
                'default': None,
            },
            'warehouse_id': {
                'type': 'INTEGER',
                'not_null': False,
                'default': None,
            },
            'price': {
                'type': 'REAL',
                'not_null': False,
                'default': 0,
            },
            'quantity': {
                'type': 'INTEGER',
                'not_null': False,
                'default': 0,
            },
            'description': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            'image': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            'image_front': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            'image_back': {
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
            {'name': 'idx_inventory_name', 'columns': ['name']},
            {'name': 'idx_inventory_category', 'columns': ['category_id']},
            {'name': 'idx_inventory_barcode', 'columns': ['barcode'], 'unique': True},
        ]

    @classmethod
    def find_with_stock(cls, keyword: Optional[str] = None, category_id: Optional[int] = None) -> List[dict]:
        """查询商品列表，附带分类名称"""
        db = cls().db
        product_fields = list(cls.get_fields().keys())
        product_select = ", ".join([f"p.[{f}] AS [{f}]" for f in product_fields])
        sql = f"""
            SELECT {product_select}, c.name as category_name, w.name as warehouse_name
            FROM [inventory] p
            LEFT JOIN [categories] c ON c.id = p.category_id
            LEFT JOIN [warehouses] w ON w.id = p.warehouse_id
            WHERE 1=1
        """
        params = []
        if keyword:
            sql += " AND (p.name LIKE ? OR p.barcode LIKE ?)"
            params += [f"%{keyword}%", f"%{keyword}%"]
        if category_id:
            sql += " AND p.category_id = ?"
            params.append(category_id)
        sql += " ORDER BY p.id DESC"
        rows = db.execute_query(sql, tuple(params))
        if not rows:
            return []
        field_names = product_fields + ['category_name', 'warehouse_name']
        return [dict(zip(field_names, row)) for row in rows]
