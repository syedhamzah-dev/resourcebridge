"""
tests/test_lifecycle.py - Booking Lifecycle, Handover Reports, Incidents & Audit Trail Tests
=============================================================================================
Validates:
1. End-to-end lifecycle: PENDING -> APPROVED -> CHECKED_IN -> RETURN_PENDING -> RETURNED.
2. Check-in validation: Approved status required; pending, rejected, cancelled cannot check in.
3. Check-out/Return validation: Valid check-in or return_pending required; rejected/cancelled cannot return.
4. Permission guards: Only authorized managers/admins can execute check-in and return.
5. Privacy controls: Students can only view their own booking detail pages; unrelated students get 403.
6. Initial & final condition reports: Correct ratings, notes, associations, and display.
7. Incident reporting: Borrower or manager can report; authorized managers can update status and resolve.
8. Security guard: Students cannot resolve incidents through manager action (403 forbidden).
9. Server-side audit logging: Every state transition generates immutable audit entries.
10. Conflict detection: Active loans (checked_in, return_pending) block overlapping requests/approvals.
11. Invalid state transitions: Duplicate check-ins, checking in already returned bookings, etc.
"""

from datetime import datetime, timezone, timedelta
import pytest
from app import create_app
from models import (
    db,
    User,
    Resource,
    Booking,
    ConditionReport,
    Incident,
    BookingAuditLog,
    check_booking_conflict
)


@pytest.fixture
def app():
    """Create test application with in-memory SQLite database."""
    test_app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-lifecycle',
    })

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()


def login_user_helper(client, email, password):
    """Log in a user."""
    client.get('/logout', follow_redirects=True)
    return client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)


def seed_lifecycle_test_env(app):
    """Seed test database with student1, student2, manager1 (owner), manager2 (unrelated), and admin."""
    with app.app_context():
        s1 = User("Alex Student", "alex@campus.edu", "Password123!", role="student", is_verified=True)
        s2 = User("Maya Lin", "maya@campus.edu", "Password123!", role="student", is_verified=True)
        m1 = User("Dr. Elena Vance", "vance@campus.edu", "Password123!", role="manager", is_verified=True)
        m2 = User("Prof. Gordon Freeman", "freeman@campus.edu", "Password123!", role="manager", is_verified=True)
        adm = User("Admin Marcus", "admin@campus.edu", "Password123!", role="admin", is_verified=True)

        db.session.add_all([s1, s2, m1, m2, adm])
        db.session.commit()

        # Manager 1 owns camera kit
        camera = Resource(
            name="Sony FX3 Cinema Rig",
            description="4K cinema production package.",
            category="Cameras & AV Equipment",
            resource_type="equipment",
            location="Media Center Locker 12",
            availability_info="Daily 09:00 - 18:00",
            owner_id=m1.id,
            status="active"
        )
        # Manager 2 owns laser suite
        laser = Resource(
            name="Laser Cutting Suite",
            description="Fabrication laser cutter.",
            category="Workshop & Fabrication",
            resource_type="equipment",
            location="Engineering Hall Bay 2",
            availability_info="Mon-Fri 10:00 - 18:00",
            owner_id=m2.id,
            status="active"
        )
        db.session.add_all([camera, laser])
        db.session.commit()

        return {
            'student1_id': s1.id,
            'student2_id': s2.id,
            'manager1_id': m1.id,
            'manager2_id': m2.id,
            'admin_id': adm.id,
            'camera_id': camera.id,
            'laser_id': laser.id
        }


