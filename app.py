"""
app.py - ResourceBridge Main Application
========================================
Main Flask application entry point for ResourceBridge.
Handles routing, authentication, role-aware dashboarding,
resource inventory, catalog discovery, search/filtering,
database initialization, and seeding of demo accounts & resources.
"""

import os
import secrets
from functools import wraps
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    session,
    abort
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)
from models import (
    db,
    User,
    Resource,
    VALID_CATEGORIES,
    VALID_RESOURCE_TYPES,
    VALID_STATUSES
)

# Load environment variables if python-dotenv is present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def role_required(*allowed_roles):
    """
    Decorator to restrict access to specific user roles.
    Example: @role_required('admin', 'manager')
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role not in allowed_roles:
                flash("Access denied: You do not have permission to access that area.", "danger")
                return redirect(url_for('dashboard')), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def create_app(test_config=None):
    """Application factory for ResourceBridge."""
    app = Flask(__name__, instance_relative_config=True)

    # Ensure the instance directory exists for SQLite database storage
    os.makedirs(app.instance_path, exist_ok=True)
    default_db_path = os.path.join(app.instance_path, 'resourcebridge.db')

    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-hackathon-insecure-secret-key-change-in-prod'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', f"sqlite:///{default_db_path}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=True
    )

    # Override configuration for testing if provided
    if test_config:
        app.config.update(test_config)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        """Flask-Login helper: Loads the logged-in user from the database by ID."""
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    # --------------------------------------------------------------------------
    # Lightweight CSRF Protection & Template Helpers
    # --------------------------------------------------------------------------

    def generate_csrf_token():
        """Generates or retrieves a unique session token for CSRF protection."""
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(16)
        return session['_csrf_token']

    @app.context_processor
    def inject_helpers():
        """Inject global helpers and constants into all Jinja2 templates."""
        return {
            'csrf_token': generate_csrf_token,
            'VALID_CATEGORIES': VALID_CATEGORIES,
            'VALID_RESOURCE_TYPES': VALID_RESOURCE_TYPES,
            'VALID_STATUSES': VALID_STATUSES
        }

    @app.before_request
    def check_csrf():
        """Verify CSRF token on state-changing HTTP requests."""
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            # Allow tests to bypass CSRF if explicitly disabled in test configuration
            if app.config.get('TESTING') and not app.config.get('WTF_CSRF_ENABLED', True):
                return
            token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
            if not token or token != session.get('_csrf_token'):
                flash("Security alert: Form session expired or invalid CSRF token. Please submit again.", "danger")
                return redirect(request.referrer or url_for('index'))

    # --------------------------------------------------------------------------
    # Public & Landing Routes
    # --------------------------------------------------------------------------

    @app.route('/')
    def index():
        """Public landing page highlighting ResourceBridge's mission and live assets."""
        # Query active sample resources from the database for the live status box
        featured_resources = Resource.query.order_by(Resource.id.asc()).limit(4).all()
        active_count = Resource.query.filter_by(status='active').count()
        return render_template('index.html', featured_resources=featured_resources, active_count=active_count)

    @app.route('/about')
    def about():
        """About page detailing trust, safety, and accountability protocols."""
        return render_template('about.html')

    # --------------------------------------------------------------------------
    # Authentication Routes
    # --------------------------------------------------------------------------

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """
        Public user registration.
        Security rule: All public registrations are strictly assigned the 'student' role.
        Manager and Admin privileges cannot be assigned via public sign-up.
        """
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            # Server-side validation
            errors = []
            if not name:
                errors.append("Full name is required.")
            if not email or '@' not in email or '.' not in email:
                errors.append("A valid academic or personal email address is required.")
            if not password:
                errors.append("Password is required.")
            elif len(password) < 6:
                errors.append("Password must be at least 6 characters long.")
            if password != confirm_password:
                errors.append("Passwords do not match.")

            # Check if email is already registered
            if not errors:
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    errors.append("An account with this email address already exists.")

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template('register.html', name=name, email=email)

            # Create new student account (strictly student role)
            try:
                new_user = User(
                    name=name,
                    email=email,
                    password=password,
                    role='student',
                    is_verified=True  # Standard demo verification for smooth hackathon testing
                )
                db.session.add(new_user)
                db.session.commit()
                flash("Your student account was created successfully! Please log in below.", "success")
                return redirect(url_for('login'))
            except Exception:
                db.session.rollback()
                flash("An unexpected error occurred while creating your account. Please try again.", "danger")
                return render_template('register.html', name=name, email=email)

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """
        User login with email and password verification.
        Includes demo credentials hint to streamline hackathon evaluation.
        """
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            remember = True if request.form.get('remember') else False

            if not email or not password:
                flash("Please enter both your email address and password.", "danger")
                return render_template('login.html', email=email)

            user = User.query.filter_by(email=email).first()

            if not user or not user.check_password(password):
                flash("Invalid email or password. Please verify your credentials.", "danger")
                return render_template('login.html', email=email)

            login_user(user, remember=remember)
            flash(f"Welcome back, {user.name}! Signed in as {user.role_title}.", "success")

            # Safe redirection to target page if specified
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            return redirect(next_page)

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        """Log out the current user and redirect to login page."""
        logout_user()
        flash("You have been signed out securely.", "info")
        return redirect(url_for('login'))

    # --------------------------------------------------------------------------
    # Resource Discovery & Catalog Routes
    # --------------------------------------------------------------------------

    @app.route('/resources')
    def resources_list():
        """
        Resource Catalogue & Search Discovery.
        Queries real database records with keyword search, category filtering,
        resource type (equipment vs space) filtering, and location filtering.
        """
        search_query = request.args.get('q', '').strip()
        selected_category = request.args.get('category', '').strip()
        selected_type = request.args.get('type', '').strip()
        selected_location = request.args.get('location', '').strip()
        selected_status = request.args.get('status', 'all').strip()
        selected_training = request.args.get('training', '').strip()
        selected_supervision = request.args.get('supervision', '').strip()

        # Build parameterized SQLAlchemy query
        query = Resource.query

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                db.or_(
                    Resource.name.ilike(search_pattern),
                    Resource.description.ilike(search_pattern),
                    Resource.location.ilike(search_pattern)
                )
            )

        if selected_category and selected_category != 'all':
            query = query.filter(Resource.category == selected_category)

        if selected_type and selected_type != 'all':
            query = query.filter(Resource.resource_type == selected_type)

        if selected_location and selected_location != 'all':
            query = query.filter(Resource.location.ilike(f"%{selected_location}%"))

        if selected_status and selected_status != 'all':
            query = query.filter(Resource.status == selected_status)

        if selected_training in ('yes', 'no'):
            query = query.filter(Resource.training_required == (selected_training == 'yes'))

        if selected_supervision in ('yes', 'no'):
            query = query.filter(Resource.supervision_required == (selected_supervision == 'yes'))

        # Fetch matching records ordered by name
        resources = query.order_by(Resource.name.asc()).all()

        # Extract available locations and categories for filter menus
        available_categories = [
            c[0] for c in db.session.query(Resource.category).distinct().order_by(Resource.category).all()
        ]
        available_locations = [
            loc[0] for loc in db.session.query(Resource.location).distinct().order_by(Resource.location).all()
        ]

        return render_template(
            'resources/index.html',
            resources=resources,
            search_query=search_query,
            selected_category=selected_category,
            selected_type=selected_type,
            selected_location=selected_location,
            selected_status=selected_status,
            selected_training=selected_training,
            selected_supervision=selected_supervision,
            available_categories=available_categories or VALID_CATEGORIES,
            available_locations=available_locations
        )

    @app.route('/resources/<int:resource_id>')
    def resource_detail(resource_id):
        """
        Resource Details Page.
        Displays complete specifications, location, availability schedule,
        eligibility, usage rules, and safety/supervision prerequisites.
        Safely handles non-existent IDs.
        """
        resource = db.session.get(Resource, resource_id)
        if not resource:
            flash(f"Resource #{resource_id} was not found in the catalog.", "danger")
            abort(404)

        return render_template('resources/detail.html', resource=resource)

    # --------------------------------------------------------------------------
    # Owner & Manager Resource Management Workflows
    # --------------------------------------------------------------------------

    @app.route('/resources/new', methods=['GET', 'POST'])
    @login_required
    def new_resource():
        """
        Resource Creation Workflow.
        Strict server-side check: Only authorized managers and administrators
        can create campus resources. Students cannot bypass this restriction.
        """
        if not current_user.can_manage_resources:
            flash("Access denied: Only authorized resource managers and administrators can add campus resources.", "danger")
            return redirect(url_for('resources_list')), 403

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', '').strip()
            resource_type = request.form.get('resource_type', 'equipment').strip()
            location = request.form.get('location', '').strip()
            availability_info = request.form.get('availability_info', '').strip()
            usage_rules = request.form.get('usage_rules', '').strip()
            eligibility = request.form.get('eligibility', '').strip()
            status = request.form.get('status', 'active').strip()

            training_required = True if request.form.get('training_required') else False
            training_details = request.form.get('training_details', '').strip()
            supervision_required = True if request.form.get('supervision_required') else False
            supervision_details = request.form.get('supervision_details', '').strip()

            # Server-side validation
            errors = []
            if not name:
                errors.append("Resource name is required.")
            if not description:
                errors.append("Resource description is required.")
            if not category or category not in VALID_CATEGORIES:
                errors.append(f"Please select a valid resource category.")
            if not resource_type or resource_type not in VALID_RESOURCE_TYPES:
                errors.append("Resource type must be either 'equipment' or 'space'.")
            if not location:
                errors.append("Campus location is required.")
            if not availability_info:
                errors.append("Availability info or operating hours are required.")
            if status not in VALID_STATUSES:
                errors.append("Status must be 'active', 'inactive', or 'maintenance'.")

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    'resources/form.html',
                    action='create',
                    form_data=request.form
                ), 400

            # Secure persistence: Never trust client for owner_id, use current_user.id
            try:
                resource = Resource(
                    name=name,
                    description=description,
                    category=category,
                    resource_type=resource_type,
                    location=location,
                    availability_info=availability_info,
                    owner_id=current_user.id,
                    usage_rules=usage_rules,
                    eligibility=eligibility,
                    training_required=training_required,
                    training_details=training_details if training_required else None,
                    supervision_required=supervision_required,
                    supervision_details=supervision_details if supervision_required else None,
                    status=status,
                    is_verified=True
                )
                db.session.add(resource)
                db.session.commit()
                flash(f"Resource '{resource.name}' was successfully catalogued in ResourceBridge!", "success")
                return redirect(url_for('resource_detail', resource_id=resource.id))
            except Exception as e:
                db.session.rollback()
                flash("An unexpected error occurred while saving the resource. Please try again.", "danger")
                return render_template(
                    'resources/form.html',
                    action='create',
                    form_data=request.form
                ), 500

        return render_template('resources/form.html', action='create', form_data={})

    @app.route('/resources/<int:resource_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_resource(resource_id):
        """
        Resource Edit Workflow.
        Strict server-side check: An owner can only edit resources they manage,
        unless they hold the administrator role.
        """
        resource = db.session.get(Resource, resource_id)
        if not resource:
            flash(f"Resource #{resource_id} not found.", "danger")
            abort(404)

        # Enforce server-side authorization guard
        if not resource.can_be_managed_by(current_user):
            flash("Access denied: You are not authorized to edit this resource.", "danger")
            return redirect(url_for('resource_detail', resource_id=resource.id)), 403

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', '').strip()
            resource_type = request.form.get('resource_type', 'equipment').strip()
            location = request.form.get('location', '').strip()
            availability_info = request.form.get('availability_info', '').strip()
            usage_rules = request.form.get('usage_rules', '').strip()
            eligibility = request.form.get('eligibility', '').strip()
            status = request.form.get('status', 'active').strip()

            training_required = True if request.form.get('training_required') else False
            training_details = request.form.get('training_details', '').strip()
            supervision_required = True if request.form.get('supervision_required') else False
            supervision_details = request.form.get('supervision_details', '').strip()

            errors = []
            if not name:
                errors.append("Resource name is required.")
            if not description:
                errors.append("Resource description is required.")
            if not category or category not in VALID_CATEGORIES:
                errors.append("Please select a valid resource category.")
            if not resource_type or resource_type not in VALID_RESOURCE_TYPES:
                errors.append("Resource type must be either 'equipment' or 'space'.")
            if not location:
                errors.append("Campus location is required.")
            if not availability_info:
                errors.append("Availability info or operating hours are required.")
            if status not in VALID_STATUSES:
                errors.append("Status must be 'active', 'inactive', or 'maintenance'.")

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    'resources/form.html',
                    action='edit',
                    resource=resource,
                    form_data=request.form
                ), 400

            try:
                resource.name = name
                resource.description = description
                resource.category = category
                resource.resource_type = resource_type
                resource.location = location
                resource.availability_info = availability_info
                resource.usage_rules = usage_rules or None
                resource.eligibility = eligibility or None
                resource.training_required = training_required
                resource.training_details = training_details if training_required else None
                resource.supervision_required = supervision_required
                resource.supervision_details = supervision_details if supervision_required else None
                resource.status = status

                db.session.commit()
                flash(f"Resource '{resource.name}' was updated successfully.", "success")
                return redirect(url_for('resource_detail', resource_id=resource.id))
            except Exception:
                db.session.rollback()
                flash("An unexpected error occurred while updating the resource.", "danger")
                return render_template(
                    'resources/form.html',
                    action='edit',
                    resource=resource,
                    form_data=request.form
                ), 500

        # Pre-populate form data for GET request
        form_data = {
            'name': resource.name,
            'description': resource.description,
            'category': resource.category,
            'resource_type': resource.resource_type,
            'location': resource.location,
            'availability_info': resource.availability_info,
            'usage_rules': resource.usage_rules or '',
            'eligibility': resource.eligibility or '',
            'training_required': resource.training_required,
            'training_details': resource.training_details or '',
            'supervision_required': resource.supervision_required,
            'supervision_details': resource.supervision_details or '',
            'status': resource.status
        }
        return render_template('resources/form.html', action='edit', resource=resource, form_data=form_data)

    @app.route('/resources/manage')
    @login_required
    def manage_resources():
        """
        Manager/Admin Inventory Overview.
        Managers view resources they own; Admins view all catalog resources.
        """
        if not current_user.can_manage_resources:
            flash("Access denied: Only managers and administrators can view the inventory management portal.", "danger")
            return redirect(url_for('dashboard')), 403

        if current_user.is_admin:
            resources = Resource.query.order_by(Resource.created_at.desc()).all()
            title = "Campus Resource Administration"
        else:
            resources = Resource.query.filter_by(owner_id=current_user.id).order_by(Resource.created_at.desc()).all()
            title = "My Managed Department Resources"

        return render_template('resources/manage.html', resources=resources, title=title)

    # --------------------------------------------------------------------------
    # Role-Aware Dashboard & Protected Routes
    # --------------------------------------------------------------------------

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """
        Main application dashboard.
        Uses real database queries for operational statistics:
        - student: actual count of active resources & catalog sample
        - manager: count of resources managed by current user, maintenance alerts, recent items
        - admin: total users, total resources, active vs maintenance breakdown
        """
        db_stats = {}

        if current_user.is_student:
            db_stats['total_active_resources'] = Resource.query.filter_by(status='active').count()
            db_stats['total_categories'] = db.session.query(Resource.category).distinct().count()
            db_stats['recent_resources'] = Resource.query.filter_by(status='active').order_by(Resource.id.desc()).limit(3).all()

        elif current_user.is_manager:
            db_stats['my_total_resources'] = Resource.query.filter_by(owner_id=current_user.id).count()
            db_stats['my_active_resources'] = Resource.query.filter_by(owner_id=current_user.id, status='active').count()
            db_stats['my_maintenance_resources'] = Resource.query.filter_by(owner_id=current_user.id, status='maintenance').count()
            db_stats['my_recent_resources'] = Resource.query.filter_by(owner_id=current_user.id).order_by(Resource.id.desc()).limit(4).all()

        elif current_user.is_admin:
            db_stats['total_users'] = User.query.count()
            db_stats['total_resources'] = Resource.query.count()
            db_stats['total_active_resources'] = Resource.query.filter_by(status='active').count()
            db_stats['total_maintenance_resources'] = Resource.query.filter_by(status='maintenance').count()
            db_stats['recent_resources'] = Resource.query.order_by(Resource.id.desc()).limit(5).all()

        return render_template('dashboard.html', user=current_user, stats=db_stats)

    # --------------------------------------------------------------------------
    # 404 Error Handler
    # --------------------------------------------------------------------------

    @app.errorhandler(404)
    def page_not_found(e):
        """Graceful, safe 404 handler for invalid resource IDs and broken links."""
        return render_template('404.html'), 404

    # --------------------------------------------------------------------------
    # CLI Commands for Database Management & Demo Seeding
    # --------------------------------------------------------------------------

    @app.cli.command('init-db')
    def init_db_command():
        """Initialize database tables without deleting existing records."""
        with app.app_context():
            db.create_all()
        print("Initialized SQLite database tables successfully.")

    @app.cli.command('seed')
    def seed_command():
        """Seed fictional demonstration accounts and campus resources for hackathon evaluation."""
        user_count = seed_demo_users(app)
        resource_count = seed_demo_resources(app)
        print(f"Seeded {user_count} demonstration accounts and {resource_count} resources.")

    return app


