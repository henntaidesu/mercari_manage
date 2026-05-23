# -*- coding: utf-8 -*-
"""订单查询端点：列表 / 统计 / 出库明细列表。"""
from typing import Optional

from fastapi import HTTPException

from ....db_manage.models.order import OrderModel
from ....db_manage.models.order_outbound_line import OrderOutboundLineModel
from ....order_goods_ratio import apply_bundle_title_ratio_pricing
from .orders_helpers import _validate_status_query, db


def order_stats(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    owner_user_id: Optional[int] = None,
    today_start_ts: Optional[int] = None,
    today_end_ts: Optional[int] = None,
):
    """当前筛选条件下的全表汇总（金额、手续费、快递费、净收益及行数），不受分页影响。

    已取消（cancelled）订单不计入本接口汇总；列表仍可按状态筛选查看。
    筛选时间区间：start_ts / end_ts 为 Unix 秒（与列表一致），按
    COALESCE(order_updated_at, purchase_time, order_date)（最后更新优先，缺省回退购入/下单）比较；
    建议由前端按本地自然日 0 点～当日结束换算。
    可选 today_start_ts / today_end_ts（同为 Unix 秒，本地「今天」起止）：在相同 keyword、status 下汇总「今日」
    （同上时间口径），不受 start_ts/end_ts 影响。

    sum_packaging / today_sum_packaging：关联订单的「包装材料」支出合计（日元），筛选条件与上述一致。
    """
    _validate_status_query(status)
    out = OrderModel.aggregate_sums(
        keyword=keyword,
        status=status,
        start_ts=start_ts,
        end_ts=end_ts,
        owner_user_id=owner_user_id,
    )
    out["sum_packaging"] = OrderModel.aggregate_packaging_expense_yen(
        keyword=keyword,
        status=status,
        start_ts=start_ts,
        end_ts=end_ts,
        owner_user_id=owner_user_id,
    )
    if today_start_ts is not None and today_end_ts is not None:
        t = OrderModel.aggregate_sums(
            keyword=keyword,
            status=status,
            start_ts=int(today_start_ts),
            end_ts=int(today_end_ts),
            owner_user_id=owner_user_id,
        )
        out["today_total_count"] = t["total_count"]
        out["today_sum_amount"] = t["sum_amount"]
        out["today_sum_service_fee"] = t["sum_service_fee"]
        out["today_sum_shipping_fee"] = t["sum_shipping_fee"]
        out["today_sum_net_income"] = t["sum_net_income"]
        out["today_sum_packaging"] = OrderModel.aggregate_packaging_expense_yen(
            keyword=keyword,
            status=status,
            start_ts=int(today_start_ts),
            end_ts=int(today_end_ts),
            owner_user_id=owner_user_id,
        )
    return out


def list_order_outbound_lines(
    order_no: str,
    owner_user_id: Optional[int] = None,
):
    """某订单从商品说明解析出的待出库明细（管理 ID、库存名称、仓库位置等）；比例价格优先组合标题在售价，否则按库存原价×件数（含手动添加）。"""
    ono = (order_no or "").strip()
    if not ono:
        raise HTTPException(status_code=400, detail="order_no 不能为空")
    # 先取全量明细再算 bundle 比例（与订单金额一致）；按归属筛选时不得只拿子集算权重
    all_items = OrderOutboundLineModel.list_enriched_for_order(ono)
    order_rows = db.execute_query(
        "SELECT COALESCE([amount], 0) FROM [orders] WHERE [order_no] = ? LIMIT 1",
        (ono,),
    )
    order_amount = int(order_rows[0][0] or 0) if order_rows else 0
    apply_bundle_title_ratio_pricing(all_items, order_amount)

    if owner_user_id is not None and int(owner_user_id) > 0:
        oid = int(owner_user_id)
        items = [
            it
            for it in all_items
            if it.get("inventory_id") is not None
            and int(
                it.get("product_owner_user_id")
                or it.get("inventory_owner_user_id")
                or 0
            )
            == oid
        ]
    else:
        items = all_items

    OrderOutboundLineModel.sort_owner_unmatched_first(items)
    return {"order_no": ono, "items": items}


def list_orders(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    owner_user_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
):
    _validate_status_query(status)
    return OrderModel.find_detail_list(
        keyword=keyword,
        status=status,
        start_ts=start_ts,
        end_ts=end_ts,
        owner_user_id=owner_user_id,
        page=page,
        page_size=page_size,
    )
