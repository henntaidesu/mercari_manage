# -*- coding: utf-8 -*-
"""
煤炉账号表模型
HTTP 请求头以 JSON 形式存放在 value 列。
"""

import json
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
            'seller_id': {
                'type': 'TEXT',
                'not_null': False,
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
            'value': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            # 自动数据获取：0 关闭，1 开启
            'is_open': {
                'type': 'INTEGER',
                'not_null': True,
                'default': 0,
            },
            # 抓取间隔：15 / 30 / 60(1h) / 3h / 6h 等（见 meilu_accounts.ALLOWED_FETCH_INTERVALS）
            'fetch_interval': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            # 上次自动拉取成功时间（UTC ISO），供后台定时任务节流
            'auto_fetch_last_at': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            # 自动同步子任务（与订单页 / 在售页 / 待办页 / 通知页按钮对应）；总开关仍为 is_open + fetch_interval
            'auto_fetch_order_list': {
                'type': 'INTEGER',
                'not_null': True,
                'default': 0,
            },
            'auto_fetch_on_sale': {
                'type': 'INTEGER',
                'not_null': True,
                'default': 0,
            },
            # 待办事项页「从煤炉同步」对应的自动开关
            'auto_fetch_todos': {
                'type': 'INTEGER',
                'not_null': True,
                'default': 0,
            },
            # 通知页「从煤炉同步」对应的自动开关
            'auto_fetch_notifications': {
                'type': 'INTEGER',
                'not_null': True,
                'default': 0,
            },
            # 不进行获取时间段（本地时间 24 小时制 "HH:MM"）；两个字段均非空时启用，
            # 当 start == end 表示无效（视为不暂停）；start > end 跨日（如 22:00 → 08:00）
            'pause_start_time': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            'pause_end_time': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
        }

    @classmethod
    def ensure_table_exists(cls) -> bool:
        ok = super().ensure_table_exists()
        if ok:
            cls._migrate_login_password_json_to_value()
            cls._migrate_auto_fetch_task_defaults()
            if hasattr(cls, '_cached_table_columns'):
                delattr(cls, '_cached_table_columns')
        return ok

    @classmethod
    def _migrate_auto_fetch_task_defaults(cls) -> None:
        """旧数据 is_open=1 且子任务全 0 时，视为「订单列表 + 在售」默认开启（与升级前行为一致）。"""
        db = cls().db
        table = cls.get_table_name()
        if not db.table_exists(table):
            return
        names = {c['name'] for c in db.get_table_columns(table)}
        for col in ('auto_fetch_order_list', 'auto_fetch_on_sale'):
            if col not in names:
                return
        try:
            db.execute_update(
                f"""
                UPDATE [{table}]
                SET [auto_fetch_order_list] = 1,
                    [auto_fetch_on_sale] = 1
                WHERE [is_open] = 1
                  AND IFNULL([auto_fetch_order_list], 0) = 0
                  AND IFNULL([auto_fetch_on_sale], 0) = 0
                  AND IFNULL([auto_fetch_todos], 0) = 0
                  AND IFNULL([auto_fetch_notifications], 0) = 0
                """,
                (),
            )
        except Exception as e:
            print(f"[meilu_accounts] auto_fetch 子任务默认迁移跳过: {e}")

    @classmethod
    def _migrate_login_password_json_to_value(cls) -> None:
        """旧版把请求头 JSON 存在 login_password；value 列为空时尝试迁移。"""
        db = cls().db
        table = cls.get_table_name()
        if not db.table_exists(table):
            return
        names = {c['name'] for c in db.get_table_columns(table)}
        if 'value' not in names or 'login_password' not in names:
            return
        try:
            db.execute_update(
                f"""
                UPDATE [{table}]
                SET [value] = [login_password]
                WHERE ([value] IS NULL OR TRIM([value]) = '')
                  AND [login_password] IS NOT NULL AND TRIM([login_password]) != ''
                  AND TRIM([login_password]) LIKE '{{%'
                """,
                (),
            )
        except Exception as e:
            print(f"[meilu_accounts] login_password -> value 迁移跳过: {e}")

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {'name': 'idx_meilu_accounts_name', 'columns': ['account_name']},
            {'name': 'idx_meilu_accounts_login', 'columns': ['login_id']},
            {'name': 'idx_meilu_accounts_seller_id', 'columns': ['seller_id']},
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
            SELECT m.id, m.account_name, m.login_id, m.seller_id, m.login_password, m.status, m.remark, m.[value], m.is_open, m.fetch_interval, m.auto_fetch_last_at, m.auto_fetch_order_list, m.auto_fetch_on_sale, m.auto_fetch_todos, m.auto_fetch_notifications, m.pause_start_time, m.pause_end_time
            {base_sql}
            ORDER BY m.id DESC
            LIMIT ? OFFSET ?
        """
        keys = ['id', 'account_name', 'login_id', 'seller_id', 'login_password', 'status', 'remark', 'value', 'is_open', 'fetch_interval', 'auto_fetch_last_at', 'auto_fetch_order_list', 'auto_fetch_on_sale', 'auto_fetch_todos', 'auto_fetch_notifications', 'pause_start_time', 'pause_end_time']
        rows = db.execute_query(select_sql, tuple(params + [page_size, (page - 1) * page_size]))
        items = []
        for row in rows:
            d = dict(zip(keys, row))
            d.pop('login_password', None)
            raw = d.pop('value', None)
            d['value'] = cls._parse_value_json(raw)
            d['is_open'] = 1 if d.get('is_open') else 0
            d['auto_fetch_order_list'] = 1 if d.get('auto_fetch_order_list') else 0
            d['auto_fetch_on_sale'] = 1 if d.get('auto_fetch_on_sale') else 0
            d['auto_fetch_todos'] = 1 if d.get('auto_fetch_todos') else 0
            d['auto_fetch_notifications'] = 1 if d.get('auto_fetch_notifications') else 0
            d['pause_start_time'] = d.get('pause_start_time') or None
            d['pause_end_time'] = d.get('pause_end_time') or None
            items.append(d)
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items,
        }

    @staticmethod
    def _parse_value_json(raw: Optional[str]) -> Dict[str, str]:
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return {}
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {}
            return {k: ('' if v is None else str(v)) for k, v in data.items()}
        except Exception:
            return {}
