"""One-shot recovery: restore mercari_accounts rows lost during the meilu→mercari rename.

Evidence:
- bundle_purchase_requests proves account_id=1 maps to seller_id='908563766'
- Process of elimination: account_id=2 maps to seller_id='452042823'
- Browser profile dirs mercari_1, mercari_2 still hold valid Edge cookies

What this script restores:
- mercari_accounts row id=1, seller_id='908563766', account_name='账号 1'
- mercari_accounts row id=2, seller_id='452042823', account_name='账号 2'

What user must do AFTER running this:
- Open each account in UI, click "打开浏览器" then "获取" to re-MITM the auth headers (value JSON)
- Optionally rename the accounts in UI
"""
import sqlite3, json, os, sys

path = os.path.join(os.path.dirname(__file__), 'backend', 'mercariDB.db')
db = sqlite3.connect(path)
cur = db.cursor()

# Verify current state
cur.execute("SELECT COUNT(*) FROM mercari_accounts")
n = cur.fetchone()[0]
if n > 0:
    print(f"mercari_accounts already has {n} rows — aborting to avoid duplicates.")
    print("If you want to re-run, delete existing rows first or clear mercari_accounts.")
    sys.exit(1)

# Reconstructed rows
rows = [
    (1, '账号 1', '账号 1', '908563766', 'active', '{}'),
    (2, '账号 2', '账号 2', '452042823', 'active', '{}'),
]

cur.executemany(
    """
    INSERT INTO mercari_accounts
        (id, account_name, login_id, seller_id, status, value, is_open,
         auto_fetch_order_list, auto_fetch_on_sale, auto_fetch_todos, auto_fetch_notifications)
    VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0)
    """,
    rows,
)
# Reset sqlite_sequence so the next INSERT continues from 3
cur.execute("DELETE FROM sqlite_sequence WHERE name='mercari_accounts'")
cur.execute("INSERT INTO sqlite_sequence(name, seq) VALUES ('mercari_accounts', 2)")

db.commit()

cur.execute("SELECT id, account_name, seller_id, status FROM mercari_accounts ORDER BY id")
print("Restored rows:")
for r in cur.fetchall():
    print(" ", r)

db.close()
print()
print("Done. Next steps:")
print("  1) Restart the backend (no more data loss — the rename hook in db_manager.py is now ordered correctly).")
print("  2) Open https://127.0.0.1:9600/#/mercari-accounts, click 编辑 on each account.")
print("  3) Click 打开浏览器 (your Edge login state was preserved in profile dirs).")
print("  4) Click 获取 next to 卖家ID and use 获取用户信息 / MITM flows to repopulate the auth headers (value).")
