"""
tests/test_security.py - Security, Concurrency, and Resilience Test Suite
========================================================================
Comprehensive verification of defense-in-depth controls for ResourceBridge:
1. HTTP Security Headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
2. Secure Session Cookie Flags (HttpOnly, SameSite=Lax)
3. CSRF Protection Enforcement & Open-Redirect Defense
4. Safe Error Handlers (403 Forbidden, 404 Not Found, 500 Safe Rollback)
5. Concurrency Race-Condition Blocking (Pre-Commit Conflict Check)
"""

import pytest
import os
import tempfile
import threading
import concurrent.futures
from datetime import datetime, timezone, timedelta
from app import create_app
from models import db, User, Resource, Booking


@pytest.fixture
def sec_app():
    """Isolated test application instance with CSRF enforcement enabled."""
    test_db_uri = "sqlite:///:memory:"
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': test_db_uri,
        'WTF_CSRF_ENABLED': True,
        'SECRET_KEY': 'test-security-secret-key'
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sec_client(sec_app):
    return sec_app.test_client()


# ------------------------------------------------------------------------------
# 1. HTTP Security Headers & Cookie Policies
# ------------------------------------------------------------------------------

def test_security_headers_present(sec_client):
    """Verify standard security headers are present on all application responses."""
    resp = sec_client.get('/')
    assert resp.status_code == 200
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert resp.headers.get('X-XSS-Protection') == '1; mode=block'
    assert resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'


def test_session_cookie_security_flags(sec_app, sec_client):
    """Verify session cookies enforce HttpOnly and SameSite=Lax flags."""
    with sec_app.app_context():
        user = User("Cookie Student", "cookie_std@campus.edu", "Pass123!", role="student")
        db.session.add(user)
        db.session.commit()

    # Log in and check Set-Cookie attributes
    with sec_client.session_transaction() as sess:
        sess['_csrf_token'] = 'valid-token'

    login_res = sec_client.post('/login', data={
        'email': 'cookie_std@campus.edu',
        'password': 'Pass123!',
        'csrf_token': 'valid-token'
    })
    assert login_res.status_code in (200, 302)
    cookie_header = login_res.headers.get('Set-Cookie')
    if cookie_header:
        assert 'HttpOnly' in cookie_header
        assert 'SameSite=Lax' in cookie_header


# ------------------------------------------------------------------------------
# 2. CSRF Token Protection & Open Redirect Defenses
# ------------------------------------------------------------------------------

def test_csrf_protection_rejects_missing_token_when_enabled(sec_client):
    """Ensure state-changing POST without CSRF token is intercepted and rejected."""
    # Attempt POST /login without token
    resp = sec_client.post('/login', data={
        'email': 'untrusted@campus.edu',
        'password': 'Password123!'
    }, follow_redirects=False)

    # Must be intercepted by check_csrf()
    assert resp.status_code == 302
    with sec_client.session_transaction() as sess:
        flashes = sess.get('_flashes', [])
        assert any("CSRF" in msg[1] for msg in flashes)


def test_csrf_open_redirect_defense(sec_client):
    """Verify that external Referrer headers on CSRF failures do not cause open redirects."""
    resp = sec_client.post(
        '/login',
        data={'email': 'hacker@campus.edu', 'password': 'Hacked!'},
        headers={'Referer': 'https://evil-phishing-site.com/exploit'},
        follow_redirects=False
    )
    assert resp.status_code == 302
    # Must redirect to safe local root or app path, NOT https://evil-phishing-site.com
    assert 'https://evil-phishing-site.com' not in resp.headers['Location']
    assert resp.headers['Location'].endswith('/') or '/login' in resp.headers['Location']


