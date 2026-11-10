
"""Dataset import routes (admin only)."""

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

        with open(
            DEFAULT_KAGGLE_CSV,
            newline="",
            encoding="utf-8-sig"
        ) as fh:
            columns = next(csv.reader(fh))

    return jsonify({
        "sample_file": os.path.basename(DEFAULT_KAGGLE_CSV),
        "exists": exists,
        "columns": columns,
        "note": (
            "BugTrack ships a sample kaggle_bugs.csv file. "
            "It can be replaced with a real Kaggle CSV export. "
            "Imports preserve existing bugs by default."
        ),
    })


@import_bp.post("/dataset/import")
@roles_required("admin")
def do_import(_user):
    data = request.get_json(silent=True) or {}

    path = (
        (data.get("path") or "").strip()
        or DEFAULT_KAGGLE_CSV
    )

    if not os.path.isfile(path):
        return jsonify({
            "error": f"Dataset file not found: {path}"
        }), 400

    # Preserve existing data unless replacement is explicitly requested.
    wipe = data.get("wipe", False)

    if not isinstance(wipe, bool):
        return jsonify({
            "error": "The wipe field must be true or false."
        }), 400

    if wipe and data.get("confirm_replace") is not True:
        return jsonify({
            "error": (
                "Replacing existing bugs requires "
                "confirm_replace=true."
            )
        }), 400

    try:
        summary = import_service.import_csv(
            path,
            wipe=wipe
        )

    except Exception as exc:
        return jsonify({
            "error": f"Import failed: {exc}"
        }), 400

    return jsonify({
        "summary": summary
    })
