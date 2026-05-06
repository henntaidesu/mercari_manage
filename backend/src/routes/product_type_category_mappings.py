# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel

from ..db_manage.models.product_type_category_mapping import ProductTypeCategoryMappingModel

router = APIRouter(prefix="/api/product-type-category-mappings", tags=["product-type-category-mappings"])


class MappingCreate(PydanticModel):
    product_type: str
    category_field: str
    description: Optional[str] = None


class MappingUpdate(PydanticModel):
    product_type: Optional[str] = None
    category_field: Optional[str] = None
    description: Optional[str] = None


def _serialize(mapping: ProductTypeCategoryMappingModel) -> dict:
    return mapping.to_dict()


@router.get("")
def list_mappings():
    rows = ProductTypeCategoryMappingModel.find_all(order_by="id ASC")
    return [_serialize(r) for r in rows]


@router.post("")
def create_mapping(data: MappingCreate):
    product_type = (data.product_type or "").strip()
    if not product_type:
        raise HTTPException(status_code=400, detail="商品类型不能为空")
    category_field = (data.category_field or "").strip()
    if not category_field:
        raise HTTPException(status_code=400, detail="类别字段不能为空")
    if ProductTypeCategoryMappingModel.find_by_pair(product_type, category_field):
        raise HTTPException(status_code=400, detail="该商品类型与类别字段映射已存在")
    row = ProductTypeCategoryMappingModel(
        product_type=product_type,
        category_field=category_field,
        description=data.description
    )
    if not row.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return _serialize(row)


@router.put("/{mapping_id}")
def update_mapping(mapping_id: int, data: MappingUpdate):
    row = ProductTypeCategoryMappingModel.find_by_id(id=mapping_id)
    if not row:
        raise HTTPException(status_code=404, detail="映射不存在")

    next_product_type = data.product_type.strip() if data.product_type is not None else row.product_type
    next_category_field = data.category_field.strip() if data.category_field is not None else row.category_field

    if not next_product_type:
        raise HTTPException(status_code=400, detail="商品类型不能为空")
    if not next_category_field:
        raise HTTPException(status_code=400, detail="类别字段不能为空")

    exists = ProductTypeCategoryMappingModel.find_by_pair(next_product_type, next_category_field)
    if exists and exists.id != mapping_id:
        raise HTTPException(status_code=400, detail="该商品类型与类别字段映射已存在")

    if data.product_type is not None:
        row.product_type = data.product_type.strip()
    if data.category_field is not None:
        row.category_field = data.category_field.strip()
    if data.description is not None:
        row.description = data.description
    row.save()
    return _serialize(row)


@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: int):
    row = ProductTypeCategoryMappingModel.find_by_id(id=mapping_id)
    if not row:
        raise HTTPException(status_code=404, detail="映射不存在")
    row.delete()
    return {"message": "删除成功"}
