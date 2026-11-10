"""BugTrack - Flask application entry point.

Run:  python app.py          (from the backend/ folder)
API:  http://localhost:5000/api/...
"""
import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from config import MAX_CONTENT_LENGTH, UPLOAD_DIR
from database.db import init_db, seed_users
from database.db import query
from routes.auth import auth_bp
from routes.bugs import bugs_bp
from routes.dashboard import dashboard_bp
from routes.import_data import import_bp
from routes.notifications import notifications_bp
from routes.reports import reports_bp
from routes.users import users_bp
from utils.auth import _get_secret_key


def create_app():
    production = os.environ.get("FLASK_ENV", "").lower() == "production"
    database_url = os.environ.get("DATABASE_URL")
    cors_origins = [
        origin.strip().rstrip("/")
        for origin in os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

    if production and not database_url:
        raise RuntimeError("DATABASE_URL is required in production.")
    if not cors_origins or (production and "*" in cors_origins):
        raise RuntimeError(
            "Set CORS_ORIGINS to the trusted web app origin(s); "
            "wildcard origins are not allowed in production."
        )
    _get_secret_key()

    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    CORS(app, resources={r"/api/*": {"origins": cors_origins}})

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(bugs_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api")
    app.register_blueprint(notifications_bp, url_prefix="/api")
    app.register_blueprint(reports_bp, url_prefix="/api")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(import_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        query("SELECT 1", one=True)
        return jsonify({"status": "ok"})

    # Uploaded screenshots/attachments
    @app.route("/api/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(UPLOAD_DIR, filename)

    # JSON error handlers
    @app.errorhandler(400)
    def bad_request(_e):
        return jsonify({"error": "Invalid request."}), 400

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(413)
    def too_large(_e):
        return jsonify({"error": "Upload is too large (max 8 MB)."}), 413

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"error": "Internal server error."}), 500

    # Optionally serve the built React app from the same server
    # (only active after `npm run build` in frontend/)
    frontend_dist = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
    )
    if os.path.isdir(frontend_dist):

        @app.route("/")
        def index():
            return send_from_directory(frontend_dist, "index.html")

        @app.route("/<path:path>")
        def spa(path):
            if path.startswith("api/"):
                return jsonify({"error": "Resource not found."}), 404
            full = os.path.join(frontend_dist, path)
            if os.path.isfile(full):
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, "index.html")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    init_db()
    if not production and not database_url:
        seed_users()

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = (
        os.environ.get("FLASK_DEBUG", "").lower() == "true"
        and os.environ.get("FLASK_ENV", "").lower() != "production"
    )
    app.run(host="0.0.0.0", port=port, debug=debug)
