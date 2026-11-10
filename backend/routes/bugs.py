"""Bug routes: list/create/read/update + lifecycle actions + notifications.

All search & filtering is executed by SQL on the backend
(/api/bugs?search=&status=&priority=&severity=&developer=&reporter=&module=&sort=&order=),
never by hiding rows in the frontend.
"""
import base64
import mimetypes
import os
import uuid

from flask import Blueprint, jsonify, request

from config import UPLOAD_DIR
from database import db as database
from database.db import query, add_notification, notify_users, notify_roles
from models import PRIORITIES, SEVERITIES, STATUS_LABELS, STATUSES
from services import lifecycle, priority_service
from services.lifecycle import allowed_next
from utils.auth import login_required, roles_required
from utils.validation import one_of

bugs_bp = Blueprint("bugs", __name__)

SELECT_BUG = """
    SELECT b.*, u.name AS assigned_name, c.name AS creator_name, c.email AS creator_email
    FROM bugs b
    LEFT JOIN users u ON b.assigned_to = u.id
    LEFT JOIN users c ON b.created_by = c.id
"""


def serialize_bug(row, include_next=False, viewer=None):
    d = dict(row)
    d["status_label"] = STATUS_LABELS.get(d["status"], d["status"])
    d["attachment_url"] = f"/api/uploads/{d['attachment']}" if d.get("attachment") else None
    if include_next and viewer is not None:
        d["allowed_next"] = allowed_next(
            viewer["role"], d["status"], d["assigned_to"], viewer["id"], d.get("created_by")
        )
    return d


def save_attachment(data_url):
    """Save a base64 data-URL screenshot/video to uploads/, return stored filename."""
    if not data_url:
        return None
    raw = None
    ext = ".png"
    if data_url.startswith("data:"):
        meta, _, b64 = data_url.partition(",")
        mime = meta.split(";")[0].split(":", 1)[-1]
        ext = mimetypes.guess_extension(mime) or ".png"
        raw = base64.b64decode(b64)
    else:
        raw = base64.b64decode(data_url)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Attachment is too large (max 8 MB).")
    fname = uuid.uuid4().hex + ext
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(os.path.join(UPLOAD_DIR, fname), "wb") as fh:
        fh.write(raw)
    return fname


def get_bug_or_404(bug_id):
    bug = query(SELECT_BUG + " WHERE b.id = ?", (bug_id,), one=True)
    if bug is None:
        return None
    return bug


# ---------------------------------------------------------------------------
# GET /api/bugs  (search + multi-filter + sorting, executed server-side)
# ---------------------------------------------------------------------------
@bugs_bp.get("/bugs")
@login_required
def list_bugs(user):
    params = request.args
    where, args = [], []

    q = (params.get("search") or "").strip()
    if q:
        like = f"%{q}%"
        where.append("(b.title LIKE ? OR b.module LIKE ? OR b.description LIKE ? OR CAST(b.id AS TEXT) = ?)")
        args += [like, like, like, q]

    if params.get("status"):
        one_of(params["status"], STATUSES, "status")
        where.append("b.status = ?")
        args.append(params["status"])

    if params.get("priority"):
        one_of(params["priority"], PRIORITIES, "priority")
        where.append("b.priority = ?")
        args.append(params["priority"])

    if params.get("severity"):
        one_of(params["severity"], SEVERITIES, "severity")
        where.append("b.severity = ?")
        args.append(params["severity"])

    if params.get("module"):
        where.append("b.module = ?")
        args.append(params["module"])

    if params.get("developer"):
        where.append("b.assigned_to = ?")
        args.append(int(params["developer"]))

    if params.get("assigned") == "me":
        where.append("b.assigned_to = ?")
        args.append(user["id"])

    if params.get("reporter") == "me":
        where.append("b.created_by = ?")
        args.append(user["id"])
    elif params.get("reporter"):
        where.append("b.created_by = ?")
        args.append(int(params["reporter"]))

    # Date filter: e.g. from_date=2026-11-01
    if params.get("from_date"):
        where.append("date(b.created_at) >= date(?)")
        args.append(params["from_date"])
    if params.get("to_date"):
        where.append("date(b.created_at) <= date(?)")
        args.append(params["to_date"])

    cond = (" WHERE " + " AND ".join(where)) if where else ""
    total = query(f"SELECT COUNT(*) AS c FROM bugs b{cond}", args, one=True)["c"]

    # Sorting
    sort_by = params.get("sort", "created_at")
    allowed_sorts = {
        "id": "b.id",
        "created_at": "b.created_at",
        "updated_at": "b.updated_at",
        "priority": "CASE b.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 ELSE 5 END",
        "status": "b.status",
        "title": "b.title",
    }
    col = allowed_sorts.get(sort_by, "b.created_at")
    direction = "ASC" if params.get("order", "desc").lower() == "asc" else "DESC"

    rows = query(
        f"{SELECT_BUG} {cond} ORDER BY {col} {direction}, b.id DESC LIMIT 300",
        args,
    )
    return jsonify({
        "total": total,
        "bugs": [serialize_bug(r, include_next=True, viewer=user) for r in rows],
    })


