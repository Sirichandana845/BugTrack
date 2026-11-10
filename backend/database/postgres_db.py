
"""PostgreSQL database connection and query helpers for BugTrack."""

import os

from database.postgres_schema import POSTGRES_SCHEMA


def _connect():
    """Open a PostgreSQL connection when needed."""
    # Import the driver only when a connection is requested.
    import psycopg
    from psycopg.rows import dict_row

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Configure it in the environment."
        )

    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql://", 1
        )

    return psycopg.connect(
        database_url,
        row_factory=dict_row
    )


def _convert_placeholders(sql):
    """Convert SQLite-style ? placeholders to PostgreSQL %s."""
    result = []
    i = 0
    quote = None
    length = len(sql)

    while i < length:
        char = sql[i]

        if quote:
            result.append(char)

            if char == quote:
                if i + 1 < length and sql[i + 1] == quote:
                    result.append(sql[i + 1])
                    i += 2
                    continue

                quote = None

            elif char == "\\" and i + 1 < length:
                result.append(sql[i + 1])
                i += 2
                continue

        elif char in ("'", '"'):
            quote = char
            result.append(char)

        elif (
            char == "-"
            and i + 1 < length
            and sql[i + 1] == "-"
        ):
            end = sql.find("\n", i)

            if end == -1:
                result.append(sql[i:])
                break

            result.append(sql[i:end + 1])
            i = end + 1
            continue

        elif (
            char == "/"
            and i + 1 < length
            and sql[i + 1] == "*"
        ):
            end = sql.find("*/", i + 2)

            if end == -1:
                result.append(sql[i:])
                break

            result.append(sql[i:end + 2])
            i = end + 2
            continue

        elif char == "?":
            result.append("%s")

        else:
            result.append(char)

        i += 1

    return "".join(result)


def query(sql, args=(), one=False):
    """Execute a SELECT query and return dictionary rows."""
    sql = _convert_placeholders(sql)

    with _connect() as conn:
        rows = conn.execute(sql, args).fetchall()

    if one:
        return rows[0] if rows else None

    return rows


def execute(sql, args=()):
    """Execute a write query and return an inserted ID when applicable."""
    sql = _convert_placeholders(sql)

    is_insert = sql.lstrip().upper().startswith("INSERT")

    if is_insert and "RETURNING" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + " RETURNING id"

    with _connect() as conn:
        cursor = conn.execute(sql, args)

        if is_insert:
            row = cursor.fetchone()
            return row["id"] if row else None

    return None


def init_db():
    """Create PostgreSQL tables and indexes."""
    with _connect() as conn:
        for statement in POSTGRES_SCHEMA:
            conn.execute(statement)
