# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel
from typing import Optional
from ..database import DatabaseManager

router = APIRouter(prefix="/api/products", tags=["products"])
db = DatabaseManager()

PRODUCT_COLUMNS = [
    "id",
    "name",
    "barcode",
    "sku",
    "category_id",
    "unit",
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
    unit: Optional[str] = "件"
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
    unit: Optional[str] = None
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
        FROM [products] p
        LEFT JOIN [categories] c ON c.id = p.category_id
        LEFT JOIN [warehouses] w ON w.id = p.warehouse_id
        WHERE 1=1 {where_sql}
    """
    rows = db.execute_query(sql, params)
    return [_row_to_product_detail(r) for r in rows]


def _product_exists(pid: int) -> bool:
    return bool(db.execute_query("SELECT 1 FROM [products] WHERE id = ? LIMIT 1", (pid,)))


def _warehouse_exists(wid: int) -> bool:
    return bool(db.execute_query("SELECT 1 FROM [warehouses] WHERE id = ? LIMIT 1", (wid,)))


@router.get("")
def list_products(keyword: Optional[str] = None, category_id: Optional[int] = None):
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
    products = _query_product_with_joins(" AND p.barcode = ? LIMIT 1", (barcode.strip(),))
    if not products:
        return {"found": False, "product": None}
    return {"found": True, "product": products[0]}


@router.post("/{pid}/stock-in")
def stock_in_product(pid: int, data: StockInRequest):
    """连续扫码入库：库存 +N；若提供 warehouse_id 则同时写入事务记录"""
    if not _product_exists(pid):
        raise HTTPException(status_code=404, detail="商品不存在")
    affected = db.execute_update(
        "UPDATE [products] SET quantity = COALESCE(quantity, 0) + ? WHERE id = ?",
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
    new_qty = db.execute_query("SELECT quantity FROM [products] WHERE id = ?", (pid,))
    return {"success": True, "new_quantity": (new_qty[0][0] if new_qty else 0), "product_id": pid}


@router.get("/{pid}")
def get_product(pid: int):
    products = _query_product_with_joins(" AND p.id = ? LIMIT 1", (pid,))
    if not products:
        raise HTTPException(status_code=404, detail="商品不存在")
    return products[0]


@router.post("")
def create_product(data: ProductCreate):
    if not (data.barcode or "").strip():
        raise HTTPException(status_code=400, detail="条形码必填")
    if data.warehouse_id and not _warehouse_exists(data.warehouse_id):
        raise HTTPException(status_code=400, detail="所属仓库不存在")
    try:
        new_id = db.execute_insert(
            """
            INSERT INTO [products] (
                name, barcode, category_id, warehouse_id, unit, price, quantity,
                description, image, image_front, image_back
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.name,
                data.barcode.strip(),
                data.category_id,
                data.warehouse_id,
                data.unit,
                data.price,
                data.quantity,
                data.description,
                data.image_front,
                data.image_front,
                data.image_back,
            ),
        )
    except Exception:
        raise HTTPException(status_code=400, detail="保存失败，条形码可能重复")
    products = _query_product_with_joins(" AND p.id = ? LIMIT 1", (new_id,))
    return products[0] if products else {"id": new_id}


@router.put("/{pid}")
def update_product(pid: int, data: ProductUpdate):
    if not _product_exists(pid):
        raise HTTPException(status_code=404, detail="商品不存在")
    update_data = data.model_dump(exclude_none=True)
    if 'barcode' in update_data and not (update_data.get('barcode') or '').strip():
        raise HTTPException(status_code=400, detail="条形码不能为空")
    if 'barcode' in update_data:
        update_data['barcode'] = update_data['barcode'].strip()
    if 'image_front' in update_data:
        update_data['image'] = update_data['image_front']
    if 'warehouse_id' in update_data and update_data['warehouse_id']:
        if not _warehouse_exists(update_data['warehouse_id']):
            raise HTTPException(status_code=400, detail="所属仓库不存在")
    allowed_fields = {
        "name", "barcode", "category_id", "warehouse_id", "unit", "price", "quantity",
        "description", "image", "image_front", "image_back",
    }
    update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
    if update_data:
        set_sql = ", ".join([f"[{k}] = ?" for k in update_data.keys()])
        params = tuple(update_data.values()) + (pid,)
        try:
            db.execute_update(f"UPDATE [products] SET {set_sql} WHERE id = ?", params)
        except Exception:
            raise HTTPException(status_code=400, detail="更新失败，条形码可能重复")
    products = _query_product_with_joins(" AND p.id = ? LIMIT 1", (pid,))
    if not products:
        raise HTTPException(status_code=400, detail="更新失败，条形码可能重复")
    return products[0]


@router.delete("/{pid}")
def delete_product(pid: int):
    if not _product_exists(pid):
        raise HTTPException(status_code=404, detail="商品不存在")
    db.execute_update("DELETE FROM [products] WHERE id = ?", (pid,))
    return {"message": "删除成功"}
