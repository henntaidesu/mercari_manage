# -*- coding: utf-8 -*-
"""
应用键值配置表 [config]：用于出品默认值等可扩展配置。
"""

from typing import Any, Dict, List, Optional

from ..base_model import BaseModel


class ConfigEntryModel(BaseModel):
    """单行一条配置：name 主键，value 文本。"""

    @classmethod
    def get_table_name(cls) -> str:
        return "config"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "name": {
                "type": "TEXT",
                "primary_key": True,
                "not_null": True,
            },
            "value": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
        }

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return []

    @classmethod
    def get_value(cls, name: str) -> Optional[str]:
        key = (name or "").strip()
        if not key:
            return None
        rows = cls.find_all("[name] = ?", (key,), limit=1)
        if not rows:
            return None
        v = rows[0].value
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @classmethod
    def set_value(cls, name: str, value: Optional[str]) -> None:
        """写入或删除：空字符串 / None 则删除该键。"""
        key = (name or "").strip()
        if not key:
            return
        raw = (value or "").strip()
        rows = cls.find_all("[name] = ?", (key,), limit=1)
        if not raw:
            if rows:
                rows[0].delete()
            return
        if rows:
            inst = rows[0]
            if inst.value != raw:
                inst.value = raw
                inst.save()
        else:
            cls(name=key, value=raw).save()
