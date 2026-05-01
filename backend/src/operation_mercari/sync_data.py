# -*- coding: utf-8 -*-
"""
Mercari 数据同步调度层

提供统一的同步入口，供 API 层调用。
后续如需扩展更多同步类型（订单详情、评价等），在本文件中添加对应方法即可。
"""

from typing import Any, Dict, Optional, Tuple

from .get_order.get_open_order.get_history_order.get_history_list import (
    fetch_and_sync_history_orders,
)
from .get_order.get_open_order.get_order_list import fetch_and_sync_open_orders
from ..db_manage.models.meilu_account import MeiluAccountModel


def _resolve_account_and_seller(account_id: Optional[int]) -> Tuple[int, int]:
    """
    解析煤炉账号与卖家 ID。

    :return: (account_id, seller_id)
    """
    if account_id is not None:
        account = MeiluAccountModel.find_by_id(id=account_id)
        if not account:
            raise RuntimeError(f"未找到 ID={account_id} 的煤炉账号")
    else:
        records = MeiluAccountModel.find_all(
            where="[status] = ?",
            params=("active",),
            order_by="id ASC",
            limit=1,
        )
        if not records:
            raise RuntimeError("数据库中无可用的 active 状态煤炉账号")
        account = records[0]
        account_id = account.id

    seller_id = (str(account.seller_id or "")).strip()
    if not seller_id:
        raise RuntimeError(f"账号「{account.account_name}」未配置卖家ID，请先在账号管理中补充")
    if not seller_id.isdigit():
        raise RuntimeError(f"账号「{account.account_name}」的卖家ID格式错误（必须为纯数字）")

    return account_id, int(seller_id)


def sync_open_orders(
    account_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    同步 Mercari 订单到本地订单管理表：
    1）出售中（trading）；2）已售完历史（sold_out）。
    由「获取历史数据」等入口统一触发。

    :param account_id: 指定使用的煤炉账号 ID；为 None 时自动选取第一个 active 账号。
    :return: 合并统计 + 分项 trading / history，便于前端展示。
    :raises RuntimeError: 账号不可用或网络请求失败时抛出。
    """
    aid, sid = _resolve_account_and_seller(account_id)
    trading = fetch_and_sync_open_orders(seller_id=sid, account_id=aid)
    history = fetch_and_sync_history_orders(seller_id=sid, account_id=aid)

    t_ic = trading.get("total_item_count")
    if t_ic is None:
        t_ic = trading["total"]
    h_ic = history.get("total_item_count")
    if h_ic is None:
        h_ic = history["total"]

    return {
        "trading": trading,
        "history": history,
        "inserted": trading["inserted"] + history["inserted"],
        "updated": trading["updated"] + history["updated"],
        "skipped": trading["skipped"] + history["skipped"],
        "total": trading["total"] + history["total"],
        "total_item_count": t_ic + h_ic,
        "errors": trading["errors"] + history["errors"],
        "info_enriched": trading.get("info_enriched", 0) + history.get("info_enriched", 0),
        "info_errors": trading.get("info_errors", []) + history.get("info_errors", []),
    }
