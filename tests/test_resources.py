"""
tests/test_resources.py - Resource Inventory & Discovery Tests
==============================================================
Validates resource creation, persistence, owner authorization,
student discovery, keyword search, multi-faceted filtering,
safety/training prerequisites, and safe error handling.
"""

import pytest
from app import create_app, seed_demo_users, seed_demo_resources
from models import db, User, Resource


@pytest.fixture
def app():
    """Create and configure a clean application instance with an in-memory SQLite database."""
    test_app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-stage2',
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
    """Helper to log in a test user via POST /login."""
    return client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)


# ------------------------------------------------------------------------------
# Test 1 & 2: Application Startup & Catalog Accessibility
# ------------------------------------------------------------------------------

def test_application_startup_and_catalog(client, app):
    """1. The application starts successfully and the resource catalog is accessible."""
    with app.app_context():
        seed_demo_users(app)
        seed_demo_resources(app)

    # Home page
    res_home = client.get('/')
    assert res_home.status_code == 200
    assert b"ResourceBridge" in res_home.data

    # Catalog page
    res_catalog = client.get('/resources')
    assert res_catalog.status_code == 200
    assert b"Campus Resource Discovery" in res_catalog.data
    assert b"Optical Microscopy Suite" in res_catalog.data


# ------------------------------------------------------------------------------
# Test 3 & 4: Resource Creation & Persistence
# ------------------------------------------------------------------------------

def test_authorized_owner_can_create_resource_and_persists(client, app):
    """3 & 4. An authorised owner can create a resource and it persists in the database."""
    with app.app_context():
        manager = User("Lab Manager", "manager@campus.edu", "ManagerPass123!", role="manager")
        db.session.add(manager)
        db.session.commit()
        manager_id = manager.id

    login_user_helper(client, "manager@campus.edu", "ManagerPass123!")

    # Submit resource creation form
    post_res = client.post('/resources/new', data={
        'name': 'High-Speed Wind Tunnel Test Cell',
        'description': 'Subsonic wind tunnel test chamber for aerospace and fluid mechanics testing with digital manometer array.',
        'category': 'Specialized Science & Optics',
        'resource_type': 'space',
        'location': 'Aerospace Hall, Bay 01',
        'availability_info': 'Mon-Fri 08:00 - 16:00',
        'usage_rules': 'Ear protection required. Do not exceed fan velocity rating 5.',
        'eligibility': 'Aero engineering capstone students',
        'training_required': '1',
        'training_details': 'Wind Tunnel Operator Level 1',
        'supervision_required': '1',
        'supervision_details': 'Faculty tech must be present',
        'status': 'active'
    }, follow_redirects=True)

    assert post_res.status_code == 200
    assert b"High-Speed Wind Tunnel Test Cell" in post_res.data

    # Verify persistence in database
    with app.app_context():
        res = Resource.query.filter_by(name='High-Speed Wind Tunnel Test Cell').first()
        assert res is not None
        assert res.owner_id == manager_id
        assert res.category == 'Specialized Science & Optics'
        assert res.resource_type == 'space'
        assert res.location == 'Aerospace Hall, Bay 01'
        assert res.training_required is True
        assert res.training_details == 'Wind Tunnel Operator Level 1'
        assert res.supervision_required is True
        assert res.status == 'active'


# ------------------------------------------------------------------------------
# Test 5: Authorized Owner Can View and Edit Their Own Resource
# ------------------------------------------------------------------------------

def test_authorized_owner_can_view_and_edit_resource(client, app):
    """5. An authorised owner can view and edit their own resource."""
    with app.app_context():
        manager = User("Manager One", "m1@campus.edu", "Pass123!", role="manager")
        db.session.add(manager)
        db.session.commit()

        resource = Resource(
            name="Original Camera Kit",
            description="Original description",
            category="Cameras & AV Equipment",
            resource_type="equipment",
            location="Cage Locker 01",
            availability_info="Daily 9-5",
            owner_id=manager.id,
            status="active"
        )
        db.session.add(resource)
        db.session.commit()
        res_id = resource.id

    login_user_helper(client, "m1@campus.edu", "Pass123!")

    # View edit form
    edit_get = client.get(f'/resources/{res_id}/edit')
    assert edit_get.status_code == 200
    assert b"Original Camera Kit" in edit_get.data

    # Post updates
    edit_post = client.post(f'/resources/{res_id}/edit', data={
        'name': 'Updated Cinema Camera Rig',
        'description': 'Updated lens and cage description',
        'category': 'Cameras & AV Equipment',
        'resource_type': 'equipment',
        'location': 'Cage Locker 05',
        'availability_info': 'Daily 10-6',
        'status': 'maintenance',
        'training_required': '0',
        'supervision_required': '0'
    }, follow_redirects=True)

    assert edit_post.status_code == 200
    assert b"Updated Cinema Camera Rig" in edit_post.data

    # Verify changes in DB
    with app.app_context():
        updated = db.session.get(Resource, res_id)
        assert updated.name == 'Updated Cinema Camera Rig'
        assert updated.location == 'Cage Locker 05'
        assert updated.status == 'maintenance'


