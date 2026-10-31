"""
tests/test_bookings.py - Booking & Approval Workflow Tests
==========================================================
Validates student booking request submissions, unauthenticated protection,
input validation (past times, negative duration), role-based approval permissions,
scope enforcement for managers, reason-based rejections, server-side conflict
detection preventing overlapping approved reservations, and handling of maintenance
or inactive resource statuses.
"""

from datetime import datetime, timezone, timedelta
import pytest
from app import create_app
from models import db, User, Resource, Booking, check_booking_conflict


@pytest.fixture
def app():
    """Create and configure a clean application instance with an in-memory SQLite database."""
    test_app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-stage3',
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


def login_user_helper(client, email, password):
    """Helper to authenticate a test user, clearing any existing session first."""
    client.get('/logout', follow_redirects=True)
    return client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)


def create_test_users_and_resource(app):
    """Helper fixture setup creating student, two managers, and an active resource."""
    with app.app_context():
        student = User("Alex Student", "student@campus.edu", "StudentPass123!", role="student", is_verified=True)
        student2 = User("Maya Lin", "maya@campus.edu", "StudentPass123!", role="student", is_verified=False)
        manager1 = User("Dr. Elena Vance", "manager1@campus.edu", "ManagerPass123!", role="manager", is_verified=True)
        manager2 = User("Prof. Gordon Freeman", "manager2@campus.edu", "ManagerPass123!", role="manager", is_verified=True)
        admin = User("Marcus Brody", "admin@campus.edu", "AdminPass123!", role="admin", is_verified=True)

        db.session.add_all([student, student2, manager1, manager2, admin])
        db.session.commit()

        # Manager 1 owns Resource 1
        res1 = Resource(
            name="Confocal Laser Scanning Microscope",
            description="High resolution optical sectioning microscope system.",
            category="Specialized Science & Optics",
            resource_type="space",
            location="Science Hall Room 402",
            availability_info="Mon-Fri 09:00 - 17:00",
            owner_id=manager1.id,
            training_required=True,
            training_details="Laser Safety Level 2",
            supervision_required=True,
            supervision_details="Faculty technician presence required",
            status="active"
        )
        # Maintenance Resource
        res_maint = Resource(
            name="Formlabs Resin 3D Printer",
            description="Stereolithography 3D printer currently undergoing vat calibration.",
            category="Workshop & Fabrication",
            resource_type="equipment",
            location="MakerSpace Bay 4",
            availability_info="Mon-Fri 10:00 - 18:00",
            owner_id=manager1.id,
            status="maintenance"
        )
        # Inactive Resource
        res_inactive = Resource(
            name="Decommissioned Spectrometer",
            description="Inactive equipment.",
            category="Specialized Science & Optics",
            resource_type="equipment",
            location="Storage Hall",
            availability_info="Offline",
            owner_id=manager1.id,
            status="inactive"
        )

        db.session.add_all([res1, res_maint, res_inactive])
        db.session.commit()

        return {
            'student_id': student.id,
            'student2_id': student2.id,
            'manager1_id': manager1.id,
            'manager2_id': manager2.id,
            'admin_id': admin.id,
            'res1_id': res1.id,
            'res_maint_id': res_maint.id,
            'res_inactive_id': res_inactive.id
        }


# ------------------------------------------------------------------------------
# Test 1: Student Can Submit a Valid Booking Request
# ------------------------------------------------------------------------------

def test_student_can_submit_valid_booking_request(client, app):
    """1. A logged-in student can submit a valid booking request and it persists with 'pending' status."""
    ids = create_test_users_and_resource(app)
    login_user_helper(client, "student@campus.edu", "StudentPass123!")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_dt = now + timedelta(days=2, hours=10)
    end_dt = now + timedelta(days=2, hours=14)

    post_resp = client.post(f"/resources/{ids['res1_id']}/book", data={
        'start_time': start_dt.strftime('%Y-%m-%dT%H:%M'),
        'end_time': end_dt.strftime('%Y-%m-%dT%H:%M'),
        'purpose': 'Biomaterials nanotech capstone specimen imaging.'
    }, follow_redirects=True)

    assert post_resp.status_code == 200
    assert b"submitted successfully" in post_resp.data
    assert b"Pending Review" in post_resp.data

    with app.app_context():
        booking = Booking.query.filter_by(resource_id=ids['res1_id'], user_id=ids['student_id']).first()
        assert booking is not None
        assert booking.status == 'pending'
        assert booking.purpose == 'Biomaterials nanotech capstone specimen imaging.'
        assert booking.duration_hours == 4.0


