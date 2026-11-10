# 🐞 BugTrack — Intelligent Software Bug Tracking, Prioritization & Resolution System

A full-stack **Software Engineering & System Design** college project.

- **Frontend:** React 18 + Vite + Tailwind CSS + Recharts
- **Backend:** Python Flask REST API (JWT auth, role-based access)
- **Database:** SQLite (zero configuration)
- **Intelligent feature:** explainable bug **priority recommendation** from *Severity + Impact*

```
User → React Frontend → Flask REST API → Business Logic → SQLite
                                                          ↓
                                        Dashboard / Reports (live statistics)
```

## ✨ Features

| Area | What it does |
|---|---|
| Lifecycle | Reported → Assigned → In Progress → Fixed → Testing → Closed; Testing fail → Reopened → In Progress. Illegal transitions rejected (400). |
| Priority engine | `priority = f(severity, impact)` with a human-readable explanation. Admin can override. |
| Role-based access | Admin / Developer / Tester — each role sees only what it may do. |
| Search & filtering | `GET /api/bugs?search=&status=&priority=&severity=&developer=` executed as SQL on the backend. |
| History | Every reported/assigned/status/priority/comment change stored in `bug_history`, shown as a timeline. |
| Dashboard | Total / Open / Critical / Resolved / Reopened + charts by status, priority, severity, module, developer. |
| Reports | Aggregated statistics + **Download CSV** export. |
| Kaggle import | `dataset/kaggle_bugs.csv` (sample) → cleaning → field mapping → SQLite. Real Kaggle exports (Bugzilla/Eclipse/JIRA style CSVs) also import. |

## 📁 Folder structure

```
bugtrack/
├── frontend/                 # React + Vite + Tailwind + Recharts
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js        # proxies /api → localhost:5000
│   └── src/
│       ├── App.jsx           # hash router, sidebar, topbar, toasts
│       ├── components/       # Icon, ui (badges, cards, modal, spinner)
│       ├── services/api.js   # fetch wrapper + JWT + attachment upload
│       └── pages/            # Login, Dashboard, BugList, ReportBug,
│                             # BugDetails, Developers, Users, Reports, ImportData
├── backend/
│   ├── app.py                # Flask entry point (python app.py)
│   ├── seed.py               # create tables + demo users
│   ├── import_dataset.py     # CLI CSV import
│   ├── config.py
│   ├── models.py             # schema + domain constants
│   ├── database/db.py        # SQLite helpers + init
│   ├── routes/               # auth, bugs, dashboard, reports, users, import_data
│   ├── services/             # priority_service, lifecycle, import_service
│   └── utils/                # auth (JWT), validation
├── dataset/
│   ├── kaggle_bugs.csv          # sample dataset (Kaggle-style schema)
│   └── generate_sample_dataset.py
├── requirements.txt
└── README.md
```

## 🚀 Run it

### 1. Backend (Flask + SQLite)

```bash
cd bugtrack/backend
pip install -r requirements.txt   # Flask, Flask-Cors, PyJWT
python seed.py                    # creates database + demo users (optional, runs automatically too)
python app.py                     # API on http://localhost:5000
```

### 2. Frontend (React)

```bash
cd bugtrack/frontend
npm install
npm run dev                       # http://localhost:5173 (proxies /api to :5000)
```

Open **http://localhost:5173**.

### 3. Load the dataset (optional but recommended)

```bash
cd bugtrack/backend
python import_dataset.py          # imports dataset/kaggle_bugs.csv
```

Or in the UI: log in as **Admin → Data Import → Import Dataset**.

## 🔑 Demo accounts

| Role | Email | Password |
|---|---|---|
| Admin | admin@bugtrack.dev | admin123 |
| Developer | dev@bugtrack.dev | dev123 |
| Developer 2 | dev2@bugtrack.dev | dev2123 |
| Tester | tester@bugtrack.dev | tester123 |

## 🧪 Demo scenario (lifecycle)

