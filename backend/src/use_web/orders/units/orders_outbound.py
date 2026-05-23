# -*- coding: utf-8 -*-
"""出库明细相关端点与订单刷新/包装免列入端点。"""
import time
from typing import List

from fastapi import HTTPException

from ....db_manage.models.order import OrderModel
from ....db_manage.models.order_outbound_line import OrderOutboundLineModel
from ....operation_mercari.get_order.description_mgmt_ids import (
    refresh_inventory_pending_outbound_qty,
)
from ....operation_mercari.get_order.get_in_progress_order.get_order_info import apply_item_info_to_order
from ....operation_mercari.sync_data import resolve_account_id_by_seller_id
from ....web_drive.core.account_serial_queue import queue_key_for_meilu_account, run_meilu_serial_async
from .orders_helpers import _outbound_line_has_inventory_id, db
from .orders_models import (
    ManualOutboundLineCreateBody,
    ManualOutboundLineItem,
    ManualOutboundLinesBatchCreateBody,
    OrderPackagingWaiveBody,
    OutboundLineBindInventoryBody,
    OutboundStockOutBody,
    RefreshOrderInfoBody,
)


def bind_outbound_line_inventory(line_id: int, data: OutboundLineBindInventoryBody):
    """未识别到库存 ID 的明细行，手动指定 inventory_id；已有关联时拒绝。"""
    line = OrderOutboundLineModel.find_by_id(id=int(line_id))
    if not line:
        raise HTTPException(status_code=404, detail="出库明细不存在")
    if _outbound_line_has_inventory_id(line):
        raise HTTPException(status_code=400, detail="该明细已关联库存，无法修改")
    if int(line.is_stocked_out or 0) == 1:
        raise HTTPException(status_code=400, detail="该明细已出库，无法修改绑定")
    inv_id = int(data.inventory_id)
    if inv_id <= 0:
        raise HTTPException(status_code=400, detail="inventory_id 无效")
    inv_rows = db.execute_query("SELECT [id] FROM [inventory] WHERE [id] = ? LIMIT 1", (inv_id,))
    if not inv_rows:
        raise HTTPException(status_code=404, detail="库存商品不存在")
    line.inventory_id = inv_id
    if data.quantity is not None:
        line.quantity = max(1, int(data.quantity))
    if not line.save():
        raise HTTPException(status_code=500, detail="保存失败")
    refresh_inventory_pending_outbound_qty([inv_id])
    return {"success": True, "line_id": int(line.id), "inventory_id": inv_id}