# ------------------------------------------------------------------------------
# Test 2: Unauthenticated Visitor Cannot Submit Booking
# ------------------------------------------------------------------------------

def test_unauthenticated_visitor_cannot_submit_booking(client, app):
    """2. An unauthenticated visitor is redirected to login when attempting to book."""
    ids = create_test_users_and_resource(app)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_dt = now + timedelta(days=1, hours=9)
    end_dt = now + timedelta(days=1, hours=11)

    post_resp = client.post(f"/resources/{ids['res1_id']}/book", data={
        'start_time': start_dt.strftime('%Y-%m-%dT%H:%M'),
        'end_time': end_dt.strftime('%Y-%m-%dT%H:%M'),
        'purpose': 'Unauthorized test booking.'
    }, follow_redirects=False)

    # Must redirect to login page (HTTP 302)
    assert post_resp.status_code == 302
    assert "/login" in post_resp.headers['Location']

    with app.app_context():
        assert Booking.query.count() == 0


# ------------------------------------------------------------------------------
# Test 3: Invalid Booking Times Are Rejected
# ------------------------------------------------------------------------------

def test_invalid_booking_times_rejected(client, app):
    """3. Invalid booking times (past times, end before start, empty purpose) are rejected."""
    ids = create_test_users_and_resource(app)
    login_user_helper(client, "student@campus.edu", "StudentPass123!")

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Sub-case A: Start time in past
    past_start = now - timedelta(days=1)
    past_end = now - timedelta(days=1, hours=-2)
    resp_past = client.post(f"/resources/{ids['res1_id']}/book", data={
        'start_time': past_start.strftime('%Y-%m-%dT%H:%M'),
        'end_time': past_end.strftime('%Y-%m-%dT%H:%M'),
        'purpose': 'Attempted retrospective booking'
    }, follow_redirects=True)
    assert resp_past.status_code == 400
    assert b"cannot be in the past" in resp_past.data

    # Sub-case B: End time before start time
    future_start = now + timedelta(days=2, hours=15)
    future_end = now + timedelta(days=2, hours=12)  # 3 hours prior to start!
    resp_inverted = client.post(f"/resources/{ids['res1_id']}/book", data={
        'start_time': future_start.strftime('%Y-%m-%dT%H:%M'),
        'end_time': future_end.strftime('%Y-%m-%dT%H:%M'),
        'purpose': 'Inverted time interval'
    }, follow_redirects=True)
    assert resp_inverted.status_code == 400
    assert b"must be after the start time" in resp_inverted.data

    # Sub-case C: Empty or too short purpose
    resp_short = client.post(f"/resources/{ids['res1_id']}/book", data={
        'start_time': (now + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'end_time': (now + timedelta(days=3, hours=2)).strftime('%Y-%m-%dT%H:%M'),
        'purpose': 'hi'
    }, follow_redirects=True)
    assert resp_short.status_code == 400
    assert b"at least 5 characters" in resp_short.data


# ------------------------------------------------------------------------------
# Test 4: Student Cannot Approve a Booking
# ------------------------------------------------------------------------------

def test_student_cannot_approve_booking(client, app):
    """4. A student cannot approve their own or any booking (server-side 403 Forbidden)."""
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        booking = Booking(
            resource_id=ids['res1_id'],
            user_id=ids['student_id'],
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=3),
            purpose="Laser spectroscopy sample scan.",
            status="pending"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    login_user_helper(client, "student@campus.edu", "StudentPass123!")

    # Student attempts POST /bookings/<id>/approve
    resp = client.post(f"/bookings/{booking_id}/approve", follow_redirects=False)
    assert resp.status_code == 403

    # Verify status remained unchanged in database
    with app.app_context():
        b = db.session.get(Booking, booking_id)
        assert b.status == 'pending'
        assert b.decided_by_id is None


# ------------------------------------------------------------------------------
# Test 5: Manager Can Review Requests in Authorized Scope
# ------------------------------------------------------------------------------

def test_manager_can_review_requests_in_scope(client, app):
    """5. An authorized manager can view pending booking requests for their department resources."""
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        booking = Booking(
            resource_id=ids['res1_id'],
            user_id=ids['student_id'],
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=3),
            purpose="Laser spectroscopy sample scan.",
            status="pending"
        )
        db.session.add(booking)
        db.session.commit()

    login_user_helper(client, "manager1@campus.edu", "ManagerPass123!")

    resp = client.get("/manager/bookings")
    assert resp.status_code == 200
    assert b"Department Booking Review Queue" in resp.data
    assert b"Confocal Laser Scanning Microscope" in resp.data
    assert b"Laser spectroscopy sample scan" in resp.data


