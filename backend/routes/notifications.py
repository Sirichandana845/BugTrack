"""Notifications endpoints and helpers."""
from flask import Blueprint, jsonify, request

from database.db import query, execute
from utils.auth import login_required

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.get("/notifications")
@login_required
def get_notifications(user):
    rows = query(
        """SELECT n.*, b.title AS bug_title
           FROM notifications n
           LEFT JOIN bugs b ON n.bug_id = b.id
           WHERE n.user_id = ?
           ORDER BY n.created_at DESC LIMIT 50""",
        (user["id"],)
    )
    unread_row = query(
        "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
        (user["id"],),
        one=True
    )
    return jsonify({
        "notifications": [dict(r) for r in rows],
        "unread_count": unread_row["c"] if unread_row else 0
    })


@notifications_bp.get("/notifications/unread-count")
@login_required
def get_unread_count(user):
    row = query(
        "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
        (user["id"],),
        one=True
    )
    return jsonify({"unread_count": row["c"] if row else 0})


@notifications_bp.put("/notifications/<int:notif_id>/read")
@login_required
def mark_as_read(user, notif_id):
    execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
        (notif_id, user["id"])
    )
    return jsonify({"ok": True})


@notifications_bp.put("/notifications/read-all")
@login_required
def mark_all_read(user):
    execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
        (user["id"],)
    )
    return jsonify({"ok": True})


@notifications_bp.delete("/notifications/<int:notif_id>")
@login_required
def delete_notification(user, notif_id):
    execute(
        "DELETE FROM notifications WHERE id = ? AND user_id = ?",
        (notif_id, user["id"])
    )
    return jsonify({"ok": True})