def test_login_open_redirect_defense(sec_app, sec_client):
    """Verify that user-supplied redirect destinations in login are strictly validated."""
    with sec_app.app_context():
        user = User("Redirect User", "redir@campus.edu", "Pass123!", role="student")
        db.session.add(user)
        db.session.commit()

    with sec_client.session_transaction() as sess:
        sess['_csrf_token'] = 'valid-token'

    # 1. Scheme-relative URL attack (//evil.com)
    resp1 = sec_client.post('/login?next=//evil.com', data={
        'email': 'redir@campus.edu',
        'password': 'Pass123!',
        'csrf_token': 'valid-token'
    }, follow_redirects=False)
    assert resp1.status_code == 302
    assert resp1.headers['Location'].endswith('/dashboard')
    assert 'evil.com' not in resp1.headers['Location']
    sec_client.get('/logout')

    # 2. Windows/backslash path attack (/\\evil.com)
    with sec_client.session_transaction() as sess:
        sess['_csrf_token'] = 'valid-token'
    resp2 = sec_client.post('/login?next=/\\\\evil.com', data={
        'email': 'redir@campus.edu',
        'password': 'Pass123!',
        'csrf_token': 'valid-token'
    }, follow_redirects=False)
    assert resp2.status_code == 302
    assert resp2.headers['Location'].endswith('/dashboard')
    assert 'evil.com' not in resp2.headers['Location']
    sec_client.get('/logout')

    # 3. Absolute external URL attack (https://attacker.org)
    with sec_client.session_transaction() as sess:
        sess['_csrf_token'] = 'valid-token'
    resp3 = sec_client.post('/login?next=https://attacker.org', data={
        'email': 'redir@campus.edu',
        'password': 'Pass123!',
        'csrf_token': 'valid-token'
    }, follow_redirects=False)
    assert resp3.status_code == 302
    assert resp3.headers['Location'].endswith('/dashboard')
    assert 'attacker.org' not in resp3.headers['Location']
    sec_client.get('/logout')

    # 4. Legitimate relative internal URL (/resources)
    with sec_client.session_transaction() as sess:
        sess['_csrf_token'] = 'valid-token'
    resp4 = sec_client.post('/login?next=/resources', data={
        'email': 'redir@campus.edu',
        'password': 'Pass123!',
        'csrf_token': 'valid-token'
    }, follow_redirects=False)
    assert resp4.status_code == 302
    assert resp4.headers['Location'].endswith('/resources')


# ------------------------------------------------------------------------------
# 3. Custom Error Handlers (403 Forbidden & 404 Not Found)
# ------------------------------------------------------------------------------

def test_custom_403_error_handler_renders_safe_page(sec_app, sec_client):
    """Ensure 403 Forbidden renders custom safe template without stack trace."""
    @sec_app.route('/test-forbidden-endpoint')
    def trigger_403():
        from flask import abort
        abort(403)

    resp = sec_client.get('/test-forbidden-endpoint')
    assert resp.status_code == 403
    assert b"Access Restricted" in resp.data
    assert b"403" in resp.data


def test_unauthorized_role_access_blocked(sec_app, sec_client):
    """Verify unauthorized role cannot access manager portal."""
    with sec_app.app_context():
        student = User("Unpriv Student", "unpriv@campus.edu", "Pass123!", role="student")
        db.session.add(student)
        db.session.commit()

    with sec_client.session_transaction() as sess:
        sess['_csrf_token'] = 'valid-token'

    sec_client.post('/login', data={
        'email': 'unpriv@campus.edu',
        'password': 'Pass123!',
        'csrf_token': 'valid-token'
    }, follow_redirects=True)

    resp = sec_client.get('/resources/manage')
    assert resp.status_code == 403
    assert '/dashboard' in resp.headers.get('Location', '')

    # Following the redirection to dashboard displays the flashed denial message
    dash_resp = sec_client.get('/dashboard')
    assert b"Access denied" in dash_resp.data


def test_custom_404_error_handler_renders_safe_page(sec_client):
    """Ensure invalid route or resource ID renders clean 404 template."""
    resp = sec_client.get('/resources/999999')
    assert resp.status_code == 404
    assert b"Resource Not Found" in resp.data
    assert b"404" in resp.data


def test_custom_500_error_handler_renders_safe_page(sec_app, sec_client):
    """Ensure 500 Internal Server Error rolls back transaction and renders safe page without leak."""
    @sec_app.route('/test-500-trigger')
    def trigger_500():
        from flask import abort
        abort(500)

    resp = sec_client.get('/test-500-trigger')
    assert resp.status_code == 500
    assert b"Temporary System Error" in resp.data
    assert b"500" in resp.data
    assert b"Traceback" not in resp.data


# ------------------------------------------------------------------------------
# 4. Concurrency Double-Booking Protection
# ------------------------------------------------------------------------------

