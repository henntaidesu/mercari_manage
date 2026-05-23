# -*- coding: utf-8 -*-
"""煤炉账号管理 Pydantic 模型与常量定义。"""
from typing import Any, Dict, Optional

from pydantic import BaseModel as PydanticModel, Field


ALLOWED_STATUS = {"active", "disabled"}
# 前端主选项 15/30/1H/3H/6H；保留旧值以便已存数据校验通过
ALLOWED_FETCH_INTERVALS = frozenset({"15", "30", "60", "3h", "6h", "10", "12h", "24h"})
MERCARI_IN_PROGRESS_URL = "https://jp.mercari.com/mypage/listings/in_progress"
MERCARI_LISTINGS_URL = "https://jp.mercari.com/mypage/listings"
IN_PROGRESS_FIRST_LINK_XPATH = '//*[@id="my-page-main-content"]/div/div/div/div/ul/li[1]/a/div[1]/div'
LISTINGS_FIRST_ITEM_XPATH = '//*[@id="my-page-main-content"]/div/div/div/div/ul/li[1]/a/div[1]/div/span[1]'
IN_PROGRESS_CLICK_XPATH_CANDIDATES = (
    IN_PROGRESS_FIRST_LINK_XPATH,
    '//*[@id="my-page-main-content"]/div/div/div/div/ul/li[1]/a/div[1]/div/span[1]',
    '//*[@id="my-page-main-content"]//ul/li[1]//a',
)

# 与 jp.mercari.com Web 抓包一致；可选：在售列表 / 单件详情专用 DPoP
_HEADER_FIELD_LABELS = [
    ("x_platform", "X-Platform"),
    ("authorization", "Authorization"),
    ("sec_ch_ua_platform", "Sec-CH-UA-Platform"),
    ("accept_language", "Accept-Language"),
    ("sec_ch_ua", "Sec-CH-UA"),
    ("sec_ch_ua_mobile", "Sec-CH-UA-Mobile"),
    ("dpop_list", "DPoP_List"),
    ("dpop_info", "DPoP_Info"),
    ("dpop_on_sale_list", "DPoP_OnSale-List"),
    ("dpop_item_get_info", "DPoP_ItemGet-Info"),
    ("user_agent", "User-Agent"),
    ("accept", "Accept"),
    ("origin", "Origin"),
    ("sec_fetch_site", "Sec-Fetch-Site"),
    ("sec_fetch_mode", "Sec-Fetch-Mode"),
    ("sec_fetch_dest", "Sec-Fetch-Dest"),
    ("referer", "Referer"),
    ("accept_encoding", "Accept-Encoding"),
    ("priority", "Priority"),
]


class MeiluAccountCreate(PydanticModel):
    account_name: str
    """省略或全空时存 {}，后续可通过 MITM 等写入完整请求头。"""
    value: Optional[Dict[str, Any]] = None
    login_id: Optional[str] = None
    seller_id: Optional[str] = None
    status: str = "disabled"
    remark: Optional[str] = None
    is_open: int = 0
    fetch_interval: Optional[str] = None
    auto_fetch_order_status: int = 0
    auto_fetch_order_list: int = 0
    auto_fetch_on_sale: int = 0


class MeiluAccountUpdate(PydanticModel):
    account_name: Optional[str] = None
    login_id: Optional[str] = None
    seller_id: Optional[str] = None
    value: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    remark: Optional[str] = None
    is_open: Optional[int] = None
    fetch_interval: Optional[str] = None
    auto_fetch_order_status: Optional[int] = None
    auto_fetch_order_list: Optional[int] = None
    auto_fetch_on_sale: Optional[int] = None


class FetchAuthViaMitmBody(PydanticModel):
    """通过 MITM 按顺序抓取 4 个 DPoP 字段并写回账号。"""

    wait_seconds: int = Field(15, ge=5, le=300)
    open_browser: bool = True
    in_progress_xpath: str = IN_PROGRESS_FIRST_LINK_XPATH
    first_item_xpath: str = LISTINGS_FIRST_ITEM_XPATH


class FetchSellerIdViaMitmBody(PydanticModel):
    """打开出品一覧页，经 MITM 截获 items/get_items（on_sale,stop）并从 URL 解析 seller_id。"""

    account_key: str = Field(
        default="meilu_prepare",
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    wait_seconds: int = Field(90, ge=10, le=300)
    headless: bool = False
    close_browser_after: bool = False
