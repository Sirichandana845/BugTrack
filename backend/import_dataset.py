"""Import the Kaggle-style dataset into SQLite.

    cd backend && python import_dataset.py            (uses dataset/kaggle_bugs.csv)
    cd backend && python import_dataset.py /path/to/real_kaggle_export.csv

Maps source columns (short_desc, component, severity, priority, status,
assigned_to_name, assigned_to_email, creation_time, ...) into BugTrack's
bug table and writes an 'imported' history row per bug.
"""
import sys

from database.db import init_db, seed_users
from services.import_service import import_csv, import_sample_csv

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    init_db()
    seed_users()
    try:
        summary = import_csv(path) if path else import_sample_csv()
    except Exception as exc:
        print(f"Import failed: {exc}")
        sys.exit(1)
    print(f"✓ Import finished: {summary['inserted']} bugs inserted, "
          f"{summary['skipped']} rows skipped, source: {summary['source']}")