def stock_out_order_outbound_line(line_id: int, data: OutboundStockOutBody):
    line = OrderOutboundLineModel.find_by_id(id=int(line_id))
    if not line:
        raise HTTPException(status_code=404, detail="出库明细不存在")
    if int(line.is_stocked_out or 0) == 1:
        raise HTTPException(status_code=400, detail="该明细已出库，不能重复出库")
    if line.inventory_id is None:
        raise HTTPException(status_code=400, detail="该明细未匹配库存，无法出库")
    inv_id = int(line.inventory_id)
    qty = max(1, int(line.quantity or 1))

    inv_rows = db.execute_query(
        "SELECT [quantity], [warehouse_id] FROM [inventory] WHERE [id] = ? LIMIT 1",
        (inv_id,),
    )
    if not inv_rows:
        raise HTTPException(status_code=404, detail="库存商品不存在")
    current_qty = int(inv_rows[0][0] or 0)
    warehouse_id = inv_rows[0][1]
    if int(line.stock_deducted or 0) == 0:
        if current_qty < qty:
            raise HTTPException(status_code=400, detail=f"库存不足，当前库存：{current_qty}")
        updated = db.execute_update(
            """
            UPDATE [inventory]
            SET [quantity] = COALESCE([quantity], 0) - ?,
                [pending_outbound_qty] = CASE
                    WHEN COALESCE([pending_outbound_qty], 0) >= ? THEN COALESCE([pending_outbound_qty], 0) - ?
                    ELSE 0
                END
            WHERE [id] = ?
            """,
            (qty, qty, qty, inv_id),
        )
        if updated <= 0:
            raise HTTPException(status_code=500, detail="库存更新失败")
        if warehouse_id is not None:
            db.execute_insert(
                """
                INSERT INTO [transactions] (
                    type, inventory_id, warehouse_id, quantity, remark, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "out",
                    inv_id,
                    warehouse_id,
                    qty,
                    (data.remark or "").strip() or f"订单手动出库 {line.order_no} / line#{line.id}",
                    int(time.time()),
                ),
            )

    line.is_stocked_out = 1
    line.stocked_out_at = int(time.time())
    if not line.save():
        raise HTTPException(status_code=500, detail="写入出库状态失败")
    refresh_inventory_pending_outbound_qty([inv_id])

    new_qty_rows = db.execute_query("SELECT [quantity] FROM [inventory] WHERE [id] = ? LIMIT 1", (inv_id,))
    new_qty = int(new_qty_rows[0][0] or 0) if new_qty_rows else 0
    return {
        "success": True,
        "line_id": int(line.id),
        "order_no": str(line.order_no or ""),
        "inventory_id": inv_id,
        "stocked_out_quantity": qty,
        "new_inventory_quantity": new_qty,
    }


def create_manual_outbound_line(data: ManualOutboundLineCreateBody):
    batch = ManualOutboundLinesBatchCreateBody(
        order_no=data.order_no,
        lines=[
            ManualOutboundLineItem(
                inventory_id=data.inventory_id,
                quantity=data.quantity,
                management_id=data.management_id,
            )
        ],
        remark=data.remark,
    )
    return create_manual_outbound_lines(batch)


def create_manual_outbound_lines(data: ManualOutboundLinesBatchCreateBody):
    ono = (data.order_no or "").strip()
    if not ono:
        raise HTTPException(status_code=400, detail="order_no 不能为空")
    rows = OrderModel.find_all(where="[order_no] = ?", params=(ono,), limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="订单不存在")
    lines = data.lines or []
    if not lines:
        raise HTTPException(status_code=400, detail="lines 不能为空")

    seen = set()
    normalized = []
    for it in lines:
        inv_id = int(it.inventory_id or 0)
        qty = int(it.quantity or 0)
        if inv_id <= 0:
            raise HTTPException(status_code=400, detail="存在无效 inventory_id")
        if qty <= 0:
            raise HTTPException(status_code=400, detail="数量必须大于0")
        if inv_id in seen:
            raise HTTPException(status_code=400, detail="同一库存商品请勿重复选择")
        seen.add(inv_id)
        normalized.append((inv_id, qty, (it.management_id or "").strip()))

    max_sort_rows = db.execute_query(
        "SELECT COALESCE(MAX([sort_index]), -1) FROM [order_outbound_lines] WHERE [order_no] = ?",
        (ono,),
    )
    next_sort = int(max_sort_rows[0][0] or -1) + 1

    created_ids: List[int] = []
    touched_inv_ids: List[int] = []
    created_items = []
    try:
        for idx, (inv_id, qty, mgmt) in enumerate(normalized):
            inv_rows = db.execute_query(
                "SELECT [quantity], [warehouse_id], [name] FROM [inventory] WHERE [id] = ? LIMIT 1",
                (inv_id,),
            )
            if not inv_rows:
                raise HTTPException(status_code=404, detail=f"库存商品不存在: {inv_id}")
            current_qty = int(inv_rows[0][0] or 0)
            warehouse_id = inv_rows[0][1]
            inv_name = str(inv_rows[0][2] or "").strip() or f"库存#{inv_id}"
            if current_qty < qty:
                raise HTTPException(status_code=400, detail=f"库存不足（inventory_id={inv_id}），当前库存：{current_qty}")

            token = mgmt or f"手动出库:{inv_name}"
            line = OrderOutboundLineModel(
                order_no=ono,
                inventory_id=inv_id,
                management_id=token,
                line_kind="manual",
                quantity=qty,
                sort_index=next_sort + idx,
                is_stocked_out=0,
                stocked_out_at=None,
                stock_deducted=1,
            )
            if not line.save():
                raise HTTPException(status_code=500, detail="保存手动出库明细失败")

            updated = db.execute_update(
                "UPDATE [inventory] SET [quantity] = COALESCE([quantity], 0) - ? WHERE [id] = ?",
                (qty, inv_id),
            )
            if updated <= 0:
                raise HTTPException(status_code=500, detail=f"库存更新失败（inventory_id={inv_id}）")

            if warehouse_id is not None:
                db.execute_insert(
                    """
                    INSERT INTO [transactions] (
                        type, inventory_id, warehouse_id, quantity, remark, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "out",
                        inv_id,
                        warehouse_id,
                        qty,
                        (data.remark or "").strip() or f"订单待出库预扣减 {ono} / line#{line.id}",
                        int(time.time()),
                    ),
                )
            created_ids.append(int(line.id))
            touched_inv_ids.append(inv_id)
            created_items.append({"line_id": int(line.id), "inventory_id": inv_id, "quantity": qty})
    except Exception:
        for lid in created_ids:
            try:
                obj = OrderOutboundLineModel.find_by_id(id=lid)
                if obj:
                    obj.delete()
            except Exception:
                pass
        raise

    refresh_inventory_pending_outbound_qty(touched_inv_ids)
    return {"success": True, "order_no": ono, "items": created_items}