# ------------------------------------------------------------------------------
# Test 6: Unauthorized Student Cannot Create a Resource
# ------------------------------------------------------------------------------

def test_unauthorized_student_cannot_create_resource(client, app):
    """6. An unauthorised student cannot create a resource."""
    with app.app_context():
        student = User("Student Jordan", "jordan@campus.edu", "Pass123!", role="student")
        db.session.add(student)
        db.session.commit()

    login_user_helper(client, "jordan@campus.edu", "Pass123!")

    # Attempt to open creation form
    get_res = client.get('/resources/new')
    assert get_res.status_code in (403, 302)

    # Attempt to POST creation form
    post_res = client.post('/resources/new', data={
        'name': 'Illegal Student Resource',
        'description': 'This should be blocked',
        'category': 'Computer Labs & Workstations',
        'location': 'Dorm Room 101',
        'availability_info': 'All day'
    })
    assert post_res.status_code in (403, 302)

    with app.app_context():
        assert Resource.query.filter_by(name='Illegal Student Resource').first() is None


# ------------------------------------------------------------------------------
# Test 7: A User Cannot Edit Another Owner's Resource
# ------------------------------------------------------------------------------

def test_user_cannot_edit_another_owners_resource(client, app):
    """7. A manager cannot edit another owner's resource unless authorized."""
    with app.app_context():
        m1 = User("Manager Alpha", "alpha@campus.edu", "Pass123!", role="manager")
        m2 = User("Manager Beta", "beta@campus.edu", "Pass123!", role="manager")
        db.session.add_all([m1, m2])
        db.session.commit()

        # Resource owned by Manager Alpha
        res = Resource(
            name="Alpha's Spec Lab",
            description="Alpha private lab",
            category="Specialized Science & Optics",
            location="Alpha Hall 101",
            availability_info="Mon-Fri",
            owner_id=m1.id
        )
        db.session.add(res)
        db.session.commit()
        res_id = res.id

    # Log in as Manager Beta
    login_user_helper(client, "beta@campus.edu", "Pass123!")

    # Attempt to access edit page for Alpha's resource
    get_res = client.get(f'/resources/{res_id}/edit')
    assert get_res.status_code in (403, 302)

    # Attempt to post modifications to Alpha's resource
    post_res = client.post(f'/resources/{res_id}/edit', data={
        'name': 'Hacked by Beta',
        'description': 'Unauthorized modification',
        'category': 'Specialized Science & Optics',
        'location': 'Beta Hall',
        'availability_info': 'Never'
    })
    assert post_res.status_code in (403, 302)

    # Ensure DB record remains untouched
    with app.app_context():
        current = db.session.get(Resource, res_id)
        assert current.name == "Alpha's Spec Lab"
        assert current.location == "Alpha Hall 101"


# ------------------------------------------------------------------------------
# Test 8: Invalid Resource Data is Rejected
# ------------------------------------------------------------------------------

def test_invalid_resource_data_rejected(client, app):
    """8. Invalid resource data is rejected with proper validation errors."""
    with app.app_context():
        manager = User("Manager Val", "val@campus.edu", "Pass123!", role="manager")
        db.session.add(manager)
        db.session.commit()

    login_user_helper(client, "val@campus.edu", "Pass123!")

    # 1. Missing name
    res1 = client.post('/resources/new', data={
        'name': '',
        'description': 'Valid desc',
        'category': 'Computer Labs & Workstations',
        'location': 'Rm 101',
        'availability_info': '9-5'
    })
    assert res1.status_code == 400
    assert b"Resource name is required" in res1.data

    # 2. Invalid category
    res2 = client.post('/resources/new', data={
        'name': 'Valid Name',
        'description': 'Valid desc',
        'category': 'Fictional Fake Category',
        'location': 'Rm 101',
        'availability_info': '9-5'
    })
    assert res2.status_code == 400
    assert b"valid resource category" in res2.data

    # 3. Invalid status
    res3 = client.post('/resources/new', data={
        'name': 'Valid Name',
        'description': 'Valid desc',
        'category': 'Computer Labs & Workstations',
        'location': 'Rm 101',
        'availability_info': '9-5',
        'status': 'super_broken_status'
    })
    assert res3.status_code == 400
    assert b"Status must be" in res3.data


# ------------------------------------------------------------------------------
# Test 9: Keyword Search
# ------------------------------------------------------------------------------

