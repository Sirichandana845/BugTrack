
"""Reports route: aggregated analytics + CSV and PDF exports."""

import csv
import datetime
import io

from fpdf import FPDF
from flask import Blueprint, Response, jsonify

from database.db import query
from models import STATUS_LABELS
from utils.auth import login_required


reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/reports")
@login_required
def reports(_user):
    return jsonify({
        "total_bugs": query(
            "SELECT COUNT(*) AS c FROM bugs", one=True
        )["c"],

        "open_bugs": query(
            "SELECT COUNT(*) AS c FROM bugs "
            "WHERE status NOT IN ('closed', 'rejected')",
            one=True
        )["c"],

        "closed_bugs": query(
            "SELECT COUNT(*) AS c FROM bugs WHERE status = 'closed'",
            one=True
        )["c"],

        "unassigned": query(
            "SELECT COUNT(*) AS c FROM bugs "
            "WHERE assigned_to IS NULL "
            "AND status NOT IN ('closed', 'rejected')",
            one=True
        )["c"],

        "avg_days_open": avg_open_days(),
        "by_priority": grouped("priority"),
        "by_status": grouped(
            "status",
            label=lambda k: STATUS_LABELS.get(k, k)
        ),
        "by_severity": grouped("severity"),
        "by_module": grouped("module", top=10),
        "by_developer": grouped(
            "assigned_to",
            join_name=True,
            top=10
        ),
        "resolution_breakdown": grouped("resolution", top=8),
    })


@reports_bp.get("/reports/csv")
@login_required
def reports_csv(_user):
    rows = query(
        """
        SELECT
            b.id,
            b.title,
            b.module,
            b.severity,
            b.impact,
            b.priority,
            b.status,
            b.resolution,
            b.operating_system,
            b.browser_device,
            b.app_version,
            u.name AS assigned_to,
            c.name AS reported_by,
            b.created_at,
            b.updated_at
        FROM bugs b
        LEFT JOIN users u ON b.assigned_to = u.id
        LEFT JOIN users c ON b.created_by = c.id
        ORDER BY b.id DESC
        """
    )

    out = io.StringIO()
    writer = csv.writer(out)

    writer.writerow([
        "Bug ID",
        "Title",
        "Module",
        "Severity",
        "Impact",
        "Priority",
        "Status",
        "Resolution",
        "Operating System",
        "Browser/Device",
        "Version",
        "Assigned To",
        "Reported By",
        "Created At",
        "Updated At"
    ])

    for r in rows:
        writer.writerow([
            r["id"],
            r["title"],
            r["module"],
            r["severity"],
            r["impact"],
            r["priority"],
            STATUS_LABELS.get(r["status"], r["status"]),
            r["resolution"] or "",
            r["operating_system"] or "",
            r["browser_device"] or "",
            r["app_version"] or "",
            r["assigned_to"] or "Unassigned",
            r["reported_by"] or "Unknown",
            r["created_at"],
            r["updated_at"]
        ])

    csv_text = out.getvalue()

    return Response(
        csv_text,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=bugtrack_report.csv"
        },
    )