def waive_order_packaging(data: OrderPackagingWaiveBody):
    """待评价/已完成：确认本单不使用包材后不再标红。"""
    order_no = (data.order_no or "").strip()
    if not order_no:
        raise HTTPException(status_code=400, detail="订单号不能为空")
    rows = OrderModel.find_all(where="[order_no] = ?", params=(order_no,), limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="订单不存在")
    item = rows[0]
    item.packaging_waived = 1
    if not item.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return item.to_dict()


async def refresh_order_info(data: RefreshOrderInfoBody):
    """WebDriver 打开 jp.mercari.com/transaction/m{订单号}，MITM 截获 transaction_evidences/get 后更新状态、金额等字段。"""
    order_no = (data.order_no or "").strip()
    if not order_no:
        raise HTTPException(status_code=400, detail="订单号不能为空")
    du = (data.data_user or "").strip()
    if not du:
        raise HTTPException(status_code=400, detail="卖家ID（data_user）不能为空")

    aid = resolve_account_id_by_seller_id(du)
    if aid is None:
        raise HTTPException(
            status_code=400,
            detail="未找到与该卖家ID绑定的 active 煤炉账号，请在账号管理中配置 seller_id",
        )

    async def _do_refresh() -> dict:
        err = await apply_item_info_to_order(order_no, account_id=aid, expected_seller_id=du)
        if err == "order_not_found":
            raise HTTPException(status_code=404, detail="本地不存在该订单号")
        if err == "seller_mismatch":
            raise HTTPException(
                status_code=400,
                detail="接口返回的商品不属于该卖家，请检查订单号与卖家ID是否匹配",
            )
        if err and err.startswith("api:"):
            raise HTTPException(status_code=502, detail=err[4:])
        if err and err.startswith("request:"):
            raise HTTPException(status_code=502, detail=err[8:])
        if err == "save_failed":
            raise HTTPException(status_code=500, detail="写入数据库失败")
        if err:
            raise HTTPException(status_code=400, detail=err)

        rows = OrderModel.find_all(where="[order_no] = ?", params=(order_no,), limit=1)
        if not rows:
            raise HTTPException(status_code=404, detail="订单不存在")
        return rows[0].to_dict()

    try:
        return await run_meilu_serial_async(queue_key_for_meilu_account(int(aid)), _do_refresh)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