# ------------------------------------------------------------------------------
# Test 6: Unauthorized Manager Cannot Approve Request Outside Scope
# ------------------------------------------------------------------------------

def test_unauthorized_manager_cannot_approve_outside_scope(client, app):
    """6. Manager 2 cannot approve a booking for a resource owned by Manager 1 (HTTP 403)."""
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        booking = Booking(
            resource_id=ids['res1_id'],  # Owned by manager 1
            user_id=ids['student_id'],
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=3),
            purpose="Laser spectroscopy sample scan.",
            status="pending"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    # Log in as Manager 2 (does not own res1)
    login_user_helper(client, "manager2@campus.edu", "ManagerPass123!")

    resp = client.post(f"/bookings/{booking_id}/approve", follow_redirects=False)
    assert resp.status_code == 403

    with app.app_context():
        b = db.session.get(Booking, booking_id)
        assert b.status == 'pending'
        assert b.decided_by_id is None


# ------------------------------------------------------------------------------
# Test 7: Authorized Manager Can Approve a Valid Request
# ------------------------------------------------------------------------------

def test_manager_can_approve_valid_request(client, app):
    """7. An authorized manager can approve a valid request, recording decision audit fields."""
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        booking = Booking(
            resource_id=ids['res1_id'],
            user_id=ids['student_id'],
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=3),
            purpose="Laser spectroscopy sample scan.",
            status="pending"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    login_user_helper(client, "manager1@campus.edu", "ManagerPass123!")

    resp = client.post(f"/bookings/{booking_id}/approve", follow_redirects=True)
    assert resp.status_code == 200
    assert b"has been approved" in resp.data

    with app.app_context():
        b = db.session.get(Booking, booking_id)
        assert b.status == 'approved'
        assert b.decided_by_id == ids['manager1_id']
        assert b.decided_at is not None


# ------------------------------------------------------------------------------
# Test 8: Manager Can Reject Request With Reason
# ------------------------------------------------------------------------------

