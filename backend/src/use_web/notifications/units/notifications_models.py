# -*- coding: utf-8 -*-
"""お知らせ通知 API 请求体（Pydantic）。"""
from typing import List, Optional

from pydantic import BaseModel as PydanticModel, Field


class SyncNotificationsRequest(PydanticModel):
    account_id: Optional[int] = None


class MarkReadRequest(PydanticModel):
    ids: List[int] = Field(default_factory=list)
    is_read: bool = True