def test_approved_booking_checkin_success(app, client):
    """Test that an approved booking can be successfully checked in by the resource manager with condition report."""
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        b = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=4),
            purpose="Short film documentary project.",
            status="approved"
        )
        db.session.add(b)
        db.session.commit()
        booking_id = b.id

    # Log in as authorized resource owner manager
    login_user_helper(client, "vance@campus.edu", "Password123!")

    # Submit check-in with initial condition report
    resp = client.post(
        f'/bookings/{booking_id}/check-in',
        data={
            'condition_rating': 'excellent',
            'notes': 'All accessories accounted for, clean lens optics, 2 batteries charged.'
        },
        follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"checked in" in resp.data.lower() or b"active loan" in resp.data.lower()

    # Verify database state
    with app.app_context():
        updated_b = db.session.get(Booking, booking_id)
        assert updated_b.status == 'checked_in'
        assert updated_b.is_checked_in is True
        assert updated_b.checked_in_at is not None

        # Verify condition report created
        report = updated_b.get_initial_condition_report()
        assert report is not None
        assert report.report_stage == 'check_in'
        assert report.condition_rating == 'excellent'
        assert 'accessories accounted for' in report.notes

        # Verify audit log
        logs = [log.event_type for log in updated_b.audit_logs]
        assert 'checked_in' in logs


def test_rejection_of_checkin_for_pending_booking(app, client):
    """Test that a pending (unapproved) booking cannot be checked in."""
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        b = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=4),
            purpose="Short film documentary project.",
            status="pending"
        )
        db.session.add(b)
        db.session.commit()
        booking_id = b.id

    login_user_helper(client, "vance@campus.edu", "Password123!")

    resp = client.post(
        f'/bookings/{booking_id}/check-in',
        data={'condition_rating': 'excellent', 'notes': 'Attempting early check-in.'},
        follow_redirects=False
    )
    assert resp.status_code == 400

    with app.app_context():
        updated_b = db.session.get(Booking, booking_id)
        assert updated_b.status == 'pending'
        assert updated_b.checked_in_at is None
        assert updated_b.get_initial_condition_report() is None


def test_rejection_of_checkin_for_rejected_or_cancelled_booking(app, client):
    """Test that rejected or cancelled bookings cannot be checked in."""
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        b_rej = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=4),
            purpose="Project A",
            status="rejected"
        )
        b_canc = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now + timedelta(hours=5),
            end_time=now + timedelta(hours=8),
            purpose="Project B",
            status="cancelled"
        )
        db.session.add_all([b_rej, b_canc])
        db.session.commit()
        rej_id, canc_id = b_rej.id, b_canc.id

    login_user_helper(client, "vance@campus.edu", "Password123!")

    resp1 = client.post(f'/bookings/{rej_id}/check-in', data={'condition_rating': 'good', 'notes': 'Test notes.'})
    assert resp1.status_code == 400

    resp2 = client.post(f'/bookings/{canc_id}/check-in', data={'condition_rating': 'good', 'notes': 'Test notes.'})
    assert resp2.status_code == 400


def test_full_return_workflow_after_checkin(app, client):
    """
    Test full lifecycle:
    Approved -> Check In -> Request Return -> Manager Return Inspection (Check Out).
    """
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        b = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now - timedelta(hours=2),
            end_time=now + timedelta(hours=2),
            purpose="Documentary filming.",
            status="approved"
        )
        db.session.add(b)
        db.session.commit()
        booking_id = b.id

    # 1. Manager checks in
    login_user_helper(client, "vance@campus.edu", "Password123!")
    client.post(
        f'/bookings/{booking_id}/check-in',
        data={'condition_rating': 'excellent', 'notes': 'Pristine kit.'},
        follow_redirects=True
    )

    # 2. Student requests return
    login_user_helper(client, "alex@campus.edu", "Password123!")
    resp_req = client.post(f'/bookings/{booking_id}/request-return', follow_redirects=True)
    assert resp_req.status_code == 200

    with app.app_context():
        b_check = db.session.get(Booking, booking_id)
        assert b_check.status == 'return_pending'
        assert b_check.return_requested_at is not None

    # 3. Manager conducts return inspection
    login_user_helper(client, "vance@campus.edu", "Password123!")
    resp_ret = client.post(
        f'/bookings/{booking_id}/return',
        data={'condition_rating': 'good', 'notes': 'Tripod plate has minor scuff. Lens pristine.'},
        follow_redirects=True
    )
    assert resp_ret.status_code == 200

    with app.app_context():
        b_final = db.session.get(Booking, booking_id)
        assert b_final.status == 'returned'
        assert b_final.is_returned is True
        assert b_final.returned_at is not None

        # Check both condition reports exist
        in_rep = b_final.get_initial_condition_report()
        out_rep = b_final.get_final_condition_report()
        assert in_rep is not None
        assert in_rep.condition_rating == 'excellent'
        assert out_rep is not None
        assert out_rep.condition_rating == 'good'
        assert 'minor scuff' in out_rep.notes

        # Audit events contain both check-in and return
        events = [log.event_type for log in b_final.audit_logs]
        assert 'checked_in' in events
        assert 'return_requested' in events
        assert 'returned' in events