@reports_bp.get("/reports/pdf")
@login_required
def reports_pdf(_user):
    total = query(
        "SELECT COUNT(*) AS c FROM bugs", one=True
    )["c"]

    open_count = query(
        "SELECT COUNT(*) AS c FROM bugs "
        "WHERE status NOT IN ('closed', 'rejected')",
        one=True
    )["c"]

    closed_count = query(
        "SELECT COUNT(*) AS c FROM bugs WHERE status = 'closed'",
        one=True
    )["c"]

    critical_count = query(
        "SELECT COUNT(*) AS c FROM bugs "
        "WHERE severity = 'Critical' AND status != 'closed'",
        one=True
    )["c"]

    avg_days = avg_open_days()

    rows = query(
        """
        SELECT
            b.id,
            b.title,
            b.module,
            b.severity,
            b.priority,
            b.status,
            u.name AS assigned_to,
            b.created_at
        FROM bugs b
        LEFT JOIN users u ON b.assigned_to = u.id
        ORDER BY b.id DESC
        LIMIT 40
        """
    )

    pdf = FPDF(
        orientation="P",
        unit="mm",
        format="A4"
    )

    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(0, 0, 210, 28, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_xy(14, 8)

    pdf.cell(
        0,
        8,
        "BUGTRACK - EXECUTIVE BUG REPORT",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(14, 18)

    pdf.cell(
        0,
        6,
        (
            f"Generated on "
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} "
            f"| Official System Audit"
        ),
        new_x="LMARGIN",
        new_y="NEXT"
    )

    pdf.set_text_color(30, 41, 59)
    pdf.set_y(36)

    # Executive Summary
    pdf.set_font("Helvetica", "B", 13)

    pdf.cell(
        0,
        8,
        "1. Executive Summary KPIs",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    pdf.set_font("Helvetica", "", 10)

    col_w = 36
    row_h = 9

    metrics = [
        ("Total Bugs", str(total)),
        ("Open Bugs", str(open_count)),
        ("Closed Bugs", str(closed_count)),
        ("Critical Active", str(critical_count)),
        ("Avg Open (Days)", str(avg_days)),
    ]

    pdf.set_fill_color(241, 245, 249)

    for title, _ in metrics:
        pdf.cell(
            col_w,
            row_h,
            title,
            border=1,
            align="C",
            fill=True
        )

    pdf.ln(row_h)

    pdf.set_font("Helvetica", "B", 12)

    for _, val in metrics:
        pdf.cell(
            col_w,
            row_h,
            val,
            border=1,
            align="C"
        )

    pdf.ln(row_h + 8)

    # Recent Bug Registry
    pdf.set_font("Helvetica", "B", 13)

    pdf.cell(
        0,
        8,
        "2. Recent Bug Registry",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(79, 70, 229)
    pdf.set_text_color(255, 255, 255)

    headers = [
        ("ID", 14),
        ("Title", 66),
        ("Module", 32),
        ("Severity", 20),
        ("Priority", 20),
        ("Status", 30)
    ]

    for header, width in headers:
        pdf.cell(
            width,
            8,
            header,
            border=1,
            align="C",
            fill=True
        )

    pdf.ln(8)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(30, 41, 59)

    fill = False

    for r in rows:
        if fill:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)

        title = r["title"] or ""
        title_text = (
            title[:38] + ".."
            if len(title) > 40
            else title
        )

        module = r["module"] or "-"
        module_text = (
            module[:16] + ".."
            if len(module) > 18
            else module
        )

        severity = r["severity"] or "-"
        priority = r["priority"] or "-"

        status_label = STATUS_LABELS.get(
            r["status"],
            r["status"]
        )[:14]

        pdf.cell(
            14, 7, str(r["id"]),
            border=1, align="C", fill=True
        )

        pdf.cell(
            66, 7, title_text,
            border=1, fill=True
        )

        pdf.cell(
            32, 7, module_text,
            border=1, fill=True
        )

        pdf.cell(
            20, 7, severity,
            border=1, align="C", fill=True
        )

        pdf.cell(
            20, 7, priority,
            border=1, align="C", fill=True
        )

        pdf.cell(
            30, 7, status_label,
            border=1, align="C", fill=True
        )

        pdf.ln(7)
        fill = not fill

    pdf_bytes = bytes(pdf.output())

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition":
                "attachment; filename=bugtrack_report.pdf"
        },
    )


def grouped(column, label=None, top=None, join_name=False):
    if join_name:
        sql = f"""
            SELECT
                COALESCE(u.name, 'Unassigned') AS key,
                COUNT(*) AS value
            FROM bugs b
            LEFT JOIN users u ON b.{column} = u.id
            GROUP BY key
            ORDER BY value DESC
        """
    else:
        sql = f"""
            SELECT
                COALESCE({column}, 'Unset') AS key,
                COUNT(*) AS value
            FROM bugs
            GROUP BY key
            ORDER BY value DESC
        """

    if top:
        sql += f" LIMIT {int(top)}"

    rows = query(sql)

    return [
        {
            **dict(row),
            "key": label(row["key"]) if label else row["key"]
        }
        for row in rows
    ]


def avg_open_days():
    """
    Calculate average age of open bugs.

    Python datetime calculation works with both SQLite and PostgreSQL.
    """

    rows = query(
        """
        SELECT created_at
        FROM bugs
        WHERE status NOT IN ('closed', 'rejected')
        """
    )

    if not rows:
        return 0

    now = datetime.datetime.now()
    total_days = 0

    for row in rows:
        created = row["created_at"]

        if isinstance(created, str):
            created = datetime.datetime.fromisoformat(created)

        if created.tzinfo is not None:
            created = created.replace(tzinfo=None)

        total_days += (
            now - created
        ).total_seconds() / 86400

    return round(total_days / len(rows), 1)
