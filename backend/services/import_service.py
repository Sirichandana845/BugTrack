"""Kaggle dataset import pipeline.

    Kaggle CSV -> cleaning & field mapping -> SQLite -> BugTrack dashboard

Supported source formats: Bugzilla (e.g. the Kaggle "Bugzilla Bug Reports"
and "Software bugs reports / Eclipse" datasets), JIRA exports, or any CSV with
similar columns. Missing fields receive documented, reasonable defaults
(shown on the Reports page and in the README).
"""
import csv
import datetime
import os
import random
import re

from config import DEFAULT_KAGGLE_CSV
from database import db as database
from services import priority_service

# ---------------- column-value normalisation maps (upper-case keys) -------
STATUS_MAP = {
    "NEW": "reported", "OPEN": "reported", "CONFIRMED": "reported", "UNCONFIRMED": "reported",
    "ASSIGNED": "assigned", "IN_PROGRESS": "in_progress", "STARTED": "in_progress", "TODO": "reported",
    "FIXED": "fixed", "RESOLVED": "fixed",
    "VERIFIED": "testing", "TESTING": "testing",
    "CLOSED": "closed",
    "REOPENED": "reopened", "REOPEN": "reopened",
}
SEV_MAP = {
    "BLOCKER": "Critical", "CRITICAL": "Critical", "CRASH": "Critical", "S1": "Critical",
    "HIGH": "High", "MAJOR": "High", "S2": "High",
    "NORMAL": "Medium", "MEDIUM": "Medium", "S3": "Medium",
    "MINOR": "Low", "LOW": "Low", "TRIVIAL": "Low", "ENHANCEMENT": "Low", "S4": "Low", "S5": "Low",
}
PRIO_MAP = {
    "P1": "Critical", "P2": "High", "P3": "Medium", "P4": "Low", "P5": "Low",
    "HIGHEST": "Critical", "URGENT": "Critical", "IMMEDIATE": "Critical",
    "HIGH": "High", "NORMAL": "Medium", "MEDIUM": "Medium", "LOW": "Low", "LOWEST": "Low",
}
IMPACT_MAP = {
    "CRITICAL": "High", "HIGH": "High", "MAJOR": "High", "BLOCKER": "High",
    "MEDIUM": "Medium", "NORMAL": "Medium", "MINOR": "Low", "LOW": "Low",
}
RESOLUTION_MAP = {
    "FIXED": "Fixed", "WONTFIX": "Won't Fix", "WONT_FIX": "Won't Fix",
    "INVALID": "Invalid", "DUPLICATE": "Duplicate", "WORKSFORME": "Works For Me",
    "WORKS_FOR_ME": "Works For Me", "MOVED": "Moved", "COMPLETE": "Fixed",
}


def _norm(value, mapping, default):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return mapping.get(text.upper(), default)


def _pick(row, *keys, default=None):
    low = {k.lower(): v for k, v in row.items()}
    for key in keys:
        value = low.get(key.lower())
        if value not in (None, ""):
            return str(value).strip()
    return default


def _parse_date(value):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%m/%d/%Y %I:%M %p"):
        try:
            return datetime.datetime.strptime(text[:19].replace("T", " "), fmt)
        except ValueError:
            continue
    digits = re.sub(r"\D", "", text)[:10]
    if len(digits) == 10:
        try:
            return datetime.datetime.fromtimestamp(int(digits))
        except (ValueError, OSError):
            pass
    return None


def _match_assignee(name, email, developers):
    """Match a dataset assignee to one of our seeded developer accounts."""
    if email:
        target = email.strip().lower()
        for dev in developers:
            if dev["email"].lower() == target:
                return dev["id"]
    if name:
        target = name.strip().lower()
        for dev in developers:
            if target == dev["name"].lower() or target in dev["name"].lower() or dev["name"].lower() in target:
                return dev["id"]
    return None


