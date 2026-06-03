# -*- coding: utf-8 -*-
"""订单表模型包。

原单文件 ``order.py`` 已拆分为模式主类 + 聚合/查询 Mixin；``__init__`` 重新导出
``OrderModel``，保持 ``from ..models.order import OrderModel`` 旧导入不变。
"""

from .model import OrderModel

__all__ = ["OrderModel"]
