"""Authentication routes: login, registration, password reset, profile, and current user."""
import datetime
import re
import secrets
from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from database import db as database
from database.db import execute, query, add_notification, notify_roles
from utils.auth import create_token, login_required

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name:
        return jsonify({"error": "Full name is required."}), 400
    if len(name) < 2:
        return jsonify({"error": "Name must be at least 2 characters long."}), 400
    if not email:
        return jsonify({"error": "Email is required."}), 400
    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "Please provide a valid email address."}), 400
    if not password:
        return jsonify({"error": "Password is required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400

    # Duplicate email prevention
    existing = query("SELECT id FROM users WHERE email = ?", (email,), one=True)
    if existing:
        return jsonify({"error": "An account with this email already exists."}), 400

    # Public registration MUST always assign the 'reporter' role.
    role = "reporter"
    pwd_hash = generate_password_hash(password)

    user_id = execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
        (name, email, pwd_hash, role),
    )

    user = query("SELECT id, name, email, role, created_at FROM users WHERE id = ?", (user_id,), one=True)

    # Welcome notification
    add_notification(
        user_id,
        "Welcome to BugTrack",
        f"Hello {name}, your Reporter account has been created. You can now report and track software bugs.",
        notif_type="success",
    )
    # Notify admins about new registration
    notify_roles(
        ["admin"],
        "New Reporter Registered",
        f"{name} ({email}) registered as a public Reporter.",
        notif_type="info",
        exclude_user_id=user_id,
    )

    return jsonify({
        "token": create_token(user),
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    return jsonify({
        "token": create_token(user),
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    })


@auth_bp.route("/logout", methods=["POST"])
def logout():
    return jsonify({"ok": True, "message": "Logged out successfully."})


@auth_bp.route("/me", methods=["GET"])
@login_required
def me(user):
    return jsonify({
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        }
    })


@auth_bp.route("/profile", methods=["PUT"])
@login_required
def update_profile(user):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name cannot be empty."}), 400

    current_pwd = data.get("current_password")
    new_pwd = data.get("new_password")

    if new_pwd:
        if len(new_pwd) < 6:
            return jsonify({"error": "New password must be at least 6 characters long."}), 400
        # verify current password
        full_user = query("SELECT password_hash FROM users WHERE id = ?", (user["id"],), one=True)
        if not current_pwd or not check_password_hash(full_user["password_hash"], current_pwd):
            return jsonify({"error": "Current password is incorrect."}), 400
        execute(
            "UPDATE users SET name = ?, password_hash = ? WHERE id = ?",
            (name, generate_password_hash(new_pwd), user["id"]),
        )
    else:
        execute("UPDATE users SET name = ? WHERE id = ?", (name, user["id"]))

    updated = query("SELECT id, name, email, role FROM users WHERE id = ?", (user["id"],), one=True)
    return jsonify({"ok": True, "user": dict(updated)})


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required."}), 400

    user = query("SELECT id, name FROM users WHERE email = ?", (email,), one=True)
    if not user:
        # Avoid user enumeration in production, but confirm email submitted
        return jsonify({
            "ok": True,
            "message": "If an account exists with this email, password reset instructions have been generated."
        })

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

    execute(
        "INSERT INTO password_resets (email, token, expires_at) VALUES (?, ?, ?)",
        (email, token, expires_at),
    )

    return jsonify({
        "ok": True,
        "message": "Password reset token generated successfully.",
        "reset_token": token,
    })


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    new_password = data.get("password") or ""

    if not token or not new_password:
        return jsonify({"error": "Token and new password are required."}), 400
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters long."}), 400

    record = query(
        """SELECT * FROM password_resets
           WHERE token = ? AND used = 0 AND datetime(expires_at) > datetime('now')""",
        (token,),
        one=True,
    )
    if not record:
        return jsonify({"error": "Invalid or expired reset token."}), 400

    email = record["email"]
    execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (generate_password_hash(new_password), email),
    )
    execute("UPDATE password_resets SET used = 1 WHERE id = ?", (record["id"],))

    return jsonify({"ok": True, "message": "Password has been reset successfully. You can now log in."})
