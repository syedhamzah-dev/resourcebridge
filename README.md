# 🌉 ResourceBridge

> **Campus Resource Sharing Network with Trust, Safety, and Accountability**  
> *College Hackathon 24-Hour Project — Stage 1 Foundation*

---

## 📖 1. What is ResourceBridge?

In almost every college or university, expensive specialized resources—such as **photonic microscopes, 4K cinema cameras, AI deep learning rigs, VR development kits, 3D printers, and seminar suites**—sit locked away and idle after 4:00 PM. Meanwhile, students building capstones or startup prototypes cannot access the gear they need.

**ResourceBridge** bridges this divide. It provides an institutional sharing network designed around **trust, safety, fair access, and accountability**:
- **Identity & Verification**: Every member belongs to an authenticated, verified campus profile.
- **Role-Based Access Control (RBAC)**: Segregated privileges for Students (borrowers), Department Managers (approvers & inspectors), and Administrators (policy stewards).
- **Zero Hoarding Safeguards**: Prevents equipment monopolization with reservation caps and fair-allocation schedules.
- **End-to-End Lifecycle**: Tracks assets from discovery and reservation to physical check-out inspection and condition verification on return.

---

## 🛠️ 2. Technology Stack

ResourceBridge is intentionally built with clean, reliable, and approachable technology—no complex JavaScript frameworks or heavy microservices:

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+ / Flask | Lightweight, readable WSGI web application framework |
| **Database** | SQLite + Flask-SQLAlchemy | File-based, zero-configuration SQL database and ORM |
| **Authentication** | Flask-Login | User session management and protected route handlers |
| **Security** | Werkzeug Security | Industry-standard password hashing (`scrypt` / `pbkdf2`) |
| **Frontend** | Jinja2 HTML5 + Vanilla CSS + JS | Responsive, modern campus UI without frontend framework bloat |
| **Testing** | Pytest | Automated unit and integration test suite |

---

## 📂 3. Project Directory Structure

```text
resourcebridge/
├── app.py                  # Main Flask application, routes, auth handlers, resource catalog & CLI
├── models.py               # User and Resource database models, validation & relationships
├── seed_demo.py            # Standalone demo seeding script (users and campus resources)
├── requirements.txt        # Pinned Python package dependencies
├── README.md               # Complete project documentation and presentation guide
├── .env.example            # Environment configuration template
├── .gitignore              # Ignores __pycache__, SQLite DBs, local virtualenvs & /reports/local/
├── instance/
│   ├── .gitkeep
│   └── resourcebridge.db   # SQLite database file (created automatically)
├── templates/
│   ├── base.html           # Master layout with responsive navbar, flash alerts, and footer
│   ├── index.html          # Public landing page with live database featured resources
│   ├── about.html          # Problem statement, architecture pillars, and roadmap
│   ├── login.html          # Sign-in form with 1-click Hackathon Demo Profile selectors & CSRF
│   ├── register.html       # Student registration form with strict role security & CSRF
│   ├── dashboard.html      # Role-aware dashboard with live database queries
│   ├── 404.html            # Graceful error handler for missing resources
│   └── resources/
│       ├── index.html      # Searchable resource catalogue with multi-criteria filters
│       ├── detail.html     # Resource specifications, safety prerequisites & Stage 2 notice
│       ├── form.html       # Resource creation and edit form with CSRF protection
│       └── manage.html     # Departmental inventory management table for managers/admins
├── static/
│   ├── css/
│   │   └── style.css       # Design system, resource cards, status badges & responsive layout
│   └── js/
│       └── main.js         # Mobile nav, password toggle, demo autofill & form prerequisites
└── tests/
    ├── __init__.py
    ├── test_auth.py        # 11 automated tests covering auth, roles, and security
    └── test_resources.py   # 15 automated tests covering resource CRUD, search & filtering
```

---

## 🚀 4. Quick Start (Step-by-Step)

### Step 1: Install Dependencies
Open your terminal in the `resourcebridge` folder:

```bash
pip install -r requirements.txt
```

### Step 2: Initialize Database and Seed Demo Accounts
Run the standalone setup script:

```bash
python seed_demo.py
```

*Alternatively, you can use the Flask CLI commands:*
```bash
flask init-db
flask seed
```

### Step 3: Run the Application
Start the local development server:

```bash
python app.py
```

Open your browser and navigate to:  
👉 **`http://127.0.0.1:5000`**

### Step 4: Run the Automated Tests
Verify that all 11 security and authentication tests pass:

```bash
pytest -v
```

---

## 🔑 5. Demonstration Accounts

For presentation and judging, three pre-seeded demonstration accounts are included. Passwords are fully hashed with Werkzeug and safely configured for development testing:

| Persona | Name | Email | Password | Role | Access Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Student** | Alex Rivera | `student@campus.edu` | `StudentPass123!` | `student` | Request resources, view active loans & trust score |
| **Manager** | Dr. Elena Vance | `manager@campus.edu` | `ManagerPass123!` | `manager` | Department inventory, loan approvals, condition check |
| **Administrator** | Marcus Brody | `admin@campus.edu` | `AdminPass123!` | `admin` | Safety logs, campus user registry, governance policies |

> 💡 **Hackathon Tip**: On the **Sign In** page (`/login`), click any of the **1-Click Demo Profiles** to instantly autofill the credentials without manual typing!

---

## 🔒 6. Security & Trust Architecture

1. **Password Hashing**: Passwords are never stored in plain text. Werkzeug generates secure salted hashes (`scrypt` / `pbkdf2`) on account creation.
2. **Public Role Isolation**: Public registration (`/register`) is strictly locked to the `student` role. Even if a malicious request injects `role=admin`, the server enforces `role='student'`.
3. **Session Protection**: Flask-Login protects private endpoints with `@login_required` and redirects unauthenticated visitors to `/login` with flash alerts.
4. **Environment Variables**: Sensitive configuration (`SECRET_KEY`, `DATABASE_URL`) defaults to safe local development values and can be configured through `.env`.

---

## 🎓 7. Beginner Explanation: How It Works

If you are presenting this project to hackathon judges:

1. **How Flask routes a request**: When a user visits `http://127.0.0.1:5000/login`, Flask executes the `login()` function in `app.py`. If it's a `GET` request, Flask renders the `login.html` template. If it's a `POST` request (the user clicked "Sign In"), Flask reads the submitted email and password.
2. **How authentication checks the password**: Flask queries the SQLite database via SQLAlchemy (`User.query.filter_by(email=...)`). It calls `user.check_password(password)`, which verifies the hash without ever knowing or saving the original password.
3. **How Flask-Login remembers the user**: If the password matches, `login_user(user)` puts a secure cookie in the user's browser. On subsequent page visits, Flask reads this cookie and sets `current_user`.
4. **How the Dashboard adapts to roles**: In `dashboard.html`, Jinja2 template tags inspect `{% if user.is_student %}`, `{% elif user.is_manager %}`, and `{% else %}` to render distinct dashboards tailored specifically for each role.

---

## 🗺️ 8. Hackathon Roadmap

- [x] **Stage 1 (Completed)**: Clean project structure, User model with secure hashing, Flask-Login authentication, role-aware dashboard, responsive UI, 1-click demo profiles, demo seeding, and 11 passing tests.
- [x] **Stage 2 (Completed)**: Resource Inventory & Discovery (Resource model, multi-criteria catalogue search, category & location filtering, owner authorization, detail profiles, safety prerequisites, live dashboard database queries, and 26 passing regression tests).
- [ ] **Stage 3 (Next)**: Request & Approval Lifecycle (student requests, manager queue, checkout condition inspection, return logging).

