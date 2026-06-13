# -*- coding: utf-8 -*-
"""
一次性【只读】审计脚本：找出「一单多归属」订单中，修复前后各归属金额/净收益分配不一致的订单。

背景：旧逻辑 apply_bundle_title_ratio_pricing 仅按「组合标题」匹配在售价计算权重。
当某归属的在售已售出/下架（on_sale_items.is_delete=1）时，该行匹配不到价格 → 权重为 0，
导致该归属被分到 0 元，整单利益错误地集中到匹配成功的归属上（如订单 m27332427087）。
修复后会回退该行已关联库存的原价作为权重。

本脚本对比【旧逻辑】与【修复后逻辑】对每个多归属订单各归属的分配结果，列出受影响订单。
不写任何数据库，仅打印报告。

用法：
    cd backend
    python audit_owner_split.py
"""
import sys

sys.path.insert(0, ".")
try:
    sys.stdout.reconfigure(encoding="utf-8")  # 避免 Windows 控制台对中文/日文乱码
except Exception:
    pass

from src.db_manage.database import DatabaseManager
from src.db_manage.models.order_outbound_line import OrderOutboundLineModel
from src.use_web.orders.units.order_goods_ratio import split_order_money_for_owner_user

db = DatabaseManager()

# 保存原始（已修复）的取行方法
_orig_list = OrderOutboundLineModel.list_enriched_for_order


def _old_list(order_no, owner_user_id=None):
    """复现旧逻辑：把组合标题行的库存原价清空，关闭修复中「回退库存原价」的分支。"""
    items = _orig_list(order_no, owner_user_id)
    for it in items:
        if str(it.get("line_kind") or "").strip() == "bundle_title":
            it["original_price"] = None
    return items


def _use_old():
    OrderOutboundLineModel.list_enriched_for_order = staticmethod(_old_list)


def _use_new():
    OrderOutboundLineModel.list_enriched_for_order = _orig_list


def _distinct_owners(ono):
    """订单各出库行关联库存的去重归属 [(owner_user_id, 展示名), ...]。"""
    rows = db.execute_query(
        """
        SELECT DISTINCT p.owner_user_id, COALESCE(u.display_name, u.username)
        FROM order_outbound_lines l
        JOIN inventory p ON p.id = l.inventory_id
        LEFT JOIN users u ON u.id = p.owner_user_id
        WHERE l.order_no = ? AND p.owner_user_id IS NOT NULL AND p.owner_user_id > 0
        """,
        (ono,),
    )
    return [(int(r[0]), str(r[1] if r[1] is not None else r[0])) for r in rows]


def _alloc(ono, owners, amount, sf, ship, net):
    return {
        oid: split_order_money_for_owner_user(ono, oid, amount, sf, ship, net)
        for oid, _ in owners
    }


def main():
    orders = db.execute_query(
        "SELECT order_no, COALESCE(amount, 0), service_fee, shipping_fee, net_income, status FROM orders"
    )

    multi_owner = 0
    affected = []

    for ono, amount, sf, ship, net, status in orders:
        owners = _distinct_owners(ono)
        if len(owners) < 2:
            continue
        multi_owner += 1

        _use_old()
        old = _alloc(ono, owners, amount, sf, ship, net)
        _use_new()
        new = _alloc(ono, owners, amount, sf, ship, net)

        changed = any(
            old[oid]["amount"] != new[oid]["amount"]
            or old[oid]["net_income"] != new[oid]["net_income"]
            for oid, _ in owners
        )
        if changed:
            affected.append((ono, status, int(amount or 0), owners, old, new))

    _use_new()  # 还原

    print("=" * 72)
    print("一单多归属 · 利益分配修复前后对比审计（只读）")
    print("=" * 72)
    print(f"订单总数：{len(orders)}    多归属订单：{multi_owner}    受影响（分配变化）：{len(affected)}")
    print()

    if not affected:
        print("没有发现分配结果变化的多归属订单。")
        return

    for ono, status, amount, owners, old, new in affected:
        print("-" * 72)
        print(f"订单 {ono}    状态 {status}    金额 {amount}")
        print(f"  {'归属':<20}{'旧·金额':>10}{'新·金额':>10}{'旧·净收益':>12}{'新·净收益':>12}")
        for oid, name in owners:
            o, n = old[oid], new[oid]
            label = f"{name}(#{oid})"
            print(
                f"  {label:<20}"
                f"{o['amount']:>10}{n['amount']:>10}"
                f"{(o['net_income'] if o['net_income'] is not None else '-'):>12}"
                f"{(n['net_income'] if n['net_income'] is not None else '-'):>12}"
            )
        old_sum = sum(int(old[oid]["amount"] or 0) for oid, _ in owners)
        new_sum = sum(int(new[oid]["amount"] or 0) for oid, _ in owners)
        print(f"  金额合计校验：旧 {old_sum} / 新 {new_sum} / 订单 {amount}")

    print("-" * 72)
    print(f"\n共 {len(affected)} 笔订单在修复后分配结果发生变化（旧逻辑分配错误）。")
    print("注：分配为实时计算，无需回写数据库；修复代码上线后页面刷新即按新结果显示。")


if __name__ == "__main__":
    main()
