# -*- coding: utf-8 -*-
"""
出入库记录表模型
"""

from typing import Dict, Any, List, Optional
from ..base_model import BaseModel


class TransactionModel(BaseModel):
    """出入库记录表（type: in=入库 / out=出库 / transfer=调拨）"""

    @classmethod
    def get_table_name(cls) -> str:
        return "transactions"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            'id': {
                'type': 'INTEGER',
                'primary_key': True,
                'autoincrement': True,
                'not_null': True,
            },
            'type': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
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
            'target_warehouse_id': {
                'type': 'INTEGER',
                'not_null': False,
                'default': None,
            },
            'quantity': {
                'type': 'INTEGER',
                'not_null': True,
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
            {'name': 'idx_transactions_product', 'columns': ['product_id']},
            {'name': 'idx_transactions_warehouse', 'columns': ['warehouse_id']},
            {'name': 'idx_transactions_created', 'columns': ['created_at']},
        ]

    @classmethod
    def find_detail_list(
        cls,
        tx_type: Optional[str] = None,
        product_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """查询出入库记录列表（含分页），附带商品和仓库名称"""
        db = cls().db
        base_sql = """
            FROM [transactions] t
            JOIN [inventory] p ON p.id = t.product_id
            JOIN [warehouses] w ON w.id = t.warehouse_id
            LEFT JOIN [warehouses] tw ON tw.id = t.target_warehouse_id
            WHERE 1=1
        """
        params = []
        if tx_type:
            base_sql += " AND t.type = ?"
            params.append(tx_type)
        if product_id:
            base_sql += " AND t.product_id = ?"
            params.append(product_id)
        if warehouse_id:
            base_sql += " AND (t.warehouse_id = ? OR t.target_warehouse_id = ?)"
            params += [warehouse_id, warehouse_id]

        total = db.execute_query(f"SELECT COUNT(*) {base_sql}", tuple(params))[0][0]

        select_sql = f"""
            SELECT t.id, t.type, t.product_id, p.name as product_name, p.unit,
                   t.warehouse_id, w.name as warehouse_name,
                   t.target_warehouse_id, tw.name as target_warehouse_name,
                   t.quantity, t.remark, t.operator, t.created_at
            {base_sql}
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
        """
        params += [page_size, (page - 1) * page_size]
        rows = db.execute_query(select_sql, tuple(params))

        keys = ['id', 'type', 'product_id', 'product_name', 'unit',
                'warehouse_id', 'warehouse_name',
                'target_warehouse_id', 'target_warehouse_name',
                'quantity', 'remark', 'operator', 'created_at']
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': [dict(zip(keys, row)) for row in rows],
        }