def import_csv(path, wipe=True):
    """Clean + map + insert a Kaggle-style CSV. Returns a summary dict."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset file not found: {path}")

    with open(path, newline="", encoding="utf-8-sig") as fh:
        raw = [dict(row) for row in csv.DictReader(fh)]
    if not raw:
        raise ValueError("Dataset is empty (no data rows found).")

    users = database.query("SELECT id, name, email, role FROM users")
    creator = next((u for u in users if u["role"] == "tester"), users[0])
    developers = [u for u in users if u["role"] == "developer"]

    conn = database._connect()
    inserted = skipped = 0
    rng = random.Random(42)  # deterministic fallback dates/round-robin
    now = datetime.datetime.utcnow()
    try:
        if wipe:  # replace existing bug data with the dataset (idempotent demo)
            conn.execute("DELETE FROM comments")
            conn.execute("DELETE FROM bug_history")
            conn.execute("DELETE FROM bugs")

        for i, row in enumerate(raw):
            try:
                title = _pick(row, "short_desc", "title", "issue_title", "bug_title", "summary", "subject")
                if not title:
                    skipped += 1
                    continue

                module = (
                    _pick(row, "component", "module", "area", "subsystem")
                    or _pick(row, "product", "project")
                    or "Unspecified"
                )
                severity = _norm(_pick(row, "severity", "bug_severity", "issue_severity"), SEV_MAP, "Medium")
                priority = _norm(_pick(row, "priority", "bug_priority", "issue_priority"), PRIO_MAP, None)

                status = _norm(
                    _pick(row, "status", "bug_status", "state", "issue_status"), STATUS_MAP, "reported"
                )
                impact = _norm(_pick(row, "impact", "business_impact"), IMPACT_MAP, None)
                if impact is None:  # documented default: derive from severity
                    impact = priority_service.impact_for_severity(severity)
                if priority is None:  # documented default: derive via recommender
                    priority = priority_service.MATRIX[severity][impact]

                assigned_to = _match_assignee(
                    _pick(row, "assigned_to_name", "assigned_to", "assignee", "owner", "developer"),
                    _pick(row, "assigned_to_email", "assignee_email", "developer_email"),
                    developers,
                )
                if assigned_to is None and status in ("assigned", "in_progress", "fixed", "testing") and developers:
                    assigned_to = developers[i % len(developers)]["id"]  # documented default

                created = _parse_date(
                    _pick(row, "creation_time", "created_at", "created", "date_created", "timestamp", "opened_at")
                )
                if created is None:
                    created = now - datetime.timedelta(days=baseline_days(i), hours=rng.randint(0, 23))
                created_str = created.strftime("%Y-%m-%d %H:%M:%S")

                resolution = _norm(_pick(row, "resolution", "resolve_result"), RESOLUTION_MAP, None)
                description = _pick(
                    row, "description", "issue_description", "long_desc", "body", "content",
                    default="No description provided in the source dataset.",
                )
                steps = _pick(
                    row, "steps_to_reproduce", "steps", "reproduction_steps", "repro_steps",
                    default="Steps to reproduce were not recorded in the source dataset.",
                )
                expected = _pick(
                    row, "expected_result", "expected",
                    default="Expected behaviour is not documented in the source dataset.",
                )
                actual = _pick(
                    row, "actual_result", "actual",
                    default="Actual behaviour is not documented in the source dataset.",
                )

                cur = conn.execute(
                    """INSERT INTO bugs (title, description, module, steps_to_reproduce,
                                          expected_result, actual_result, severity, impact,
                                          recommended_priority, priority, status, assigned_to,
                                          created_by, resolution, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        title[:500], description[:4000], module[:120], steps[:2000],
                        expected[:2000], actual[:2000], severity, impact,
                        priority, priority, status, assigned_to, creator["id"],
                        resolution, created_str, created_str,
                    ),
                )
                conn.execute(
                    """INSERT INTO bug_history (bug_id, user_id, action, old_value, new_value, note, timestamp)
                       VALUES (?,?,?,?,?,?,?)""",
                    (cur.lastrowid, creator["id"], "imported", None, status,
                     f"Imported from {os.path.basename(path)}", created_str),
                )
                inserted += 1
            except Exception:
                skipped += 1
        conn.commit()
    finally:
        conn.close()

    return {"inserted": inserted, "skipped": skipped, "source": os.path.basename(path)}


def baseline_days(index):
    """Deterministic pseudo-age between 1 and 70 days."""
    return 1 + (index * 7 % 70)


def import_sample_csv():
    """Import the bundled sample dataset (dataset/kaggle_bugs.csv)."""
    return import_csv(DEFAULT_KAGGLE_CSV)
