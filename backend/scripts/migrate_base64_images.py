# -*- coding: utf-8 -*-
"""
将 inventory 表中的 base64 图片迁移为本地文件路径。

用法：
  python scripts/migrate_base64_images.py
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from src.database import DatabaseManager  # noqa: E402
from src.image_storage import is_base64_image, save_base64_image  # noqa: E402


def main():
    db = DatabaseManager()
    rows = db.execute_query("SELECT id, image, image_front, image_back FROM [inventory] ORDER BY id ASC")
    converted = 0

    for row in rows:
        pid, image, image_front, image_back = row
        update_data = {}

        if is_base64_image(image_front):
            update_data["image_front"] = save_base64_image(image_front, prefix="product_front_migrated")
        if is_base64_image(image_back):
            update_data["image_back"] = save_base64_image(image_back, prefix="product_back_migrated")
        if is_base64_image(image):
            update_data["image"] = save_base64_image(image, prefix="product_legacy_migrated")

        # 保持 image 与 image_front 一致（历史兼容字段）
        if "image_front" in update_data:
            update_data["image"] = update_data["image_front"]
        elif is_base64_image(image) and "image" not in update_data:
            update_data["image"] = save_base64_image(image, prefix="product_legacy_migrated")

        if not update_data:
            continue

        set_sql = ", ".join([f"[{k}] = ?" for k in update_data.keys()])
        params = tuple(update_data.values()) + (pid,)
        db.execute_update(f"UPDATE [inventory] SET {set_sql} WHERE id = ?", params)
        converted += 1
        print(f"[OK] product_id={pid} 已迁移")

    print(f"\n迁移完成：共处理 {converted} 条商品记录")


if __name__ == "__main__":
    main()
