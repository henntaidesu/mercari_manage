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
        return "products"

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
            'unit': {
                'type': 'TEXT',
                'not_null': False,
                'default': "'件'",
            },
            'price': {
                'type': 'REAL',
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
            'created_at': {
                'type': 'DATETIME',
                'not_null': False,
                'default': 'CURRENT_TIMESTAMP',
            },
        }

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {'name': 'idx_products_name', 'columns': ['name']},
            {'name': 'idx_products_category', 'columns': ['category_id']},
        ]

    @classmethod
    def find_with_stock(cls, keyword: Optional[str] = None, category_id: Optional[int] = None) -> List[dict]:
        """查询商品列表，附带分类名称和总库存"""
        db = cls().db
        sql = """
            SELECT p.*, c.name as category_name,
                   COALESCE(SUM(i.quantity), 0) as total_stock
            FROM [products] p
            LEFT JOIN [categories] c ON c.id = p.category_id
            LEFT JOIN [inventory] i ON i.product_id = p.id
            WHERE 1=1
        """
        params = []
        if keyword:
            sql += " AND (p.name LIKE ? OR p.sku LIKE ?)"
            params += [f"%{keyword}%", f"%{keyword}%"]
        if category_id:
            sql += " AND p.category_id = ?"
            params.append(category_id)
        sql += " GROUP BY p.id ORDER BY p.id DESC"
        rows = db.execute_query(sql, tuple(params))
        if not rows:
            return []
        # 获取列名
        cols = [desc[0] for desc in db.execute_query("PRAGMA table_info(products)")]
        col_names = [c[1] for c in db.execute_query("PRAGMA table_info(products)")]
        # 手动构建列名（使用 SELECT 返回的列顺序）
        field_names = list(cls.get_fields().keys()) + ['category_name', 'total_stock']
        return [dict(zip(field_names, row)) for row in rows]

    @classmethod
    def get_total_stock(cls, product_id: int) -> int:
        """获取商品的总库存"""
        db = cls().db
        result = db.execute_query(
            "SELECT COALESCE(SUM(quantity), 0) FROM [inventory] WHERE product_id = ?",
            (product_id,)
        )
        return result[0][0] if result else 0