def test_search_returns_matching_database_records(client, app):
    """9. Search returns matching database records."""
    with app.app_context():
        manager = User("Manager Search", "m_search@campus.edu", "Pass123!", role="manager")
        db.session.add(manager)
        db.session.commit()

        r1 = Resource("Fluorescence Microscope", "Optical bio imaging", "Specialized Science & Optics", "Bio Hall 1", "9-5", manager.id)
        r2 = Resource("4K Cinema Prime Rig", "Cinema production gear", "Cameras & AV Equipment", "Media 10", "9-5", manager.id)
        r3 = Resource("Raspberry Pi Sensor Cluster", "IoT prototyping kit", "Electronics & Testing Devices", "CS 20", "9-5", manager.id)
        db.session.add_all([r1, r2, r3])
        db.session.commit()

    # Search for "Microscope"
    res1 = client.get('/resources?q=Microscope')
    assert b"Fluorescence Microscope" in res1.data
    assert b"Cinema Prime Rig" not in res1.data

    # Search for "Cinema"
    res2 = client.get('/resources?q=Cinema')
    assert b"4K Cinema Prime Rig" in res2.data
    assert b"Fluorescence Microscope" not in res2.data


# ------------------------------------------------------------------------------
# Test 10: Category Filtering
# ------------------------------------------------------------------------------

def test_category_filtering(client, app):
    """10. Category filtering works correctly against database records."""
    with app.app_context():
        manager = User("Manager Cat", "m_cat@campus.edu", "Pass123!", role="manager")
        db.session.add(manager)
        db.session.commit()

        r1 = Resource("Laser Cutter Pro", "CO2 Laser", "Workshop & Fabrication", "Bay 1", "9-5", manager.id)
        r2 = Resource("VR Testing Suite", "Oculus Headset", "Computer Labs & Workstations", "VR 2", "9-5", manager.id)
        db.session.add_all([r1, r2])
        db.session.commit()

    res = client.get('/resources', query_string={'category': 'Workshop & Fabrication'})
    assert b"Laser Cutter Pro" in res.data
    assert b"VR Testing Suite" not in res.data


# ------------------------------------------------------------------------------
# Test 11: Location Filtering
# ------------------------------------------------------------------------------

def test_location_filtering(client, app):
    """11. Location filtering works correctly against database records."""
    with app.app_context():
        manager = User("Manager Loc", "m_loc@campus.edu", "Pass123!", role="manager")
        db.session.add(manager)
        db.session.commit()

        r1 = Resource("Sound Booth A", "Quiet room", "Meeting Rooms & Collab Spaces", "Library Media Annex", "9-5", manager.id)
        r2 = Resource("PCB Milling Machine", "Circuit fab", "Electronics & Testing Devices", "Engineering Block D", "9-5", manager.id)
        db.session.add_all([r1, r2])
        db.session.commit()

    res = client.get('/resources?location=Library')
    assert b"Sound Booth A" in res.data
    assert b"PCB Milling Machine" not in res.data


# ------------------------------------------------------------------------------
# Test 12: Equipment vs Space Filtering
# ------------------------------------------------------------------------------

def test_equipment_space_filtering(client, app):
    """12. Equipment vs space filtering works."""
    with app.app_context():
        manager = User("Manager Type", "m_type@campus.edu", "Pass123!", role="manager")
        db.session.add(manager)
        db.session.commit()

        r1 = Resource("Cleanroom Room 101", "Lab facility", "Specialized Science & Optics", "Rm 101", "9-5", manager.id, resource_type='space')
        r2 = Resource("Digital Multimeter", "Handheld meter", "Electronics & Testing Devices", "Shelf B", "9-5", manager.id, resource_type='equipment')
        db.session.add_all([r1, r2])
        db.session.commit()

    # Filter spaces only
    res_space = client.get('/resources?type=space')
    assert b"Cleanroom Room 101" in res_space.data
    assert b"Digital Multimeter" not in res_space.data

    # Filter equipment only
    res_equip = client.get('/resources?type=equipment')
    assert b"Digital Multimeter" in res_equip.data
    assert b"Cleanroom Room 101" not in res_equip.data


# ------------------------------------------------------------------------------
# Test 13: Empty Results Render Correctly
# ------------------------------------------------------------------------------

def test_empty_results_render_correctly(client, app):
    """13. Empty results render correctly with helpful user feedback."""
    res = client.get('/resources?q=NonExistentSuperWidget999')
    assert res.status_code == 200
    assert b"No Campus Resources Found" in res.data
    assert b"Try clearing your filters" in res.data


# ------------------------------------------------------------------------------
# Test 14: Inactive and Maintenance Statuses Represented
# ------------------------------------------------------------------------------

