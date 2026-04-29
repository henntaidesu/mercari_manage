# -*- coding: utf-8 -*-
"""
数据库管理器 - 统一管理所有表模型
"""

from typing import List, Type
from .base_model import BaseModel
from .database import DatabaseManager
from .models import (
    CategoryModel,
    WarehouseModel,
    ProductModel,
    InventoryModel,
    TransactionModel,
)


class DBManager:
    """数据库管理器 - 统一注册、初始化所有表"""

    def __init__(self):
        self.db = DatabaseManager()
        self.models: List[Type[BaseModel]] = self._get_all_models()

    def _get_all_models(self) -> List[Type[BaseModel]]:
        """按依赖顺序返回所有模型类"""
        return [
            CategoryModel,    # 无外键依赖
            WarehouseModel,   # 无外键依赖
            ProductModel,     # 依赖 categories
            InventoryModel,   # 依赖 products, warehouses
            TransactionModel, # 依赖 products, warehouses
        ]

    def initialize_database(self) -> bool:
        """初始化数据库：按顺序检查/创建所有表，删除代码中不存在的表"""
        print("正在初始化数据库...")

        defined_tables = {m.get_table_name() for m in self.models}
        db_tables = self.db.get_all_tables()

        # 删除代码中已移除的表
        to_drop = [t for t in db_tables if t not in defined_tables]
        for table_name in to_drop:
            print(f"发现废弃表 {table_name}，正在删除...")
            self.db.drop_table(table_name)

        success, failed = 0, []
        for model_class in self.models:
            table_name = model_class.get_table_name()
            try:
                if model_class.ensure_table_exists():
                    success += 1
                else:
                    failed.append(table_name)
            except Exception as e:
                failed.append(table_name)
                print(f"表 {table_name} 初始化异常: {e}")

        total = len(self.models)
        if not failed:
            print(f"[OK] 数据库初始化成功: {success}/{total} 个表")
        else:
            print(f"[WARN] 数据库初始化完成: {success}/{total}，失败: {', '.join(failed)}")
            return False

        self._seed_default_data()
        return True

    def _seed_default_data(self):
        """写入默认初始数据"""
        if CategoryModel.count() == 0:
            for name, desc in [
                ("电子产品", "电子类商品"),
                ("办公用品", "办公室日常用品"),
                ("食品饮料", "食品及饮料类"),
                ("服装配件", "服装及配件类"),
            ]:
                CategoryModel(name=name, description=desc).save()

        if WarehouseModel.count() == 0:
            for name, loc, desc in [
                ("主仓库", "1号楼A区", "主要存储仓库"),
                ("备用仓库", "2号楼B区", "备用存储仓库"),
            ]:
                WarehouseModel(name=name, location=loc, description=desc).save()

    def check_integrity(self) -> bool:
        """检查所有表结构完整性"""
        for model_class in self.models:
            table_name = model_class.get_table_name()
            if not self.db.table_exists(table_name):
                return False
            existing = {col['name'] for col in self.db.get_table_columns(table_name)}
            if set(model_class.get_fields().keys()) - existing:
                return False
        print("[OK] 所有表完整性检查通过")
        return True

    def get_statistics(self) -> dict:
        """获取各表记录数统计"""
        stats = {'tables': {}, 'total_records': 0}
        for model_class in self.models:
            count = model_class.count()
            stats['tables'][model_class.get_table_name()] = count
            stats['total_records'] += count
        return stats


# 全局单例
_db_manager = DBManager()
_initialized = False


def init_database() -> bool:
    """初始化数据库的便捷函数"""
    global _initialized
    if _initialized:
        return True
    result = _db_manager.initialize_database()
    if result:
        _initialized = True
    return result


def get_db_manager() -> DBManager:
    return _db_manager
