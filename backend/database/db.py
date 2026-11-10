
"""Database selector for BugTrack.

Uses SQLite locally and PostgreSQL when DATABASE_URL is configured.
"""

import os
import sqlite3

from werkzeug.security import generate_password_hash
from models import SCHEMA


DB_PATH = os.environ.get(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "bugtrack.db"),
)


def _use_postgres():
    """Check whether PostgreSQL is configured."""
    return bool(os.environ.get("DATABASE_URL"))


def _postgres():
    """Load PostgreSQL helpers only when needed."""
    from database import postgres_db
    return postgres_db


def _connect():
    """Open a connection to the selected database."""
    if _use_postgres():
        return _postgres()._connect()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, args=(), one=False):
    """Run a SELECT query."""
    if _use_postgres():
        return _postgres().query(sql, args, one)

    conn = _connect()
    try:
        rows = conn.execute(sql, args).fetchall()
    finally:
        conn.close()

    if one:
        return rows[0] if rows else None

    return rows


def execute(sql, args=()):
    """Run an INSERT, UPDATE or DELETE."""
    if _use_postgres():
        return _postgres().execute(sql, args)

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
    """Initialize the selected database."""
    if _use_postgres():
        _postgres().init_db()
        return

    conn = _connect()
    try:
        user_table_sql = conn.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name='users'"
        ).fetchone()

        if user_table_sql and "reporter" not in user_table_sql[0]:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("ALTER TABLE users RENAME TO users_old")

            conn.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (
                        role IN ('admin','developer','tester','reporter')
                    ),
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)

            conn.execute("""
                INSERT INTO users
                (id, name, email, password_hash, role, created_at)
                SELECT id, name, email, password_hash, role, created_at
                FROM users_old
            """)

            conn.execute("DROP TABLE users_old")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

        bugs_table_info = conn.execute(
            "PRAGMA table_info(bugs)"
        ).fetchall()

        existing_cols = {col["name"] for col in bugs_table_info}

        new_cols = [
            ("operating_system", "TEXT"),
            ("browser_device", "TEXT"),
            ("app_version", "TEXT"),
            ("fix_description", "TEXT"),
        ]

        for col_name, col_type in new_cols:
            if existing_cols and col_name not in existing_cols:
                conn.execute(
                    f"ALTER TABLE bugs ADD COLUMN {col_name} {col_type}"
                )

        conn.commit()

        for statement in SCHEMA:
            conn.execute(statement)

        conn.commit()

    finally:
        conn.close()


def seed_users():
    """Insert demo accounts if they do not already exist."""
    demo_users = [
        ("Priya Sharma", "admin@bugtrack.dev", "admin123", "admin"),
        ("Arjun Mehta", "dev@bugtrack.dev", "dev123", "developer"),
        ("Sneha Patel", "dev2@bugtrack.dev", "dev2123", "developer"),
        ("Rohan Gupta", "tester@bugtrack.dev", "tester123", "tester"),
        ("Pooja Verma", "reporter@bugtrack.dev", "reporter123", "reporter"),
    ]

    for name, email, password, role in demo_users:
        exists = query(
            "SELECT id FROM users WHERE email = ?",
            (email,),
            one=True
        )

        if not exists:
            execute(
                """
                INSERT INTO users
                (name, email, password_hash, role)
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    generate_password_hash(password),
                    role
                )
            )


def add_notification(
    user_id,
    title,
    message,
    bug_id=None,
    notif_type="info"
):
    """Insert a notification."""
    return execute(
        """
        INSERT INTO notifications
        (user_id, title, message, bug_id, type)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, title, message, bug_id, notif_type)
    )


def notify_users(
    user_ids,
    title,
    message,
    bug_id=None,
    notif_type="info",
    exclude_user_id=None
):
    """Notify multiple users."""
    for uid in set(user_ids):
        if exclude_user_id and uid == exclude_user_id:
            continue

        add_notification(
            uid, title, message, bug_id, notif_type
        )


def notify_roles(
    roles,
    title,
    message,
    bug_id=None,
    notif_type="info",
    exclude_user_id=None
):
    """Notify users belonging to selected roles."""
    if not roles:
        return

    placeholders = ",".join("?" for _ in roles)

    rows = query(
        f"SELECT id FROM users WHERE role IN ({placeholders})",
        tuple(roles)
    )

    user_ids = [
        row["id"]
        for row in rows
        if not exclude_user_id or row["id"] != exclude_user_id
    ]

    notify_users(
        user_ids,
        title,
        message,
        bug_id,
        notif_type
    )