def test_permission_guard_unauthorized_manager_cannot_checkin_or_return(app, client):
    """Test that a manager cannot check in or complete returns for resources owned by another manager."""
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        # Camera is owned by Manager 1 (Elena Vance)
        b = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=4),
            purpose="Filming",
            status="approved"
        )
        db.session.add(b)
        db.session.commit()
        booking_id = b.id

    # Log in as Manager 2 (Gordon Freeman)
    login_user_helper(client, "freeman@campus.edu", "Password123!")

    # Attempt check-in on Manager 1's resource
    resp = client.post(
        f'/bookings/{booking_id}/check-in',
        data={'condition_rating': 'excellent', 'notes': 'Unauthorized check-in.'}
    )
    assert resp.status_code == 403

    # Student also cannot check in
    login_user_helper(client, "alex@campus.edu", "Password123!")
    resp_student = client.post(
        f'/bookings/{booking_id}/check-in',
        data={'condition_rating': 'excellent', 'notes': 'Student check-in.'}
    )
    assert resp_student.status_code == 403


def test_privacy_enforcement_student_cannot_view_others_booking_detail(app, client):
    """
    Test server-side privacy rule:
    Student Alex owns booking A. Student Maya Lin attempts to view GET /bookings/<booking_A_id>.
    Must return HTTP 403 Forbidden.
    """
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        b = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],  # Alex Student
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=4),
            purpose="Alex private booking purpose",
            status="approved"
        )
        db.session.add(b)
        db.session.commit()
        booking_id = b.id

    # Maya logs in
    login_user_helper(client, "maya@campus.edu", "Password123!")

    resp = client.get(f'/bookings/{booking_id}')
    assert resp.status_code == 403

    # Alex (requester) can access
    login_user_helper(client, "alex@campus.edu", "Password123!")
    resp_alex = client.get(f'/bookings/{booking_id}')
    assert resp_alex.status_code == 200
    assert b"Alex private booking purpose" in resp_alex.data


def test_condition_report_validation_rejects_empty_notes_or_bad_rating(app, client):
    """Test that check-in rejects invalid rating or missing notes."""
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        b = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=4),
            purpose="Filming",
            status="approved"
        )
        db.session.add(b)
        db.session.commit()
        booking_id = b.id

    login_user_helper(client, "vance@campus.edu", "Password123!")

    # Invalid rating
    resp1 = client.post(
        f'/bookings/{booking_id}/check-in',
        data={'condition_rating': 'super_mint', 'notes': 'Valid note string.'}
    )
    assert resp1.status_code == 400

    # Empty notes
    resp2 = client.post(
        f'/bookings/{booking_id}/check-in',
        data={'condition_rating': 'good', 'notes': ''}
    )
    assert resp2.status_code == 400


def test_incident_reporting_and_manager_resolution(app, client):
    """
    Test that an authorized user can report an incident on a booking,
    and only an authorized manager can update status / resolve it.
    """
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        b = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now - timedelta(hours=2),
            end_time=now + timedelta(hours=2),
            purpose="Filming",
            status="checked_in"
        )
        db.session.add(b)
        db.session.commit()
        booking_id = b.id

    # Student Alex reports missing lens cap
    login_user_helper(client, "alex@campus.edu", "Password123!")
    resp_inc = client.post(
        f'/bookings/{booking_id}/incidents',
        data={
            'category': 'missing_accessory',
            'severity': 'low',
            'description': 'Front 82mm lens protective cap missing from hard case compartment.'
        },
        follow_redirects=True
    )
    assert resp_inc.status_code == 200

    with app.app_context():
        inc = Incident.query.filter_by(booking_id=booking_id).first()
        assert inc is not None
        assert inc.category == 'missing_accessory'
        assert inc.status == 'open'
        incident_id = inc.id

    # Security check: Student Alex attempts to resolve the incident -> Must be 403 Forbidden!
    resp_student_resolve = client.post(
        f'/incidents/{incident_id}/resolve',
        data={'status': 'resolved', 'resolution_notes': 'Student self-resolving issue.'}
    )
    assert resp_student_resolve.status_code == 403

    # Authorized manager Vance resolves the incident
    login_user_helper(client, "vance@campus.edu", "Password123!")
    resp_mgr_resolve = client.post(
        f'/incidents/{incident_id}/resolve',
        data={
            'status': 'resolved',
            'resolution_notes': 'Spare 82mm lens cap provided from cage inventory. Verified kit complete.'
        },
        follow_redirects=True
    )
    assert resp_mgr_resolve.status_code == 200

    with app.app_context():
        resolved_inc = db.session.get(Incident, incident_id)
        assert resolved_inc.status == 'resolved'
        assert resolved_inc.resolved_by_id == ids['manager1_id']
        assert 'Spare 82mm lens cap' in resolved_inc.resolution_notes

        # Audit event recorded for incident reporting and resolution
        b_audit = db.session.get(Booking, booking_id)
        event_types = [e.event_type for e in b_audit.audit_logs]
        assert 'incident_reported' in event_types
        assert 'incident_resolved' in event_types


