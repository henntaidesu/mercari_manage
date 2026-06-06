# -*- coding: utf-8 -*-
"""订单列表/详情查询：批量信息刷新候选 / 详情列表"""

from typing import Any, Dict, List, Optional, Tuple
from ..order_outbound_line import OUTBOUND_ALERT_SKIP_STATUSES, PACKAGING_CHECK_STATUSES, TERMINAL_ORDER_STATUSES


class _QueryMixin:

    # 批量信息刷新时跳过的「已结束」状态集合
    _STATUSES_SKIP_BATCH_INFO: Tuple[str, ...] = (
        "done",
        "cancelled",
        "sold_out",
    )

    @classmethod
    def find_for_batch_info_refresh(
        cls,
        seller_id_filter: Optional[str] = None,
    ) -> List[Tuple[str, str]]:
        """
        从库中取得待用 transaction_evidences/get 刷新的 (order_no, data_user)。
        仅含 data_user 非空且状态非「已完成」集合中的行；可选只限某一卖家（与煤炉账号 seller_id 一致）。
        """
        skip = cls._STATUSES_SKIP_BATCH_INFO
        placeholders = ",".join("?" * len(skip))
        sql = (
            f"SELECT order_no, data_user FROM [{cls.get_table_name()}] "
            f"WHERE IFNULL(TRIM(data_user), '') != '' "
            f"AND status NOT IN ({placeholders}) "
        )
        params: List[Any] = list(skip)
        if seller_id_filter is not None and str(seller_id_filter).strip():
            sql += "AND TRIM(data_user) = TRIM(?) "
            params.append(str(seller_id_filter).strip())
        sql += (
            "ORDER BY COALESCE(purchase_time, order_updated_at, order_date) DESC, "
            "id DESC"
        )
        db = cls().db
        rows = db.execute_query(sql, tuple(params))
        out: List[Tuple[str, str]] = []
        for r in rows:
            if not r or len(r) < 2:
                continue
            ono, du = r[0], r[1]
            if ono is None or str(ono).strip() == "":
                continue
            out.append((str(ono).strip(), str(du).strip()))
        return out


    @classmethod
    def find_detail_list(
        cls,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        owner_user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        db = cls().db
        base_sql, params = cls._build_list_filter(
            keyword=keyword,
            status=status,
            start_ts=start_ts,
            end_ts=end_ts,
            owner_user_id=owner_user_id,
        )

        total = db.execute_query(f"SELECT COUNT(*) {base_sql}", tuple(params))[0][0]
        term_ph = ",".join("?" * len(TERMINAL_ORDER_STATUSES))
        pending_sql = f"""
            COALESCE((
                SELECT SUM(COALESCE(l.[quantity], 1))
                FROM [order_outbound_lines] l
                WHERE l.[order_no] = o.[order_no]
                  AND COALESCE(l.[is_stocked_out], 0) = 0
            ), 0)
        """
        pending_case_sql = f"""
            CASE
                WHEN o.[status] IN ({term_ph}) THEN 0
                ELSE ({pending_sql})
            END
        """
        owner_unmatched_sql = """
            CASE WHEN EXISTS (
                SELECT 1 FROM [order_outbound_lines] l
                LEFT JOIN [inventory] p ON p.id = l.inventory_id
                WHERE l.[order_no] = o.[order_no]
                  AND (
                    l.[inventory_id] IS NULL
                    OR IFNULL(p.[owner_user_id], 0) = 0
                  )
            ) THEN 1 ELSE 0 END
        """
        skip_ph = ",".join("?" * len(OUTBOUND_ALERT_SKIP_STATUSES))
        no_bound_outbound_sql = f"""
            CASE
                WHEN o.[status] IN ({skip_ph}) THEN 0
                WHEN NOT EXISTS (
                    SELECT 1 FROM [order_outbound_lines] l
                    WHERE l.[order_no] = o.[order_no]
                      AND l.[inventory_id] IS NOT NULL
                      AND IFNULL(l.[inventory_id], 0) > 0
                ) THEN 1
                ELSE 0
            END
        """
        pkg_ph = ",".join("?" * len(PACKAGING_CHECK_STATUSES))
        packaging_pending_sql = f"""
            CASE
                WHEN o.[status] NOT IN ({pkg_ph}) THEN 0
                WHEN COALESCE(o.[packaging_waived], 0) != 0 THEN 0
                WHEN NOT EXISTS (
                    SELECT 1 FROM [cost_expenses] e
                    WHERE e.[order_no] = o.[order_no]
                      AND TRIM(COALESCE(e.[type], '')) = '包装材料'
                ) THEN 1
                ELSE 0
            END
        """
        wait_review_pending_alert_sql = f"""
            CASE
                WHEN o.[status] = 'wait_review' AND ({pending_sql}) > 0 THEN 1
                ELSE 0
            END
        """
        order_needs_alert_sql = f"""
            CASE WHEN ({owner_unmatched_sql}) = 1
                      OR ({no_bound_outbound_sql}) = 1
                      OR ({packaging_pending_sql}) = 1
                      OR ({wait_review_pending_alert_sql}) = 1
                 THEN 1 ELSE 0 END
        """
        select_sql = f"""
            SELECT o.id, o.order_no, o.order_date, o.order_updated_at, o.purchase_time, o.customer_name, o.data_user,
                   o.status, o.amount,
                   o.service_fee, o.net_income, o.carrier_display_name, o.request_class_display_name,
                   o.shipping_fee, o.tracking_no, o.ship_confirm_code, o.transaction_evidence_id, o.remark, o.description,
                   o.inventory_synced, o.inventory_synced_quantity, o.thumbnails,
                   COALESCE(o.[packaging_waived], 0) AS packaging_waived,
                   {pending_case_sql} AS pending_outbound_qty,
                   {owner_unmatched_sql} AS has_owner_unmatched_outbound,
                   {no_bound_outbound_sql} AS has_no_bound_outbound,
                   {packaging_pending_sql} AS has_packaging_pending,
                   {order_needs_alert_sql} AS order_needs_alert
            {base_sql}
            ORDER BY order_needs_alert DESC,
                     COALESCE(o.purchase_time, o.order_updated_at, o.order_date) DESC, o.id DESC
            LIMIT ? OFFSET ?
        """
        term_bind = tuple(TERMINAL_ORDER_STATUSES)
        skip_bind = tuple(OUTBOUND_ALERT_SKIP_STATUSES)
        pkg_bind = tuple(PACKAGING_CHECK_STATUSES)
        # order_needs_alert 内再次引用 no_bound / packaging 子句，占位符须重复绑定
        bind = (
            term_bind
            + skip_bind
            + pkg_bind
            + skip_bind
            + pkg_bind
            + tuple(params)
            + (page_size, (page - 1) * page_size)
        )
        rows = db.execute_query(select_sql, bind)
        keys = [
            'id', 'order_no', 'order_date', 'order_updated_at', 'purchase_time', 'customer_name', 'data_user', 'status',
            'amount',
            'service_fee', 'net_income', 'carrier_display_name', 'request_class_display_name',
            'shipping_fee', 'tracking_no', 'ship_confirm_code', 'transaction_evidence_id', 'remark', 'description',
            'inventory_synced', 'inventory_synced_quantity', 'thumbnails', 'packaging_waived',
            'pending_outbound_qty', 'has_owner_unmatched_outbound', 'has_no_bound_outbound',
            'has_packaging_pending', 'order_needs_alert',
        ]
        items = [dict(zip(keys, row)) for row in rows]
        if owner_user_id is not None and int(owner_user_id) > 0:
            from ....use_web.orders.units.order_goods_ratio import split_order_money_for_owner_user

            oid = int(owner_user_id)
            for row in items:
                row["_owner_split_money_db"] = {
                    "amount": row.get("amount"),
                    "service_fee": row.get("service_fee"),
                    "shipping_fee": row.get("shipping_fee"),
                    "net_income": row.get("net_income"),
                }
                parts = split_order_money_for_owner_user(
                    str(row.get("order_no") or "").strip(),
                    oid,
                    row.get("amount"),
                    row.get("service_fee"),
                    row.get("shipping_fee"),
                    row.get("net_income"),
                )
                row["amount"] = parts["amount"]
                row["service_fee"] = parts["service_fee"]
                row["shipping_fee"] = parts["shipping_fee"]
                row["net_income"] = parts["net_income"]
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items,
        }
