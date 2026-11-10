"""Dataset import routes (admin only).

The Kaggle CSV itself cannot be downloaded automatically (Kaggle requires an
account/API key), so BugTrack ships a documented SAMPLE with the same column
schema and provides this import endpoint. Point it at any real Kaggle export
(files like bugzilla_bug_reports.csv / Eclipse.csv / JIRA issues.csv) that
has similar columns - see README.md -> "Dataset Source".
"""
import os

from flask import Blueprint, jsonify, request

from config import DEFAULT_KAGGLE_CSV
from services import import_service
from utils.auth import roles_required

import_bp = Blueprint("import_data", __name__)


@import_bp.get("/dataset/info")
def dataset_info():
    exists = os.path.exists(DEFAULT_KAGGLE_CSV)
    columns = []
    if exists:
        import csv
        with open(DEFAULT_KAGGLE_CSV, newline="", encoding="utf-8-sig") as fh:
            columns = next(csv.reader(fh))
    return jsonify({
        "sample_file": os.path.basename(DEFAULT_KAGGLE_CSV),
        "exists": exists,
        "columns": columns,
        "note": (
            "BugTrack ships a sample 'kaggle_bugs.csv' (same column schema as the "
            "Kaggle 'Bugzilla Bug Reports' / 'Software bugs reports' datasets). "
            "It is a documented stand-in - replace it with the real CSV export and "
            "re-import. See README section 'Kaggle Dataset Import'."
        ),
    })


@import_bp.post("/dataset/import")
@roles_required("admin")
def do_import(_user):
    data = request.get_json(silent=True) or {}
    path = (data.get("path") or "").strip() or DEFAULT_KAGGLE_CSV
    if not os.path.isfile(path):
        return jsonify({"error": f"Dataset file not found: {path}"}), 400
    try:
        summary = import_service.import_csv(path, wipe=True)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Import failed: {exc}"}), 400
    return jsonify({"summary": summary})
