# -*- coding: utf-8 -*-
"""在售商品详情同步包。

原单文件 ``on_sale_item_detail_sync.py`` 已按功能拆分（解析 / 详情回写 / 自动补抓）；
``__init__`` 重新导出对外公开 API（含若干外部使用的下划线名），保持旧导入不变。
"""

from .parsing import (
    _is_matome_listing_bundle_by_title_and_description,
    extract_mgmt_barcode_hints,
    parse_listing_description_tokens_with_quantity,
    resolve_inventory_id_from_listing_description,
)
from .detail_sync import (
    detail_sync_inventory_from_item_get_response,
    fetch_detail_and_sync_inventory,
)
from .auto_fetch import (
    auto_fetch_details_for_inserted_items,
    on_sale_sync_auto_detail_settings,
    relink_inventory_from_persisted_listing,
)

__all__ = [
    "_is_matome_listing_bundle_by_title_and_description",
    "extract_mgmt_barcode_hints",
    "parse_listing_description_tokens_with_quantity",
    "resolve_inventory_id_from_listing_description",
    "detail_sync_inventory_from_item_get_response",
    "fetch_detail_and_sync_inventory",
    "auto_fetch_details_for_inserted_items",
    "on_sale_sync_auto_detail_settings",
    "relink_inventory_from_persisted_listing",
]
