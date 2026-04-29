# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..models.product import ProductModel
from ..models.inventory import InventoryModel
from ..models.category import CategoryModel

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductCreate(PydanticModel):
    name: str
    sku: Optional[str] = None
    category_id: Optional[int] = None
    unit: Optional[str] = "件"
    price: Optional[float] = 0.0
    description: Optional[str] = None
    image: Optional[str] = None


class ProductUpdate(PydanticModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category_id: Optional[int] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    image: Optional[str] = None


def _get_detail(product: ProductModel) -> dict:
    d = product.to_dict()
    cat = CategoryModel.find_by_id(id=product.category_id) if product.category_id else None
    d['category_name'] = cat.name if cat else None
    d['total_stock'] = ProductModel.get_total_stock(product.id)
    # 各仓库库存明细
    inv_list = InventoryModel.find_all("product_id = ?", (product.id,))
    d['inventory'] = [i.to_dict() for i in inv_list]
    return d


@router.get("")
def list_products(keyword: Optional[str] = None, category_id: Optional[int] = None):
    return ProductModel.find_with_stock(keyword=keyword, category_id=category_id)


@router.get("/{pid}")
def get_product(pid: int):
    product = ProductModel.find_by_id(id=pid)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return _get_detail(product)


@router.post("")
def create_product(data: ProductCreate):
    product = ProductModel(**data.model_dump())
    if not product.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return _get_detail(product)


@router.put("/{pid}")
def update_product(pid: int, data: ProductUpdate):
    product = ProductModel.find_by_id(id=pid)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    product.save()
    return _get_detail(product)


@router.delete("/{pid}")
def delete_product(pid: int):
    product = ProductModel.find_by_id(id=pid)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    if ProductModel.get_total_stock(pid) > 0:
        raise HTTPException(status_code=400, detail="商品存在库存，无法删除")
    InventoryModel.delete_all("product_id = ?", (pid,))
    product.delete()
    return {"message": "删除成功"}
