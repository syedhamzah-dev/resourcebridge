# 🌉 ResourceBridge

> **Campus Resource Sharing Network with Trust, Safety, and Physical Accountability**  
> *A secure, full-stack college resource management platform built for hackathon demonstration.*

[![Tests](https://img.shields.io/badge/tests-59%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Flask](https://img.shields.io/badge/flask-3.0%2B-black.svg)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

---

## 📖 1. Problem Statement & Intended Users

### The Problem
In college and university campuses, millions of dollars worth of specialized equipment and facilities—such as **photonic microscopes, cinema-grade cameras, deep-learning GPU workstations, VR headsets, 3D printers, and seminar spaces**—sit idle behind locked departmental doors after 4:00 PM. Simultaneously, enterprising students pursuing capstone engineering projects, research papers, or startup prototypes cannot access this critical equipment due to fragmented departmental silos, lack of trust, fear of unreturned gear, and informal paper-based sign-out clipboards.

### Intended Users
1. **Students (Borrowers)**: Third-year and postgraduate students needing high-end resources for academic or extracurricular coursework, verified by campus credentials.
2. **Lab & Department Managers (Custodians)**: Faculty members, lab directors, and department technicians who own and safeguard institutional assets, requiring verifiable chain-of-custody tracking.
3. **Campus Administrators (Auditors)**: Institutional oversight officers responsible for campus-wide inventory compliance, safety policy enforcement, and incident dispute resolution.

---

## 💡 2. Solution Overview & Core Architecture

**ResourceBridge** establishes a secure, structured physical asset lending network built around five foundational pillars:

1. **Role-Based Access Control (RBAC)**: Strict segregation among `student`, `manager`, and `admin` roles, enforced at both route and database layers.
2. **Transparent Resource Discovery**: A multi-criteria catalogue enabling students to search by keyword, category, physical building location, and asset type (Equipment vs. Space).
3. **Automated Reservation & Conflict Engine**: Interval-overlap prevention algorithms that block double-booking, enforce maximum loan durations (7 days), and reject booking attempts on inactive or maintained assets.
4. **Verifiable Two-Point Physical Custody**: Digital condition reports recorded both at **Check-In** (asset release) and **Return** (asset intake), capturing physical ratings and baseline notes to resolve equipment damage disputes.
5. **Formal Incident Escalation & Resolution**: Built-in reporting system allowing students and custodians to document damage, operational defects, or missing accessories, complete with administrative status tracking (`open`, `investigating`, `resolved`).

---

## 🔄 3. End-to-End Borrowing Workflow

ResourceBridge models the realistic, physical borrowing lifecycle across seven discrete stages:

```
[1. Discovery] ➔ [2. Reservation] ➔ [3. Manager Review] ➔ [4. Physical Check-In] ➔ [5. Active Loan] ➔ [6. Return Inspection] ➔ [7. Closed / Incident]
```

1. **Discovery & Inspection**: A student browses `/resources`, filters by category/location, and views detailed prerequisites, safety guidelines, and custodian contact information.
2. **Reservation Request**: The student submits a booking request specifying desired start and end timestamps and project purpose. The system verifies:
   - Valid forward-looking dates (start time >= current time; end time > start time).
   - Maximum loan window constraint (<= 7 days).
   - No temporal overlap with existing `approved` or `active` bookings.
   - Resource status is `active`.
3. **Manager Review & Approval**: The designated department manager reviews pending requests in `/manager/bookings`. When approved, competing conflicting pending requests are flagged, and atomic pre-commit validation ensures no race condition double-booking occurs.
4. **Physical Check-In**: Upon meeting in person at the lab, the custodian inspects the asset, files a digital **Check-In Condition Report** (rating: `excellent`, `good`, `fair`, `poor` with mandatory notes), and marks the asset as `active` (checked out).
5. **Active Loan Custody**: The student dashboard displays the ongoing loan status, countdown to return due date, and custodian emergency contact details.
6. **Return Inspection Verification**: When returning the asset, the manager conducts a return inspection, files a **Return Condition Report**, and marks the booking as `returned`. The resource immediately becomes available for subsequent approved reservations.
7. **Incident Handling (If Applicable)**: If damage or discrepancies occur, either party logs a formal Incident Report (`/bookings/<id>/incident`). Managers can update the incident status to `investigating` or `resolved` with documented administrative resolutions.

---

## 🛠️ 4. Technology Stack

ResourceBridge intentionally adheres to a lean, approachable, and maintainable Python web architecture without unnecessary single-page application frameworks or complex microservices:

| Layer | Component | Technical Selection | Rationale |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | WSGI Web Framework | **Python 3.10+ / Flask 3.0** | Minimal boilerplate, explicit routing, readable architecture |
| **Database & ORM** | Relational Database & Layer | **SQLite + Flask-SQLAlchemy 3.1** | Zero-configuration file storage, relational integrity, ACID transactions |
| **Authentication** | Session & User Management | **Flask-Login 0.6** | Robust session lifecycle, `@login_required`, role isolation |
| **Security & Cryptography** | Password Hashing & Defense | **Werkzeug Security + Custom Middleware** | `scrypt`/`pbkdf2` salted hashes, CSRF validation, HTTP defense headers |
| **Frontend Templates** | Server-Side Rendering | **Jinja2 HTML5 Templates** | Automatic contextual XSS escaping, clean component reuse |
| **Styling & UI** | Design System | **Vanilla CSS3 (Responsive Grid/Flexbox)** | Custom clean aesthetic, high contrast, zero Tailwind/Bootstrap overhead |
| **Interactivity** | Client Scripting | **Vanilla JavaScript (ES6)** | Zero framework dependencies; handles demo profile autofill and UI toggles |
| **Test Suite** | Testing Framework | **Pytest 9.1** | 59 automated unit, integration, security, and lifecycle tests |

---

## 📂 5. Project Directory Structure

```text
resourcebridge/
├── app.py                          # Application factory, routes, security middleware, error handlers, CLI
├── models.py                       # SQLAlchemy models: User, Resource, Booking, ConditionReport, Incident
├── seed_demo.py                    # Standalone database seeder (users, resources, demo bookings)
├── requirements.txt                # Pinned dependencies (Flask, SQLAlchemy, Flask-Login, Pytest, etc.)
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
│   │   ├── detail.html             # Detailed asset specs, custodian profile, and booking action button
│   │   ├── form.html               # Resource creation and editing form with CSRF protection
│   │   └── manage.html             # Inventory management table for department managers and admins
│   └── bookings/
│       ├── book.html               # Booking submission form with duration guidelines and time pickers
│       ├── detail.html             # Full booking lifecycle overview, timeline, reports, and incident logs
│       ├── manager_review.html     # Custodian approval queue with conflict badges and reject modals
│       ├── checkin.html            # Physical handoff inspection form (condition rating + notes)
│       ├── return.html             # Return verification form (intake rating + maintenance toggle)
│       └── report_incident.html    # Incident logging form for damage or operational discrepancies
├── static/
│   ├── css/
│   │   └── style.css               # Design system: typography, cards, badges, modal dialogs, responsive tables
│   └── js/
│       └── main.js                 # 1-click login autofill, mobile menu toggling, modal controls
└── tests/
    ├── __init__.py
    ├── test_auth.py                # 11 tests: password hashing, role escalation blocking, login/logout
    ├── test_resources.py           # 15 tests: resource CRUD, search queries, location/category filters
    ├── test_bookings.py            # 14 tests: booking creation, 7-day limits, manager approval, double-booking prevention
    ├── test_lifecycle.py           # 11 tests: physical check-in, return inspection, incident logging, privacy
    └── test_security.py            # 8 tests: HTTP security headers, session flags, CSRF defense, 403/404, race checks
```

---

## 🚀 6. Local Setup & Quick Start

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
Open your browser and navigate to:  
👉 **`http://127.0.0.1:5000`**

---

## 🧪 7. Running the Automated Test Suite

ResourceBridge includes an exhaustive regression and security test suite covering **59 test cases**:

```bash
# Run all tests with verbose output
pytest -v

# Run targeted test suites
pytest tests/test_security.py -v
pytest tests/test_lifecycle.py -v
pytest tests/test_bookings.py -v
pytest tests/test_resources.py -v
pytest tests/test_auth.py -v
```

### Current Test Suite Summary
- **Total Tests**: **59 passed** (0 failed, 0 skipped)
- **Execution Runtime**: ~27 seconds
- **Code Coverage Areas**: Authentication, role escalation defense, CSRF token verification, open redirect mitigation, session cookie parameters, HTTP defense headers, object-level privacy authorization, conflict detection, physical condition tracking, and incident escalation.

---

## 🔑 8. Demonstration Accounts & Roles

For local hackathon demonstrations, the database is pre-populated with three distinct personas. 

> ⚠️ **DEMO NOTICE**: The credentials below are provided **exclusively for local evaluation and hackathon judging**. Never deploy demo credentials to public environments.

| Role | Persona Name | Email | Password | Primary Demo Responsibilities |
| :--- | :--- | :--- | :--- | :--- |
| **Student (Borrower)** | Alex Rivera | `student@campus.edu` | `StudentPass123!` | Search resources, submit booking requests, view active loans, report incidents |
| **Manager (Custodian)** | Dr. Elena Vance | `manager@campus.edu` | `ManagerPass123!` | Review pending bookings, approve/reject requests, record physical check-in and return condition |
| **Administrator** | Marcus Brody | `admin@campus.edu` | `AdminPass123!` | Manage all departmental resources, review safety incidents, audit platform usage |

> 💡 **Hackathon Speed-Demonstration**: On the **Sign In** screen (`/login`), click any of the **1-Click Demo Profile** buttons to automatically fill the credentials and sign in instantly!

---

## 🔒 9. Security, Privacy & Integrity Hardening

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
   - CSRF validation failures safely redirect to origin; external domain open-redirect vectors are strictly filtered.
6. **SQL Injection Defense**: All database queries are executed via SQLAlchemy ORM parameterized methods. Zero raw SQL string formatting is used anywhere in the codebase.
7. **Cross-Site Scripting (XSS) Defense**: All user-supplied input rendered in Jinja2 templates is automatically HTML-escaped. No unsafe `| safe` filter bypasses are used on user content.
8. **Double-Booking & Concurrency Protection**:
   - Reservation intervals are checked via SQL queries checking `(existing_start < requested_end) and (existing_end > requested_start)` for any booking in `['approved', 'active']`.
   - An atomic pre-commit conflict re-check occurs inside the transaction commit block in both `book_resource` and `approve_booking`, ensuring near-simultaneous submissions fail safely.
9. **Centralized Safe Error Handling**:
   - Custom `403.html`, `404.html`, and `500.html` templates prevent technical stack trace or sensitive directory disclosures to clients.
   - The `500` handler automatically invokes `db.session.rollback()` to ensure failed operations do not leave the database transaction in a poisoned state.
10. **Environment-Aware Configuration**:
    - `SECRET_KEY` validation raises a `RuntimeError` if left on the default development fallback when `FLASK_ENV=production`.
    - `app.run(debug=False)` is enforced when running in production mode.

---

## ⚠️ 10. Honest Disclosures, Known Limitations & Roadmap

In adherence to hackathon academic integrity standards, the current technical limitations and operational scope are documented transparently:

### Current Limitations
1. **Physical File Uploads**: Condition reports and incident tickets currently rely on comprehensive structured text notes and categorical ratings (`excellent`, `good`, `fair`, `poor`). Direct image/photo file attachments are planned for future cloud storage integration (e.g., AWS S3).
2. **Email Notifications**: System alerts and status updates are presented via in-app flash banners and real-time dashboard notification badges. Outbound SMTP email dispatch is not enabled in local mode to avoid external delivery dependencies.
3. **Database Architecture**: The project runs on SQLite for portable zero-configuration local evaluation. For multi-tenant production concurrency under heavy write loads, migrating to PostgreSQL with row-level pessimistic locking (`SELECT ... FOR UPDATE`) is recommended.
4. **Campus Verification**: Student and faculty accounts are verified via seeded campus email domains (`@campus.edu`). Live Single Sign-On (SSO / SAML 2.0 / Shibboleth) integration remains an institutional roadmap feature.

### Future Roadmap
- [ ] Direct AWS S3 / Cloudinary photo upload integration for damaged gear evidence.
- [ ] Institutional SSO / OAuth2 (Google Workspace, Microsoft Entra ID) authentication.
- [ ] Automated QR-code scanning for rapid mobile physical check-in and check-out.
- [ ] Automated overdue notification reminders via email/SMS.
- [ ] Departmental budget transfers for equipment replacement or repair fees.

---

## 🤖 11. AI-Assisted Development Disclosure

In accordance with hackathon competition rules and transparency best practices:
- **Developer & Presenter**: Solo third-year student developer.
- **AI Tool Utilized**: Google Antigravity IDE (Gemini-powered coding agent).
- **Scope of AI Assistance**:
  - The AI assistant served as an interactive pair-programming partner, helping author test suites, scaffold template structures, verify SQL conflict queries, and conduct systematic security code audits.
  - All architecture decisions, domain model schemas, lifecycle state machines, security policies, and documentation were reviewed, validated, and tested by the student developer.
  - All test logs, commit histories, and code changes are preserved with full traceability.

---

## 📜 12. License

This project is developed for educational and hackathon demonstration purposes under the **MIT License**.
