"""
tests/test_auth.py - Authentication and Role Permission Tests
=============================================================
Verifies User model password hashing, role restrictions, public registration,
login/logout flows, and role-aware dashboard protections.
"""

import pytest
from app import create_app, seed_demo_users
from models import db, User


@pytest.fixture
def app():
    """Create and configure a clean application instance for testing."""
    test_app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-123',
    })

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client for simulating HTTP requests."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner for testing Flask commands."""
    return app.test_cli_runner()


# ------------------------------------------------------------------------------
# 1. User Model & Password Hashing Tests
# ------------------------------------------------------------------------------

def test_password_hashing(app):
    """Ensure plain-text passwords are never stored and hash verification works."""
    with app.app_context():
        user = User(
            name="Test Student",
            email="test@campus.edu",
            password="SecurePassword123!"
        )
        # Check that hash exists and does NOT contain the plaintext password
        assert user.password_hash is not None
        assert "SecurePassword123!" not in user.password_hash
        assert user.password_hash.startswith("scrypt:") or user.password_hash.startswith("pbkdf2:")

        # Check verification
        assert user.check_password("SecurePassword123!") is True
        assert user.check_password("WrongPassword") is False
        assert user.check_password("") is False


def test_user_roles_and_privileges(app):
    """Test role flags and automatic fallback to student for invalid roles."""
    with app.app_context():
        student = User("Student", "student1@campus.edu", "pass123", role="student")
        manager = User("Manager", "manager1@campus.edu", "pass123", role="manager")
        admin = User("Admin", "admin1@campus.edu", "pass123", role="admin")
        invalid = User("Hacker", "hacker@campus.edu", "pass123", role="superadmin_invalid")

        assert student.is_student is True
        assert student.is_manager is False
        assert student.is_admin is False

        assert manager.is_student is False
        assert manager.is_manager is True
        assert manager.is_admin is False

        assert admin.is_student is False
        assert admin.is_manager is False
        assert admin.is_admin is True

        # Invalid role should safely default to 'student'
        assert invalid.role == 'student'
        assert invalid.is_student is True


# ------------------------------------------------------------------------------
# 2. Registration Security Tests
# ------------------------------------------------------------------------------

