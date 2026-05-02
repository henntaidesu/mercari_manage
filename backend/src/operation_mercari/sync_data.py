# -*- coding: utf-8 -*-
"""
Mercari 数据同步调度层

提供统一的同步入口，供 API 层调用。
后续如需扩展更多同步类型（订单详情、评价等），在本文件中添加对应方法即可。
"""

from typing import Any, Dict, List, Optional, Tuple

from .get_order.get_open_order.get_history_order.get_history_list import (
    fetch_and_sync_history_orders,
)
from .get_order.get_open_order.get_order_list import (
    fetch_and_sync_open_orders,
    fetch_open_order_items,
    _item_to_order_data,
    _upsert_order,
)
from .get_order.get_open_order.get_order_info import apply_item_info_to_order
from ..db_manage.models.meilu_account import MeiluAccountModel
from ..db_manage.models.order import OrderModel


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


def sync_new_data(account_id: Optional[int] = None) -> Dict[str, Any]:
    """
    增量同步出售中订单：先查本地该卖家「最新一条」订单号（水印），再拉 Mercari 列表，
    只对尚未入库的 item 入库；入库顺序与接口列表顺序相反（倒序入库：较早的新单先写入）。
    每条成功写入后调用 get_order_info.apply_item_info_to_order（items/get）解析并回填扩展字段。

    - 仅处理当前 API 返回的这一页 trading 数据（与全量 sync_open_orders 中 open 段一致）。
    - 依赖订单表 data_user 与当前卖家 ID 一致；筛选水印时也按 data_user 限定。
    """
    aid, sid = _resolve_account_and_seller(account_id)
    seller_key = str(int(sid))

    latest_rows = OrderModel.find_all(
        where="[data_user] = ?",
        params=(seller_key,),
        order_by="COALESCE([order_updated_at], [order_date]) DESC, [id] DESC",
        limit=1,
    )
    watermark_order_no = latest_rows[0].order_no if latest_rows else None

    items, meta = fetch_open_order_items(seller_id=sid, account_id=aid)

    raw_ids: List[str] = []
    for it in items:
        oid = it.get("id")
        if oid is not None and str(oid).strip():
            raw_ids.append(str(oid).strip())
    uniq_ids = list(dict.fromkeys(raw_ids))

    db = OrderModel().db
    existing_nos: set = set()
    if uniq_ids:
        placeholders = ",".join(["?"] * len(uniq_ids))
        sql = f"SELECT [order_no] FROM [orders] WHERE [order_no] IN ({placeholders})"
        existing_nos = {r[0] for r in db.execute_query(sql, tuple(uniq_ids))}

    pending: List[Dict[str, Any]] = [
        it for it in items if str(it.get("id", "")).strip() not in existing_nos
    ]
    to_save = list(reversed(pending))

    stats: Dict[str, Any] = {
        "watermark_order_no": watermark_order_no,
        "api_item_count": len(items),
        "pending_new": len(pending),
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "info_enriched": 0,
        "info_errors": [],
        "has_next": meta.get("has_next", False),
        "total_item_count": meta.get("total_item_count", len(items)),
    }

    for item in to_save:
        iid = item.get("id")
        try:
            order_data = _item_to_order_data(item, seller_id=sid)
            result = _upsert_order(order_data)
            stats[result] += 1
        except Exception as exc:
            stats["errors"].append({"item_id": item.get("id"), "error": str(exc)})
            continue

        # 与 fetch_and_sync_open_orders 一致：入库后必须 items/get（get_order_info）回填手续费、快递费、净收益等
        if result == "skipped" or not iid:
            continue
        try:
            err = apply_item_info_to_order(str(iid), account_id=aid)
            if err is None:
                stats["info_enriched"] += 1
            else:
                stats["info_errors"].append({"item_id": iid, "error": err})
        except Exception as exc:
            stats["info_errors"].append({"item_id": iid, "error": f"info_exception:{exc}"})

    print(
        f"[sync_new_data] watermark_order_no={watermark_order_no!r} "
        f"api_items={len(items)} pending_new={len(pending)} "
        f"inserted={stats['inserted']} updated={stats['updated']} "
        f"info_ok={stats['info_enriched']}"
    )
    return stats
