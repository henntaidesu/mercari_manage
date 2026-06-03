# -*- coding: utf-8 -*-
"""WebDrive HTTP 层包。

原单文件 ``web_drive_handler.py`` 已按职责拆分（会话 / 出品 / 在售商品操作）；
``__init__`` 重新导出对外公开 API，保持旧导入不变。
"""

from .sessions import (
    CloseSessionBody,
    OpenSessionBody,
    close_session,
    get_profiles_root,
    list_sessions,
    open_session,
)
from .listing import (
    PostToMarketBody,
    listing_post_progress,
    post_to_market,
)
from .items import (
    DeleteMercariItemBody,
    ResumeMercariItemBody,
    ReviseMercariItemBody,
    SuspendMercariItemBody,
    delete_on_sale_item,
    resume_on_sale_item,
    revise_on_sale_item,
    suspend_on_sale_item,
)

__all__ = [
    "OpenSessionBody",
    "CloseSessionBody",
    "get_profiles_root",
    "list_sessions",
    "open_session",
    "close_session",
    "PostToMarketBody",
    "listing_post_progress",
    "post_to_market",
    "DeleteMercariItemBody",
    "ReviseMercariItemBody",
    "ResumeMercariItemBody",
    "SuspendMercariItemBody",
    "delete_on_sale_item",
    "revise_on_sale_item",
    "resume_on_sale_item",
    "suspend_on_sale_item",
]