def test_public_registration_success(client, app):
    """Ensure valid student registration creates an account and redirects to login."""
    response = client.post('/register', data={
        'name': 'Sam Rivera',
        'email': 'sam@campus.edu',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Your student account was created successfully" in response.data

    with app.app_context():
        user = User.query.filter_by(email="sam@campus.edu").first()
        assert user is not None
        assert user.name == "Sam Rivera"
        assert user.role == "student"


def test_public_registration_cannot_escalate_role(client, app):
    """Ensure public users cannot self-assign manager or admin roles."""
    # Attempt to inject role=admin and role=manager
    response = client.post('/register', data={
        'name': 'Sneaky User',
        'email': 'sneaky@campus.edu',
        'password': 'Password123!',
        'confirm_password': 'Password123!',
        'role': 'admin'
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="sneaky@campus.edu").first()
        assert user is not None
        # Must be student despite the malicious role form field
        assert user.role == "student"
        assert user.is_student is True
        assert user.is_admin is False


def test_registration_validation_errors(client, app):
    """Ensure invalid submissions produce appropriate errors."""
    # 1. Missing name
    res = client.post('/register', data={
        'name': '',
        'email': 'test@campus.edu',
        'password': 'Pass1234!',
        'confirm_password': 'Pass1234!'
    })
    assert b"Full name is required" in res.data

    # 2. Mismatched passwords
    res = client.post('/register', data={
        'name': 'Test User',
        'email': 'mismatch@campus.edu',
        'password': 'PasswordOne1!',
        'confirm_password': 'PasswordTwo2!'
    })
    assert b"Passwords do not match" in res.data

    # 3. Short password
    res = client.post('/register', data={
        'name': 'Short Pass',
        'email': 'short@campus.edu',
        'password': '123',
        'confirm_password': '123'
    })
    assert b"Password must be at least 6 characters" in res.data


def test_registration_duplicate_email(client, app):
    """Ensure registering with an already existing email is rejected."""
    # Register first user
    client.post('/register', data={
        'name': 'User One',
        'email': 'shared@campus.edu',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    })

    # Try registering again with same email
    res = client.post('/register', data={
        'name': 'User Two',
        'email': 'shared@campus.edu',
        'password': 'DifferentPass123!',
        'confirm_password': 'DifferentPass123!'
    })
    assert b"already exists" in res.data


# ------------------------------------------------------------------------------
# 3. Authentication & Session Tests
# ------------------------------------------------------------------------------

def test_login_and_logout(client, app):
    """Test standard login with valid credentials and subsequent logout."""
    with app.app_context():
        user = User("Morgan Hall", "morgan@campus.edu", "MorganPass123!", role="student")
        db.session.add(user)
        db.session.commit()

    # Attempt login with correct credentials
    login_res = client.post('/login', data={
        'email': 'morgan@campus.edu',
        'password': 'MorganPass123!'
    }, follow_redirects=True)

    assert login_res.status_code == 200
    assert b"Welcome back, Morgan Hall!" in login_res.data
    assert b"Morgan" in login_res.data

    # Logout
    logout_res = client.get('/logout', follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"You have been signed out securely" in logout_res.data


def test_login_invalid_credentials(client, app):
    """Test login failure on bad password and nonexistent user."""
    with app.app_context():
        user = User("Valid User", "valid@campus.edu", "CorrectPass123!")
        db.session.add(user)
        db.session.commit()

    # Wrong password
    bad_pass_res = client.post('/login', data={
        'email': 'valid@campus.edu',
        'password': 'WrongPassword123!'
    })
    assert b"Invalid email or password" in bad_pass_res.data

    # Nonexistent email
    bad_email_res = client.post('/login', data={
        'email': 'unknown@campus.edu',
        'password': 'AnyPassword123!'
    })
    assert b"Invalid email or password" in bad_email_res.data


# ------------------------------------------------------------------------------
# 4. Route Protection & Role-Aware Dashboard Tests
# ------------------------------------------------------------------------------

def test_dashboard_requires_login(client):
    """Unauthenticated users attempting to access /dashboard must be redirected to /login."""
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_role_aware_dashboard_rendering(client, app):
    """Verify that student, manager, and admin view customized dashboards according to role."""
    with app.app_context():
        student = User("Student Alice", "alice@campus.edu", "Pass123!", role="student")
        manager = User("Manager Bob", "bob@campus.edu", "Pass123!", role="manager")
        admin = User("Admin Carol", "carol@campus.edu", "Pass123!", role="admin")
        db.session.add_all([student, manager, admin])
        db.session.commit()

    # 1. Verify Student View
    client.post('/login', data={'email': 'alice@campus.edu', 'password': 'Pass123!'})
    student_dash = client.get('/dashboard')
    assert b"Student Access Portal" in student_dash.data
    assert b"Student Member" in student_dash.data
    assert b"Active Loans" in student_dash.data
    client.get('/logout')

    # 2. Verify Manager View
    client.post('/login', data={'email': 'bob@campus.edu', 'password': 'Pass123!'})
    manager_dash = client.get('/dashboard')
    assert b"Resource Manager Operations" in manager_dash.data
    assert b"Resource Manager" in manager_dash.data
    assert b"Managed Assets" in manager_dash.data
    client.get('/logout')

    # 3. Verify Admin View
    client.post('/login', data={'email': 'carol@campus.edu', 'password': 'Pass123!'})
    admin_dash = client.get('/dashboard')
    assert b"Campus System Administration" in admin_dash.data
    assert b"System Administrator" in admin_dash.data
    assert b"Institutional Safety & Audit Log" in admin_dash.data
    client.get('/logout')


# ------------------------------------------------------------------------------
# 5. Demo Seeder Verification
# ------------------------------------------------------------------------------

def test_demo_seeder(app):
    """Verify seed_demo_users correctly provisions the 3 demo roles with hashed passwords."""
    with app.app_context():
        count = seed_demo_users(app)
        assert count == 3

        student = User.query.filter_by(email="student@campus.edu").first()
        manager = User.query.filter_by(email="manager@campus.edu").first()
        admin = User.query.filter_by(email="admin@campus.edu").first()

        assert student is not None and student.role == "student"
        assert student.check_password("StudentPass123!") is True

        assert manager is not None and manager.role == "manager"
        assert manager.check_password("ManagerPass123!") is True

        assert admin is not None and admin.role == "admin"
        assert admin.check_password("AdminPass123!") is True
