import sqlite3

conn = sqlite3.connect("database/bugtrack.db")

tables = [
    "users",
    "bugs",
    "bug_history",
    "comments",
    "notifications",
    "password_resets"
]

for table in tables:
    print(f"\n--- {table} ---")
    columns = conn.execute(f"PRAGMA table_info({table})").fetchall()

    for col in columns:
        print(col[1], col[2])

conn.close()