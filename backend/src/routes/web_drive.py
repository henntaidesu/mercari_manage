# -*- coding: utf-8 -*-
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel, Field

from ..web_drive import get_web_drive_manager, profiles_root

router = APIRouter(prefix="/api/web-drive", tags=["web-drive"])
log = logging.getLogger(__name__)


class OpenSessionBody(PydanticModel):
    """启动指定账号的 Edge 子浏览器（独立 profile，Cookie 持久化在服务端目录）。"""

    account_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    headless: bool = False
    start_url: Optional[str] = None
    use_mitm_proxy: bool = False
    mitm_proxy_url: Optional[str] = None


class CloseSessionBody(PydanticModel):
    account_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )


@router.get("/profiles-root")
def get_profiles_root():
    """返回当前 profile 根目录（环境变量 WEB_DRIVE_PROFILES_DIR 可覆盖）。"""
    return {"profiles_root": profiles_root()}


@router.get("/sessions")
async def list_sessions():
    return {"sessions": get_web_drive_manager().list_sessions()}


@router.post("/sessions/open")
async def open_session(body: OpenSessionBody):
    try:
        proxy = None
        if body.use_mitm_proxy:
            from ..ssl_mitm_proxy.runner import default_mitm_proxy_url

            proxy = (body.mitm_proxy_url or "").strip() or default_mitm_proxy_url()
        return {
            "success": True,
            "data": await get_web_drive_manager().open_session(
                body.account_key,
                headless=body.headless,
                start_url=body.start_url,
                proxy_server=proxy,
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sessions/close")
async def close_session(body: CloseSessionBody):
    try:
        return {"success": True, "data": await get_web_drive_manager().close_session(body.account_key)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ──────────────────────── 出品自动化 ──────────────────────── #

class PostToMarketBody(PydanticModel):
    """出品自动化请求体（全字段）。"""

    account_key: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = ""
    description: str = ""
    image_urls: List[str] = []
    # 商品类型：mapping_id 用于从 DB 查出各级 position
    category_mapping_id: Optional[str] = None
    # 商品状態
    status: str = ""
    # 快递費負担：seller / buyer
    shipping_payer: str = "seller"
    # 配送方法：undecided / rakuraku / yuuyu / tanome / regular_mail
    shipping_method: str = "undecided"
    # 販売タイプ + 价格
    sale_type: str = "instant_buy"   # "instant_buy" | "negotiable"
    price: int = 0
    # 发货
    shipping_days: str = "2_3_days"  # "1_2_days" | "2_3_days" | "4_7_days"
    shipping_from_area_id: str = ""  # Mercari area id，如 "13"
    # 代理
    proxy_server: Optional[str] = None
    use_mitm_proxy: bool = True


def _get_category_positions(mapping_id: Optional[str]) -> dict:
    """根据 mapping_id 查询类别各级 position，找不到时返回全 None。"""
    if not mapping_id:
        return {}
    try:
        from ..db_manage.models.product_type_category_mapping import (
            ProductTypeCategoryMappingModel,
        )
        rows = ProductTypeCategoryMappingModel.find_all(
            where="mapping_id = ?",
            params=(str(mapping_id),),
            limit=1,
        )
        if not rows:
            return {}
        row = rows[0].to_dict()
        return {
            "category_level1_pos": row.get("category_level1_position"),
            "category_level2_pos": row.get("category_level2_position"),
            "category_level3_pos": row.get("category_level3_position"),
            "product_type_pos":    row.get("product_type_position"),
        }
    except Exception as exc:
        log.warning("查询 category positions 失败: %s", exc)
        return {}


@router.post("/listing/post-to-market")
async def post_to_market(body: PostToMarketBody):
    """
    启动（或复用）指定账号的 Edge 持久化会话（SSL 中间人代理），
    导航到 https://jp.mercari.com/sell/create，并自动完成全部表单步骤：
      · Switch 检查 → 图片上传 → 商品名/说明填写
      · 商品类型选择 → 販売タイプ+价格 → 发货天数 → 发货地址
    """
    from ..web_drive.web_operate.post_to_macket import post_to_market as _do_post
    from ..ssl_mitm_proxy.runner import default_mitm_proxy_url

    try:
        proxy: Optional[str] = None
        if body.use_mitm_proxy:
            proxy = (body.proxy_server or "").strip() or default_mitm_proxy_url()

        # 从 DB 查询 category position 字段
        cat_pos = _get_category_positions(body.category_mapping_id)

        data = await _do_post(
            get_web_drive_manager(),
            body.account_key,
            name=body.name,
            description=body.description,
            image_urls=body.image_urls,
            category_level1_pos=cat_pos.get("category_level1_pos"),
            category_level2_pos=cat_pos.get("category_level2_pos"),
            category_level3_pos=cat_pos.get("category_level3_pos"),
            product_type_pos=cat_pos.get("product_type_pos"),
            status=body.status,
            shipping_payer=body.shipping_payer,
            shipping_method=body.shipping_method,
            sale_type=body.sale_type,
            price=body.price,
            shipping_days=body.shipping_days,
            shipping_from_area_id=body.shipping_from_area_id,
            proxy_server=proxy,
        )
        return {"success": True, "data": data}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("post_to_market 异常")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
