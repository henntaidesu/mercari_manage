# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..db_manage.models.product_type import ProductTypeModel

router = APIRouter(prefix="/api/product-types", tags=["product-types"])


class ProductTypeCreate(PydanticModel):
    name: str
    description: Optional[str] = None


class ProductTypeUpdate(PydanticModel):
    name: Optional[str] = None
    description: Optional[str] = None


def _serialize(product_type: ProductTypeModel) -> dict:
    d = product_type.to_dict()
    d['product_count'] = ProductTypeModel.get_product_count(product_type.id)
    return d


@router.get("")
def list_product_types():
    return [_serialize(t) for t in ProductTypeModel.find_all(order_by="id ASC")]


@router.post("")
def create_product_type(data: ProductTypeCreate):
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="商品类型名称不能为空")
    if ProductTypeModel.find_by_name(name):
        raise HTTPException(status_code=400, detail="商品类型名称已存在")
    product_type = ProductTypeModel(name=name, description=data.description)
    if not product_type.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return _serialize(product_type)


@router.put("/{type_id}")
def update_product_type(type_id: int, data: ProductTypeUpdate):
    product_type = ProductTypeModel.find_by_id(id=type_id)
    if not product_type:
        raise HTTPException(status_code=404, detail="商品类型不存在")
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="商品类型名称不能为空")
        exists = ProductTypeModel.find_by_name(name)
        if exists and exists.id != type_id:
            raise HTTPException(status_code=400, detail="商品类型名称已存在")
        product_type.name = name
    if data.description is not None:
        product_type.description = data.description
    product_type.save()
    return _serialize(product_type)


@router.delete("/{type_id}")
def delete_product_type(type_id: int):
    product_type = ProductTypeModel.find_by_id(id=type_id)
    if not product_type:
        raise HTTPException(status_code=404, detail="商品类型不存在")
    if ProductTypeModel.get_product_count(type_id) > 0:
        raise HTTPException(status_code=400, detail="该商品类型下存在商品，无法删除")
    product_type.delete()
    return {"message": "删除成功"}
