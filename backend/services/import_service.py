
"""Kaggle dataset import pipeline.

Supports SQLite and PostgreSQL through shared database helpers.
Imports are non-destructive by default.
"""

import csv
import datetime
import os
import random
import re

from config import DEFAULT_KAGGLE_CSV
from database import db as database
from services import priority_service


STATUS_MAP = {
    "NEW": "reported",
    "OPEN": "reported",
    "CONFIRMED": "reported",
    "UNCONFIRMED": "reported",
    "ASSIGNED": "assigned",
    "IN_PROGRESS": "in_progress",
    "STARTED": "in_progress",
    "TODO": "reported",
    "FIXED": "fixed",
    "RESOLVED": "fixed",
    "VERIFIED": "testing",
    "TESTING": "testing",
    "CLOSED": "closed",
    "REOPENED": "reopened",
    "REOPEN": "reopened",
}

SEV_MAP = {
    "BLOCKER": "Critical",
    "CRITICAL": "Critical",
    "CRASH": "Critical",
    "S1": "Critical",
    "HIGH": "High",
    "MAJOR": "High",
    "S2": "High",
    "NORMAL": "Medium",
    "MEDIUM": "Medium",
    "S3": "Medium",
    "MINOR": "Low",
    "LOW": "Low",
    "TRIVIAL": "Low",
    "ENHANCEMENT": "Low",
    "S4": "Low",
    "S5": "Low",
}

PRIO_MAP = {
    "P1": "Critical",
    "P2": "High",
    "P3": "Medium",
    "P4": "Low",
    "P5": "Low",
    "HIGHEST": "Critical",
    "URGENT": "Critical",
    "IMMEDIATE": "Critical",
    "HIGH": "High",
    "NORMAL": "Medium",
    "MEDIUM": "Medium",
    "LOW": "Low",
    "LOWEST": "Low",
}

IMPACT_MAP = {
    "CRITICAL": "High",
    "HIGH": "High",
    "MAJOR": "High",
    "BLOCKER": "High",
    "MEDIUM": "Medium",
    "NORMAL": "Medium",
    "MINOR": "Low",
    "LOW": "Low",
}

RESOLUTION_MAP = {
    "FIXED": "Fixed",
    "WONTFIX": "Won't Fix",
    "WONT_FIX": "Won't Fix",
    "INVALID": "Invalid",
    "DUPLICATE": "Duplicate",
    "WORKSFORME": "Works For Me",
    "WORKS_FOR_ME": "Works For Me",
    "MOVED": "Moved",
    "COMPLETE": "Fixed",
}


def _norm(value, mapping, default):
    if value is None:
        return default

    text = str(value).strip()

    if not text:
        return default

    return mapping.get(text.upper(), default)


def _pick(row, *keys, default=None):
    low = {key.lower(): value for key, value in row.items()}

    for key in keys:
        value = low.get(key.lower())

        if value not in (None, ""):
            return str(value).strip()

    return default


def _parse_date(value):
    if not value:
        return None

    text = str(value).strip()

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %I:%M %p",
    )

    for fmt in formats:
        try:
            return datetime.datetime.strptime(
                text[:19].replace("T", " "),
                fmt,
            )
        except ValueError:
            continue

    digits = re.sub(r"\D", "", text)[:10]

    if len(digits) == 10:
        try:
            return datetime.datetime.fromtimestamp(
                int(digits),
                tz=datetime.timezone.utc,
            ).replace(tzinfo=None)
        except (ValueError, OSError):
            pass

    return None


def _match_assignee(name, email, developers):
    """Match a dataset assignee to an existing developer."""

    if email:
        target = email.strip().lower()

        for developer in developers:
            if developer["email"].lower() == target:
                return developer["id"]

    if name:
        target = name.strip().lower()

        for developer in developers:
            developer_name = developer["name"].lower()

            if (
                target == developer_name
                or target in developer_name
                or developer_name in target
            ):
                return developer["id"]

    return None


