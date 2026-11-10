
"""Dashboard statistics - computed dynamically for each role from the live database."""

from flask import Blueprint, jsonify

from database.db import query
from models import STATUS_LABELS
from utils.auth import login_required


dashboard_bp = Blueprint("dashboard", __name__)


def count(sql, args=()):
    """Return a count compatible with SQLite and PostgreSQL."""
    res = query(sql, args, one=True)
    return res["count"] if res else 0


def _grouped(sql, args=(), label=None):
    rows = query(sql, args)
    result = []

    for r in rows:
        key = r["key"] or "Unset"

        result.append({
            "key": label(key) if label else key,
            "value": r["value"]
        })

    return result


@dashboard_bp.get("/dashboard")
@login_required
def dashboard(user):
    role = user["role"]
    uid = user["id"]

    # 1. Admin Metrics
    admin_counts = {
        "total_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs"
        ),

        "open_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE status NOT IN ('closed', 'rejected')"
        ),

        "in_progress_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE status = 'in_progress'"
        ),

        "resolved_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE status IN ('fixed', 'testing', 'verified')"
        ),

        "closed_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE status = 'closed'"
        ),

        "critical_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE severity = 'Critical' "
            "AND status NOT IN ('closed', 'rejected')"
        ),

        "reopened_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE status = 'reopened'"
        ),

        "unassigned_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE assigned_to IS NULL "
            "AND status NOT IN ('closed', 'rejected')"
        ),
    }

    # 2. Developer Metrics
    developer_counts = {
        "assigned_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE assigned_to = ?",
            (uid,)
        ),

        "pending_tasks": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE assigned_to = ? AND status = 'assigned'",
            (uid,)
        ),

        "in_progress_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE assigned_to = ? AND status = 'in_progress'",
            (uid,)
        ),

        "fixed_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE assigned_to = ? AND status = 'fixed'",
            (uid,)
        ),

        "critical_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE assigned_to = ? "
            "AND severity = 'Critical' "
            "AND status NOT IN ('closed', 'rejected')",
            (uid,)
        ),
    }

    # 3. Tester Metrics
    tester_counts = {
        "awaiting_verification": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE status IN ('fixed', 'testing')"
        ),

        "verified_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE status = 'verified'"
        ),

        "reopened_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE status = 'reopened'"
        ),

        "testing_history": count(
            """
            SELECT COUNT(DISTINCT bug_id) AS count
            FROM bug_history
            WHERE user_id = ?
            AND action IN ('status_change', 'comment')
            """,
            (uid,)
        ),
    }

    # 4. Reporter Metrics
    reporter_counts = {
        "my_reported_bugs": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE created_by = ?",
            (uid,)
        ),

        "pending_reports": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE created_by = ? "
            "AND status IN ('reported', 'triaged')",
            (uid,)
        ),

        "under_investigation": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE created_by = ? "
            "AND status IN ('assigned', 'in_progress')",
            (uid,)
        ),

        "resolved_reports": count(
            "SELECT COUNT(*) AS count FROM bugs "
            "WHERE created_by = ? "
            "AND status IN ('fixed', 'testing', 'verified', 'closed')",
            (uid,)
        ),
    }

    # Grouped breakdowns
    by_status = _grouped(
        """
        SELECT status AS key, COUNT(*) AS value
        FROM bugs
        GROUP BY status
        ORDER BY value DESC
        """,
        label=lambda k: STATUS_LABELS.get(k, k)
    )

    by_priority = _grouped(
        """
        SELECT priority AS key, COUNT(*) AS value
        FROM bugs
        GROUP BY priority
        ORDER BY value DESC
        """
    )

    by_severity = _grouped(
        """
        SELECT severity AS key, COUNT(*) AS value
        FROM bugs
        GROUP BY severity
        ORDER BY value DESC
        """
    )

    by_module = _grouped(
        """
        SELECT COALESCE(module, 'Unspecified') AS key,
               COUNT(*) AS value
        FROM bugs
        GROUP BY key
        ORDER BY value DESC
        LIMIT 8
        """
    )

    by_developer = _grouped(
        """
        SELECT COALESCE(u.name, 'Unassigned') AS key,
               COUNT(*) AS value
        FROM bugs b
        LEFT JOIN users u ON b.assigned_to = u.id
        GROUP BY key
        ORDER BY value DESC
        LIMIT 8
        """
    )

    # Developer workload table for Admin
    developer_workload = query(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            COUNT(b.id) AS total_assigned,

            SUM(
                CASE WHEN b.status = 'in_progress'
                THEN 1 ELSE 0 END
            ) AS in_progress,

            SUM(
                CASE WHEN b.status = 'fixed'
                THEN 1 ELSE 0 END
            ) AS fixed,

            SUM(
                CASE
                    WHEN b.severity = 'Critical'
                    AND b.status NOT IN ('closed', 'rejected')
                    THEN 1 ELSE 0
                END
            ) AS critical

        FROM users u
        LEFT JOIN bugs b ON u.id = b.assigned_to
        WHERE u.role = 'developer'
        GROUP BY u.id, u.name, u.email
        ORDER BY total_assigned DESC
        """
    )

    # Role-tailored recent activity
    if role == "developer":
        recent = query(
            """
            SELECT
                b.id,
                b.title,
                b.module,
                b.severity,
                b.priority,
                b.status,
                u.name AS assigned_name,
                b.created_at,
                b.updated_at
            FROM bugs b
            LEFT JOIN users u ON b.assigned_to = u.id
            WHERE b.assigned_to = ?
            ORDER BY b.updated_at DESC
            LIMIT 8
            """,
            (uid,)
        )

    elif role == "reporter":
        recent = query(
            """
            SELECT
                b.id,
                b.title,
                b.module,
                b.severity,
                b.priority,
                b.status,
                u.name AS assigned_name,
                b.created_at,
                b.updated_at
            FROM bugs b
            LEFT JOIN users u ON b.assigned_to = u.id
            WHERE b.created_by = ?
            ORDER BY b.updated_at DESC
            LIMIT 8
            """,
            (uid,)
        )

    elif role == "tester":
        recent = query(
            """
            SELECT
                b.id,
                b.title,
                b.module,
                b.severity,
                b.priority,
                b.status,
                u.name AS assigned_name,
                b.created_at,
                b.updated_at
            FROM bugs b
            LEFT JOIN users u ON b.assigned_to = u.id
            WHERE b.status IN (
                'fixed',
                'testing',
                'verified',
                'reopened'
            )
            ORDER BY b.updated_at DESC
            LIMIT 8
            """
        )

    else:
        # Admin
        recent = query(
            """
            SELECT
                b.id,
                b.title,
                b.module,
                b.severity,
                b.priority,
                b.status,
                u.name AS assigned_name,
                b.created_at,
                b.updated_at
            FROM bugs b
            LEFT JOIN users u ON b.assigned_to = u.id
            ORDER BY b.created_at DESC, b.id DESC
            LIMIT 8
            """
        )

    # Active counts according to current viewer
    active_counts = {
        "admin": admin_counts,
        "developer": developer_counts,
        "tester": tester_counts,
        "reporter": reporter_counts,
    }.get(role, admin_counts)

    return jsonify({
        "role": role,

        "counts": active_counts,

        "all_counts": {
            "admin": admin_counts,
            "developer": developer_counts,
            "tester": tester_counts,
            "reporter": reporter_counts,
        },

        "by_status": by_status,
        "by_priority": by_priority,
        "by_severity": by_severity,
        "by_module": by_module,
        "by_developer": by_developer,

        "developer_workload": [
            dict(r) for r in developer_workload
        ],

        "recent": [
            dict(r) for r in recent
        ],
    })
