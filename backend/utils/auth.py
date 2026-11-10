
"""JWT authentication and role-based access control helpers."""

import functools
import os
import time

import jwt
from flask import jsonify, request

from database.db import query


TOKEN_TTL_HOURS = 12


def _get_secret_key():
    """Get the configured JWT secret key."""

    secret = os.environ.get("SECRET_KEY")

    if not secret:
        raise RuntimeError(
            "SECRET_KEY is missing. Configure a secure environment variable."
        )

    if len(secret) < 32:
        raise RuntimeError(
            "SECRET_KEY must contain at least 32 characters."
        )

    return secret


def create_token(user):
    """Create a signed JWT for an authenticated user."""

    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "name": user["name"],
        "email": user["email"],
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_TTL_HOURS * 3600,
    }

    return jwt.encode(
        payload,
        _get_secret_key(),
        algorithm="HS256",
    )


def get_current_user():
    """Validate the Bearer token and return the current database user."""

    header = request.headers.get("Authorization", "")

    if not header.startswith("Bearer "):
        return None

    token = header[7:].strip()

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            _get_secret_key(),
            algorithms=["HS256"],
        )

        user_id = int(payload["sub"])

        if user_id <= 0:
            return None

    except (
        jwt.InvalidTokenError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
    ):
        return None

    return query(
        """
        SELECT id, name, email, role, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
        one=True,
    )


def login_required(view):
    """Allow access only to authenticated users."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        user = get_current_user()

        if user is None:
            return jsonify({
                "error": "Authentication required. Please log in."
            }), 401

        return view(user, *args, **kwargs)

    return wrapper


def roles_required(*roles):
    """Restrict access to users with specified roles."""

    def decorator(view):

        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            user = get_current_user()

            if user is None:
                return jsonify({
                    "error": "Authentication required. Please log in."
                }), 401

            if user["role"] not in roles:
                return jsonify({
                    "error": (
                        "You do not have permission "
                        "to perform this action."
                    )
                }), 403

            return view(user, *args, **kwargs)

        return wrapper

    return decorator
