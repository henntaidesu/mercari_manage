# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..models.transaction import TransactionModel
from ..models.inventory import InventoryModel

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


class TransactionCreate(PydanticModel):
    type: str
    product_id: int
    warehouse_id: int
    target_warehouse_id: Optional[int] = None
    quantity: int
    remark: Optional[str] = None
    operator: Optional[str] = "管理员"


@router.get("")
def list_transactions(
    type: Optional[str] = None,
    product_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
):
    return TransactionModel.find_detail_list(
        tx_type=type,
        product_id=product_id,
        warehouse_id=warehouse_id,
        page=page,
        page_size=page_size,
    )


@router.post("")
def create_transaction(data: TransactionCreate):
    if data.type not in ("in", "out", "transfer"):
        raise HTTPException(status_code=400, detail="类型错误，仅支持 in/out/transfer")
    if data.quantity <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于0")
    if data.type == "transfer" and not data.target_warehouse_id:
        raise HTTPException(status_code=400, detail="调拨操作需要指定目标仓库")

    if data.type == "in":
        InventoryModel.upsert(data.product_id, data.warehouse_id, data.quantity)

    elif data.type == "out":
        ok, current = InventoryModel.deduct(data.product_id, data.warehouse_id, data.quantity)
        if not ok:
            raise HTTPException(status_code=400, detail=f"库存不足，当前库存：{current}")

    elif data.type == "transfer":
        ok, current = InventoryModel.deduct(data.product_id, data.warehouse_id, data.quantity)
        if not ok:
            raise HTTPException(status_code=400, detail=f"库存不足，当前库存：{current}")
        InventoryModel.upsert(data.product_id, data.target_warehouse_id, data.quantity)

    tx = TransactionModel(
        type=data.type,
        product_id=data.product_id,
        warehouse_id=data.warehouse_id,
        target_warehouse_id=data.target_warehouse_id,
        quantity=data.quantity,
        remark=data.remark,
        operator=data.operator,
    )
    if not tx.save():
        raise HTTPException(status_code=500, detail="记录保存失败")

    # 返回带关联名称的详情
    result = TransactionModel.find_detail_list(page=1, page_size=1)
    items = result.get('items', [])
    return items[0] if items else tx.to_dict()
