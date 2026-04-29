# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..models.product import ProductModel
from ..models.category import CategoryModel

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductCreate(PydanticModel):
    name: Optional[str] = None
    barcode: str
    category_id: Optional[int] = None
    unit: Optional[str] = "件"
    price: Optional[float] = 0.0
    quantity: Optional[int] = 0
    description: Optional[str] = None
    image_front: Optional[str] = None
    image_back: Optional[str] = None


class ProductUpdate(PydanticModel):
    name: Optional[str] = None
    barcode: Optional[str] = None
    category_id: Optional[int] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    description: Optional[str] = None
    image_front: Optional[str] = None
    image_back: Optional[str] = None


def _get_detail(product: ProductModel) -> dict:
    d = product.to_dict()
    cat = CategoryModel.find_by_id(id=product.category_id) if product.category_id else None
    d['category_name'] = cat.name if cat else None
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
    if not (data.barcode or "").strip():
        raise HTTPException(status_code=400, detail="条形码必填")
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
