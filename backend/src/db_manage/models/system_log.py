# -*- coding: utf-8 -*-
"""
系统日志表 [system_logs]：记录「自动上架(auto_relist)」「自动获取(auto_fetch)」等后台动作。

- category: 日志大类（'auto_relist' | 'auto_fetch'）
- level:    级别（'info' | 'warning' | 'error'）
- detail:   JSON 详情（stats / 上架的 inventory_id·name·price 等）

写入用类方法 ``add(...)``，全程吞异常——记日志失败绝不影响业务主流程。
"""

import json
import time
from typing import Any, Dict, List, Optional

from ..base_model import BaseModel

# 允许的取值（仅用于内部约束/文档，不强制校验）
# operation: 前端用户操作日志（来自页面提示）
# listing:   手动出品记录（库存管理「出品」成功后记录的提交信息）
LOG_CATEGORIES = ("auto_relist", "auto_fetch", "operation", "listing")
LOG_LEVELS = ("info", "warning", "error", "success")


class SystemLogModel(BaseModel):
    """system_logs：一行一条系统日志。"""

    @classmethod
    def get_table_name(cls) -> str:
        return "system_logs"

    @classmethod
    def get_fields(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "id": {
                "type": "INTEGER",
                "primary_key": True,
                "autoincrement": True,
                "not_null": True,
            },
            # 日志大类：auto_relist / auto_fetch
            "category": {
                "type": "TEXT",
                "not_null": True,
                "default": None,
            },
            # 级别：info / warning / error
            "level": {
                "type": "TEXT",
                "not_null": True,
                "default": "'info'",
            },
            "account_id": {
                "type": "INTEGER",
                "not_null": False,
                "default": None,
            },
            # 冗余账号名：账号删除后日志仍可展示
            "account_name": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            # 操作用户 ID（operation 类日志记录触发用户）
            "user_id": {
                "type": "INTEGER",
                "not_null": False,
                "default": None,
            },
            # 冗余用户名：用户删除后日志仍可展示
            "username": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            # 人类可读摘要
            "message": {
                "type": "TEXT",
                "not_null": True,
                "default": "''",
            },
            # JSON 详情字符串
            "detail": {
                "type": "TEXT",
                "not_null": False,
                "default": None,
            },
            # unix 秒
            "created_at": {
                "type": "INTEGER",
                "not_null": True,
                "default": 0,
            },
        }

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "idx_system_logs_created_at", "columns": ["created_at"]},
            {"name": "idx_system_logs_category", "columns": ["category"]},
            {"name": "idx_system_logs_account_id", "columns": ["account_id"]},
        ]

    @classmethod
    def add(
        cls,
        *,
        category: str,
        level: str = "info",
        message: str = "",
        account_id: Optional[int] = None,
        account_name: Optional[str] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        detail: Any = None,
    ) -> None:
        """写入一条系统日志。失败仅吞掉，不影响调用方主流程。"""
        try:
            detail_str: Optional[str] = None
            if detail is not None:
                if isinstance(detail, (dict, list)):
                    detail_str = json.dumps(detail, ensure_ascii=False, default=str)
                else:
                    detail_str = str(detail)
            aid: Optional[int] = None
            if account_id is not None:
                try:
                    aid = int(account_id)
                except (TypeError, ValueError):
                    aid = None
            uid: Optional[int] = None
            if user_id is not None:
                try:
                    uid = int(user_id)
                except (TypeError, ValueError):
                    uid = None
            cls().db.execute_insert(
                """
                INSERT INTO [system_logs]
                    (category, level, account_id, account_name, user_id, username, message, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(category or "").strip() or "info",
                    str(level or "info").strip() or "info",
                    aid,
                    (str(account_name).strip() if account_name else None),
                    uid,
                    (str(username).strip() if username else None),
                    str(message or ""),
                    detail_str,
                    int(time.time()),
                ),
            )
        except Exception:
            # 记日志失败绝不影响业务
            pass
