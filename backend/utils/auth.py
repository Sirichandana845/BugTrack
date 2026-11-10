"""JWT authentication + role-based access control helpers."""
import functools
import os
import time

import jwt
from flask import jsonify, request

from database.db import query

SECRET_KEY = os.environ.get("SECRET_KEY", "bugtrack-college-demo-secret-key")
TOKEN_TTL_HOURS = 12


def create_token(user):
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "name": user["name"],
        "email": user["email"],
        "exp": int(time.time()) + TOKEN_TTL_HOURS * 3600,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user():
    """Read the Bearer token from the request and return the user row (or None)."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(header[7:], SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return None
    return query(
        "SELECT id, name, email, role, created_at FROM users WHERE id = ?",
        (int(payload["sub"]),),
        one=True,
    )


def login_required(view):
    """Decorator: any authenticated user."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return view(user, *args, **kwargs)

    return wrapper


def roles_required(*roles):
    """Decorator factory: restrict an endpoint to given roles."""

    def decorator(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return jsonify({"error": "Authentication required. Please log in."}), 401
            if user["role"] not in roles:
                return jsonify({"error": "You do not have permission to perform this action."}), 403
            return view(user, *args, **kwargs)

        return wrapper

    return decorator
