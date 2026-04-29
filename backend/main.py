from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.db_manager import init_database
from src.routes.categories import router as categories_router
from src.routes.warehouses import router as warehouses_router
from src.routes.products import router as products_router
from src.routes.inventory import router as inventory_router
from src.routes.transactions import router as transactions_router

app = FastAPI(title="仓储管理系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories_router)
app.include_router(warehouses_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(transactions_router)


@app.on_event("startup")
def startup():
    init_database()


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "仓储管理系统运行中"}
