# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..database import DatabaseManager
from ..image_storage import is_base64_image, save_base64_image, delete_image_file

router = APIRouter(prefix="/api/inventory", tags=["inventory"])
db = DatabaseManager()

PRODUCT_COLUMNS = [
    "id",
    "name",
    "barcode",
    "sku",
    "category_id",
    "price",
    "quantity",
    "description",
    "image",
    "image_front",
    "image_back",
    "created_at",
    "warehouse_id",
]


class StockInRequest(PydanticModel):
    warehouse_id: Optional[int] = None   # 不传则只更新库存，不写事务记录
    quantity: int = 1
    remark: Optional[str] = None


class ProductCreate(PydanticModel):
    name: Optional[str] = None
    barcode: str
    category_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    price: Optional[float] = 0.0
    quantity: Optional[int] = 1
    description: Optional[str] = None
    image_front: Optional[str] = None
    image_back: Optional[str] = None


class ProductUpdate(PydanticModel):
    name: Optional[str] = None
    barcode: Optional[str] = None
    category_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    description: Optional[str] = None
    image_front: Optional[str] = None
    image_back: Optional[str] = None


def _row_to_product_detail(row: tuple) -> dict:
    keys = PRODUCT_COLUMNS + ["category_name", "warehouse_name"]
    return dict(zip(keys, row))


def _query_product_with_joins(where_sql: str = "", params: tuple = ()) -> list[dict]:
    select_cols = ", ".join([f"p.[{c}]" for c in PRODUCT_COLUMNS])
    sql = f"""
        SELECT {select_cols}, c.name AS category_name, w.name AS warehouse_name
        FROM [inventory] p
        LEFT JOIN [categories] c ON c.id = p.category_id
        LEFT JOIN [warehouses] w ON w.id = p.warehouse_id
        WHERE 1=1 {where_sql}
    """
    rows = db.execute_query(sql, params)
    return [_row_to_product_detail(r) for r in rows]


def _product_exists(pid: int) -> bool:
    return bool(db.execute_query("SELECT 1 FROM [inventory] WHERE id = ? LIMIT 1", (pid,)))


def _warehouse_exists(wid: int) -> bool:
    return bool(db.execute_query("SELECT 1 FROM [warehouses] WHERE id = ? LIMIT 1", (wid,)))


def _convert_image_payload(image_value: Optional[str], prefix: str) -> Optional[str]:
    if image_value is None:
        return None
    val = image_value.strip() if isinstance(image_value, str) else image_value
    if not val:
        return None
    if is_base64_image(val):
        try:
            return save_base64_image(val, prefix=prefix)
        except Exception:
            raise HTTPException(status_code=400, detail="图片格式无效或保存失败")
    return val


