# -*- coding: utf-8 -*-
"""代办事项 API 请求体（Pydantic）。"""
from typing import Optional

from pydantic import BaseModel as PydanticModel, Field


class SyncTodosRequest(PydanticModel):
    account_id: Optional[int] = None


class SendTransactionMessageRequest(PydanticModel):
    text: str = Field(..., min_length=1, max_length=2000)


class ConfirmShippingSelectionRequest(PydanticModel):
    class_text: str = Field(..., min_length=1, max_length=200)
    # 仅对需要选择 facility 的 size 必填：'post_office' | 'lawson' | None
    facility: Optional[str] = None


class SubmitTransactionReviewRequest(PydanticModel):
    text: str = Field(..., min_length=1, max_length=140)
