# -*- coding: utf-8 -*-
"""代办事项 API 请求体（Pydantic）。"""
from typing import Optional

from pydantic import BaseModel as PydanticModel


class SyncTodosRequest(PydanticModel):
    account_id: Optional[int] = None