@router.get("")
def list_inventory(keyword: Optional[str] = None, category_id: Optional[int] = None):
    where_parts = []
    params = []
    if keyword:
        where_parts.append("AND (p.name LIKE ? OR p.barcode LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if category_id:
        where_parts.append("AND p.category_id = ?")
        params.append(category_id)
    where_sql = " " + " ".join(where_parts) + " ORDER BY p.id DESC"
    return _query_product_with_joins(where_sql, tuple(params))


@router.get("/barcode/{barcode}")
def find_by_barcode(barcode: str):
    """根据条形码精确查找商品（用于连续扫码流程）"""
    inventory_items = _query_product_with_joins(" AND p.barcode = ? LIMIT 1", (barcode.strip(),))
    if not inventory_items:
        return {"found": False, "product": None}
    return {"found": True, "product": inventory_items[0]}


@router.post("/{pid}/stock-in")
def stock_in_product(pid: int, data: StockInRequest):
    """连续扫码入库：库存 +N；若提供 warehouse_id 则同时写入事务记录"""
    if not _product_exists(pid):
        raise HTTPException(status_code=404, detail="商品不存在")
    affected = db.execute_update(
        "UPDATE [inventory] SET quantity = COALESCE(quantity, 0) + ? WHERE id = ?",
        (data.quantity, pid),
    )
    if affected <= 0:
        raise HTTPException(status_code=500, detail="库存更新失败")
    if data.warehouse_id:
        db.execute_insert(
            """
            INSERT INTO [transactions] (
                type, product_id, warehouse_id, quantity, remark
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("in", pid, data.warehouse_id, data.quantity, data.remark or "扫码快速入库"),
        )
    new_qty = db.execute_query("SELECT quantity FROM [inventory] WHERE id = ?", (pid,))
    return {"success": True, "new_quantity": (new_qty[0][0] if new_qty else 0), "product_id": pid}


@router.get("/{pid}")
def get_product(pid: int):
    inventory_items = _query_product_with_joins(" AND p.id = ? LIMIT 1", (pid,))
    if not inventory_items:
        raise HTTPException(status_code=404, detail="商品不存在")
    return inventory_items[0]


@router.post("")
def create_product(data: ProductCreate):
    if not (data.barcode or "").strip():
        raise HTTPException(status_code=400, detail="条形码必填")
    if data.warehouse_id is None:
        raise HTTPException(status_code=400, detail="所属仓库必填")
    if not _warehouse_exists(data.warehouse_id):
        raise HTTPException(status_code=400, detail="所属仓库不存在")
    image_front_path = _convert_image_payload(data.image_front, "product_front")
    image_back_path = _convert_image_payload(data.image_back, "product_back")
    try:
        new_id = db.execute_insert(
            """
            INSERT INTO [inventory] (
                name, barcode, category_id, warehouse_id, price, quantity,
                description, image, image_front, image_back
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.name,
                data.barcode.strip(),
                data.category_id,
                data.warehouse_id,
                data.price,
                data.quantity,
                data.description,
                image_front_path,
                image_front_path,
                image_back_path,
            ),
        )
    except Exception:
        raise HTTPException(status_code=400, detail="保存失败，条形码可能重复")
    inventory_items = _query_product_with_joins(" AND p.id = ? LIMIT 1", (new_id,))
    return inventory_items[0] if inventory_items else {"id": new_id}


@router.put("/{pid}")
def update_product(pid: int, data: ProductUpdate):
    if not _product_exists(pid):
        raise HTTPException(status_code=404, detail="商品不存在")
    update_data = data.model_dump(exclude_unset=True)
    if 'barcode' in update_data and not (update_data.get('barcode') or '').strip():
        raise HTTPException(status_code=400, detail="条形码不能为空")
    if 'barcode' in update_data:
        update_data['barcode'] = update_data['barcode'].strip()
    existing = db.execute_query("SELECT image_front, image_back, warehouse_id FROM [inventory] WHERE id = ? LIMIT 1", (pid,))
    old_front = existing[0][0] if existing else None
    old_back = existing[0][1] if existing else None
    old_warehouse_id = existing[0][2] if existing else None

    if 'image_front' in update_data:
        new_front = _convert_image_payload(update_data.get('image_front'), "product_front")
        update_data['image_front'] = new_front
        update_data['image'] = new_front
        if old_front and old_front != new_front:
            delete_image_file(old_front)
    if 'image_back' in update_data:
        new_back = _convert_image_payload(update_data.get('image_back'), "product_back")
        update_data['image_back'] = new_back
        if old_back and old_back != new_back:
            delete_image_file(old_back)
    final_warehouse_id = update_data['warehouse_id'] if 'warehouse_id' in update_data else old_warehouse_id
    if final_warehouse_id is None:
        raise HTTPException(status_code=400, detail="所属仓库必填")
    if 'warehouse_id' in update_data:
        if not _warehouse_exists(final_warehouse_id):
            raise HTTPException(status_code=400, detail="所属仓库不存在")
    allowed_fields = {
        "name", "barcode", "category_id", "warehouse_id", "price", "quantity",
        "description", "image", "image_front", "image_back",
    }
    update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
    if update_data:
        set_sql = ", ".join([f"[{k}] = ?" for k in update_data.keys()])
        params = tuple(update_data.values()) + (pid,)
        try:
            db.execute_update(f"UPDATE [inventory] SET {set_sql} WHERE id = ?", params)
        except Exception:
            raise HTTPException(status_code=400, detail="更新失败，条形码可能重复")
    inventory_items = _query_product_with_joins(" AND p.id = ? LIMIT 1", (pid,))
    if not inventory_items:
        raise HTTPException(status_code=400, detail="更新失败，条形码可能重复")
    return inventory_items[0]


@router.delete("/{pid}")
def delete_product(pid: int):
    if not _product_exists(pid):
        raise HTTPException(status_code=404, detail="商品不存在")
    images = db.execute_query("SELECT image_front, image_back FROM [inventory] WHERE id = ? LIMIT 1", (pid,))
    if images:
        delete_image_file(images[0][0])
        delete_image_file(images[0][1])
    db.execute_update("DELETE FROM [inventory] WHERE id = ?", (pid,))
    return {"message": "删除成功"}
