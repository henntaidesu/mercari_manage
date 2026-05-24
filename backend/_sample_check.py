import sqlite3
con = sqlite3.connect("mercariDB.db")
cur = con.cursor()
cur.execute("SELECT photo_url FROM todo_items WHERE photo_url IS NOT NULL AND photo_url != '' LIMIT 2")
print("todo_items.photo_url:", cur.fetchall())
cur.execute("SELECT thumbnails FROM orders WHERE thumbnails IS NOT NULL AND thumbnails != '' LIMIT 2")
print("orders.thumbnails:", cur.fetchall())