def test_concurrency_double_booking_rejection(sec_app, sec_client):
    """Verify atomic pre-commit conflict detection blocks race condition double-booking."""
    now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=2)
    start = now
    end = now + timedelta(hours=3)

    with sec_app.app_context():
        mgr = User("Lab Manager", "manager_sec@campus.edu", "Pass123!", role="manager")
        std1 = User("Student One", "std1@campus.edu", "Pass123!", role="student")
        std2 = User("Student Two", "std2@campus.edu", "Pass123!", role="student")
        db.session.add_all([mgr, std1, std2])
        db.session.commit()

        res = Resource("High-End Electron Scope", "Electron microscope", "Specialized Science & Optics", "Bay 1", "9-5", mgr.id)
        db.session.add(res)
        db.session.commit()

        # Two pending bookings submitted for the same resource and time slot
        b1 = Booking(resource_id=res.id, user_id=std1.id, start_time=start, end_time=end, purpose="Experiment A", status='pending')
        b2 = Booking(resource_id=res.id, user_id=std2.id, start_time=start, end_time=end, purpose="Experiment B", status='pending')
        db.session.add_all([b1, b2])
        db.session.commit()
        b1_id, b2_id = b1.id, b2.id

    # Manager logs in
    with sec_client.session_transaction() as sess:
        sess['_csrf_token'] = 'valid-token'

    sec_client.post('/login', data={
        'email': 'manager_sec@campus.edu',
        'password': 'Pass123!',
        'csrf_token': 'valid-token'
    }, follow_redirects=True)

    # Manager approves Booking 1
    resp1 = sec_client.post(f'/bookings/{b1_id}/approve', data={'csrf_token': 'valid-token'}, follow_redirects=False)
    assert resp1.status_code in (200, 302)

    with sec_app.app_context():
        b1_fresh = db.session.get(Booking, b1_id)
        assert b1_fresh.status == 'approved'

    # Now attempt to approve Booking 2 (overlapping slot)
    resp2 = sec_client.post(f'/bookings/{b2_id}/approve', data={'csrf_token': 'valid-token'}, follow_redirects=False)
    # Must be blocked by conflict detection (HTTP 409 Conflict)
    assert resp2.status_code == 409

    with sec_app.app_context():
        b2_fresh = db.session.get(Booking, b2_id)
        assert b2_fresh.status == 'pending'  # Remains pending, NOT double-booked!


def test_multithreaded_concurrent_double_booking_rejection():
    """
    Verify multi-threaded concurrent approval requests for overlapping slots cannot double-book.
    Uses independent client worker threads and a threading.Barrier to simulate real race conditions.
    """
    temp_db = os.path.join(tempfile.gettempdir(), f'test_conc_{datetime.now().timestamp()}.db')
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{temp_db}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-conc-secret'
    })
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=2)
        start = now
        end = now + timedelta(hours=3)

        with app.app_context():
            db.create_all()
            mgr = User("Concur Mgr", "concur_mgr@campus.edu", "Pass123!", role="manager")
            std1 = User("Student A", "stda@campus.edu", "Pass123!", role="student")
            std2 = User("Student B", "stdb@campus.edu", "Pass123!", role="student")
            db.session.add_all([mgr, std1, std2])
            db.session.commit()

            res = Resource("Electron Scope 2", "Optics", "Specialized Science & Optics", "Bay 2", "9-5", mgr.id)
            db.session.add(res)
            db.session.commit()

            b1 = Booking(resource_id=res.id, user_id=std1.id, start_time=start, end_time=end, purpose="Thread Exp A", status='pending')
            b2 = Booking(resource_id=res.id, user_id=std2.id, start_time=start, end_time=end, purpose="Thread Exp B", status='pending')
            db.session.add_all([b1, b2])
            db.session.commit()
            b1_id, b2_id = b1.id, b2.id

        barrier = threading.Barrier(2)
        results = []

        def worker(booking_id):
            client = app.test_client()
            client.post('/login', data={'email': 'concur_mgr@campus.edu', 'password': 'Pass123!'}, follow_redirects=False)
            barrier.wait()
            resp = client.post(f'/bookings/{booking_id}/approve', follow_redirects=False)
            return booking_id, resp.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(worker, b1_id)
            f2 = ex.submit(worker, b2_id)
            for f in concurrent.futures.as_completed([f1, f2]):
                results.append(f.result())

        status_codes = [r[1] for r in results]
        # Exactly one must be 302 (success redirect) and the other must be 409 (conflict)
        assert 302 in status_codes
        assert 409 in status_codes

        with app.app_context():
            b1_fresh = db.session.get(Booking, b1_id)
            b2_fresh = db.session.get(Booking, b2_id)
            statuses = [b1_fresh.status, b2_fresh.status]
            assert 'approved' in statuses
            assert 'pending' in statuses
            assert statuses.count('approved') == 1
    finally:
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except Exception:
                pass
