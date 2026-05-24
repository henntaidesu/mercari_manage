# -*- coding: utf-8 -*-
"""在售商品列表处理器：从煤炉同步及详情拉取。"""
from typing import Any, Dict, List, Set

from fastapi import HTTPException

from ....db_manage.models.on_sale_item import OnSaleItemModel
from ....web_drive.core.account_serial_queue import (
    queue_key_for_meilu_account,
    resolve_meilu_account_id,
    run_meilu_serial_async,
)
from ....use_mercari.on_sale_item_detail_sync import fetch_detail_and_sync_inventory
from ....use_mercari.on_sale_items_sync import sync_on_sale_items_from_mercari
from ....use_mercari.sync_data import resolve_account_id_by_seller_id

from .on_sale_items_models import (
    FetchOnSaleDetailRequest,
    FetchOnSaleDetailsBatchRequest,
    SyncOnSaleRequest,
)


_FETCH_DETAILS_BATCH_MAX = 200


async def sync_on_sale(data: SyncOnSaleRequest):
    """
    从煤炉拉取在售列表并同步本地：用账号主 profile ``meilu_{id}`` 经 MITM 打开
    jp.mercari.com/mypage/listings，截获 api.mercari.jp/items/get_items 响应。
    在同一浏览器会话内，对本次**新增**的商品依次打开商品页截获 items/get，执行与「获取详情」相同的库存回写（可用 WEB_DRIVE_ON_SALE_SYNC_AUTO_DETAIL=0 关闭）。
    新列表中不存在的本地记录不物理删除，而是标记 is_delete=1（软删除）。
    列表接口默认仅返回 is_delete=0 数据。须已启动 mitmdump（与出品/抓包共用）。
    """
    try:
        aid = resolve_meilu_account_id(data.account_id)
        result = await run_meilu_serial_async(
            queue_key_for_meilu_account(aid),
            lambda: sync_on_sale_items_from_mercari(account_id=aid),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"同步失败: {exc}") from exc
    return {"success": True, "data": result}


async def fetch_on_sale_item_detail(data: FetchOnSaleDetailRequest):
    """
    使用对应账号 Edge（MITM）打开 ``https://jp.mercari.com/item/m{item_id}``，
    截获 api.mercari.jp/items/get 响应；解析 data.description 中的末行暗号（-=~<>）、
    「管理ID / 管理番号 / バーコード」，
    匹配库存后写入 mercari_item_id、on_sale_quantity。须已启动 mitmdump。
    """
    item_id = (data.item_id or "").strip()
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id 不能为空")

    account_id = data.account_id
    if account_id is None:
        rows = OnSaleItemModel.find_all(
            where="TRIM([item_id]) = TRIM(?)",
            params=(item_id,),
            limit=1,
        )
        seller_id = None
        if rows:
            seller_id = str(rows[0].seller_id or "").strip() or None
        if seller_id:
            account_id = resolve_account_id_by_seller_id(seller_id)
        if account_id is None:
            raise HTTPException(
                status_code=400,
                detail="请传 account_id，或在在售列表中存在该商品且卖家已绑定 active 煤炉账号（seller_id）",
            )

    try:
        qk = queue_key_for_meilu_account(int(account_id))
        payload = await run_meilu_serial_async(
            qk,
            lambda: fetch_detail_and_sync_inventory(item_id, account_id=account_id),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取详情失败: {exc}") from exc

    return {"success": True, "data": payload}


async def fetch_on_sale_item_details_batch(data: FetchOnSaleDetailsBatchRequest):
    """
    对多个 item_id 依次执行 fetch_detail_and_sync_inventory，且整段只提交一次
    run_meilu_serial_async（与单条 fetch-detail、在售同步同一队列键 FIFO），避免多 HTTP
    并发在同一账号下抢占 Edge / MITM。
    """
    raw_ids = data.item_ids or []
    cleaned: List[str] = []
    seen: Set[str] = set()
    for x in raw_ids:
        t = str(x or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        cleaned.append(t)
    if not cleaned:
        raise HTTPException(status_code=400, detail="item_ids 不能为空")
    if len(cleaned) > _FETCH_DETAILS_BATCH_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"单次最多处理 {_FETCH_DETAILS_BATCH_MAX} 个商品 ID",
        )

    try:
        aid = resolve_meilu_account_id(data.account_id)
        qk = queue_key_for_meilu_account(int(aid))

        async def _run_batch() -> Dict[str, Any]:
            results: List[Dict[str, Any]] = []
            ok_synced = 0
            not_ok = 0
            for iid in cleaned:
                try:
                    payload = await fetch_detail_and_sync_inventory(iid, account_id=aid)
                    sync = payload.get("sync") if isinstance(payload.get("sync"), dict) else {}
                    if sync.get("updated"):
                        ok_synced += 1
                    else:
                        not_ok += 1
                    results.append({"item_id": iid, "sync": sync})
                except Exception as exc:
                    not_ok += 1
                    results.append({"item_id": iid, "sync": None, "error": str(exc)})
            return {
                "account_id": int(aid),
                "total": len(cleaned),
                "ok_synced": ok_synced,
                "not_ok": not_ok,
                "results": results,
            }

        out = await run_meilu_serial_async(qk, _run_batch)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"批量获取详情失败: {exc}") from exc

    return {"success": True, "data": out}
