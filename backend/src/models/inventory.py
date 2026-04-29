# -*- coding: utf-8 -*-
"""
库存表模型
"""

from typing import Dict, Any, List, Optional
from ..base_model import BaseModel


class InventoryModel(BaseModel):
    """库存表（product_id + warehouse_id 唯一约束通过唯一索引实现）"""

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
            'product_id': {
                'type': 'INTEGER',
                'not_null': True,
                'default': None,
            },
            'warehouse_id': {
                'type': 'INTEGER',
                'not_null': True,
                'default': None,
            },
            'quantity': {
                'type': 'INTEGER',
                'not_null': False,
                'default': 0,
            },
            'min_quantity': {
                'type': 'INTEGER',
                'not_null': False,
                'default': 0,
            },
            'updated_at': {
                'type': 'DATETIME',
                'not_null': False,
                'default': 'CURRENT_TIMESTAMP',
            },
        }

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'uq_inventory_product_warehouse',
                'columns': ['product_id', 'warehouse_id'],
                'unique': True,
            }
        ]

    @classmethod
    def find_by_product_warehouse(cls, product_id: int, warehouse_id: int):
        """根据商品和仓库查找库存记录"""
        result = cls.find_all("product_id = ? AND warehouse_id = ?", (product_id, warehouse_id), limit=1)
        return result[0] if result else None

    @classmethod
    def upsert(cls, product_id: int, warehouse_id: int, delta: int) -> bool:
        """增加库存（不存在则新建）"""
        db = cls().db
        existing = cls.find_by_product_warehouse(product_id, warehouse_id)
        if existing:
            return db.execute_update(
                "UPDATE [inventory] SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE product_id = ? AND warehouse_id = ?",
                (delta, product_id, warehouse_id)
            ) >= 0
        else:
            inv = cls(product_id=product_id, warehouse_id=warehouse_id, quantity=delta)
            return inv.save()

    @classmethod
    def deduct(cls, product_id: int, warehouse_id: int, quantity: int) -> tuple:
        """扣减库存，返回 (success, current_qty)"""
        existing = cls.find_by_product_warehouse(product_id, warehouse_id)
        current = existing.quantity if existing else 0
        if current < quantity:
            return False, current
        db = cls().db
        db.execute_update(
            "UPDATE [inventory] SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE product_id = ? AND warehouse_id = ?",
            (quantity, product_id, warehouse_id)
        )
        return True, current - quantity

    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """获取库存汇总数据（控制台用）"""
        db = cls().db
        from datetime import date
        today = date.today().isoformat()
        return {
            'total_products': db.execute_query("SELECT COUNT(*) FROM [products]")[0][0],
            'total_warehouses': db.execute_query("SELECT COUNT(*) FROM [warehouses]")[0][0],
            'total_stock': db.execute_query("SELECT COALESCE(SUM(quantity),0) FROM [inventory]")[0][0],
            'low_stock_count': db.execute_query(
                "SELECT COUNT(*) FROM [inventory] WHERE quantity <= min_quantity AND min_quantity > 0"
            )[0][0],
            'today_in': db.execute_query(
                "SELECT COALESCE(SUM(quantity),0) FROM [transactions] WHERE type='in' AND DATE(created_at)=?",
                (today,)
            )[0][0],
            'today_out': db.execute_query(
                "SELECT COALESCE(SUM(quantity),0) FROM [transactions] WHERE type='out' AND DATE(created_at)=?",
                (today,)
            )[0][0],
        }

    @classmethod
    def find_detail_list(cls, warehouse_id: Optional[int] = None, low_stock: Optional[bool] = None) -> List[dict]:
        """查询库存列表，附带商品和仓库信息"""
        db = cls().db
        sql = """
            SELECT i.id, i.product_id, p.name as product_name, p.sku, p.unit, p.image,
                   c.name as category_name, i.warehouse_id, w.name as warehouse_name,
                   i.quantity, i.min_quantity, i.updated_at
            FROM [inventory] i
            JOIN [products] p ON p.id = i.product_id
            LEFT JOIN [categories] c ON c.id = p.category_id
            JOIN [warehouses] w ON w.id = i.warehouse_id
            WHERE 1=1
        """
        params = []
        if warehouse_id:
            sql += " AND i.warehouse_id = ?"
            params.append(warehouse_id)
        if low_stock:
            sql += " AND i.quantity <= i.min_quantity AND i.min_quantity > 0"
        sql += " ORDER BY i.updated_at DESC"

        rows = db.execute_query(sql, tuple(params))
        keys = ['id', 'product_id', 'product_name', 'sku', 'unit', 'image',
                'category_name', 'warehouse_id', 'warehouse_name',
                'quantity', 'min_quantity', 'updated_at']
        return [dict(zip(keys, row)) for row in rows]