def import_csv(path, wipe=False):
    """Import a CSV without deleting existing records by default."""

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset file not found: {path}"
        )

    with open(
        path,
        newline="",
        encoding="utf-8-sig",
    ) as file:
        raw = [
            dict(row)
            for row in csv.DictReader(file)
        ]

    if not raw:
        raise ValueError(
            "Dataset is empty (no data rows found)."
        )

    users = database.query(
        "SELECT id, name, email, role FROM users"
    )

    if not users:
        raise ValueError(
            "No users exist. Create users before importing."
        )

    creator = next(
        (
            user
            for user in users
            if user["role"] == "tester"
        ),
        users[0],
    )

    developers = [
        user
        for user in users
        if user["role"] == "developer"
    ]

    inserted = 0
    skipped = 0
    errors = []

    rng = random.Random(42)

    now = datetime.datetime.now(
        datetime.timezone.utc
    ).replace(tzinfo=None)

    if wipe:
        # Destructive operation: only enabled by explicit request.
        connection = database._connect()

        try:
            connection.execute("DELETE FROM comments")
            connection.execute("DELETE FROM bug_history")
            connection.execute("DELETE FROM bugs")
            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    for index, row in enumerate(raw):
        try:
            title = _pick(
                row,
                "short_desc",
                "title",
                "issue_title",
                "bug_title",
                "summary",
                "subject",
            )

            if not title:
                skipped += 1
                continue

            module = (
                _pick(
                    row,
                    "component",
                    "module",
                    "area",
                    "subsystem",
                )
                or _pick(row, "product", "project")
                or "Unspecified"
            )

            severity = _norm(
                _pick(
                    row,
                    "severity",
                    "bug_severity",
                    "issue_severity",
                ),
                SEV_MAP,
                "Medium",
            )

            priority = _norm(
                _pick(
                    row,
                    "priority",
                    "bug_priority",
                    "issue_priority",
                ),
                PRIO_MAP,
                None,
            )

            status = _norm(
                _pick(
                    row,
                    "status",
                    "bug_status",
                    "state",
                    "issue_status",
                ),
                STATUS_MAP,
                "reported",
            )

            impact = _norm(
                _pick(
                    row,
                    "impact",
                    "business_impact",
                ),
                IMPACT_MAP,
                None,
            )

            if impact is None:
                impact = priority_service.impact_for_severity(
                    severity
                )

            if priority is None:
                priority = priority_service.MATRIX[
                    severity
                ][impact]

            assigned_to = _match_assignee(
                _pick(
                    row,
                    "assigned_to_name",
                    "assigned_to",
                    "assignee",
                    "owner",
                    "developer",
                ),
                _pick(
                    row,
                    "assigned_to_email",
                    "assignee_email",
                    "developer_email",
                ),
                developers,
            )

            if (
                assigned_to is None
                and status in (
                    "assigned",
                    "in_progress",
                    "fixed",
                    "testing",
                )
                and developers
            ):
                assigned_to = developers[
                    index % len(developers)
                ]["id"]

            created = _parse_date(
                _pick(
                    row,
                    "creation_time",
                    "created_at",
                    "created",
                    "date_created",
                    "timestamp",
                    "opened_at",
                )
            )

            if created is None:
                created = now - datetime.timedelta(
                    days=baseline_days(index),
                    hours=rng.randint(0, 23),
                )

            created_string = created.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            resolution = _norm(
                _pick(
                    row,
                    "resolution",
                    "resolve_result",
                ),
                RESOLUTION_MAP,
                None,
            )

            description = _pick(
                row,
                "description",
                "issue_description",
                "long_desc",
                "body",
                "content",
                default=(
                    "No description provided in the source dataset."
                ),
            )

            steps = _pick(
                row,
                "steps_to_reproduce",
                "steps",
                "reproduction_steps",
                "repro_steps",
                default=(
                    "Steps to reproduce were not recorded "
                    "in the source dataset."
                ),
            )

            expected = _pick(
                row,
                "expected_result",
                "expected",
                default=(
                    "Expected behaviour is not documented "
                    "in the source dataset."
                ),
            )

            actual = _pick(
                row,
                "actual_result",
                "actual",
                default=(
                    "Actual behaviour is not documented "
                    "in the source dataset."
                ),
            )

            bug_id = database.execute(
                """
                INSERT INTO bugs (
                    title,
                    description,
                    module,
                    steps_to_reproduce,
                    expected_result,
                    actual_result,
                    severity,
                    impact,
                    recommended_priority,
                    priority,
                    status,
                    assigned_to,
                    created_by,
                    resolution,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title[:500],
                    description[:4000],
                    module[:120],
                    steps[:2000],
                    expected[:2000],
                    actual[:2000],
                    severity,
                    impact,
                    priority,
                    priority,
                    status,
                    assigned_to,
                    creator["id"],
                    resolution,
                    created_string,
                    created_string,
                ),
            )

            if bug_id is None:
                raise RuntimeError(
                    "Database did not return the new bug ID."
                )

            database.execute(
                """
                INSERT INTO bug_history (
                    bug_id,
                    user_id,
                    action,
                    old_value,
                    new_value,
                    note,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bug_id,
                    creator["id"],
                    "imported",
                    None,
                    status,
                    f"Imported from {os.path.basename(path)}",
                    created_string,
                ),
            )

            inserted += 1

        except Exception as exc:
            skipped += 1

            if len(errors) < 10:
                errors.append({
                    "row": index + 1,
                    "error": str(exc),
                })

    return {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "source": os.path.basename(path),
    }


def baseline_days(index):
    """Deterministic pseudo-age between 1 and 70 days."""
    return 1 + (index * 7 % 70)


def import_sample_csv():
    """Import the bundled sample dataset without deleting existing bugs."""
    return import_csv(DEFAULT_KAGGLE_CSV)
