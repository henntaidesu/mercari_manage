# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..models.product import ProductModel
from ..models.category import CategoryModel
from ..models.warehouse import WarehouseModel
from ..models.transaction import TransactionModel

router = APIRouter(prefix="/api/products", tags=["products"])


class StockInRequest(PydanticModel):
    warehouse_id: Optional[int] = None   # 不传则只更新库存，不写事务记录
    quantity: int = 1
    remark: Optional[str] = None


class ProductCreate(PydanticModel):
    name: Optional[str] = None
    barcode: str
    category_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    unit: Optional[str] = "件"
    price: Optional[float] = 0.0
    quantity: Optional[int] = 1
    description: Optional[str] = None
    image_front: Optional[str] = None
    image_back: Optional[str] = None


class ProductUpdate(PydanticModel):
    name: Optional[str] = None
    barcode: Optional[str] = None
    category_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    description: Optional[str] = None
    image_front: Optional[str] = None
    image_back: Optional[str] = None


def _get_detail(product: ProductModel) -> dict:
    d = product.to_dict()
    cat = CategoryModel.find_by_id(id=product.category_id) if product.category_id else None
    wh = WarehouseModel.find_by_id(id=product.warehouse_id) if product.warehouse_id else None
    d['category_name'] = cat.name if cat else None
    d['warehouse_name'] = wh.name if wh else None
    return d


@router.get("")
def list_products(keyword: Optional[str] = None, category_id: Optional[int] = None):
    return ProductModel.find_with_stock(keyword=keyword, category_id=category_id)


@router.get("/barcode/{barcode}")
def find_by_barcode(barcode: str):
    """根据条形码精确查找商品（用于连续扫码流程）"""
    products = ProductModel.find_all("barcode = ?", (barcode.strip(),), limit=1)
    if not products:
        return {"found": False, "product": None}
    return {"found": True, "product": _get_detail(products[0])}


@router.post("/{pid}/stock-in")
def stock_in_product(pid: int, data: StockInRequest):
    """连续扫码入库：库存 +N；若提供 warehouse_id 则同时写入事务记录"""
    product = ProductModel.find_by_id(id=pid)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    product.quantity = (product.quantity or 0) + data.quantity
    if not product.save():
        raise HTTPException(status_code=500, detail="库存更新失败")
    if data.warehouse_id:
        tx = TransactionModel(
            type="in",
            product_id=pid,
            warehouse_id=data.warehouse_id,
            quantity=data.quantity,
            remark=data.remark or "扫码快速入库",
        )
        tx.save()
    return {"success": True, "new_quantity": product.quantity, "product_id": pid}


@router.get("/{pid}")
def get_product(pid: int):
    product = ProductModel.find_by_id(id=pid)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return _get_detail(product)


@router.post("")
def create_product(data: ProductCreate):
    if not (data.barcode or "").strip():
        raise HTTPException(status_code=400, detail="条形码必填")
    if data.warehouse_id and not WarehouseModel.find_by_id(id=data.warehouse_id):
        raise HTTPException(status_code=400, detail="所属仓库不存在")
    payload = data.model_dump()
    payload['image'] = payload.get('image_front')
    product = ProductModel(**payload)
    if not product.save():
        raise HTTPException(status_code=400, detail="保存失败，条形码可能重复")
    return _get_detail(product)


@router.put("/{pid}")
def update_product(pid: int, data: ProductUpdate):
    product = ProductModel.find_by_id(id=pid)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    update_data = data.model_dump(exclude_none=True)
    if 'barcode' in update_data and not (update_data.get('barcode') or '').strip():
        raise HTTPException(status_code=400, detail="条形码不能为空")
    if 'image_front' in update_data:
        update_data['image'] = update_data['image_front']
    if 'warehouse_id' in update_data and update_data['warehouse_id']:
        if not WarehouseModel.find_by_id(id=update_data['warehouse_id']):
            raise HTTPException(status_code=400, detail="所属仓库不存在")
    for field, value in update_data.items():
        setattr(product, field, value)
    if not product.save():
        raise HTTPException(status_code=400, detail="更新失败，条形码可能重复")
    return _get_detail(product)


@router.delete("/{pid}")
def delete_product(pid: int):
    product = ProductModel.find_by_id(id=pid)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    product.delete()
    return {"message": "删除成功"}
