# -*- coding: utf-8 -*-
"""
将 [transactions].created_at 从 DATETIME/TEXT 转为 INTEGER（Unix 秒），不删表数据。

使用前：
  - 停止占用 mercariDB.db 的后端进程（避免锁库）。
  - 脚本会先复制 mercariDB.db -> mercariDB.db.bak_ts_<时间戳>。

用法（在 backend 目录下）：
  python scripts/migrate_transactions_created_at.py
  python scripts/migrate_transactions_created_at.py --db D:\\path\\mercariDB.db
  python scripts/migrate_transactions_created_at.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from src.db_manage.models.transaction import TransactionModel  # noqa: E402


def default_db_path() -> str:
    return os.path.join(BACKEND_ROOT, "mercariDB.db")


def parse_created_at_to_unix(val: Any) -> int:
    """旧库 DATETIME 串（多为 SQLite UTC）或已是整数 -> Unix 秒。"""
    if val is None:
        return int(time.time())
    if isinstance(val, bytes):
        val = val.decode("utf-8", errors="replace")
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        n = int(val)
        if abs(n) > 10**12:
            return n // 1000
        return n
    s = str(val).strip()
    if not s:
        return int(time.time())
    if re.fullmatch(r"-?\d+", s):
        n = int(s)
        if abs(n) > 10**12:
            return n // 1000
        return n
    for fmt, ln in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            chunk = s[:ln]
            dt = datetime.strptime(chunk, fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    print(f"  [warn] 无法解析 created_at={val!r}，使用当前时间")
    return int(time.time())


def _create_table_sql(table_name: str, fields: Dict[str, Dict[str, Any]]) -> str:
    """与 DatabaseManager.create_table 一致的单列主键建表语句。"""
    column_defs: List[str] = []
    primary_keys = [f"[{n}]" for n, fd in fields.items() if fd.get("primary_key")]
    multi_pk = len(primary_keys) > 1

    for fname, fdef in fields.items():
        col_name = f"[{fname}]"
        col_def = f"{col_name} {fdef['type']}"
        if fdef.get("primary_key") and len(primary_keys) == 1:
            col_def += " PRIMARY KEY"
            if fdef.get("autoincrement"):
                col_def += " AUTOINCREMENT"
        elif fdef.get("not_null") and not fdef.get("primary_key"):
            col_def += " NOT NULL"
        if fdef.get("unique") and not fdef.get("primary_key"):
            col_def += " UNIQUE"
        if fdef.get("default") is not None:
            col_def += f" DEFAULT {fdef['default']}"
        column_defs.append(col_def)

    if multi_pk:
        column_defs.append(f"PRIMARY KEY ({', '.join(primary_keys)})")

    return f"CREATE TABLE [{table_name}] ({', '.join(column_defs)})"


def _create_indexes_sql(table_name: str) -> List[str]:
    stmts: List[str] = []
    for idx in TransactionModel.get_indexes():
        idx_name = idx.get("name", f"idx_{table_name}_{idx['columns'][0]}")
        unique_kw = "UNIQUE " if idx.get("unique") else ""
        idx_cols = ", ".join(f"[{c}]" for c in idx["columns"])
        stmts.append(
            f"CREATE {unique_kw}INDEX IF NOT EXISTS {idx_name} ON [{table_name}] ({idx_cols})"
        )
    return stmts


def migrate(db_path: str, dry_run: bool) -> None:
    db_path = os.path.abspath(db_path)
    if not os.path.isfile(db_path):
        raise SystemExit(f"数据库文件不存在: {db_path}")

    fields = TransactionModel.get_fields()
    field_names: Sequence[str] = tuple(fields.keys())
    tmp_name = "transactions_migrate_ts_tmp"

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
        )
        if not cur.fetchone():
            raise SystemExit("未找到表 transactions")
        cur.execute("PRAGMA table_info(transactions)")
        old_cols = [r[1] for r in cur.fetchall()]
        cur.execute("SELECT * FROM transactions ORDER BY id")
        rows = cur.fetchall()
    finally:
        conn.close()

    converted: List[Tuple[Any, ...]] = []
    for row in rows:
        d = dict(zip(old_cols, row))
        out: List[Any] = []
        for fn in field_names:
            if fn == "created_at":
                out.append(parse_created_at_to_unix(d.get("created_at")))
            else:
                out.append(d.get(fn))
        converted.append(tuple(out))

    print(f"数据库: {db_path}")
    print(f"transactions 行数: {len(converted)}（created_at -> Unix 秒）")

    if dry_run:
        for i, tup in enumerate(converted[:5]):
            print(f"  dry-run 样本 {i}: id={tup[0]} created_at={tup[-1]}")
        print("dry-run 结束，未修改文件。")
        return

    bak = f"{db_path}.bak_ts_{int(time.time())}"
    shutil.copy2(db_path, bak)
    print(f"已备份: {bak}")

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS [{tmp_name}]")
        cur.execute(_create_table_sql(tmp_name, fields))
        placeholders = ",".join(["?"] * len(field_names))
        cols_sql = ",".join(f"[{n}]" for n in field_names)
        insert_sql = (
            f"INSERT INTO [{tmp_name}] ({cols_sql}) VALUES ({placeholders})"
        )
        cur.executemany(insert_sql, converted)

        cur.execute("DROP TABLE [transactions]")
        cur.execute(f"ALTER TABLE [{tmp_name}] RENAME TO [transactions]")
        for stmt in _create_indexes_sql("transactions"):
            cur.execute(stmt)
        conn.commit()
        print("迁移完成：transactions.created_at 已为 INTEGER（Unix 秒），索引已重建。")
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"迁移失败（已尝试回滚当前连接操作）: {e}") from e
    finally:
        conn.close()

    # 清除 BaseModel 列缓存（若进程内曾加载过模型）
    if hasattr(TransactionModel, "_cached_table_columns"):
        delattr(TransactionModel, "_cached_table_columns")


def main() -> None:
    ap = argparse.ArgumentParser(description="transactions.created_at -> Unix 秒 INTEGER")
    ap.add_argument("--db", default=default_db_path(), help="SQLite 数据库路径")
    ap.add_argument("--dry-run", action="store_true", help="只打印样本不写库")
    args = ap.parse_args()
    migrate(args.db, args.dry_run)


if __name__ == "__main__":
    main()
