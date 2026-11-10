"""SQLite helpers: connection, queries and schema initialisation.

Every call opens a short-lived connection, which keeps the code simple and
safe to use both from Flask request handlers and from standalone scripts
(seed.py / import_dataset.py).
"""
import os
import sqlite3

from werkzeug.security import generate_password_hash

from models import SCHEMA

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bugtrack.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, args=(), one=False):
    """Run a SELECT. Returns sqlite3.Row / list of Rows."""
    conn = _connect()
    try:
        rows = conn.execute(sql, args).fetchall()
    finally:
        conn.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, args=()):
    """Run a single INSERT/UPDATE/DELETE, commit, return lastrowid."""
    conn = _connect()
    try:
        cur = conn.execute(sql, args)
        conn.commit()
        return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables, indexes, and apply idempotent migrations."""
    conn = _connect()
    try:
        # 1. Check if users table needs migration to support 'reporter' role
        user_table_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if user_table_sql and "reporter" not in user_table_sql[0]:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("ALTER TABLE users RENAME TO users_old")
            conn.execute("""
                CREATE TABLE users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT NOT NULL,
                    email         TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role          TEXT NOT NULL CHECK (role IN ('admin','developer','tester','reporter')),
                    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                INSERT INTO users (id, name, email, password_hash, role, created_at)
                SELECT id, name, email, password_hash, role, created_at FROM users_old
            """)
            conn.execute("DROP TABLE users_old")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

        # 2. Check if bugs table needs new columns
        bugs_table_info = conn.execute("PRAGMA table_info(bugs)").fetchall()
        existing_cols = {col["name"] for col in bugs_table_info}
        new_cols = [
            ("operating_system", "TEXT"),
            ("browser_device", "TEXT"),
            ("app_version", "TEXT"),
            ("fix_description", "TEXT"),
        ]
        for col_name, col_type in new_cols:
            if existing_cols and col_name not in existing_cols:
                conn.execute(f"ALTER TABLE bugs ADD COLUMN {col_name} {col_type}")
        conn.commit()

        # 3. Create any remaining tables and indexes
        for stmt in SCHEMA:
            conn.execute(stmt)
        conn.commit()
    finally:
        conn.close()


def seed_users():
    """Insert demo accounts on first run or ensure default demo users exist."""
    demo_users = [
        # name, email, password, role
        ("Priya Sharma", "admin@bugtrack.dev", "admin123", "admin"),
        ("Arjun Mehta", "dev@bugtrack.dev", "dev123", "developer"),
        ("Sneha Patel", "dev2@bugtrack.dev", "dev2123", "developer"),
        ("Rohan Gupta", "tester@bugtrack.dev", "tester123", "tester"),
        ("Pooja Verma", "reporter@bugtrack.dev", "reporter123", "reporter"),
    ]
    conn = _connect()
    try:
        for name, email, password, role in demo_users:
            exists = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
                    (name, email, generate_password_hash(password), role),
                )
        conn.commit()
    finally:
        conn.close()


def add_notification(user_id, title, message, bug_id=None, notif_type="info"):
    """Insert a single notification for a user."""
    return execute(
        """INSERT INTO notifications (user_id, title, message, bug_id, type)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, title, message, bug_id, notif_type),
    )


def notify_users(user_ids, title, message, bug_id=None, notif_type="info", exclude_user_id=None):
    """Notify multiple users."""
    for uid in set(user_ids):
        if exclude_user_id and uid == exclude_user_id:
            continue
        add_notification(uid, title, message, bug_id, notif_type)


def notify_roles(roles, title, message, bug_id=None, notif_type="info", exclude_user_id=None):
    """Notify all users who have one of the given roles."""
    placeholders = ",".join("?" for _ in roles)
    rows = query(f"SELECT id FROM users WHERE role IN ({placeholders})", tuple(roles))
    uids = [r["id"] for r in rows if not exclude_user_id or r["id"] != exclude_user_id]
    notify_users(uids, title, message, bug_id, notif_type)

