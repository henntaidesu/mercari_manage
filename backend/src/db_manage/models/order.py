# -*- coding: utf-8 -*-
"""
订单表模型
"""

from typing import Any, Dict, List, Optional, Tuple
from ..base_model import BaseModel


class OrderModel(BaseModel):
    """订单表"""

    @classmethod
    def ensure_table_exists(cls) -> bool:
        ok = super().ensure_table_exists()
        if ok and hasattr(cls, "_cached_table_columns"):
            delattr(cls, "_cached_table_columns")
        return ok

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
            # Mercari item.updated，精确到秒 YYYY-MM-DD HH:MM:SS（UTC）
            'order_updated_at': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            # 买家用户 ID（Mercari buyer.id），非昵称
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
            # 手续费（由 get_order_info 等后续填充）
            'service_fee': {
                'type': 'REAL',
                'not_null': False,
                'default': None,
            },
            # 收益（到手等，由 info 接口计算或回填）
            'net_income': {
                'type': 'REAL',
                'not_null': False,
                'default': None,
            },
            # 快递公司（items/get shipping_class.carrier_display_name）
            'carrier_display_name': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            # 寄件方式展示名（items/get shipping_class.request_class_display_name）
            'request_class_display_name': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            # 快递费（items/get shipping_class.fee）
            'shipping_fee': {
                'type': 'REAL',
                'not_null': False,
                'default': None,
            },
            # 快递单号
            'tracking_no': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            # items/get data.transaction_evidence.id
            'transaction_evidence_id': {
                'type': 'INTEGER',
                'not_null': False,
                'default': None,
            },
            'remark': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            # Mercari item.thumbnails：JSON 字符串，如 ["https://..."]
            'thumbnails': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
        }

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {'name': 'idx_orders_order_no', 'columns': ['order_no'], 'unique': True},
            {'name': 'idx_orders_order_date', 'columns': ['order_date']},
            {'name': 'idx_orders_order_updated_at', 'columns': ['order_updated_at']},
            {'name': 'idx_orders_status', 'columns': ['status']},
        ]

    @classmethod
    def _build_list_filter(
        cls,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[str, List[Any]]:
        base_sql = """
            FROM [orders] o
            WHERE 1=1
        """
        params: List[Any] = []
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
        return base_sql, params

    @classmethod
    def aggregate_sums(
        cls,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        与列表相同的筛选条件下，对全量匹配行求和（非当前页）。
        """
        db = cls().db
        base_sql, params = cls._build_list_filter(
            keyword=keyword, status=status, start_date=start_date, end_date=end_date
        )
        sql = f"""
            SELECT
                COUNT(*),
                COALESCE(SUM(o.amount), 0),
                COALESCE(SUM(o.service_fee), 0),
                COALESCE(SUM(o.shipping_fee), 0),
                COALESCE(SUM(o.net_income), 0)
            {base_sql}
        """
        row = db.execute_query(sql, tuple(params))[0]
        return {
            "total_count": int(row[0]),
            "sum_amount": float(row[1]),
            "sum_service_fee": float(row[2]),
            "sum_shipping_fee": float(row[3]),
            "sum_net_income": float(row[4]),
        }

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
        base_sql, params = cls._build_list_filter(
            keyword=keyword, status=status, start_date=start_date, end_date=end_date
        )

        total = db.execute_query(f"SELECT COUNT(*) {base_sql}", tuple(params))[0][0]
        select_sql = f"""
            SELECT o.id, o.order_no, o.order_date, o.order_updated_at, o.customer_name, o.status, o.amount,
                   o.service_fee, o.net_income, o.carrier_display_name, o.request_class_display_name,
                   o.shipping_fee, o.tracking_no, o.transaction_evidence_id, o.remark, o.thumbnails
            {base_sql}
            ORDER BY o.order_date DESC, o.id DESC
            LIMIT ? OFFSET ?
        """
        rows = db.execute_query(select_sql, tuple(params + [page_size, (page - 1) * page_size]))
        keys = [
            'id', 'order_no', 'order_date', 'order_updated_at', 'customer_name', 'status', 'amount',
            'service_fee', 'net_income', 'carrier_display_name', 'request_class_display_name',
            'shipping_fee', 'tracking_no', 'transaction_evidence_id', 'remark', 'thumbnails',
        ]
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': [dict(zip(keys, row)) for row in rows],
        }
