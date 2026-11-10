"""Intelligent Priority Recommendation.

A simple, fully explainable rule-based recommender:

    priority = f(severity, impact)

    Critical severity + High impact  ->  Critical priority
    High severity    + High impact   ->  High priority
    Medium severity  + Medium impact ->  Medium priority
    Low severity     + Low impact    ->  Low priority

Every recommendation comes with a human-readable explanation so the logic
is transparent (and easy to explain in a viva).
"""
from models import IMPACTS, SEVERITIES

# severity -> impact -> priority
MATRIX = {
    "Critical": {"High": "Critical", "Medium": "High", "Low": "Medium"},
    "High":     {"High": "High",     "Medium": "High", "Low": "Medium"},
    "Medium":   {"High": "Medium",   "Medium": "Medium", "Low": "Low"},
    "Low":      {"High": "Low",      "Medium": "Low", "Low": "Low"},
}

EXPLANATIONS = {
    "Critical": "Critical priority because the bug has {sev} severity and {imp} impact — "
                "it blocks a core function and affects a large set of users.",
    "High":     "High priority because the bug has {sev} severity and {imp} impact — "
                "it significantly affects an important system function.",
    "Medium":   "Medium priority because the bug has {sev} severity and {imp} impact — "
                "it affects a normal system function but the product remains usable.",
    "Low":      "Low priority because the bug has {sev} severity and {imp} impact — "
                "the effect is limited, so it can be scheduled later.",
}


def recommend(severity, impact):
    """Return {severity, impact, recommended_priority, explanation}."""
    sev = (severity or "").strip().title()
    imp = (impact or "").strip().title()
    if sev not in SEVERITIES:
        raise ValueError("Invalid severity. Must be one of: Critical, High, Medium, Low")
    if imp not in IMPACTS:
        raise ValueError("Invalid impact. Must be one of: High, Medium, Low")
    prio = MATRIX[sev][imp]
    return {
        "severity": sev,
        "impact": imp,
        "recommended_priority": prio,
        "explanation": EXPLANATIONS[prio].format(sev=sev.lower(), imp=imp.lower()),
    }


def impact_for_severity(severity):
    """Default impact when a source dataset has no impact column."""
    if severity in ("Critical", "High"):
        return "High"
    if severity == "Low":
        return "Low"
    return "Medium"
