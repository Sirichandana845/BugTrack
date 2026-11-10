"""Generate dataset/kaggle_bugs.csv - a documented SAMPLE stand-in.

The real Kaggle datasets ("Bugzilla Bug Reports", "Software bugs reports /
Eclipse", or any JIRA/issue-tracker export) require a Kaggle account + API
key to download, so this generator produces a CSV with the SAME column
schema the import pipeline maps:

    short_desc, description, component, product, severity, priority, status,
    resolution, assigned_to_name, assigned_to_email, creation_time,
    steps_to_reproduce, expected_result, actual_result, impact

Usage:  python generate_sample_dataset.py
Output: ../dataset/kaggle_bugs.csv  (relative to backend/, or run from project root)
"""
import csv
import datetime
import os
import random

def main():
    rng = random.Random(7)
    now = datetime.datetime(2026, 9, 6, 12, 0, 0)

    modules = ["Login / Auth", "Dashboard", "Payments", "Reports", "User Profile",
               "Search", "Notifications", "API Gateway"]
    statuses = [
        ("closed", "FIXED"), ("closed", "FIXED"), ("closed", "FIXED"),
        ("closed", "WONTFIX"), ("fixed", "FIXED"), ("testing", None),
        ("testing", None), ("in_progress", None), ("in_progress", None),
        ("assigned", None), ("assigned", None), ("reported", None),
        ("reported", None), ("reopened", None),
    ]
    developers = [
        ("Arjun Mehta", "dev@bugtrack.dev"),
        ("Sneha Patel", "dev2@bugtrack.dev"),
    ]
    severities = ["Critical", "High", "High", "Medium", "Medium", "Medium", "Low", "Low"]
    priorities = ["Critical", "High", "High", "Medium", "Medium", "Low"]

    bugs = [
        # title, module, severity, priority, status, resolution, developer, description
        ("Checkout page crashes when applying a discount code", "Payments", "Critical", "Critical",
         "closed", "FIXED", 0,
         "Applying any promo code on the checkout page throws a 500 error and the order is lost."),
        ("User cannot reset password - reset link expires instantly", "Login / Auth", "Critical", "Critical",
         "closed", "FIXED", 1,
         "The password reset token is stored without the 30 minute expiry and gets invalidated immediately."),
        ("Dashboard charts render blank on Safari 17", "Dashboard", "High", "High",
         "testing", None, 0,
         "Line and bar charts on the analytics dashboard show an empty frame on Safari 17."),
        ("Duplicate invoices generated when clicking Pay twice", "Payments", "High", "High",
         "in_progress", None, 1,
         "Rapid double clicks on the Pay button create two invoices with the same reference."),
        ("Search results are not filtered by selected project", "Search", "Medium", "Medium",
         "closed", "FIXED", 0,
         "Search ignores the active project filter and returns results from all projects."),
        ("Notification email contains broken image links", "Notifications", "Low", "Low",
         "closed", "FIXED", 1,
         "Email templates reference asset URLs that 404 after the CDN migration."),
        ("Report export hangs for datasets over 50k rows", "Reports", "High", "High",
         "assigned", None, 0,
         "CSV export for large result sets times out after 60 seconds."),
        ("Avatar upload accepts non-image files", "User Profile", "Medium", "Medium",
         "reported", None, None,
         "The profile picture endpoint accepts any file type; a .html file is stored as an avatar."),
        ("Session does not persist after browser refresh", "Login / Auth", "High", "High",
         "in_progress", None, 1,
         "The JWT is not stored in a persistent cookie, so refresh logs the user out."),
        ("Numbers on report totals are misaligned for 4-digit values", "Reports", "Low", "Low",
         "closed", "WONTFIX", None,
         "Table cells overflow for totals above 1,000 in the summary view."),
        ("Role change does not refresh sidebar permissions", "Login / Auth", "Medium", "Medium",
         "testing", None, 0,
         "After an admin changes a user's role, the UI keeps showing stale menu items."),
        ("Notifications tab shows unread badge after all read", "Notifications", "Low", "Low",
         "closed", "FIXED", 1,
         "The unread counter is not decremented when the user opens the notifications panel."),
        ("API Gateway returns 502 for requests above 10 MB payload", "API Gateway", "Medium", "Medium",
         "reopened", None, 0,
         "Large JSON uploads fail with 502; a retry fixes it intermittently."),
        ("Edit profile form loses unsaved changes on validation error", "User Profile", "Medium", "Medium",
         "fixed", "FIXED", 1,
         "Client-side validation re-renders the form and discards typed values."),
        ("Dark mode toggle resets to light after page reload", "User Profile", "Low", "Low",
         "reported", None, None,
         "Theme preference is not persisted to localStorage."),
        ("Bulk delete of bugs does not confirm before deleting", "Dashboard", "Medium", "Medium",
         "assigned", None, 0,
         "No confirmation dialog; accidental bulk deletes are irreversible."),
        ("Login button does not respond on mobile viewport", "Login / Auth", "High", "High",
         "closed", "FIXED", 1,
         "The submit handler is covered by an overlapping element on small screens."),
        ("Pagination shows wrong page count for filtered views", "Search", "Medium", "Medium",
         "testing", None, 0,
         "Total pages are computed from the unfiltered result set."),
        ("Invoice PDF missing company logo for new tenants", "Payments", "Low", "Low",
         "closed", "FIXED", 1,
         "Logo path resolution fails for tenants created after the branding update."),
        ("Keyboard shortcut Ctrl+S saves the wrong form", "API Gateway", "Medium", "Medium",
         "reported", None, None,
         "Global shortcut handler binds to the first form on the page instead of the active one."),
        ("Deprecation warnings flood the logs for every search call", "Search", "Low", "Low",
         "closed", "FIXED", 0,
         "Legacy query builder emits warnings on every invocation."),
        ("Team members list shows deleted users as active", "User Profile", "High", "High",
         "in_progress", None, 1,
         "Soft-deleted users are not filtered out of the team listing endpoint."),
        ("Timezone selector resets to UTC on profile update", "User Profile", "Low", "Low",
         "closed", "FIXED", 0,
         "The timezone field is not included in the update payload."),
        ("Webhook deliveries fail silently for invalid signatures", "API Gateway", "High", "High",
         "reported", None, None,
         "Signature verification errors are swallowed; no retry or alert is triggered."),
        ("Chart tooltips overlap the header on small screens", "Dashboard", "Low", "Low",
         "closed", "FIXED", 1,
         "Tooltip positioning is not clamped to the chart container."),
        ("Export to Excel truncates long description cells", "Reports", "Medium", "Medium",
         "reported", None, None,
         "Cells are limited to 255 characters in the XLSX export."),
        ("OAuth callback does not handle cancelled login", "Login / Auth", "Medium", "Medium",
         "testing", None, 0,
         "Cancelling the OAuth flow leaves the app stuck on a loading spinner."),
        ("Rate limiter blocks legitimate API keys during peak hours", "API Gateway", "High", "High",
         "assigned", None, 1,
         "Burst traffic from a single client key trips the global limiter."),
        ("Search autocomplete suggests deleted modules", "Search", "Medium", "Medium",
         "reopened", None, 0,
         "Index is not refreshed when modules are archived."),
        ("Notification preferences cannot be saved with none selected", "Notifications", "Low", "Low",
         "closed", "WONTFIX", None,
         "The preferences form requires at least one channel, but the schema allows zero."),
        ("Signup page leaks whether an email is already registered", "Login / Auth", "Medium", "Medium",
         "reported", None, None,
         "The signup response differs for existing vs new emails."),
        ("Invoice amount displayed with wrong currency symbol", "Payments", "High", "High",
         "testing", None, 1,
         "Multi-currency tenants see the tenant currency symbol with the wrong locale."),
    ]

    impact_by_severity = {"Critical": "High", "High": "High", "Medium": "Medium", "Low": "Low"}

    with open(os.path.join(os.path.dirname(__file__), "..", "dataset", "kaggle_bugs.csv"),
              "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "short_desc", "description", "component", "product", "severity",
            "priority", "status", "resolution", "assigned_to_name",
            "assigned_to_email", "creation_time", "steps_to_reproduce",
            "expected_result", "actual_result", "impact",
        ])
        base = now - datetime.timedelta(days=65)
        for i, (title, module, sev, prio, status, resolution, dev_idx, description) in enumerate(bugs):
            created = base + datetime.timedelta(days=rng.randint(0, 64),
                                                hours=rng.randint(0, 23),
                                                minutes=rng.randint(0, 59))
            dev_name, dev_email = developers[dev_idx] if dev_idx is not None else ("", "")
            writer.writerow([
                title,
                f"{title}. {description}",
                module,
                "BugTrack Web App",
                sev,
                prio,
                status,
                resolution or "",
                dev_name,
                dev_email,
                created.strftime("%Y-%m-%d %H:%M:%S"),
                "1. Open the page\n2. Perform the reported action\n3. Observe the failure",
                "The system performs the action correctly and shows a success state.",
                "The system fails with an error state and the user cannot complete the action.",
                impact_by_severity[sev],
            ])

    print("✓ Generated dataset/kaggle_bugs.csv with", len(bugs), "sample bug records")


if __name__ == "__main__":
    main()