def seed_demo_users(app):
    """
    Populates database with 3 fictional demonstration accounts representing
    each role: Student, Manager, and Admin.
    Passwords are fully hashed using Werkzeug.
    """
    demo_accounts = [
        {
            'name': 'Alex Rivera (Demo Student)',
            'email': 'student@campus.edu',
            'password': 'StudentPass123!',
            'role': 'student',
            'is_verified': True
        },
        {
            'name': 'Dr. Elena Vance (Lab Manager)',
            'email': 'manager@campus.edu',
            'password': 'ManagerPass123!',
            'role': 'manager',
            'is_verified': True
        },
        {
            'name': 'Marcus Brody (Campus Admin)',
            'email': 'admin@campus.edu',
            'password': 'AdminPass123!',
            'role': 'admin',
            'is_verified': True
        }
    ]

    count = 0
    with app.app_context():
        db.create_all()
        for data in demo_accounts:
            existing = User.query.filter_by(email=data['email']).first()
            if not existing:
                user = User(
                    name=data['name'],
                    email=data['email'],
                    password=data['password'],
                    role=data['role'],
                    is_verified=data['is_verified']
                )
                db.session.add(user)
                count += 1
            else:
                existing.name = data['name']
                existing.role = data['role']
                existing.set_password(data['password'])
                existing.is_verified = data['is_verified']
                count += 1
        db.session.commit()
    return count


