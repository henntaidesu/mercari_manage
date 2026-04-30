# -*- coding: utf-8 -*-
"""
煤炉账号表模型
"""

from typing import Dict, Any, List, Optional
from ..base_model import BaseModel


class MeiluAccountModel(BaseModel):
    """煤炉账号"""

    @classmethod
    def get_table_name(cls) -> str:
        return "meilu_accounts"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            'id': {
                'type': 'INTEGER',
                'primary_key': True,
                'autoincrement': True,
                'not_null': True,
            },
            'account_name': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
            },
            'login_id': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
            },
            'login_password': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            'status': {
                'type': 'TEXT',
                'not_null': True,
                'default': "'active'",
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
            {'name': 'idx_meilu_accounts_name', 'columns': ['account_name']},
            {'name': 'idx_meilu_accounts_login', 'columns': ['login_id']},
            {'name': 'idx_meilu_accounts_status', 'columns': ['status']},
        ]

    @classmethod
    def find_detail_list(
        cls,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        db = cls().db
        base_sql = "FROM [meilu_accounts] m WHERE 1=1"
        params = []
        if keyword:
            base_sql += " AND (m.account_name LIKE ? OR m.login_id LIKE ?)"
            kw = f"%{keyword}%"
            params += [kw, kw]
        if status:
            base_sql += " AND m.status = ?"
            params.append(status)

        total = db.execute_query(f"SELECT COUNT(*) {base_sql}", tuple(params))[0][0]
        select_sql = f"""
            SELECT m.id, m.account_name, m.login_id, m.login_password, m.status, m.remark, m.created_at
            {base_sql}
            ORDER BY m.id DESC
            LIMIT ? OFFSET ?
        """
        rows = db.execute_query(select_sql, tuple(params + [page_size, (page - 1) * page_size]))
        keys = ['id', 'account_name', 'login_id', 'login_password', 'status', 'remark', 'created_at']
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': [dict(zip(keys, row)) for row in rows],
        }
