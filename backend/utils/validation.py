"""Small input-validation helpers. Invalid input raises ValueError,
which the route layer converts into a 400 JSON response."""


def require_fields(data, fields):
    missing = [f for f in fields if not data.get(f)]
    if missing:
        raise ValueError("Missing required field(s): " + ", ".join(missing))


def one_of(value, choices, field):
    if value not in choices:
        raise ValueError(
            f"Invalid {field} '{value}'. Must be one of: {', '.join(choices)}"
        )


def non_empty(value, field):
    if not value or not str(value).strip():
        raise ValueError(f"{field} cannot be empty.")
    return str(value).strip()
