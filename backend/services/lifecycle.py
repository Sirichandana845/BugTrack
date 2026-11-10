"""Bug lifecycle state machine.

Standard flow:
    Reported -> Triaged -> Assigned -> In Progress -> Fixed -> Ready for Testing (testing) -> Verified -> Closed

Alternative resolutions & handling:
    Reopened (from testing / verified / closed)
    Rejected (admin/triage)
    Duplicate (admin/triage)
    Cannot Reproduce (developer/tester)

Illegal transitions are rejected with a 400 error, and every transition is
restricted by role (see ROLE_ALLOWED below).
"""
from models import STATUS_LABELS, STATUSES

TRANSITIONS = {
    "reported":         ["triaged", "assigned", "in_progress", "rejected", "duplicate", "cannot_reproduce"],
    "triaged":          ["assigned", "in_progress", "rejected", "duplicate", "cannot_reproduce"],
    "assigned":         ["in_progress", "cannot_reproduce"],
    "in_progress":      ["fixed", "cannot_reproduce"],
    "fixed":            ["testing", "verified"],
    "testing":          ["verified", "reopened"],
    "verified":         ["closed", "reopened"],
    "closed":           ["reopened"],
    "reopened":         ["in_progress", "triaged", "assigned"],
    "rejected":         ["reopened", "triaged"],
    "duplicate":        ["reopened", "triaged"],
    "cannot_reproduce": ["reopened", "in_progress"],
}

# Which roles may perform each target status.
ROLE_ALLOWED = {
    "triaged":          {"admin"},
    "assigned":         {"admin"},
    "in_progress":      {"admin", "developer"},
    "fixed":            {"admin", "developer"},
    "testing":          {"admin", "developer", "tester"},
    "verified":         {"admin", "tester"},
    "closed":           {"admin", "tester"},
    "reopened":         {"admin", "tester", "developer"},
    "rejected":         {"admin"},
    "duplicate":        {"admin"},
    "cannot_reproduce": {"admin", "developer"},
}


def validate_transition(role, current, new, assigned_to=None, user_id=None, created_by=None):
    """Return (ok: bool, message: str) for a requested status change."""
    if new not in STATUSES:
        return False, f"Invalid status '{new}'."
    if new == current:
        return False, f"Bug is already in '{STATUS_LABELS.get(new, new)}' status."
    if new not in TRANSITIONS.get(current, []):
        return False, (
            f"Illegal status change: '{STATUS_LABELS.get(current, current)}' -> "
            f"'{STATUS_LABELS.get(new, new)}' is not allowed by the bug lifecycle."
        )
    if role == "admin":
        return True, ""
    if role == "developer" and new in ("in_progress", "fixed", "testing", "cannot_reproduce"):
        if assigned_to == user_id or assigned_to is None:
            return True, ""
        return False, "You can only change status for bugs assigned to you."
    if role == "tester" and new in ("testing", "verified", "reopened", "closed"):
        return True, ""
    if role == "reporter" and created_by == user_id and new in ("closed", "reopened"):
        return True, ""
    return False, "Your role does not allow this status change."


def allowed_next(role, status, assigned_to=None, user_id=None, created_by=None):
    """Statuses the current user is allowed to move the bug to (for the UI)."""
    result = []
    for nxt in TRANSITIONS.get(status, []):
        ok, _ = validate_transition(role, status, nxt, assigned_to, user_id, created_by)
        if ok:
            result.append(nxt)
    return result

