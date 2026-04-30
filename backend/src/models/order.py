# -*- coding: utf-8 -*-
"""
订单表模型
"""

from typing import Dict, Any, List, Optional
from ..base_model import BaseModel


class OrderModel(BaseModel):
    """订单表"""

    @classmethod
    def get_table_name(cls) -> str:
        return "orders"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            'id': {
                'type': 'INTEGER',
                'primary_key': True,
                'autoincrement': True,
                'not_null': True,
            },
            'order_no': {
                'type': 'TEXT',
                'not_null': True,
                'unique': True,
                'default': None,
            },
            'order_date': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
            },
            'customer_name': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            'status': {
                'type': 'TEXT',
                'not_null': True,
                'default': "'pending'",
            },
            'amount': {
                'type': 'REAL',
                'not_null': True,
                'default': 0,
            },
            'remark': {
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
            {'name': 'idx_orders_order_no', 'columns': ['order_no'], 'unique': True},
            {'name': 'idx_orders_order_date', 'columns': ['order_date']},
            {'name': 'idx_orders_status', 'columns': ['status']},
        ]

    @classmethod
    def find_detail_list(
        cls,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        db = cls().db
        base_sql = """
            FROM [orders] o
            WHERE 1=1
        """
        params = []
        if keyword:
            base_sql += " AND (o.order_no LIKE ? OR o.customer_name LIKE ?)"
            kw = f"%{keyword}%"
            params += [kw, kw]
        if status:
            base_sql += " AND o.status = ?"
            params.append(status)
        if start_date:
            base_sql += " AND o.order_date >= ?"
            params.append(start_date)
        if end_date:
            base_sql += " AND o.order_date <= ?"
            params.append(end_date)

        total = db.execute_query(f"SELECT COUNT(*) {base_sql}", tuple(params))[0][0]
        select_sql = f"""
            SELECT o.id, o.order_no, o.order_date, o.customer_name, o.status, o.amount, o.remark, o.created_at
            {base_sql}
            ORDER BY o.order_date DESC, o.id DESC
            LIMIT ? OFFSET ?
        """
        rows = db.execute_query(select_sql, tuple(params + [page_size, (page - 1) * page_size]))
        keys = ['id', 'order_no', 'order_date', 'customer_name', 'status', 'amount', 'remark', 'created_at']
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': [dict(zip(keys, row)) for row in rows],
        }