# ---------------------------------------------------------------------------
# POST /api/bugs  (report a bug -> automatic priority recommendation + notify)
# ---------------------------------------------------------------------------
@bugs_bp.post("/bugs")
@login_required
def create_bug(user):
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Bug title is required."}), 400

    try:
        rec = priority_service.recommend(data.get("severity"), data.get("impact"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        attachment = save_attachment(data.get("attachment"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    operating_system = (data.get("operating_system") or "")[:80]
    browser_device = (data.get("browser_device") or "")[:80]
    app_version = (data.get("app_version") or "")[:40]

    bug_id = database.execute(
        """INSERT INTO bugs (title, description, module, steps_to_reproduce,
                             expected_result, actual_result, severity, impact,
                             recommended_priority, priority, status, created_by,
                             attachment, operating_system, browser_device, app_version)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            title[:500],
            (data.get("description") or "")[:4000],
            (data.get("module") or "Unspecified")[:120],
            (data.get("steps_to_reproduce") or "")[:2000],
            (data.get("expected_result") or "")[:2000],
            (data.get("actual_result") or "")[:2000],
            rec["severity"], rec["impact"],
            rec["recommended_priority"], rec["recommended_priority"],
            "reported", user["id"], attachment,
            operating_system, browser_device, app_version,
        ),
    )

    database.execute(
        """INSERT INTO bug_history (bug_id, user_id, action, note) VALUES (?,?,?,?)""",
        (bug_id, user["id"], "reported", f"Bug reported by {user['name']} ({user['role']})"),
    )

    # Real-time notification: When a reporter creates a bug, notify the admin.
    notify_roles(
        ["admin"],
        "New Bug Reported",
        f"Bug #{bug_id} '{title[:60]}' reported by {user['name']}.",
        bug_id=bug_id,
        notif_type="warning",
        exclude_user_id=user["id"],
    )

    bug = get_bug_or_404(bug_id)
    return jsonify({"bug": serialize_bug(bug, include_next=True, viewer=user), "recommendation": rec}), 201


# ---------------------------------------------------------------------------
# POST /api/priority-recommend  (live preview of the recommendation)
# ---------------------------------------------------------------------------
@bugs_bp.post("/priority-recommend")
@login_required
def recommend_priority(_user):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(priority_service.recommend(data.get("severity"), data.get("impact")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


# ---------------------------------------------------------------------------
# GET /api/bugs/<id>
# ---------------------------------------------------------------------------
@bugs_bp.get("/bugs/<int:bug_id>")
@login_required
def get_bug(user, bug_id):
    bug = get_bug_or_404(bug_id)
    if bug is None:
        return jsonify({"error": "Bug not found."}), 404
    comments = query(
        """SELECT c.*, u.name AS user_name, u.role AS user_role
           FROM comments c
           LEFT JOIN users u ON c.user_id = u.id
           WHERE c.bug_id = ? ORDER BY c.created_at ASC""",
        (bug_id,),
    )
    return jsonify({
        "bug": serialize_bug(bug, include_next=True, viewer=user),
        "comments": [dict(c) for c in comments],
    })


# ---------------------------------------------------------------------------
# PUT /api/bugs/<id>  (edit fields; admin may override the priority)
# ---------------------------------------------------------------------------
@bugs_bp.put("/bugs/<int:bug_id>")
@roles_required("admin")
def update_bug(user, bug_id):
    bug = get_bug_or_404(bug_id)
    if bug is None:
        return jsonify({"error": "Bug not found."}), 404
    data = request.get_json(silent=True) or {}

    rec = priority_service.recommend(
        data.get("severity", bug["severity"]), data.get("impact", bug["impact"])
    )
    database.execute(
        "UPDATE bugs SET recommended_priority = ? WHERE id = ?",
        (rec["recommended_priority"], bug_id),
    )
    if "priority" in data and data["priority"]:
        one_of(data["priority"], PRIORITIES, "priority")
        if data["priority"] != bug["priority"]:
            database.execute(
                """INSERT INTO bug_history (bug_id, user_id, action, old_value, new_value)
                   VALUES (?,?,?,?,?)""",
                (bug_id, user["id"], "priority_change", bug["priority"] or "Unset", data["priority"]),
            )
            # Notify assigned developer
            if bug["assigned_to"]:
                add_notification(
                    bug["assigned_to"],
                    "Priority Changed",
                    f"Bug #{bug_id} priority changed to {data['priority']} by Admin.",
                    bug_id=bug_id,
                    notif_type="info",
                )
        database.execute("UPDATE bugs SET priority = ? WHERE id = ?", (data["priority"], bug_id))

    database.execute(
        """UPDATE bugs SET title=?, description=?, module=?, steps_to_reproduce=?,
           expected_result=?, actual_result=?, severity=?, impact=?,
           operating_system=?, browser_device=?, app_version=?, updated_at=datetime('now')
           WHERE id=?""",
        (
            (data.get("title") or bug["title"])[:500],
            (data.get("description", bug["description"] or ""))[:4000],
            (data.get("module", bug["module"] or "Unspecified"))[:120],
            (data.get("steps_to_reproduce", bug["steps_to_reproduce"] or ""))[:2000],
            (data.get("expected_result", bug["expected_result"] or ""))[:2000],
            (data.get("actual_result", bug["actual_result"] or ""))[:2000],
            rec["severity"], rec["impact"],
            (data.get("operating_system", bug["operating_system"] or ""))[:80],
            (data.get("browser_device", bug["browser_device"] or ""))[:80],
            (data.get("app_version", bug["app_version"] or ""))[:40],
            bug_id,
        ),
    )
    updated = get_bug_or_404(bug_id)
    return jsonify({"bug": serialize_bug(updated, include_next=True, viewer=user), "recommendation": rec})


# ---------------------------------------------------------------------------
# PUT /api/bugs/<id>/status  (lifecycle state machine + notifications)
# ---------------------------------------------------------------------------
@bugs_bp.put("/bugs/<int:bug_id>/status")
@login_required
def change_status(user, bug_id):
    bug = get_bug_or_404(bug_id)
    if bug is None:
        return jsonify({"error": "Bug not found."}), 404
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required."}), 400

    ok, message = lifecycle.validate_transition(
        user["role"], bug["status"], new_status, bug["assigned_to"], user["id"], bug["created_by"]
    )
    if not ok:
        return jsonify({"error": message}), 400

    note = (data.get("note") or "").strip()
    fix_description = (data.get("fix_description") or "").strip()

    # If developer marks fixed, require or store fix_description
    if new_status == "fixed" and fix_description:
        database.execute(
            "UPDATE bugs SET fix_description = ? WHERE id = ?",
            (fix_description[:4000], bug_id)
        )
        if not note:
            note = f"Fix description: {fix_description}"

    database.execute(
        """UPDATE bugs SET status=?, updated_at=datetime('now') WHERE id=?""",
        (new_status, bug_id),
    )
    database.execute(
        """INSERT INTO bug_history (bug_id, user_id, action, old_value, new_value, note)
           VALUES (?,?,?,?,?,?)""",
        (bug_id, user["id"], "status_change", bug["status"], new_status, note or None),
    )

    # ------------------ Real-time Notifications on Status Changes ------------------
    # 1. Developer fixes a bug -> notify reporter and tester
    if new_status == "fixed":
        if bug["created_by"] and bug["created_by"] != user["id"]:
            add_notification(
                bug["created_by"],
                "Bug Fixed",
                f"Your reported bug #{bug_id} '{bug['title']}' has been marked as Fixed.",
                bug_id=bug_id,
                notif_type="success",
            )
        notify_roles(
            ["tester"],
            "Bug Awaiting Testing",
            f"Bug #{bug_id} '{bug['title']}' was marked as Fixed and is ready for testing.",
            bug_id=bug_id,
            notif_type="info",
            exclude_user_id=user["id"],
        )

    # 2. Tester reopens a bug -> notify developer and admin
    elif new_status == "reopened":
        if bug["assigned_to"] and bug["assigned_to"] != user["id"]:
            add_notification(
                bug["assigned_to"],
                "Bug Reopened",
                f"Bug #{bug_id} '{bug['title']}' was reopened by {user['name']}. Note: {note or 'Requires rework'}",
                bug_id=bug_id,
                notif_type="danger",
            )
        notify_roles(
            ["admin"],
            "Bug Reopened",
            f"Bug #{bug_id} '{bug['title']}' was reopened by {user['name']}.",
            bug_id=bug_id,
            notif_type="warning",
            exclude_user_id=user["id"],
        )

    # 3. Bug verified or closed -> notify reporter
    elif new_status in ("verified", "closed"):
        if bug["created_by"] and bug["created_by"] != user["id"]:
            add_notification(
                bug["created_by"],
                f"Bug {STATUS_LABELS.get(new_status, new_status)}",
                f"Your bug report #{bug_id} '{bug['title']}' is now {STATUS_LABELS.get(new_status, new_status)}.",
                bug_id=bug_id,
                notif_type="success",
            )

    # 4. General status update -> notify reporter if not actor
    elif bug["created_by"] and bug["created_by"] != user["id"]:
        add_notification(
            bug["created_by"],
            "Bug Status Updated",
            f"Bug #{bug_id} status changed from {STATUS_LABELS.get(bug['status'], bug['status'])} to {STATUS_LABELS.get(new_status, new_status)}.",
            bug_id=bug_id,
            notif_type="info",
        )

    updated = get_bug_or_404(bug_id)
    return jsonify({"bug": serialize_bug(updated, include_next=True, viewer=user)})


# ---------------------------------------------------------------------------
# PUT /api/bugs/<id>/fix  (developer records fix details & marks fixed)
# ---------------------------------------------------------------------------
@bugs_bp.put("/bugs/<int:bug_id>/fix")
@roles_required("admin", "developer")
def mark_fixed(user, bug_id):
    bug = get_bug_or_404(bug_id)
    if bug is None:
        return jsonify({"error": "Bug not found."}), 404
    if user["role"] == "developer" and bug["assigned_to"] != user["id"]:
        return jsonify({"error": "You can only fix bugs assigned to you."}), 403

    data = request.get_json(silent=True) or {}
    fix_description = (data.get("fix_description") or "").strip()
    if not fix_description:
        return jsonify({"error": "Fix description is required."}), 400

    database.execute(
        """UPDATE bugs SET status='fixed', fix_description=?, updated_at=datetime('now') WHERE id=?""",
        (fix_description[:4000], bug_id),
    )
    database.execute(
        """INSERT INTO bug_history (bug_id, user_id, action, old_value, new_value, note)
           VALUES (?,?,?,?,?,?)""",
        (bug_id, user["id"], "fixed", bug["status"], "fixed", f"Fix: {fix_description[:300]}"),
    )

    # Notifications
    if bug["created_by"]:
        add_notification(
            bug["created_by"],
            "Bug Fixed",
            f"Your bug #{bug_id} '{bug['title']}' was marked as Fixed by {user['name']}.",
            bug_id=bug_id,
            notif_type="success",
        )
    notify_roles(
        ["tester"],
        "Bug Ready For Testing",
        f"Bug #{bug_id} was marked as Fixed and is ready for verification.",
        bug_id=bug_id,
        notif_type="info",
    )

    updated = get_bug_or_404(bug_id)
    return jsonify({"bug": serialize_bug(updated, include_next=True, viewer=user)})


# ---------------------------------------------------------------------------
# PUT /api/bugs/<id>/assign  (admin assigns a developer -> notify developer)
# ---------------------------------------------------------------------------
@bugs_bp.put("/bugs/<int:bug_id>/assign")
@roles_required("admin")
def assign_bug(user, bug_id):
    bug = get_bug_or_404(bug_id)
    if bug is None:
        return jsonify({"error": "Bug not found."}), 404
    data = request.get_json(silent=True) or {}
    developer_id = data.get("developer_id")

    if developer_id is None:  # unassign
        database.execute("UPDATE bugs SET assigned_to = NULL, updated_at=datetime('now') WHERE id=?", (bug_id,))
        database.execute(
            "INSERT INTO bug_history (bug_id, user_id, action, old_value, new_value) VALUES (?,?,?,?,?)",
            (bug_id, user["id"], "unassigned", bug["assigned_name"] or "Unassigned", None),
        )
        updated = get_bug_or_404(bug_id)
        return jsonify({"bug": serialize_bug(updated, include_next=True, viewer=user)})

    dev = query("SELECT * FROM users WHERE id = ? AND role = 'developer'", (developer_id,), one=True)
    if dev is None:
        return jsonify({"error": "Developer not found. Choose a user with role 'developer'."}), 400

    database.execute("UPDATE bugs SET assigned_to = ?, updated_at=datetime('now') WHERE id=?", (developer_id, bug_id))
    database.execute(
        "INSERT INTO bug_history (bug_id, user_id, action, old_value, new_value) VALUES (?,?,?,?,?)",
        (bug_id, user["id"], "assigned", bug["assigned_name"] or "Unassigned", dev["name"]),
    )

    # First assignment moves the lifecycle: reported -> assigned
    if bug["status"] in ("reported", "triaged"):
        database.execute("UPDATE bugs SET status='assigned', updated_at=datetime('now') WHERE id=?", (bug_id,))
        database.execute(
            """INSERT INTO bug_history (bug_id, user_id, action, old_value, new_value)
               VALUES (?,?,?,?,?)""",
            (bug_id, user["id"], "status_change", bug["status"], "assigned"),
        )

    # Real-time notification: When an admin assigns a bug, notify the developer.
    add_notification(
        developer_id,
        "New Bug Assigned",
        f"Admin assigned you bug #{bug_id} '{bug['title']}'.",
        bug_id=bug_id,
        notif_type="info",
    )

    # Also notify reporter that work is assigned
    if bug["created_by"]:
        add_notification(
            bug["created_by"],
            "Bug Assigned to Developer",
            f"Your reported bug #{bug_id} was assigned to developer {dev['name']}.",
            bug_id=bug_id,
            notif_type="info",
        )

    updated = get_bug_or_404(bug_id)
    return jsonify({"bug": serialize_bug(updated, include_next=True, viewer=user)})


# ---------------------------------------------------------------------------
# POST /api/bugs/<id>/comments
# ---------------------------------------------------------------------------
@bugs_bp.post("/bugs/<int:bug_id>/comments")
@login_required
def add_comment(user, bug_id):
    bug = get_bug_or_404(bug_id)
    if bug is None:
        return jsonify({"error": "Bug not found."}), 404
    data = request.get_json(silent=True) or {}
    comment = (data.get("comment") or "").strip()
    if not comment:
        return jsonify({"error": "Comment cannot be empty."}), 400

    comment_id = database.execute(
        "INSERT INTO comments (bug_id, user_id, comment) VALUES (?,?,?)",
        (bug_id, user["id"], comment[:2000]),
    )
    database.execute(
        "INSERT INTO bug_history (bug_id, user_id, action, note) VALUES (?,?,?,?)",
        (bug_id, user["id"], "comment", f"{user['name']} ({user['role']}) added a comment: {comment[:160]}"),
    )

    # Notify stakeholders
    stakeholders = {bug["assigned_to"], bug["created_by"]} - {None, user["id"]}
    for uid in stakeholders:
        add_notification(
            uid,
            "New Comment on Bug",
            f"{user['name']} commented on bug #{bug_id}: \"{comment[:80]}...\"",
            bug_id=bug_id,
            notif_type="info",
        )

    row = query(
        """SELECT c.*, u.name AS user_name, u.role AS user_role
           FROM comments c
           LEFT JOIN users u ON c.user_id = u.id WHERE c.id = ?""",
        (comment_id,),
        one=True,
    )
    return jsonify({"comment": dict(row)}), 201


# ---------------------------------------------------------------------------
# GET /api/bugs/<id>/history  (audit trail)
# ---------------------------------------------------------------------------
@bugs_bp.get("/bugs/<int:bug_id>/history")
@login_required
def get_history(_user, bug_id):
    if get_bug_or_404(bug_id) is None:
        return jsonify({"error": "Bug not found."}), 404
    rows = query(
        """SELECT h.*, u.name AS user_name, u.role AS user_role
           FROM bug_history h
           LEFT JOIN users u ON h.user_id = u.id
           WHERE h.bug_id = ? ORDER BY h.timestamp ASC, h.id ASC""",
        (bug_id,),
    )
    return jsonify({"history": [dict(r) for r in rows]})
