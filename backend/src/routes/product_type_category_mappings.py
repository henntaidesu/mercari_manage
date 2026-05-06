# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel

from ..db_manage.models.product_type_category_mapping import ProductTypeCategoryMappingModel

router = APIRouter(prefix="/api/product-type-category-mappings", tags=["product-type-category-mappings"])


class MappingCreate(PydanticModel):
    product_type: str
    mapping_id: str
    description: Optional[str] = None


class MappingUpdate(PydanticModel):
    product_type: Optional[str] = None
    mapping_id: Optional[str] = None
    description: Optional[str] = None


def _serialize(mapping: ProductTypeCategoryMappingModel) -> dict:
    return mapping.to_dict()


@router.get("")
def list_mappings():
    rows = ProductTypeCategoryMappingModel.find_all(order_by="created_at DESC, mapping_id ASC")
    return [_serialize(r) for r in rows]


@router.post("")
def create_mapping(data: MappingCreate):
    mapping_id = (data.mapping_id or "").strip()
    if not mapping_id:
        raise HTTPException(status_code=400, detail="映射ID不能为空")
    if ProductTypeCategoryMappingModel.find_by_id(mapping_id=mapping_id):
        raise HTTPException(status_code=400, detail="映射ID已存在")
    product_type = (data.product_type or "").strip()
    if not product_type:
        raise HTTPException(status_code=400, detail="商品类型不能为空")
    row = ProductTypeCategoryMappingModel(
        product_type=product_type,
        mapping_id=mapping_id,
        description=data.description
    )
    if not row.save():
        raise HTTPException(status_code=500, detail="保存失败")
    return _serialize(row)


@router.put("/{pk_mapping_id}")
def update_mapping(pk_mapping_id: str, data: MappingUpdate):
    row = ProductTypeCategoryMappingModel.find_by_id(mapping_id=pk_mapping_id)
    if not row:
        raise HTTPException(status_code=404, detail="映射不存在")

    next_mapping_id = data.mapping_id.strip() if data.mapping_id is not None else row.mapping_id
    next_product_type = data.product_type.strip() if data.product_type is not None else row.product_type

    if not next_mapping_id:
        raise HTTPException(status_code=400, detail="映射ID不能为空")
    if not next_product_type:
        raise HTTPException(status_code=400, detail="商品类型不能为空")
    if next_mapping_id != pk_mapping_id and ProductTypeCategoryMappingModel.find_by_id(mapping_id=next_mapping_id):
        raise HTTPException(status_code=400, detail="映射ID已存在")

    if data.product_type is not None:
        row.product_type = data.product_type.strip()
    if data.mapping_id is not None:
        row.mapping_id = data.mapping_id.strip()
    if data.description is not None:
        row.description = data.description
    row.save()
    return _serialize(row)


@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: str):
    row = ProductTypeCategoryMappingModel.find_by_id(mapping_id=mapping_id)
    if not row:
        raise HTTPException(status_code=404, detail="映射不存在")
    row.delete()
    return {"message": "删除成功"}
