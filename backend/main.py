from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.auth import require_auth
from src.db_manager import init_database
from src.image_storage import ensure_image_dir
from src.routes.categories import router as categories_router
from src.routes.warehouses import router as warehouses_router
from src.routes.products import router as products_router
from src.routes.transactions import router as transactions_router
from src.routes.scan import router as scan_router
from src.routes.auth import router as auth_router
from src.routes.ocr import router as ocr_router

app = FastAPI(title="仓储管理系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/imges", StaticFiles(directory=ensure_image_dir()), name="imges")

auth_required = [Depends(require_auth)]

app.include_router(categories_router, dependencies=auth_required)
app.include_router(warehouses_router, dependencies=auth_required)
app.include_router(products_router, dependencies=auth_required)
app.include_router(transactions_router, dependencies=auth_required)
app.include_router(scan_router, dependencies=auth_required)
app.include_router(ocr_router, dependencies=auth_required)
app.include_router(auth_router)


@app.on_event("startup")
def startup():
    init_database()


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "仓储管理系统运行中"}
