"""Central configuration for BugTrack."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Where uploaded screenshots/attachments are stored
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# Default Kaggle sample dataset (relative to project root: bugtrack/dataset/)
DATASET_DIR = os.path.join(BASE_DIR, "..", "dataset")
DEFAULT_KAGGLE_CSV = os.environ.get("KAGGLE_CSV", os.path.join(DATASET_DIR, "kaggle_bugs.csv"))

# JWT secret - change this in production
SECRET_KEY = os.environ.get("SECRET_KEY", "bugtrack-college-demo-secret-key")
TOKEN_TTL_HOURS = 12

# Max request payload (attachments are sent as base64 inside JSON)
MAX_CONTENT_LENGTH = 8 * 1024 * 1024