def test_conflict_detection_blocks_when_active_or_checked_in(app, client):
    """
    Test that conflict detection treats 'checked_in' and 'return_pending' bookings
    as occupied slots, preventing overlapping approval.
    """
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        # Booking 1 is checked in for 10:00 - 14:00
        b1 = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=5),
            purpose="Active shoot",
            status="checked_in"
        )
        # Booking 2 is pending for 12:00 - 16:00 (overlaps with b1)
        b2 = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student2_id'],
            start_time=now + timedelta(hours=3),
            end_time=now + timedelta(hours=7),
            purpose="Second shoot",
            status="pending"
        )
        db.session.add_all([b1, b2])
        db.session.commit()
        b2_id = b2.id

    # Manager attempts to approve b2 -> Must return 409 Conflict
    login_user_helper(client, "vance@campus.edu", "Password123!")
    resp = client.post(f'/bookings/{b2_id}/approve')
    assert resp.status_code == 409

    with app.app_context():
        b2_check = db.session.get(Booking, b2_id)
        assert b2_check.status == 'pending'  # Remains unapproved


def test_duplicate_checkin_and_return_rejection(app, client):
    """Test that duplicate check-ins or returning already returned bookings are strictly rejected."""
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        b = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=5),
            purpose="Documentary shoot",
            status="checked_in"
        )
        b.checked_in_at = now
        db.session.add(b)
        db.session.commit()
        booking_id = b.id

    login_user_helper(client, "vance@campus.edu", "Password123!")

    # Attempting duplicate check-in on already checked-in booking
    resp_dup_checkin = client.post(
        f'/bookings/{booking_id}/check-in',
        data={'condition_rating': 'excellent', 'notes': 'Second check-in attempt.'}
    )
    assert resp_dup_checkin.status_code == 400

    # Complete return to 'returned'
    resp_ret = client.post(
        f'/bookings/{booking_id}/return',
        data={'condition_rating': 'good', 'notes': 'Returned successfully.'},
        follow_redirects=True
    )
    assert resp_ret.status_code == 200

    # Attempting second return on already returned booking
    resp_dup_return = client.post(
        f'/bookings/{booking_id}/return',
        data={'condition_rating': 'good', 'notes': 'Second return attempt.'}
    )
    assert resp_dup_return.status_code == 400

    # Attempting check-in on already returned booking
    resp_checkin_after_return = client.post(
        f'/bookings/{booking_id}/check-in',
        data={'condition_rating': 'good', 'notes': 'Checkin on returned.'}
    )
    assert resp_checkin_after_return.status_code == 400


def test_booking_detail_page_renders_condition_reports_and_timeline(app, client):
    """Test that booking detail page renders all condition reports, incidents, and audit timeline correctly."""
    ids = seed_lifecycle_test_env(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        b = Booking(
            resource_id=ids['camera_id'],
            user_id=ids['student1_id'],
            start_time=now - timedelta(hours=3),
            end_time=now + timedelta(hours=1),
            purpose="Capfilm shoot",
            status="approved"
        )
        db.session.add(b)
        db.session.commit()
        booking_id = b.id

    # Manager checks in
    login_user_helper(client, "vance@campus.edu", "Password123!")
    client.post(
        f'/bookings/{booking_id}/check-in',
        data={'condition_rating': 'excellent', 'notes': 'Checkin verified by Vance.'},
        follow_redirects=True
    )

    # Student requests return
    login_user_helper(client, "alex@campus.edu", "Password123!")
    client.post(f'/bookings/{booking_id}/request-return', follow_redirects=True)

    # Manager completes return
    login_user_helper(client, "vance@campus.edu", "Password123!")
    client.post(
        f'/bookings/{booking_id}/return',
        data={'condition_rating': 'good', 'notes': 'Final check out notes.'},
        follow_redirects=True
    )

    # Check detail page rendering
    resp = client.get(f'/bookings/{booking_id}')
    assert resp.status_code == 200
    assert b"Handover Condition Reports" in resp.data
    assert b"Checkin verified by Vance" in resp.data
    assert b"Final check out notes" in resp.data
    assert b"Booking Audit Trail" in resp.data
    assert b"Checked In" in resp.data
    assert b"Returned" in resp.data
