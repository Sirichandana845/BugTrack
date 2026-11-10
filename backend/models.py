"""Database schema and domain constants for BugTrack.

SQLite is used so the project runs anywhere with zero configuration.
The four tables below implement the full bug lifecycle as described in the
project specification: users, bugs, bug_history and comments.
"""

USERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,              -- werkzeug hash, never plain text
    role          TEXT NOT NULL CHECK (role IN ('admin','developer','tester','reporter')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

BUGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS bugs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    title                TEXT NOT NULL,
    description          TEXT,
    module               TEXT,
    steps_to_reproduce   TEXT,
    expected_result      TEXT,
    actual_result        TEXT,
    severity             TEXT NOT NULL DEFAULT 'Medium',
    impact               TEXT NOT NULL DEFAULT 'Medium',
    recommended_priority TEXT,               -- what the system recommends
    priority             TEXT,               -- effective priority (admin may override)
    status               TEXT NOT NULL DEFAULT 'reported',
    assigned_to          INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_by           INTEGER REFERENCES users(id) ON DELETE SET NULL,
    resolution           TEXT,               -- from dataset (FIXED, WONTFIX, ...)
    attachment           TEXT,               -- stored filename of the screenshot/video
    operating_system     TEXT,               -- Windows, macOS, Linux, Android, iOS, etc.
    browser_device       TEXT,               -- Chrome, Firefox, Safari, Edge, Mobile, etc.
    app_version          TEXT,               -- e.g. v1.0.0
    fix_description      TEXT,               -- developer's notes on how bug was fixed
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

BUG_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS bug_history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    bug_id    INTEGER NOT NULL REFERENCES bugs(id) ON DELETE CASCADE,
    user_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action    TEXT NOT NULL,                 -- e.g. reported, assigned, status_change ...
    old_value TEXT,
    new_value TEXT,
    note      TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

COMMENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    bug_id     INTEGER NOT NULL REFERENCES bugs(id) ON DELETE CASCADE,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    comment    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

NOTIFICATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    message    TEXT NOT NULL,
    bug_id     INTEGER REFERENCES bugs(id) ON DELETE CASCADE,
    type       TEXT NOT NULL DEFAULT 'info',
    is_read    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

PASSWORD_RESETS_SCHEMA = """
CREATE TABLE IF NOT EXISTS password_resets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL,
    token      TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

INDEX_SCHEMA = [
    "CREATE INDEX IF NOT EXISTS idx_bugs_status        ON bugs(status);",
    "CREATE INDEX IF NOT EXISTS idx_bugs_module        ON bugs(module);",
    "CREATE INDEX IF NOT EXISTS idx_bugs_assigned      ON bugs(assigned_to);",
    "CREATE INDEX IF NOT EXISTS idx_bugs_creator       ON bugs(created_by);",
    "CREATE INDEX IF NOT EXISTS idx_history_bug        ON bug_history(bug_id);",
    "CREATE INDEX IF NOT EXISTS idx_comments_bug       ON comments(bug_id);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);",
    "CREATE INDEX IF NOT EXISTS idx_resets_token       ON password_resets(token);",
]

SCHEMA = [
    USERS_SCHEMA, BUGS_SCHEMA, BUG_HISTORY_SCHEMA,
    COMMENTS_SCHEMA, NOTIFICATIONS_SCHEMA, PASSWORD_RESETS_SCHEMA
] + INDEX_SCHEMA

# ----------------------------------------------------------------------------
# Domain constants shared by the whole application
# ----------------------------------------------------------------------------
ROLES       = ('admin', 'developer', 'tester', 'reporter')
STATUSES    = (
    'reported', 'triaged', 'assigned', 'in_progress', 'fixed',
    'testing', 'verified', 'closed', 'reopened',
    'rejected', 'duplicate', 'cannot_reproduce'
)
SEVERITIES  = ('Critical', 'High', 'Medium', 'Low')
IMPACTS     = ('High', 'Medium', 'Low')
PRIORITIES  = ('Critical', 'High', 'Medium', 'Low')

STATUS_LABELS = {
    'reported': 'Reported',
    'triaged': 'Triaged',
    'assigned': 'Assigned',
    'in_progress': 'In Progress',
    'fixed': 'Fixed',
    'testing': 'Ready for Testing',
    'verified': 'Verified',
    'closed': 'Closed',
    'reopened': 'Reopened',
    'rejected': 'Rejected',
    'duplicate': 'Duplicate',
    'cannot_reproduce': 'Cannot Reproduce',
}

MODULES = (
    'Auth / Login', 'Dashboard', 'Bug Tracker', 'User Management',
    'Reports & Analytics', 'Notifications', 'Settings / Profile',
    'API Gateway', 'Mobile Application', 'UI / UX', 'Database / Storage', 'Other'
)
