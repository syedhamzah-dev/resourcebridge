# 🌉 ResourceBridge

> **Campus Resource Sharing Network with Trust, Safety, and Physical Accountability**
> *A secure, full-stack college resource management platform built for hackathon demonstration.*

[![Live Demo](https://img.shields.io/badge/Render-Live%20Demo-brightgreen?logo=render)](https://resourcebridge-79f6.onrender.com)
[![Tests](https://img.shields.io/badge/tests-70%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Flask](https://img.shields.io/badge/flask-3.0%2B-black.svg)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

---

## 📖 1. Problem Statement & Intended Users

### The Problem
In college and university campuses, millions of dollars worth of specialized equipment and facilities—such as **photonic microscopes, cinema-grade cameras, deep-learning GPU workstations, VR headsets, 3D printers, and seminar spaces**—sit idle behind locked departmental doors after 4:00 PM. Simultaneously, enterprising students pursuing capstone engineering projects, research papers, or creative prototypes cannot access this critical equipment due to fragmented departmental silos, lack of trust, fear of unreturned gear, and informal paper-based sign-out clipboards.

### Intended Users
1. **Students (Borrowers)**: Enrolled students needing specialized high-end resources for academic or extracurricular coursework, verified by campus credentials.
2. **Lab & Department Managers (Custodians)**: Faculty members, lab directors, and department technicians who own and safeguard institutional assets, requiring verifiable chain-of-custody tracking.
3. **Campus Administrators (Auditors)**: Institutional oversight officers responsible for campus-wide inventory compliance, safety policy enforcement, and incident dispute resolution.

---

## 💡 2. Solution Overview & Core Architecture

**ResourceBridge** establishes a secure, structured physical asset lending network built around five foundational pillars:

1. **Role-Based Access Control (RBAC)**: Strict segregation among `student`, `manager`, and `admin` roles, enforced at both route and database layers.
2. **Transparent Resource Discovery**: A multi-criteria catalogue enabling students to search by keyword, category, physical building location, and asset type (Equipment vs. Space), including safety prerequisites.
3. **Automated Reservation & Conflict Engine**: Interval-overlap prevention algorithms that block double-booking, enforce maximum loan durations (14 days), and reject booking attempts on inactive or maintained assets.
4. **Verifiable Two-Point Physical Custody**: Digital condition reports recorded both at **Check-In** (asset release) and **Return** (asset intake), capturing physical ratings and baseline notes to resolve equipment damage disputes.
5. **Formal Incident Escalation & Resolution**: Built-in reporting system allowing students and custodians to document damage, operational defects, or missing accessories, complete with administrative status tracking (`open`, `under_review`, `resolved`).

---

## 🔄 3. End-to-End Borrowing Workflow

ResourceBridge models the realistic, physical borrowing lifecycle across seven discrete stages:

```
[1. Discovery] ➔ [2. Reservation] ➔ [3. Manager Review] ➔ [4. Physical Check-In] ➔ [5. Active Loan] ➔ [6. Return Inspection] ➔ [7. Closed / Incident]
```

1. **Discovery & Inspection**: A student browses `/resources`, filters by category/location, and views detailed prerequisites, safety guidelines, and custodian contact information.
2. **Reservation Request**: The student submits a booking request specifying desired start and end timestamps and project purpose. The system verifies:
   - Valid forward-looking dates (start time >= current time; end time > start time).
   - Maximum loan window constraint (<= 14 days).
   - No temporal overlap with existing `approved` or `active` bookings.
   - Resource status is `active`.
3. **Manager Review & Approval**: The designated department manager reviews pending requests in `/manager/bookings`. When approved, a process-level mutex lock (`threading.Lock`) combined with pre-commit database re-checks guarantees atomic conflict prevention under concurrent requests.
4. **Physical Check-In**: Upon meeting in person at the lab, the custodian inspects the asset, files a digital **Check-In Condition Report** (rating: `excellent`, `good`, `fair`, `poor` with mandatory notes), and marks the asset as `checked_in` (active loan).
5. **Active Loan Custody**: The student dashboard displays ongoing loan status, scheduled return time, and custodian contact details.
6. **Return Handover Request & Inspection**: The borrower signals return readiness, and the custodian conducts a physical intake inspection, records a **Return Condition Report**, and marks the booking as `returned`. The resource immediately becomes available for subsequent approved reservations.
7. **Incident Handling & Audit Trail**: If damage or discrepancies occur, either party logs an Incident Report (`/bookings/<id>/incidents`). All lifecycle events, status changes, and actor decisions are immutably logged to the `BookingAuditLog`.

---

## 🛠️ 4. Technology Stack

ResourceBridge intentionally adheres to a lean, approachable, and maintainable Python web architecture without unnecessary single-page application frameworks or complex microservices:

| Layer | Component | Technical Selection | Rationale |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | WSGI Web Framework | **Python 3.10+ / Flask 3.0** | Minimal boilerplate, explicit routing, readable architecture |
| **Database & ORM** | Relational Database & Layer | **SQLite + Flask-SQLAlchemy 3.1** | Zero-configuration file storage, relational integrity, ACID transactions |
| **Authentication** | Session & User Management | **Flask-Login 0.6** | Robust session lifecycle, `@login_required`, role isolation |
| **Security & Cryptography** | Password Hashing & Defense | **Werkzeug Security + Custom Middleware** | PBKDF2 salted hashes, CSRF validation, HTTP defense headers, safe redirect filters |
| **Production WSGI** | WSGI Server Entrypoint | **Gunicorn / Waitress / wsgi.py** | Production-ready process serving, standard PaaS compatibility |
| **Frontend Templates** | Server-Side Rendering | **Jinja2 HTML5 Templates** | Automatic contextual XSS escaping, clean component reuse |
| **Styling & UI** | Design System | **Custom Academic Slate CSS** | High contrast, calm professional palette, zero Tailwind/Bootstrap overhead |
| **Interactivity** | Client Scripting | **Vanilla JavaScript (ES6)** | Zero framework dependencies; handles demo profile autofill and UI toggles |
| **Test Suite** | Testing Framework | **Pytest 9.1** | 68 automated unit, integration, security, and UI regression tests |

---

## 📂 5. Project Directory Structure

```text
resourcebridge/
├── app.py                          # Application factory, routes, security middleware, error handlers, CLI
├── models.py                       # SQLAlchemy models: User, Resource, Booking, ConditionReport, Incident, BookingAuditLog
├── seed_demo.py                    # Standalone database seeder (users, resources, demo bookings, audit logs)
├── wsgi.py                         # Production WSGI server entrypoint
├── Procfile                        # Cloud deployment process configuration (gunicorn wsgi:app)
├── runtime.txt                     # Target Python runtime specification
├── requirements.txt                # Pinned dependencies (Flask, SQLAlchemy, Flask-Login, Gunicorn, Pytest)
├── README.md                       # Comprehensive project documentation and hackathon presentation guide
├── .env.example                    # Environment variable template
├── .gitignore                      # Excludes SQLite databases, __pycache__, virtual environments, and local reports
├── instance/
│   └── resourcebridge.db           # SQLite database file (auto-created on first run)
├── templates/
│   ├── base.html                   # Master layout with responsive navbar, flash alerts, and accessible footer
│   ├── index.html                  # Public landing page with live database featured items & architecture pillars
│   ├── about.html                  # Problem statement, campus sharing principles, and technical roadmap
│   ├── login.html                  # Sign-in form with 1-Click Hackathon Demo Profile selectors & CSRF
│   ├── register.html               # Registration form with strict student role locking & validation
│   ├── dashboard.html              # Role-aware dashboard with live statistics & booking tables
│   ├── 403.html                    # Safe Forbidden access page with user-friendly recovery links
│   ├── 404.html                    # Safe Not Found page for invalid routes or missing resources
│   ├── 500.html                    # Safe Internal Server Error page with database rollback notice
│   ├── resources/
│   │   ├── index.html              # Searchable resource catalogue with category & location filter pills
│   │   ├── detail.html             # Detailed asset specs, custodian profile, and sticky booking panel
│   │   ├── form.html               # Resource creation and editing form with CSRF protection
│   │   └── manage.html             # Inventory management table for department managers and admins
│   └── bookings/
│       ├── detail.html             # Full booking lifecycle overview, timeline, condition reports, incident logs
│       ├── manager_list.html       # Custodian approval queue with conflict badges and inline reject controls
│       └── student_list.html       # Student reservation tracking table with status filters
├── static/
│   ├── css/
│   │   └── style.css               # Design system: academic slate palette, high-contrast tokens, accessible focus rings
│   └── js/
│       └── main.js                 # 1-click login autofill, mobile menu toggling, prerequisite toggles
└── tests/
    ├── __init__.py
    ├── test_auth.py                # 11 tests: password hashing, role escalation blocking, login/logout, dashboard rendering
    ├── test_resources.py           # 15 tests: resource CRUD, search queries, location/category filters, empty states
    ├── test_bookings.py            # 14 tests: booking creation, 14-day limits, manager approval, double-booking prevention
    ├── test_lifecycle.py           # 11 tests: physical check-in, return inspection, incident logging, privacy
    ├── test_security.py            # 13 tests: HTTP security headers, session flags, CSRF defense, open redirect, concurrency locks
    └── test_frontend.py            # 4 tests: redesigned UI components, accessibility, about page roadmap, demo selectors
```

---

## 🐍 6. Python Backend Walkthrough

The backend is organized around standard, conventional Python/Flask design patterns:

### Application Factory (`app.py:create_app`)
- Initializes Flask with environment-driven configuration (testing, development, production).
- Configures SQLAlchemy, Flask-Login, and session cookie security parameters.
- Registers route blueprints/endpoints, security response headers (`@app.after_request`), safe error handlers (`403`, `404`, `500`), and CLI commands.

### Authentication & Authorization Flow
- Passwords are encrypted using Werkzeug PBKDF2 (`scrypt`/`pbkdf2:sha256`) with salted hashes.
- Role checks utilize Python decorators (`@login_required`, `@manager_required`, `@admin_required`) to prevent unauthorized route execution.
- Open Redirect defense utilizes an RFC-compliant URI parser (`is_safe_redirect_url`) validating relative paths and explicitly rejecting leading double-slashes (`//`).

### Concurrency & Conflict Prevention
- Multi-threaded booking approvals are synchronized via an in-memory `threading.Lock` (`approval_lock`).
- Inside the lock, `db.session.refresh(booking)` re-reads the latest database state, executes interval overlap validation against all active/approved bookings, commits atomically, and releases the lock.

---

## 🚀 7. Local Setup & Quick Start

### Prerequisites
- **Python 3.10+** (Tested on Python 3.10, 3.11, 3.12, 3.14)
- **pip** package installer

### Step 1: Clone or Navigate to Project Directory
```bash
cd resourcebridge
```

### Step 2: Set Up Virtual Environment (Recommended)
```bash
# On Linux/macOS
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Environment Variables (Optional)
The application provides safe local development defaults. To customize secrets or set production parameters, copy `.env.example`:
```bash
cp .env.example .env
```
*(On Windows: `copy .env.example .env`)*

### Step 5: Initialize Database & Seed Demonstration Data
Run the standalone database initialization script:
```bash
python seed_demo.py
```
*Alternatively, you can initialize via the Flask CLI:*
```bash
flask init-db
flask seed
```

### Step 6: Launch the Application
```bash
python app.py
```
*Or via the production WSGI entrypoint:*
```bash
python wsgi.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🧪 8. Running the Automated Test Suite

ResourceBridge includes an exhaustive regression and security test suite covering **70 test cases**:

```bash
# Run all tests with verbose output
python -m pytest -v

# Run targeted test suites
python -m pytest tests/test_security.py -v
python -m pytest tests/test_lifecycle.py -v
python -m pytest tests/test_bookings.py -v
python -m pytest tests/test_resources.py -v
python -m pytest tests/test_frontend.py -v
python -m pytest tests/test_auth.py -v
```

### Current Test Suite Summary
- **Total Tests**: **70 passed** (0 failed, 0 skipped)
- **Execution Runtime**: ~35 seconds
- **Code Coverage Areas**: Authentication, role escalation defense, CSRF token verification, open redirect mitigation, session cookie parameters, HTTP defense headers, object-level privacy authorization, conflict detection, physical condition tracking, incident escalation, multi-threaded race conditions, and frontend redesign layout, and health monitoring endpoint (/health).

---

## 🔑 9. Demonstration Accounts & Roles

For local hackathon demonstrations, the database is pre-populated with three distinct personas.

> ⚠️ **DEMO NOTICE**: The credentials below are provided **exclusively for local evaluation and hackathon judging**. Never deploy demo credentials to public environments.

| Role | Persona Name | Email | Password | Primary Demo Responsibilities |
| :--- | :--- | :--- | :--- | :--- |
| **Student (Borrower)** | Alex Rivera | `student@campus.edu` | `StudentPass123!` | Search resources, submit booking requests, view active loans, report incidents |
| **Manager (Custodian)** | Dr. Elena Vance | `manager@campus.edu` | `ManagerPass123!` | Review pending bookings, approve/reject requests, record physical check-in and return condition |
| **Administrator** | Marcus Brody | `admin@campus.edu` | `AdminPass123!` | Manage all departmental resources, review safety incidents, audit platform usage |

> 💡 **Hackathon 1-Click Evaluation**: On the **Sign In** screen (`/login`), click any of the **1-Click Demo Profile** buttons to automatically fill the credentials and sign in instantly!

---

## ☁️ 10. Deployment Configuration & Persistence Disclosures

### 🌐 Verified Live Hackathon Deployment
- **Live Public URL**: 👉 **[https://resourcebridge-79f6.onrender.com](https://resourcebridge-79f6.onrender.com)**
- **Health Check Endpoint**: [https://resourcebridge-79f6.onrender.com/health](https://resourcebridge-79f6.onrender.com/health) (`HTTP 200 OK`, `{"status": "healthy", "database": "connected"}`)
- **Hosting Platform**: Render.com (Cloud Web Service, Native GitHub Integration)
- **Deployment Architecture**: Gunicorn 21.2 (`--workers 1 --threads 4 --timeout 60`) on Python 3.11.8
- **Security & Transport**: Enforced TLS/HTTPS, `SESSION_COOKIE_SECURE=True`, `HttpOnly`, `SameSite=Lax`, HTTP security headers (`nosniff`, `SAMEORIGIN`, `X-XSS-Protection`)
- **Live Multi-Role Verification**: Verified live HTTP authentication and dashboard access across Student (Alex Rivera), Facility Manager (Dr. Elena Vance), and System Admin (Marcus Brody).

### Production WSGI Server Configuration
The repository includes standard production deployment artifacts:
- `wsgi.py`: Production WSGI entrypoint with automatic database table verification and seed fallback (`app = create_app()`).
- `Procfile`: Process manager configuration declaring `web: gunicorn wsgi:app --workers 1 --threads 4 --timeout 60`.
- `runtime.txt`: Locked Python target runtime (`python-3.11.8`).
- `requirements.txt`: Pinned dependencies including `gunicorn>=21.2.0`, `Flask>=3.0.0`, and `Flask-SQLAlchemy>=3.1.0`.

### Production Environment Variables Reference

| Variable Name | Required? | Recommended Production Value | Description |
| :--- | :---: | :--- | :--- |
| `FLASK_ENV` | **Yes** | `production` | Enforces production security checks and disables debug mode. |
| `SECRET_KEY` | **Yes** | *(Generate via `python -c "import secrets; print(secrets.token_hex(32))"`)* | Cryptographic key for session cookies and CSRF protection. In production, application will raise `RuntimeError` if missing. |
| `SESSION_COOKIE_SECURE` | **Yes** | `true` | Ensures authentication cookies are only transmitted over secure HTTPS connections. |
| `DATABASE_URL` | Optional | `postgresql://user:pass@host/db` | Defaults to SQLite (`sqlite:///instance/resourcebridge.db`). If connecting managed PostgreSQL, automatically normalizes legacy `postgres://` prefixes. |
| `PYTHON_VERSION` | Optional | `3.11.8` | Declares Python runtime for buildpacks. |

---

### Step-by-Step Deployment Guide: Render.com (Recommended Free Tier)

Render provides a 100% free Web Service tier with automatic SSL/TLS (`https://*.onrender.com`), native GitHub integration, and zero credit card requirement:

1. **Sign In & Create Web Service**:
   - Navigate to [Render Dashboard](https://dashboard.render.com).
   - Click **New +** -> **Web Service**.
   - Connect your GitHub account and select repository: `syedhamzah-dev/resourcebridge`.

2. **Configure Service Details**:
   - **Name**: `resourcebridge` (or custom subdomain)
   - **Region**: Choose closest to your judges (e.g., Frankfurt, Oregon, Singapore)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && flask init-db`
   - **Start Command**: `gunicorn wsgi:app --workers 1 --threads 4 --timeout 60`
   - **Instance Type**: `Free`

3. **Set Environment Variables** (Under *Advanced* -> *Add Environment Variable*):
   - `FLASK_ENV` = `production`
   - `SECRET_KEY` = `<paste-your-generated-64-character-hex-string>`
   - `SESSION_COOKIE_SECURE` = `true`
   - `PYTHON_VERSION` = `3.11.8`

4. **Deploy**:
   - Click **Create Web Service**. Render will build and deploy the container in ~2 minutes.
   - Upon completion, your live URL will be: `https://<service-name>.onrender.com`.

5. **Verify Live Deployment**:
   - Check Health Endpoint: `curl -I https://<service-name>.onrender.com/health` (Returns HTTP 200 `{"status": "healthy", ...}`).
   - Verify Catalog: Open `https://<service-name>.onrender.com` in your browser.
   - Test Demo Login: Navigate to `/login` and test 1-Click Demo Profiles.

---

### Alternative Deployment Options

- **Railway.app**:
  1. Click **New Project** -> **Deploy from GitHub repo**.
  2. Add environment variables (`FLASK_ENV=production`, `SECRET_KEY=...`).
  3. Railway auto-detects `Procfile` and assigns a public `*.up.railway.app` URL.

- **PythonAnywhere (Native Persistent SQLite)**:
  1. Open a Web app on PythonAnywhere (Manual configuration, Python 3.11).
  2. Clone repository into `~/resourcebridge`.
  3. Point the WSGI configuration file to `from wsgi import app as application`.
  4. Native persistent disk preserves SQLite across all restarts without container wipes.

---

### Honest Technical Disclosures: SQLite Persistence & Concurrency
1. **SQLite Ephemeral Filesystem Warning**:
   Standard free-tier cloud containers (e.g., Render Free, Heroku Dynos) operate on ephemeral filesystems. Any writes to `instance/resourcebridge.db` will reset upon container restart or redeployment unless a persistent disk volume is mounted (e.g., Render Persistent Disk mounted at `/var/data` or Railway persistent volume).
   *Built-in Mitigation:* ResourceBridge's `wsgi.py` automatically checks and seeds the complete demo state (Student, Manager, Admin, 4 core campus resources, sample bookings) on every container cold start, ensuring hackathon judges always land on a pristine, fully populated working demo! For long-term multi-user production, connecting a managed PostgreSQL database via `DATABASE_URL` is recommended.
2. **Process-Level Locking vs. Distributed Locking**:
   The current race-condition prevention utilizes an in-memory `threading.Lock` within `approve_booking`. Running Gunicorn with `--workers 1 --threads 4` guarantees that all concurrent requests are processed within a single Python process, fully preventing double-bookings. In horizontally scaled multi-worker or multi-server distributed clusters (`gunicorn -w 4`), distributed database locking (such as PostgreSQL `SELECT ... FOR UPDATE`) or Redis-based distributed locks should be utilized.

---

## 🔒 11. Security, Privacy & Integrity Hardening

ResourceBridge underwent comprehensive application security hardening:

1. **Role Escalation Prevention**: Public registration (`/register`) explicitly hardcodes user creation to `role='student'`. Form payloads attempting to inject `role='admin'` or `role='manager'` are safely rejected.
2. **Object-Level Authorization & Privacy**:
   - Students can only view and manage their own booking records. Direct access to `/bookings/<id>` for unauthorized users returns `403 Forbidden`.
   - Department managers can only review, approve, check in, or return assets owned by their department. Unauthorized managers attempting cross-departmental operations are rejected with `403 Forbidden`.
3. **Session Cookie Security**:
   - `SESSION_COOKIE_HTTPONLY = True` (prevents client-side JavaScript access via XSS).
   - `SESSION_COOKIE_SAMESITE = 'Lax'` (mitigates cross-site request forgery in top-level navigations).
   - `SESSION_COOKIE_SECURE` automatically enables in production environments (`FLASK_ENV=production`).
   - Session duration capped with `PERMANENT_SESSION_LIFETIME = 8 hours`.
4. **HTTP Defense-in-Depth Headers**: Injected automatically via an `@app.after_request` hook:
   - `X-Content-Type-Options: nosniff` (prevents MIME sniffing).
   - `X-Frame-Options: SAMEORIGIN` (prevents UI clickjacking attacks).
   - `X-XSS-Protection: 1; mode=block` (activates browser legacy XSS filters).
   - `Referrer-Policy: strict-origin-when-cross-origin` (protects private URLs during outbound navigation).
5. **CSRF Protection & Safe Referrer Redirection**:
   - Every state-changing form incorporates a hidden `csrf_token` validated on submission.
   - User-supplied redirect destinations (`next` parameter) are validated using RFC-compliant URI splitting (`is_safe_redirect_url`).
6. **SQL Injection Defense**: All database queries are executed via SQLAlchemy ORM parameterized methods. Zero raw SQL string formatting is used anywhere in the codebase.
7. **Cross-Site Scripting (XSS) Defense**: All user-supplied input rendered in Jinja2 templates is automatically HTML-escaped. No unsafe `| safe` filter bypasses are used on user content.
8. **Double-Booking & Concurrency Protection**:
   - Reservation intervals are checked via SQL queries checking `(existing_start < requested_end) and (existing_end > requested_start)` for any booking in `['approved', 'checked_in']`.
   - In-memory `threading.Lock` prevents thread race conditions during approval.
9. **Centralized Safe Error Handling**:
   - Custom `403.html`, `404.html`, and `500.html` templates prevent technical stack trace or sensitive directory disclosures to clients.
   - The `500` handler automatically invokes `db.session.rollback()` to ensure failed operations do not leave the database transaction in a poisoned state.
10. **Environment-Aware Configuration**:
    - `SECRET_KEY` validation raises a `RuntimeError` if left on default fallback in production.
    - `app.run(debug=False)` is enforced when running in production mode.

---

## 🤖 12. Authorship Transparency & AI Assistance Disclosure

In accordance with hackathon competition rules and transparency best practices:
- **Primary Developer & Project Architect**: Solo student engineer.
  - Primary technical responsibility: Python/Flask backend architecture, data model schema, database migration/seeding, lifecycle state machine implementation, authorization decorators, concurrency locking, and regression test suites.
- **AI Tool Utilized**: Google Antigravity IDE (Gemini-powered coding assistant).
- **Scope of AI Assistance**:
  - The AI assistant served as an interactive pair-programming partner, helping author test cases, structure CSS variables, diagnose template rendering edge cases, and conduct systematic security and concurrency audits.
  - All architecture decisions, domain schemas, route boundaries, security controls, bug fixes, and documentation were reviewed, validated, and verified by the student developer.
  - All test logs, commit histories, and code changes are preserved with full traceability.

---

## 📜 13. License

This project is developed for educational and hackathon demonstration purposes under the **MIT License**.
