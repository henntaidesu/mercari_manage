# -*- coding: utf-8 -*-
"""
商品类型与类别字段映射表
"""

from typing import Dict, Any, List
from ..base_model import BaseModel


class ProductTypeCategoryMappingModel(BaseModel):
    """商品类型映射（独立模块，不依赖外部表）"""

    @classmethod
    def get_table_name(cls) -> str:
        return "product_type_category_mappings"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            'id': {
                'type': 'INTEGER',
                'primary_key': True,
                'autoincrement': True,
                'not_null': True,
            },
            'product_type': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
            },
            'category_field': {
                'type': 'TEXT',
                'not_null': True,
                'default': None,
            },
            'description': {
                'type': 'TEXT',
                'not_null': False,
                'default': None,
            },
            'created_at': {
                'type': 'DATETIME',
                'not_null': False,
                'default': 'CURRENT_TIMESTAMP',
            },
        }

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'idx_ptcm_product_type_category_field',
                'columns': ['product_type', 'category_field'],
                'unique': True,
            },
        ]

    @classmethod
    def find_by_pair(cls, product_type: str, category_field: str):
        result = cls.find_all(
            where="product_type = ? AND category_field = ?",
            params=(product_type, category_field),
            limit=1
        )
        return result[0] if result else None