def test_inactive_and_maintenance_statuses_represented(client, app):
    """14. Inactive and maintenance statuses are represented correctly with clear badges."""
    with app.app_context():
        manager = User("Manager Stat", "m_stat@campus.edu", "Pass123!", role="manager")
        db.session.add(manager)
        db.session.commit()

        r_maint = Resource("Broken 3D Printer", "Needs belt replace", "Workshop & Fabrication", "Bay 3", "9-5", manager.id, status='maintenance')
        r_inact = Resource("Archived Oscilloscope", "End of term hold", "Electronics & Testing Devices", "EE 10", "9-5", manager.id, status='inactive')
        r_act = Resource("Active Soldering Station", "Ready for use", "Electronics & Testing Devices", "EE 12", "9-5", manager.id, status='active')
        db.session.add_all([r_maint, r_inact, r_act])
        db.session.commit()

    # Test maintenance filter
    res_maint = client.get('/resources?status=maintenance')
    assert b"Broken 3D Printer" in res_maint.data
    assert b"Under Maintenance" in res_maint.data
    assert b"Active Soldering Station" not in res_maint.data

    # Test inactive filter
    res_inact = client.get('/resources?status=inactive')
    assert b"Archived Oscilloscope" in res_inact.data
    assert b"Inactive" in res_inact.data
    assert b"Active Soldering Station" not in res_inact.data


# ------------------------------------------------------------------------------
# Test 15: Invalid Resource IDs Handled Safely
# ------------------------------------------------------------------------------

def test_invalid_resource_ids_handled_safely(client, app):
    """15. Invalid resource IDs are handled safely (404 Not Found without crashing)."""
    response = client.get('/resources/99999999')
    assert response.status_code == 404
    assert b"Resource Not Found" in response.data


# ------------------------------------------------------------------------------
# Test 16: Admin Can Manage Resources Across All Departments
# ------------------------------------------------------------------------------

def test_admin_can_manage_all_resources(client, app):
    """16. System Administrators have global oversight and can edit any resource."""
    with app.app_context():
        manager = User("Dept Manager", "dept_mgr@campus.edu", "Pass123!", role="manager")
        admin = User("Global Admin", "global_admin@campus.edu", "Pass123!", role="admin")
        db.session.add_all([manager, admin])
        db.session.commit()

        res = Resource("Dept Asset", "Managed by dept", "Cameras & AV Equipment", "Locker 1", "9-5", manager.id)
        db.session.add(res)
        db.session.commit()
        res_id = res.id

    login_user_helper(client, "global_admin@campus.edu", "Pass123!")

    # Admin GETs edit form
    edit_get = client.get(f'/resources/{res_id}/edit')
    assert edit_get.status_code == 200

    # Admin POSTs updates
    edit_post = client.post(f'/resources/{res_id}/edit', data={
        'name': 'Admin Approved Asset',
        'description': 'Updated by institution administrator',
        'category': 'Cameras & AV Equipment',
        'location': 'Central Warehouse',
        'availability_info': 'By appointment',
        'status': 'active'
    }, follow_redirects=True)

    assert edit_post.status_code == 200
    assert b"Admin Approved Asset" in edit_post.data


# ------------------------------------------------------------------------------
# Test 17: Dashboard Queries Live Database Counts
# ------------------------------------------------------------------------------

def test_dashboard_queries_live_database_counts(client, app):
    """17. Dashboards dynamically query real database counts rather than static values."""
    with app.app_context():
        manager = User("Live Mgr", "live_mgr@campus.edu", "Pass123!", role="manager")
        student = User("Live Student", "live_std@campus.edu", "Pass123!", role="student")
        db.session.add_all([manager, student])
        db.session.commit()

        # Add 3 active resources and 1 maintenance resource owned by manager
        for i in range(3):
            db.session.add(Resource(f"Active Resource {i}", "Desc", "Workshop & Fabrication", "Bay 1", "9-5", manager.id, status='active'))
        db.session.add(Resource("Maintenance Resource 1", "Desc", "Workshop & Fabrication", "Bay 2", "9-5", manager.id, status='maintenance'))
        db.session.commit()

    # Log in as manager and check live counts
    login_user_helper(client, "live_mgr@campus.edu", "Pass123!")
    mgr_dash = client.get('/dashboard')
    assert b"4" in mgr_dash.data  # my_total_resources
    assert b"3" in mgr_dash.data  # my_active_resources
    assert b"1" in mgr_dash.data  # my_maintenance_resources
    client.get('/logout')

    # Log in as student and check active catalog count
    login_user_helper(client, "live_std@campus.edu", "Pass123!")
    std_dash = client.get('/dashboard')
    assert b"3" in std_dash.data  # total_active_resources
