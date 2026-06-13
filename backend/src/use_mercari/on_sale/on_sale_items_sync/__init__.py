# -*- coding: utf-8 -*-
"""在售商品列表同步包。

原单文件 ``on_sale_items_sync.py`` 已按功能拆分；``__init__`` 重新导出对外公开 API，
保持 ``from ...on_sale.on_sale_items_sync import X`` 旧导入不变。
"""

from .inventory_qty import (
    _is_active_on_sale,
    count_active_on_sale_for_mercari_ids,
    enrich_inventory_rows_on_sale_quantity,
    recalculate_and_persist_inventory_on_sale_quantity,
)
from .row_mapping import mercari_list_item_to_row, upsert_on_sale_item_row
from .sync import apply_on_sale_list_sync, sync_on_sale_items_from_mercari
# TEMP_FULL_UPDATE: 临时功能，现有数据补齐后删除下面一行导入与 __all__ 项。
from .full_update import full_update_on_sale_details_from_mercari

__all__ = [
    "full_update_on_sale_details_from_mercari",  # TEMP_FULL_UPDATE
    "_is_active_on_sale",
    "count_active_on_sale_for_mercari_ids",
    "enrich_inventory_rows_on_sale_quantity",
    "recalculate_and_persist_inventory_on_sale_quantity",
    "mercari_list_item_to_row",
    "upsert_on_sale_item_row",
    "apply_on_sale_list_sync",
    "sync_on_sale_items_from_mercari",
]
