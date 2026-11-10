"""User management (admin only)."""
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from database import db as database
from database.db import query
from models import ROLES
from utils.auth import login_required, roles_required
from utils.validation import one_of

users_bp = Blueprint("users", __name__)

USER_STATS = """
    SELECT u.id, u.name, u.email, u.role, u.created_at,
      (SELECT COUNT(*) FROM bugs b WHERE b.assigned_to = u.id)                    AS total_bugs,
      (SELECT COUNT(*) FROM bugs b WHERE b.assigned_to = u.id AND b.status != 'closed') AS open_bugs,
      (SELECT COUNT(*) FROM bugs b WHERE b.assigned_to = u.id AND b.status = 'closed')   AS resolved_bugs,
      (SELECT COUNT(*) FROM bugs b WHERE b.assigned_to = u.id
          AND b.severity = 'Critical' AND b.status != 'closed')                   AS critical_bugs,
      (SELECT COUNT(*) FROM bugs b WHERE b.created_by = u.id)                     AS reported_bugs
    FROM users u
"""


@users_bp.get("/developers")
@login_required
def list_developers(_user):
    """Drop-down list of developers for assign modals & filters (any logged-in role)."""
    rows = query("SELECT id, name, email FROM users WHERE role = 'developer' ORDER BY name")
    return jsonify({"developers": [dict(r) for r in rows]})


@users_bp.get("/users")
@roles_required("admin")
def list_users(_user):
    rows = query(USER_STATS + " ORDER BY u.role, u.name")
    return jsonify({"users": [dict(r) for r in rows]})


@users_bp.post("/users")
@roles_required("admin")
def create_user(_user):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role")
    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required."}), 400
    one_of(role, ROLES, "role")
    if query("SELECT id FROM users WHERE email = ?", (email,), one=True):
        return jsonify({"error": "A user with this email already exists."}), 400
    user_id = database.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
        (name, email, generate_password_hash(password), role),
    )
    row = query(USER_STATS + " WHERE u.id = ?", (user_id,), one=True)
    return jsonify({"user": dict(row)}), 201


@users_bp.put("/users/<int:user_id>")
@roles_required("admin")
def update_user(user, user_id):
    data = request.get_json(silent=True) or {}
    target = query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if target is None:
        return jsonify({"error": "User not found."}), 404

    name = (data.get("name") or target["name"]).strip()
    role = data.get("role") or target["role"]
    one_of(role, ROLES, "role")
    database.execute("UPDATE users SET name=?, role=? WHERE id=?", (name, role, user_id))
    if data.get("password"):
        database.execute("UPDATE users SET password_hash=? WHERE id=?",
                         (generate_password_hash(data["password"]), user_id))
    row = query(USER_STATS + " WHERE u.id = ?", (user_id,), one=True)
    return jsonify({"user": dict(row)})


@users_bp.delete("/users/<int:user_id>")
@roles_required("admin")
def delete_user(user, user_id):
    if user_id == user["id"]:
        return jsonify({"error": "You cannot delete your own account."}), 400
    target = query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if target is None:
        return jsonify({"error": "User not found."}), 404
    n = query("SELECT COUNT(*) AS c FROM bugs WHERE assigned_to = ?", (user_id,), one=True)["c"]
    if n:
        return jsonify({"error": f"Cannot delete: user still has {n} bug(s) assigned. Reassign them first."}), 400
    database.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return jsonify({"ok": True})