def seed_demo_resources(app):
    """
    Populates database with realistic, diverse fictional campus resources
    spanning computer labs, cameras, testing devices, seminar rooms, and makerspace tools.
    Safely updates or skips existing items without creating duplicates.
    """
    with app.app_context():
        db.create_all()
        manager = User.query.filter_by(email='manager@campus.edu').first()
        admin = User.query.filter_by(email='admin@campus.edu').first()

        if not manager or not admin:
            seed_demo_users(app)
            manager = User.query.filter_by(email='manager@campus.edu').first()
            admin = User.query.filter_by(email='admin@campus.edu').first()

        demo_resources = [
            {
                'name': 'Photonics & Optical Microscopy Suite',
                'description': 'Clean-room research laboratory equipped with confocal laser scanning microscopes, vibration isolation tables, and spectroscopic analysis workstations for advanced nanotechnology and materials science projects.',
                'category': 'Specialized Science & Optics',
                'resource_type': 'space',
                'location': 'Science Complex, Hall B, Room 402',
                'availability_info': 'Mon-Fri 08:30 - 17:30, After-hours access requires faculty induction',
                'usage_rules': 'Class 3B laser safety eyewear is mandatory at all times. Log all laser runtime hours in physical ledger upon checkout.',
                'eligibility': 'Enrolled engineering, physics, and bio-nanotech students with approved faculty supervisor endorsement.',
                'training_required': True,
                'training_details': 'Level 2 Laser Safety Certification and Cleanroom Protocol Induction.',
                'supervision_required': True,
                'supervision_details': 'Must be supervised by designated optical technician or faculty mentor.',
                'status': 'active',
                'owner_id': manager.id
            },
            {
                'name': 'Sony FX3 Cinema Rig & Ronin Stabilizer Kit',
                'description': 'Full-frame 4K cinema production package complete with 24-70mm f/2.8 G Master zoom lens, DJI Ronin-RS3 Pro 3-axis motorized gimbal, dual high-speed CFexpress cards, and wireless Sennheiser lavalier microphone kit.',
                'category': 'Cameras & AV Equipment',
                'resource_type': 'equipment',
                'location': 'Arts & Media Center, Equipment Cage Locker 12',
                'availability_info': 'Daily 09:00 - 18:00, Maximum loan duration 48 hours',
                'usage_rules': 'Must be returned packed in waterproof Pelican hard case. Inspect camera sensor and lens optics with cage technician before signing receipt.',
                'eligibility': 'Film studies, digital media, journalism students, and registered student organization media officers in good standing.',
                'training_required': False,
                'training_details': None,
                'supervision_required': False,
                'supervision_details': None,
                'status': 'active',
                'owner_id': manager.id
            },
            {
                'name': 'NVIDIA RTX 4090 Deep Learning Node',
                'description': 'Dedicated high-performance GPU computing node with 24GB VRAM, 64-core AMD Threadripper CPU, and 128GB ECC RAM. Pre-configured with PyTorch, CUDA 12, JupyterLab, and local Ollama inference models.',
                'category': 'Computer Labs & Workstations',
                'resource_type': 'equipment',
                'location': 'Turing Computer Science Building, Server Bay 03',
                'availability_info': '24/7 Remote SSH and on-site terminal sessions in Turing 104',
                'usage_rules': 'No persistent long-term storage on root partition. Remove Docker containers and training checkpoints within 24 hours of job completion.',
                'eligibility': 'All verified students enrolled in AI, data science, machine learning, or robotics capstones.',
                'training_required': False,
                'training_details': None,
                'supervision_required': False,
                'supervision_details': None,
                'status': 'active',
                'owner_id': manager.id
            },
            {
                'name': 'Formlabs Form 3+ SLA Resin 3D Printer',
                'description': 'Industrial-grade stereolithography 3D printer for ultra-high resolution engineering prototypes, microfluidics, and architectural scale models. Supports Tough 2000 and Clear photopolymer resins.',
                'category': 'Workshop & Fabrication',
                'resource_type': 'equipment',
                'location': 'Engineering Innovation MakerSpace, Workbay 04',
                'availability_info': 'Mon-Fri 10:00 - 19:00',
                'usage_rules': 'Nitrile gloves and UV-filtering goggles must be worn when decanting resin. Run parts through IPA wash and Form Cure stations before handling.',
                'eligibility': 'Engineering, design, and architecture students with active MakerSpace access pass.',
                'training_required': True,
                'training_details': 'SLA Resin Handling & IPA Wash Station Chemical Safety Course.',
                'supervision_required': False,
                'supervision_details': None,
                'status': 'maintenance',  # Demonstrates maintenance state
                'owner_id': manager.id
            },
            {
                'name': 'Collaborative Innovation Seminar Suite 204',
                'description': 'Acoustically isolated group collaboration suite seating up to 12 members. Equipped with dual 75-inch 4K interactive touchscreens, writeable whiteboard walls, and high-definition video conference bar.',
                'category': 'Meeting Rooms & Collab Spaces',
                'resource_type': 'space',
                'location': 'Student Union Building, 2nd Floor, Room 204',
                'availability_info': 'Mon-Sat 08:00 - 22:00, 2-hour reservations per student team',
                'usage_rules': 'Leave dry-erase whiteboards clean. Reset furniture to original seminar configuration before exiting.',
                'eligibility': 'Open to all recognized campus student organizations, study groups, and hackathon teams.',
                'training_required': False,
                'training_details': None,
                'supervision_required': False,
                'supervision_details': None,
                'status': 'active',
                'owner_id': admin.id
            },
            {
                'name': 'Keysight 4-Channel 500MHz Mixed-Signal Oscilloscope',
                'description': 'High-precision digital storage oscilloscope with 16 integrated digital logic channels, dual-channel arbitrary function generator, and I2C/SPI serial protocol decoding.',
                'category': 'Electronics & Testing Devices',
                'resource_type': 'equipment',
                'location': 'Electrical Engineering Lab, Station 08',
                'availability_info': 'Mon-Fri 09:00 - 17:00',
                'usage_rules': 'Ensure proper probe ground connection before measuring test circuit points above 30V. Store calibrated 10:1 passive probes in protective case.',
                'eligibility': 'Electrical, computer, and biomedical engineering students.',
                'training_required': False,
                'training_details': None,
                'supervision_required': False,
                'supervision_details': None,
                'status': 'inactive',  # Demonstrates inactive state
                'owner_id': manager.id
            },
            {
                'name': 'Acoustic Recording & Podcast Studio C',
                'description': 'Professional sound-dampened audio production studio featuring 4 Shure SM7B broadcast microphones, Rodecaster Pro II audio mixer, and Sony MDR studio monitor headphones.',
                'category': 'Meeting Rooms & Collab Spaces',
                'resource_type': 'space',
                'location': 'Library Media Annex, Lower Level Studio C',
                'availability_info': 'Mon-Fri 10:00 - 20:00, Sat 12:00 - 17:00',
                'usage_rules': 'Strictly no food or unsealed liquids inside the acoustic booth. Export multitrack recordings to personal external storage.',
                'eligibility': 'All verified campus students in good standing.',
                'training_required': True,
                'training_details': 'Basic Audio Production Console Orientation (15-min walkthrough).',
                'supervision_required': False,
                'supervision_details': None,
                'status': 'active',
                'owner_id': manager.id
            }
        ]

        count = 0
        for data in demo_resources:
            existing = Resource.query.filter_by(name=data['name']).first()
            if not existing:
                res = Resource(**data)
                db.session.add(res)
                count += 1
            else:
                # Update attributes to ensure consistency
                for key, val in data.items():
                    setattr(existing, key, val)
                count += 1
        db.session.commit()
    return count


# Create standard application instance for direct running & WSGI servers
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            seed_demo_users(app)
        if Resource.query.count() == 0:
            seed_demo_resources(app)
    app.run(debug=True, port=5000)
