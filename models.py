"""
models.py - Database Models for ResourceBridge
==============================================
Defines the User, Resource, and Booking models using Flask-SQLAlchemy.
Includes role-based access control, secure password hashing with Werkzeug,
resource inventory management, and end-to-end booking/approval workflows
with server-side conflict detection and safety prerequisite checks.
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the SQLAlchemy database instance
db = SQLAlchemy()

# Valid system roles for access control
VALID_ROLES = ('student', 'manager', 'admin')

# Standard campus resource categories
VALID_CATEGORIES = (
    'Computer Labs & Workstations',
    'Cameras & AV Equipment',
    'Electronics & Testing Devices',
    'Meeting Rooms & Collab Spaces',
    'Workshop & Fabrication',
    'Specialized Science & Optics'
)

# Resource types and operational statuses
VALID_RESOURCE_TYPES = ('equipment', 'space')
VALID_STATUSES = ('active', 'inactive', 'maintenance')

# Booking lifecycle statuses
VALID_BOOKING_STATUSES = (
    'pending',
    'approved',
    'checked_in',
    'return_pending',
    'returned',
    'rejected',
    'cancelled',
    'overdue'
)

# Condition reporting standards
VALID_CONDITION_RATINGS = ('excellent', 'good', 'fair', 'damaged', 'maintenance_required')
VALID_REPORT_STAGES = ('check_in', 'check_out')

# Incident management standards
VALID_INCIDENT_CATEGORIES = (
    'equipment_damage',
    'missing_accessory',
    'late_return',
    'safety_concern',
    'malfunction',
    'other'
)
VALID_INCIDENT_STATUSES = ('open', 'under_review', 'resolved')
VALID_INCIDENT_SEVERITIES = ('low', 'medium', 'high', 'critical')


class User(UserMixin, db.Model):
    """
    User Account Model
    ------------------
    Represents students, resource managers, and campus administrators.
    Inherits from UserMixin to provide default Flask-Login implementations
    (is_authenticated, is_active, is_anonymous, get_id).
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    is_verified = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationship to resources managed by this user
    resources = db.relationship(
        'Resource',
        backref='owner',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __init__(self, name, email, password, role='student', is_verified=True):
        self.name = name.strip()
        self.email = email.strip().lower()
        self.set_password(password)
        # Ensure only recognized roles are stored
        self.role = role if role in VALID_ROLES else 'student'
        self.is_verified = is_verified

    def set_password(self, password):
        """Hash the plain-text password using Werkzeug's secure algorithm."""
        if not password:
            raise ValueError("Password cannot be empty.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify candidate password against the stored password hash."""
        if not password or not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # Role inspection helpers (cleaner in templates and route guards)
    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def can_manage_resources(self):
        """Returns True if the user is authorized to create/manage resources."""
        return self.role in ('manager', 'admin')

    @property
    def role_title(self):
        """Human-readable title for UI display."""
        titles = {
            'student': 'Student Member',
            'manager': 'Resource Manager',
            'admin': 'System Administrator'
        }
        return titles.get(self.role, self.role.title())

    @property
    def role_badge_class(self):
        """CSS class helper for role badges."""
        classes = {
            'student': 'badge-student',
            'manager': 'badge-manager',
            'admin': 'badge-admin'
        }
        return classes.get(self.role, 'badge-default')

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"


class Resource(db.Model):
    """
    Resource Inventory Model
    ------------------------
    Represents institutional campus resources such as laboratories, cameras,
    computers, testing devices, meeting rooms, and workshop equipment.
    Includes availability details, safety/training prerequisites, and owner mapping.
    """
    __tablename__ = 'resources'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(60), nullable=False, index=True)
    resource_type = db.Column(db.String(20), nullable=False, default='equipment')  # 'equipment' or 'space'
    location = db.Column(db.String(120), nullable=False, index=True)
    availability_info = db.Column(db.String(200), nullable=False)
    usage_rules = db.Column(db.Text, nullable=True)
    eligibility = db.Column(db.String(255), nullable=True)

    # Safety, Induction, and Supervision Flags
    training_required = db.Column(db.Boolean, nullable=False, default=False)
    training_details = db.Column(db.String(255), nullable=True)
    supervision_required = db.Column(db.Boolean, nullable=False, default=False)
    supervision_details = db.Column(db.String(255), nullable=True)

    # Operational status: active, inactive, or maintenance
    status = db.Column(db.String(20), nullable=False, default='active', index=True)

    # Distinguishes independently verified resources from unverified owner-provided information
    is_verified = db.Column(db.Boolean, nullable=False, default=True)

    # Authorised manager or faculty owner
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def __init__(
        self,
        name,
        description,
        category,
        location,
        availability_info,
        owner_id,
        resource_type='equipment',
        usage_rules=None,
        eligibility=None,
        training_required=False,
        training_details=None,
        supervision_required=False,
        supervision_details=None,
        status='active',
        is_verified=True
    ):
        self.name = name.strip()
        self.description = description.strip()
        self.category = category.strip()
        self.location = location.strip()
        self.availability_info = availability_info.strip()
        self.owner_id = owner_id
        self.resource_type = resource_type if resource_type in VALID_RESOURCE_TYPES else 'equipment'
        self.usage_rules = usage_rules.strip() if usage_rules else None
        self.eligibility = eligibility.strip() if eligibility else None
        self.training_required = bool(training_required)
        self.training_details = training_details.strip() if training_details else None
        self.supervision_required = bool(supervision_required)
        self.supervision_details = supervision_details.strip() if supervision_details else None
        self.status = status if status in VALID_STATUSES else 'active'
        self.is_verified = bool(is_verified)

    # Status helpers
    @property
    def is_active(self):
        return self.status == 'active'

    @property
    def is_maintenance(self):
        return self.status == 'maintenance'

    @property
    def is_inactive(self):
        return self.status == 'inactive'

    @property
    def is_equipment(self):
        return self.resource_type == 'equipment'

    @property
    def is_space(self):
        return self.resource_type == 'space'

    @property
    def status_title(self):
        titles = {
            'active': 'Active in Catalog',
            'maintenance': 'Under Maintenance',
            'inactive': 'Inactive'
        }
        return titles.get(self.status, self.status.title())

    @property
    def status_badge_class(self):
        classes = {
            'active': 'badge-success',
            'maintenance': 'badge-warning',
            'inactive': 'badge-default'
        }
        return classes.get(self.status, 'badge-default')

    @property
    def type_badge_class(self):
        return 'badge-equipment' if self.is_equipment else 'badge-space'

    def can_be_managed_by(self, user):
        """
        Server-side permission guard:
        - System administrators can manage all resources.
        - Resource managers can manage resources they own.
        - Students and unauthenticated users cannot manage any resources.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        if user.is_manager and self.owner_id == user.id:
            return True
        return False

    def __repr__(self):
        return f"<Resource id={self.id} name='{self.name}' status='{self.status}' owner_id={self.owner_id}>"


class Booking(db.Model):
    """
    Booking Reservation Model
    -------------------------
    Represents a student booking request for a college resource.
    Tracks requested time period, purpose, status lifecycle (pending, approved,
    rejected, cancelled), manager decision timestamps, rejection reasons,
    and timestamps for future check-in/return accountability.
    """
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    purpose = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)

    # Decision audit fields
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    decided_at = db.Column(db.DateTime, nullable=True)
    decided_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Future lifecycle checkpoints (physical hand-off & return reconciliation)
    checked_in_at = db.Column(db.DateTime, nullable=True)
    checked_out_at = db.Column(db.DateTime, nullable=True)  # Legacy alias for check-in
    return_requested_at = db.Column(db.DateTime, nullable=True)
    returned_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    resource = db.relationship(
        'Resource',
        backref=db.backref('bookings', lazy=True, cascade='all, delete-orphan')
    )
    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('bookings', lazy=True, cascade='all, delete-orphan')
    )
    decision_maker = db.relationship(
        'User',
        foreign_keys=[decided_by_id]
    )

    condition_reports = db.relationship(
        'ConditionReport',
        backref=db.backref('booking', lazy=True),
        lazy=True,
        cascade='all, delete-orphan',
        order_by='ConditionReport.created_at.asc()'
    )
    incidents = db.relationship(
        'Incident',
        backref=db.backref('booking', lazy=True),
        lazy=True,
        cascade='all, delete-orphan',
        order_by='Incident.created_at.desc()'
    )
    audit_logs = db.relationship(
        'BookingAuditLog',
        backref=db.backref('booking', lazy=True),
        lazy=True,
        cascade='all, delete-orphan',
        order_by='BookingAuditLog.created_at.asc()'
    )

    def __init__(
        self,
        resource_id,
        user_id,
        start_time,
        end_time,
        purpose,
        status='pending'
    ):
        self.resource_id = resource_id
        self.user_id = user_id
        self.start_time = start_time
        self.end_time = end_time
        self.purpose = purpose.strip()
        self.status = status if status in VALID_BOOKING_STATUSES else 'pending'

    # Status helpers
    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def is_approved(self):
        return self.status == 'approved'

    @property
    def is_checked_in(self):
        return self.status == 'checked_in'

    @property
    def is_return_pending(self):
        return self.status == 'return_pending'

    @property
    def is_returned(self):
        return self.status == 'returned'

    @property
    def is_rejected(self):
        return self.status == 'rejected'

    @property
    def is_cancelled(self):
        return self.status == 'cancelled'

    @property
    def is_overdue(self):
        return self.status == 'overdue'

    @property
    def status_title(self):
        titles = {
            'pending': 'Pending Review',
            'approved': 'Approved',
            'checked_in': 'Checked In (Active)',
            'return_pending': 'Return Pending',
            'returned': 'Returned & Completed',
            'rejected': 'Rejected',
            'cancelled': 'Cancelled',
            'overdue': 'Overdue'
        }
        return titles.get(self.status, self.status.replace('_', ' ').title())

    @property
    def status_badge_class(self):
        classes = {
            'pending': 'badge-warning',
            'approved': 'badge-info',
            'checked_in': 'badge-success',
            'return_pending': 'badge-warning',
            'returned': 'badge-default',
            'rejected': 'badge-danger',
            'cancelled': 'badge-default',
            'overdue': 'badge-danger'
        }
        return classes.get(self.status, 'badge-default')

    @property
    def duration_hours(self):
        """Calculates duration in decimal hours."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return round(delta.total_seconds() / 3600.0, 1)
        return 0.0

    def can_be_managed_by(self, user):
        """
        Check if user is authorized to approve, reject, check-in, or return this booking:
        - Admin can manage all bookings.
        - Manager can manage bookings for resources they own.
        - Requester/student cannot manage.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        if user.is_manager and self.resource and self.resource.owner_id == user.id:
            return True
        return False

    def can_be_viewed_by(self, user):
        """
        Server-side privacy guard:
        A booking detail page and audit history can only be viewed by:
        - The student who created the booking (requester).
        - The manager who owns the resource.
        - System administrators.
        Other students or unrelated managers receive 403 Forbidden.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        if self.user_id == user.id:
            return True
        if user.is_manager and self.resource and self.resource.owner_id == user.id:
            return True
        return False

    def get_initial_condition_report(self):
        """Returns the check-in condition report if recorded."""
        for r in self.condition_reports:
            if r.report_stage == 'check_in':
                return r
        return None

    def get_final_condition_report(self):
        """Returns the check-out condition report if recorded."""
        for r in self.condition_reports:
            if r.report_stage == 'check_out':
                return r
        return None

    def __repr__(self):
        return f"<Booking id={self.id} resource_id={self.resource_id} user_id={self.user_id} status='{self.status}'>"


class ConditionReport(db.Model):
    """
    Condition Report Model
    ----------------------
    Records equipment/space condition at physical check-in and check-out handovers.
    Supports rating, structured notes, and optional photo attachment path.
    """
    __tablename__ = 'condition_reports'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    report_stage = db.Column(db.String(20), nullable=False)  # 'check_in' or 'check_out'
    condition_rating = db.Column(db.String(30), nullable=False)  # excellent, good, fair, damaged, maintenance_required
    notes = db.Column(db.Text, nullable=False)
    photo_path = db.Column(db.String(255), nullable=True)  # Optional photo attachment path
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    reporter = db.relationship('User', foreign_keys=[reporter_id])
    resource = db.relationship('Resource', foreign_keys=[resource_id])

    @property
    def rating_badge_class(self):
        classes = {
            'excellent': 'badge-success',
            'good': 'badge-info',
            'fair': 'badge-warning',
            'damaged': 'badge-danger',
            'maintenance_required': 'badge-danger'
        }
        return classes.get(self.condition_rating, 'badge-default')

    @property
    def rating_title(self):
        return self.condition_rating.replace('_', ' ').title()

    @property
    def stage_title(self):
        return 'Check-In Condition' if self.report_stage == 'check_in' else 'Check-Out Return Condition'

    def __repr__(self):
        return f"<ConditionReport id={self.id} booking_id={self.booking_id} stage='{self.report_stage}' rating='{self.condition_rating}'>"


class Incident(db.Model):
    """
    Incident Tracking Model
    -----------------------
    Records safety concerns, equipment damage, missing accessories, or operational
    issues related to a booking. Enables transparent review and manager resolution notes.
    """
    __tablename__ = 'incidents'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    category = db.Column(db.String(40), nullable=False)  # equipment_damage, missing_accessory, late_return, etc.
    severity = db.Column(db.String(20), nullable=False, default='medium')  # low, medium, high, critical
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='open')  # open, under_review, resolved
    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    reporter = db.relationship('User', foreign_keys=[reporter_id])
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id])
    resource = db.relationship('Resource', foreign_keys=[resource_id])

    @property
    def is_open(self):
        return self.status == 'open'

    @property
    def is_under_review(self):
        return self.status == 'under_review'

    @property
    def is_resolved(self):
        return self.status == 'resolved'

    @property
    def status_title(self):
        titles = {
            'open': 'Open Issue',
            'under_review': 'Under Review',
            'resolved': 'Resolved'
        }
        return titles.get(self.status, self.status.replace('_', ' ').title())

    @property
    def status_badge_class(self):
        classes = {
            'open': 'badge-danger',
            'under_review': 'badge-warning',
            'resolved': 'badge-success'
        }
        return classes.get(self.status, 'badge-default')

    @property
    def category_title(self):
        return self.category.replace('_', ' ').title()

    @property
    def severity_badge_class(self):
        classes = {
            'low': 'badge-info',
            'medium': 'badge-warning',
            'high': 'badge-danger',
            'critical': 'badge-danger'
        }
        return classes.get(self.severity, 'badge-default')

    def can_be_managed_by(self, user):
        """
        Only resource owner manager or admin can update status or resolve an incident.
        Students can never resolve their own or others' incidents.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        if user.is_manager and self.resource and self.resource.owner_id == user.id:
            return True
        return False

    def __repr__(self):
        return f"<Incident id={self.id} booking_id={self.booking_id} category='{self.category}' status='{self.status}'>"


class BookingAuditLog(db.Model):
    """
    Booking Audit Log Model
    -----------------------
    Server-generated immutable audit trail for every booking lifecycle event.
    Records who, what, when, and context (e.g. rejection reason, handover notes).
    """
    __tablename__ = 'booking_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    summary = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    actor = db.relationship('User', foreign_keys=[actor_id])

    @property
    def event_badge_class(self):
        classes = {
            'requested': 'badge-warning',
            'approved': 'badge-info',
            'rejected': 'badge-danger',
            'cancelled': 'badge-default',
            'checked_in': 'badge-success',
            'return_requested': 'badge-warning',
            'returned': 'badge-default',
            'condition_reported': 'badge-info',
            'incident_reported': 'badge-danger',
            'incident_resolved': 'badge-success',
            'status_updated': 'badge-info'
        }
        return classes.get(self.event_type, 'badge-default')

    def __repr__(self):
        return f"<BookingAuditLog id={self.id} booking_id={self.booking_id} event_type='{self.event_type}'>"


def log_booking_event(booking_id, actor_id, event_type, summary, details=None):
    """
    Server-Side Audit Logger Helper:
    Creates and persists a BookingAuditLog entry within the active db.session.
    Guarantees that event descriptions and timestamps originate from the backend.
    """
    audit_entry = BookingAuditLog(
        booking_id=booking_id,
        actor_id=actor_id,
        event_type=event_type,
        summary=summary.strip() if summary else event_type.replace('_', ' ').title(),
        details=details.strip() if details else None
    )
    db.session.add(audit_entry)
    return audit_entry


def check_booking_conflict(resource_id, start_time, end_time, exclude_booking_id=None):
    """
    Server-Side Conflict Detection Algorithm:
    Checks if an approved, checked-in, or return-pending booking already exists
    for the specified resource that overlaps with the candidate [start_time, end_time] interval.

    Standard Overlap Condition:
        (existing.start_time < candidate.end_time) AND (existing.end_time > candidate.start_time)

    Returns the conflicting Booking instance if found, or None if the slot is clear.
    """
    query = Booking.query.filter(
        Booking.resource_id == resource_id,
        Booking.status.in_(['approved', 'checked_in', 'return_pending']),
        Booking.start_time < end_time,
        Booking.end_time > start_time
    )
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    return query.first()
