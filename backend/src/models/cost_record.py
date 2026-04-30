# -*- coding: utf-8 -*-
"""
成本记录表模型
"""

from typing import Dict, Any, List, Optional
from ..base_model import BaseModel


class CostRecordModel(BaseModel):
    """成本记录表"""

    @classmethod
    def get_table_name(cls) -> str:
        return "cost_records"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            'id': {
                'type': 'INTEGER',
                'primary_key': True,
                'autoincrement': True,
                'not_null': True,
            },
            'cost_date': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
            },
            'type': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
            },
            'amount': {
                'type': 'REAL',
                'not_null': True,
                'default': 0,
            },
            'quantity': {
                'type': 'INTEGER',
                'not_null': True,
                'default': 1,
            },
            'warehouse_id': {
                'type': 'INTEGER',
                'not_null': False,
                'default': None,
            },
            'remark': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            'operator': {
                'type': 'TEXT',
                'not_null': False,
                'default': "'管理员'",
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
            {'name': 'idx_cost_records_date', 'columns': ['cost_date']},
            {'name': 'idx_cost_records_type', 'columns': ['type']},
            {'name': 'idx_cost_records_warehouse', 'columns': ['warehouse_id']},
        ]

    @classmethod
    def find_detail_list(
        cls,
        cost_type: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        db = cls().db
        base_sql = """
            FROM [cost_records] c
            LEFT JOIN [warehouses] w ON w.id = c.warehouse_id
            WHERE 1=1
        """
        params = []

        if cost_type:
            base_sql += " AND c.type = ?"
            params.append(cost_type)
        if warehouse_id:
            base_sql += " AND c.warehouse_id = ?"
            params.append(warehouse_id)
        if start_date:
            base_sql += " AND c.cost_date >= ?"
            params.append(start_date)
        if end_date:
            base_sql += " AND c.cost_date <= ?"
            params.append(end_date)

        total = db.execute_query(f"SELECT COUNT(*) {base_sql}", tuple(params))[0][0]

        select_sql = f"""
            SELECT c.id, c.cost_date, c.type, c.amount, c.quantity, c.warehouse_id, w.name as warehouse_name,
                   c.remark, c.operator, c.created_at
            {base_sql}
            ORDER BY c.cost_date DESC, c.id DESC
            LIMIT ? OFFSET ?
        """
        query_params = params + [page_size, (page - 1) * page_size]
        rows = db.execute_query(select_sql, tuple(query_params))

        keys = ['id', 'cost_date', 'type', 'amount', 'quantity', 'warehouse_id', 'warehouse_name', 'remark', 'operator', 'created_at']
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': [dict(zip(keys, row)) for row in rows],
        }
