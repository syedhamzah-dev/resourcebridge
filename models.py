"""
models.py - Database Models for ResourceBridge
==============================================
Defines the User and Resource models and database schema using Flask-SQLAlchemy.
Includes role-based access fields, secure password hashing with Werkzeug,
and full resource inventory management with safety/training prerequisites.
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
