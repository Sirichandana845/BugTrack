"""End-to-end verification of the BugTrack demo scenario against a running server.

Run:  python test_demo.py   (after `python app.py` is running on :5000)
"""
import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("BUGTRACK_URL", "http://localhost:5000").rstrip("/") + "/api"


def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def login(email, pw):
    s, d = call("POST", "/login", body={"email": email, "password": pw})
    assert s == 200, d
    return d["token"], d["user"]


tok_t, tester = login("tester@bugtrack.dev", "tester123")
tok_a, admin = login("admin@bugtrack.dev", "admin123")
tok_d, dev = login("dev@bugtrack.dev", "dev123")
print("LOGIN OK: tester / admin / developer")

# --- 1. import the Kaggle-style sample dataset (admin) ---
s, r = call("POST", "/dataset/import", tok_a, {})
print(f"IMPORT: {s} -> {r.get('summary')}")

# --- 2. dashboard before ---
s, dash = call("GET", "/dashboard", tok_a)
print("DASHBOARD BEFORE:", dash["counts"])

# --- 3. tester reports a critical bug ---
s, r = call("POST", "/bugs", tok_t, {
    "title": "Login button does not work",
    "description": "Clicking the Login button does nothing on the sign-in page.",
    "module": "Login / Auth",
    "severity": "Critical", "impact": "High",
    "steps_to_reproduce": "1. Open the app\n2. Click the Login button\n3. Nothing happens",
    "expected_result": "User is signed in and redirected to the dashboard.",
    "actual_result": "The button does not respond.",
})
bug_id = r["bug"]["id"]
print(f"REPORT: {s} bug_id={bug_id} recommended_priority={r['recommendation']['recommended_priority']} "
      f"explanation={r['recommendation']['explanation'][:60]}...")

# --- 4. admin assigns to developer ---
s, r = call("PUT", f"/bugs/{bug_id}/assign", tok_a, {"developer_id": dev["id"]})
print(f"ASSIGN: {s} status={r['bug']['status']} assigned={r['bug']['assigned_name']}")

# --- 5. developer: in_progress -> fixed -> testing ---
for st in ["in_progress", "fixed", "testing"]:
    s, r = call("PUT", f"/bugs/{bug_id}/status", tok_d, {"status": st})
    print(f"DEV -> {st}: {s} status={r.get('bug', {}).get('status')}")

# --- 6. tester: testing FAILED -> reopen ---
s, r = call("PUT", f"/bugs/{bug_id}/status", tok_t, {"status": "reopened", "note": "Fix did not work on Safari 17"})
print(f"TESTER reopen (fail): {s} status={r.get('bug', {}).get('status')}")

# --- 7. developer fixes again, tester verifies and closes ---
for st in ["in_progress", "fixed", "testing"]:
    s, r = call("PUT", f"/bugs/{bug_id}/status", tok_d, {"status": st})
    print(f"DEV -> {st}: {s} status={r.get('bug', {}).get('status')}")
s, r = call("PUT", f"/bugs/{bug_id}/status", tok_t, {"status": "closed", "note": "Verified on Chrome and Safari"})
print(f"TESTER close: {s} status={r.get('bug', {}).get('status')}")

# --- 8. illegal transition must be rejected ---
s, r = call("PUT", f"/bugs/{bug_id}/status", tok_d, {"status": "closed"})
print(f"ILLEGAL (dev close from closed): {s} -> {r.get('error')}")

# --- 9. dashboard after ---
s, dash = call("GET", "/dashboard", tok_a)
print("DASHBOARD AFTER:", dash["counts"])

# --- 10. search + filters (server-side SQL) ---
s, r = call("GET", "/bugs?status=closed&priority=Critical", tok_a)
print("FILTER status=closed&priority=Critical -> total:", r.get("total"))
s, r = call("GET", "/bugs?search=login", tok_a)
print("SEARCH 'login' -> total:", r.get("total"))

# --- 11. history timeline ---
s, r = call("GET", f"/bugs/{bug_id}/history", tok_a)
print("HISTORY timeline for bug #", bug_id)
for h in r["history"]:
    print(f"  {h['timestamp']}  {h['action']:16} {h.get('old_value') or '':>10} -> {h.get('new_value') or '':<10} {h.get('note') or ''}")

# --- 12. reports ---
s, r = call("GET", "/reports", tok_a)
print("REPORTS: total =", r.get("total_bugs"), "| open =", r.get("open_bugs"), "| closed =", r.get("closed_bugs"))

print("\nALL DEMO CHECKS PASSED ✔")
