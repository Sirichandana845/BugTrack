"""Copy BugTrack SQLite records into an empty PostgreSQL database."""

import argparse
import datetime
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.db import DB_PATH


TABLES = (
    "users",
    "bugs",
    "bug_history",
    "comments",
    "notifications",
    "password_resets",
)
TIMESTAMP_COLUMNS = {
    "created_at",
    "updated_at",
    "timestamp",
    "expires_at",
}
BATCH_SIZE = 500


def _read_source(source_path):
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {source_path}")

    connection = sqlite3.connect(
        source_path.resolve().as_uri() + "?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    return connection


def _source_counts(connection):
    existing = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    missing = set(TABLES) - existing
    if missing:
        raise RuntimeError(
            "SQLite database is missing required tables: "
            + ", ".join(sorted(missing))
        )

    broken = connection.execute("PRAGMA foreign_key_check").fetchall()
    if broken:
        raise RuntimeError(
            f"SQLite database contains {len(broken)} broken foreign-key reference(s)."
        )

    return {
        table: connection.execute(
            f'SELECT COUNT(*) AS count FROM "{table}"'
        ).fetchone()["count"]
        for table in TABLES
    }


def _to_timestamp(value):
    if value is None or not isinstance(value, str):
        return value

    parsed = datetime.datetime.fromisoformat(
        value.strip().replace("Z", "+00:00")
    )
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return parsed


def _copy_records(source, target):
    from psycopg import sql

    with target.cursor() as cursor:
        for table in TABLES:
            source_cursor = source.execute(
                f'SELECT * FROM "{table}" ORDER BY id'
            )
            columns = [column[0] for column in source_cursor.description]
            target_columns = {
                row["column_name"]
                for row in cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema() AND table_name = %s
                    """,
                    (table,),
                ).fetchall()
            }
            missing = set(columns) - target_columns
            if missing:
                raise RuntimeError(
                    f"PostgreSQL table {table} is missing columns: "
                    + ", ".join(sorted(missing))
                )

            timestamp_indexes = [
                index
                for index, name in enumerate(columns)
                if name in TIMESTAMP_COLUMNS
            ]
            statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table),
                sql.SQL(", ").join(map(sql.Identifier, columns)),
                sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            )

            while True:
                batch = source_cursor.fetchmany(BATCH_SIZE)
                if not batch:
                    break

                values = []
                for row in batch:
                    record = list(row)
                    for index in timestamp_indexes:
                        record[index] = _to_timestamp(record[index])
                    values.append(record)
                cursor.executemany(statement, values)

            sequence_statement = sql.SQL(
                """
                SELECT setval(
                    pg_get_serial_sequence(%s, 'id'),
                    COALESCE(MAX(id), 1),
                    MAX(id) IS NOT NULL
                )
                FROM {}
                """
            ).format(sql.Identifier(table))
            cursor.execute(sequence_statement, (table,))


def _target_counts(connection):
    return {
        table: connection.execute(
            f'SELECT COUNT(*) AS count FROM "{table}"'
        ).fetchone()["count"]
        for table in TABLES
    }


def _verify_primary_keys(source, target):
    for table in TABLES:
        source_ids = [
            row["id"]
            for row in source.execute(
                f'SELECT id FROM "{table}" ORDER BY id'
            )
        ]
        target_ids = [
            row["id"]
            for row in target.execute(
                f'SELECT id FROM "{table}" ORDER BY id'
            ).fetchall()
        ]
        if source_ids != target_ids:
            raise RuntimeError(
                f"PostgreSQL verification failed: primary keys differ in {table}."
            )


def migrate(source_path, apply):
    source = _read_source(source_path)
    try:
        counts = _source_counts(source)
        print("SQLite source rows:")
        for table, count in counts.items():
            print(f"  {table}: {count}")
        print("SQLite foreign-key relationships: valid")

        if not apply:
            print("Dry run only. PostgreSQL was not contacted or changed.")
            return

        if not os.environ.get("DATABASE_URL"):
            raise RuntimeError(
                "Set DATABASE_URL in this terminal before using --apply."
            )

        from database.postgres_db import _connect, init_db

        init_db()
        with _connect() as target:
            current_counts = _target_counts(target)
            populated = {
                table: count
                for table, count in current_counts.items()
                if count
            }
            if populated:
                raise RuntimeError(
                    "Refusing to migrate into a non-empty PostgreSQL database: "
                    + ", ".join(
                        f"{table}={count}"
                        for table, count in populated.items()
                    )
                )

            _copy_records(source, target)
            migrated_counts = _target_counts(target)
            if migrated_counts != counts:
                raise RuntimeError(
                    "PostgreSQL verification failed. The transaction will be rolled back."
                )
            _verify_primary_keys(source, target)

        print(
            "Migration committed; row counts and primary keys match SQLite, "
            "and PostgreSQL foreign keys were enforced:"
        )
        for table, count in counts.items():
            print(f"  {table}: {count}")
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(DB_PATH),
        help="SQLite database to copy (default: backend/database/bugtrack.db)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy records to DATABASE_URL. Without this flag, only inspect SQLite.",
    )
    args = parser.parse_args()
    migrate(args.source, args.apply)


if __name__ == "__main__":
    main()