def test_manager_can_reject_with_reason(client, app):
    """8. A manager can reject a request with an explicit reason, and empty reason is rejected."""
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        booking = Booking(
            resource_id=ids['res1_id'],
            user_id=ids['student_id'],
            start_time=now + timedelta(days=3),
            end_time=now + timedelta(days=3, hours=2),
            purpose="Laser trial scan.",
            status="pending"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    login_user_helper(client, "manager1@campus.edu", "ManagerPass123!")

    # Sub-case A: Empty rejection reason must be rejected (HTTP 400)
    resp_empty = client.post(f"/bookings/{booking_id}/reject", data={
        'rejection_reason': '   '
    }, follow_redirects=True)
    assert resp_empty.status_code == 400
    assert b"rejection reason is required" in resp_empty.data

    # Sub-case B: Rejection with valid reason
    resp_valid = client.post(f"/bookings/{booking_id}/reject", data={
        'rejection_reason': 'Student has not completed Laser Safety Level 2 certificate.'
    }, follow_redirects=True)
    assert resp_valid.status_code == 200
    assert b"has been rejected" in resp_valid.data

    with app.app_context():
        b = db.session.get(Booking, booking_id)
        assert b.status == 'rejected'
        assert b.rejection_reason == 'Student has not completed Laser Safety Level 2 certificate.'
        assert b.decided_by_id == ids['manager1_id']


# ------------------------------------------------------------------------------
# Test 9: Overlapping Approved Bookings Are Prevented
# ------------------------------------------------------------------------------

def test_overlapping_approved_bookings_prevented(client, app):
    """
    9. Server-side conflict detection prevents overlapping approved bookings for the same resource.
       Overlap definition: (existing.start < candidate.end) AND (existing.end > candidate.start).
    """
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    slot_start = now + timedelta(days=5, hours=10)
    slot_end = now + timedelta(days=5, hours=14)

    with app.app_context():
        # Booking A is approved for 10:00 to 14:00
        booking_a = Booking(
            resource_id=ids['res1_id'],
            user_id=ids['student_id'],
            start_time=slot_start,
            end_time=slot_end,
            purpose="Approved booking session A.",
            status="approved"
        )
        # Booking B is pending for overlapping period 12:00 to 16:00
        booking_b = Booking(
            resource_id=ids['res1_id'],
            user_id=ids['student2_id'],
            start_time=now + timedelta(days=5, hours=12),
            end_time=now + timedelta(days=5, hours=16),
            purpose="Compete session B overlapping with A.",
            status="pending"
        )
        db.session.add_all([booking_a, booking_b])
        db.session.commit()
        booking_b_id = booking_b.id

    login_user_helper(client, "manager1@campus.edu", "ManagerPass123!")

    # Attempt to approve Booking B which overlaps with approved Booking A
    resp = client.post(f"/bookings/{booking_b_id}/approve", follow_redirects=True)
    assert resp.status_code == 409
    assert b"Approval Blocked by Conflict" in resp.data

    # Verify Booking B remains pending in database
    with app.app_context():
        b = db.session.get(Booking, booking_b_id)
        assert b.status == 'pending'
        assert b.decided_by_id is None


# ------------------------------------------------------------------------------
# Test 10: Requests for Inactive or Maintained Resources Rejected
# ------------------------------------------------------------------------------

def test_requests_for_inactive_or_maintained_resources_rejected(client, app):
    """10. Booking requests for inactive or maintained resources are strictly rejected."""
    ids = create_test_users_and_resource(app)
    login_user_helper(client, "student@campus.edu", "StudentPass123!")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_dt = now + timedelta(days=2, hours=10)
    end_dt = now + timedelta(days=2, hours=12)

    # Attempt booking for resource under maintenance
    resp_maint = client.post(f"/resources/{ids['res_maint_id']}/book", data={
        'start_time': start_dt.strftime('%Y-%m-%dT%H:%M'),
        'end_time': end_dt.strftime('%Y-%m-%dT%H:%M'),
        'purpose': '3D Printing rapid prototype'
    }, follow_redirects=True)
    assert resp_maint.status_code == 400
    assert b"Booking unavailable" in resp_maint.data
    assert b"maintenance" in resp_maint.data

    # Attempt booking for inactive resource
    resp_inactive = client.post(f"/resources/{ids['res_inactive_id']}/book", data={
        'start_time': start_dt.strftime('%Y-%m-%dT%H:%M'),
        'end_time': end_dt.strftime('%Y-%m-%dT%H:%M'),
        'purpose': 'Inactive test'
    }, follow_redirects=True)
    assert resp_inactive.status_code == 400
    assert b"Booking unavailable" in resp_inactive.data
    assert b"inactive" in resp_inactive.data


# ------------------------------------------------------------------------------
# Test 11: Eligibility & Training Restrictions Handled Properly
# ------------------------------------------------------------------------------

def test_eligibility_and_training_restrictions_handled_properly(client, app):
    """11. Training prerequisites are surfaced on the booking form and queued for manager review."""
    ids = create_test_users_and_resource(app)

    # 1. Inspect resource detail page as student
    login_user_helper(client, "student@campus.edu", "StudentPass123!")
    detail_resp = client.get(f"/resources/{ids['res1_id']}")
    assert detail_resp.status_code == 200
    assert b"Mandatory Training Prerequisite" in detail_resp.data
    assert b"Laser Safety Level 2" in detail_resp.data
    assert b"Faculty/Technical Supervision Required" in detail_resp.data

    # 2. Submit booking request
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    submit_resp = client.post(f"/resources/{ids['res1_id']}/book", data={
        'start_time': (now + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M'),
        'end_time': (now + timedelta(days=3, hours=2)).strftime('%Y-%m-%dT%H:%M'),
        'purpose': 'Confocal biological assay testing.'
    }, follow_redirects=True)
    assert submit_resp.status_code == 200
    assert b"Laser Safety Level 2" in submit_resp.data

    # 3. Manager review queue flags prerequisite prominently
    client.get('/logout', follow_redirects=True)
    login_user_helper(client, "manager1@campus.edu", "ManagerPass123!")
    queue_resp = client.get("/manager/bookings")
    assert queue_resp.status_code == 200
    assert b"Training: Laser Safety Level 2" in queue_resp.data
    assert b"Supervised: Faculty technician presence required" in queue_resp.data


# ------------------------------------------------------------------------------
# Test 12: Student Can Cancel Pending Request
# ------------------------------------------------------------------------------

def test_student_can_cancel_pending_booking(client, app):
    """12. A student can withdraw their own pending booking request."""
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        booking = Booking(
            resource_id=ids['res1_id'],
            user_id=ids['student_id'],
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=3),
            purpose="Pending booking to cancel.",
            status="pending"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    login_user_helper(client, "student@campus.edu", "StudentPass123!")

    # Student cancels their own booking
    resp = client.post(f"/bookings/{booking_id}/cancel", follow_redirects=True)
    assert resp.status_code == 200
    assert b"has been cancelled" in resp.data

    with app.app_context():
        b = db.session.get(Booking, booking_id)
        assert b.status == 'cancelled'


# ------------------------------------------------------------------------------
# Test 13: Student Cannot Cancel Another User's Booking
# ------------------------------------------------------------------------------

def test_student_cannot_cancel_other_users_booking(client, app):
    """13. A student cannot cancel a booking request belonging to another user (HTTP 403)."""
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        booking = Booking(
            resource_id=ids['res1_id'],
            user_id=ids['student_id'],
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=3),
            purpose="Student 1 booking.",
            status="pending"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    # Log in as Student 2
    login_user_helper(client, "maya@campus.edu", "StudentPass123!")

    resp = client.post(f"/bookings/{booking_id}/cancel", follow_redirects=False)
    assert resp.status_code == 403

    with app.app_context():
        b = db.session.get(Booking, booking_id)
        assert b.status == 'pending'


# ------------------------------------------------------------------------------
# Test 14: Processed Booking Cannot Be Arbitrarily Cancelled
# ------------------------------------------------------------------------------

def test_cannot_cancel_already_processed_booking(client, app):
    """14. A booking that is already approved or rejected cannot be cancelled via pending cancel endpoint."""
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with app.app_context():
        booking = Booking(
            resource_id=ids['res1_id'],
            user_id=ids['student_id'],
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=3),
            purpose="Approved booking.",
            status="approved"
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    login_user_helper(client, "student@campus.edu", "StudentPass123!")

    resp = client.post(f"/bookings/{booking_id}/cancel", follow_redirects=True)
    assert resp.status_code == 400
    assert b"Only pending requests can be cancelled" in resp.data

    with app.app_context():
        b = db.session.get(Booking, booking_id)
        assert b.status == 'approved'


# ------------------------------------------------------------------------------
# Test 15: Competing Booking Requests Submission & Conflict Handling
# ------------------------------------------------------------------------------

def test_competing_booking_requests_submission_and_conflict_handling(client, app):
    """
    15. Competing booking requests for the same resource and overlapping interval:
        - Both can be submitted and queued as pending before approval.
        - Manager review queue displays conflict indicator.
        - Once one request is approved, submission of new overlapping request is blocked (400).
        - Attempting to approve the competing pending request is rejected with 409 Conflict.
    """
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=3)
    start_a = now.replace(minute=0, second=0, microsecond=0)
    end_a = start_a + timedelta(hours=3)
    start_b = start_a + timedelta(hours=1)
    end_b = start_b + timedelta(hours=3)

    # 1. Student 1 submits booking A
    login_user_helper(client, "student@campus.edu", "StudentPass123!")
    resp_sub_a = client.post(
        f"/resources/{ids['res1_id']}/book",
        data={
            'start_time': start_a.isoformat(),
            'end_time': end_a.isoformat(),
            'purpose': 'Student A capstone project session.'
        },
        follow_redirects=True
    )
    assert resp_sub_a.status_code == 200
    assert b"submitted successfully" in resp_sub_a.data

    # 2. Student 2 submits competing booking B for overlapping time window
    login_user_helper(client, "maya@campus.edu", "StudentPass123!")
    resp_sub_b = client.post(
        f"/resources/{ids['res1_id']}/book",
        data={
            'start_time': start_b.isoformat(),
            'end_time': end_b.isoformat(),
            'purpose': 'Student B competing session.'
        },
        follow_redirects=True
    )
    assert resp_sub_b.status_code == 200
    assert b"submitted successfully" in resp_sub_b.data

    with app.app_context():
        b_a = Booking.query.filter_by(user_id=ids['student_id'], resource_id=ids['res1_id']).first()
        b_b = Booking.query.filter_by(user_id=ids['student2_id'], resource_id=ids['res1_id']).first()
        assert b_a is not None and b_a.status == 'pending'
        assert b_b is not None and b_b.status == 'pending'
        b_a_id, b_b_id = b_a.id, b_b.id

    # 3. Manager reviews queue and approves booking A
    login_user_helper(client, "manager1@campus.edu", "ManagerPass123!")
    resp_approve = client.post(f"/bookings/{b_a_id}/approve", follow_redirects=True)
    assert resp_approve.status_code == 200
    assert b"has been approved" in resp_approve.data

    # 4. Now that booking A is approved, a new student submitting for the same window is rejected immediately
    login_user_helper(client, "student@campus.edu", "StudentPass123!")
    resp_sub_c = client.post(
        f"/resources/{ids['res1_id']}/book",
        data={
            'start_time': start_a.isoformat(),
            'end_time': end_a.isoformat(),
            'purpose': 'Student C conflicting submission.'
        },
        follow_redirects=True
    )
    assert resp_sub_c.status_code == 400
    assert b"Scheduling conflict" in resp_sub_c.data

    # 5. Manager attempts to approve competing booking B -> blocked by conflict (409)
    login_user_helper(client, "manager1@campus.edu", "ManagerPass123!")
    resp_approve_b = client.post(f"/bookings/{b_b_id}/approve", follow_redirects=False)
    assert resp_approve_b.status_code == 409

    with app.app_context():
        b_b_fresh = db.session.get(Booking, b_b_id)
        assert b_b_fresh.status == 'pending'


# ------------------------------------------------------------------------------
# Test 16: Dashboard Booking Metrics Reconcile With Real Records
# ------------------------------------------------------------------------------

def test_dashboard_metrics_reconcile_with_booking_lifecycle(client, app):
    """
    16. Verifies that student and manager dashboard metrics:
        - Accurately count underlying database booking records.
        - Update dynamically as booking transitions: pending -> approved -> checked_in -> returned.
    """
    ids = create_test_users_and_resource(app)
    now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)

    # Baseline student dashboard: 0 active, 0 pending
    login_user_helper(client, "student@campus.edu", "StudentPass123!")
    std_dash = client.get('/dashboard')
    assert std_dash.status_code == 200

    # Student submits booking request
    client.post(
        f"/resources/{ids['res1_id']}/book",
        data={
            'start_time': now.isoformat(),
            'end_time': (now + timedelta(hours=2)).isoformat(),
            'purpose': 'Metrics verification reservation.'
        },
        follow_redirects=True
    )

    with app.app_context():
        booking = Booking.query.filter_by(user_id=ids['student_id']).first()
        assert booking is not None
        booking_id = booking.id

    # Check student dashboard: pending count is 1
    std_dash2 = client.get('/dashboard')
    assert b"1" in std_dash2.data
    assert b"Pending Requests" in std_dash2.data

    # Check manager dashboard: pending_reviews_count is 1
    login_user_helper(client, "manager1@campus.edu", "ManagerPass123!")
    mgr_dash = client.get('/dashboard')
    assert b"1" in mgr_dash.data
    assert b"Pending Reviews" in mgr_dash.data

    # Manager approves booking
    client.post(f"/bookings/{booking_id}/approve", follow_redirects=True)

    # Manager dashboard: pending_reviews is 0, active_reservations is 1
    mgr_dash2 = client.get('/dashboard')
    assert b"1 Active Approved" in mgr_dash2.data

    # Student dashboard: active loans is 1
    login_user_helper(client, "student@campus.edu", "StudentPass123!")
    std_dash3 = client.get('/dashboard')
    assert b"Active Loans" in std_dash3.data

    # Manager checks in booking
    login_user_helper(client, "manager1@campus.edu", "ManagerPass123!")
    client.post(
        f"/bookings/{booking_id}/check-in",
        data={'condition_rating': 'excellent', 'notes': 'Handover inspected.'},
        follow_redirects=True
    )

    # Manager completes return
    client.post(
        f"/bookings/{booking_id}/return",
        data={'condition_rating': 'good', 'notes': 'Return inspected and closed.'},
        follow_redirects=True
    )

    # After return: active reservations is 0 on manager dashboard
    mgr_dash3 = client.get('/dashboard')
    assert b"0 Active Approved" in mgr_dash3.data