1. **Tester** logs in → *Report Bug*: “Login button does not work”, Severity **Critical**, Impact **High** → system recommends **Priority: Critical** (with explanation).
2. **Admin** assigns it to a developer → status **Assigned**.
3. **Developer** → *Start Work* (**In Progress**) → *Mark Fixed* (**Fixed**) → *Send to Testing* (**Testing**).
4. **Tester** verifies: pass → *Close Bug* (**Closed**); fail → *Reopen Bug* (**Reopened**) → developer *Start Work* again (**In Progress**).
5. Dashboard counts & charts update automatically after every step.

## 🧠 Priority recommendation (the “intelligent” feature)

Pure rule matrix, fully explainable — no ML:

| Severity \ Impact | High | Medium | Low |
|---|---|---|---|
| Critical | Critical | High | Medium |
| High | High | High | Medium |
| Medium | Medium | Medium | Low |
| Low | Low | Low | Low |

Example explanation: *“High priority because the bug has high severity and high impact — it significantly affects an important system function.”*
Admins can override the priority; the recommendation is always kept on record in `recommended_priority`.

## 🗄️ Database schema

- **users** — id, name, email, password_hash (werkzeug, never plain text), role, created_at
- **bugs** — id, title, description, module, steps_to_reproduce, expected_result, actual_result, severity, impact, recommended_priority, priority, status, assigned_to, created_by, resolution, attachment, created_at, updated_at
- **bug_history** — id, bug_id, user_id, action, old_value, new_value, note, timestamp
- **comments** — id, bug_id, user_id, comment, created_at

## 📡 Main API endpoints

```
POST /api/login
GET  /api/me
GET  /api/bugs                ?search=&status=&priority=&severity=&developer=&assigned=me
POST /api/bugs
POST /api/priority-recommend
GET  /api/bugs/<id>
PUT  /api/bugs/<id>
PUT  /api/bugs/<id>/status
PUT  /api/bugs/<id>/assign
POST /api/bugs/<id>/comments
GET  /api/bugs/<id>/history
GET  /api/dashboard
GET  /api/reports             GET /api/reports/csv  (CSV export)
GET/POST/PUT/DELETE /api/users      (admin)
GET  /api/developers
GET  /api/dataset/info
POST /api/dataset/import      (admin)
```

All routes except `/api/login` require `Authorization: Bearer <JWT>`; role checks return 403.

## 📊 Dataset source & honesty note

The bundled `dataset/kaggle_bugs.csv` is a **generated sample stand-in** (32 records) using the same column schema as the real Kaggle datasets:

- **“Bugzilla Bug Reports”** — https://www.kaggle.com/datasets/qicongliu/bugzilla-bug-reports (35,000+ Bugzilla bugs)
- **“Software bugs reports” (Eclipse)** — https://www.kaggle.com/datasets/samanthakumara/software-bug-reports

Kaggle requires a free account + API key to download CSV files, so the real file cannot be fetched automatically. To use real data: download the CSV from Kaggle, save it as `dataset/kaggle_bugs.csv` (or any path), then run `python import_dataset.py <path>` or use the Admin → **Data Import** page. The importer maps and normalises columns (`short_desc→title`, `component→module`, plus severity/priority/status/resolution); missing fields get documented defaults (e.g. impact derived from severity, priority from the recommendation matrix). The data is **not real-time**.

## 🔒 Security

- Passwords hashed with `werkzeug.security` (no plain text in DB)
- JWT (HS256, 12 h expiry) for sessions
- Role-based authorization (403 on forbidden actions)
- Lifecycle state machine (400 on illegal transitions)
- Input validation on every endpoint + 8 MB upload cap

## 🧩 Run in one command (optional)

You can also serve the built frontend from Flask itself:

```bash
cd frontend && npm run build    # produces frontend/dist
cd ../backend && python app.py  # http://localhost:5000 serves the app
```

---

Made for the college **Software Engineering & System Design** course — simple enough to explain in a viva, complete enough to demonstrate.
