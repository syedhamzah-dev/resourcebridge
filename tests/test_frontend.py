"""
ResourceBridge - Frontend Redesign & Accessibility Integration Tests
=====================================================================
Validates that the final redesigned UI components, layout structures,
accessible attributes, and operational elements render correctly.
"""

import pytest
from app import create_app
from models import db, User, Resource, Booking
from datetime import datetime, timezone, timedelta


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


def test_redesigned_homepage_elements(client, app):
    """Verify that the redesigned landing page has professional structure and no AI tropes."""
    with app.app_context():
        # Create a sample manager and resource
        mgr = User("Dr. Elena Vance", "manager@campus.edu", "ManagerPass123!", role="manager")
        db.session.add(mgr)
        db.session.commit()
        res = Resource(
            name="Confocal Laser Scanning Microscope",
            description="High-resolution fluorescence microscopy system for cellular analysis.",
            category="Specialized Science & Optics",
            resource_type="space",
            location="BioSciences Rm 302",
            availability_info="Mon-Fri 09:00 - 17:00",
            owner_id=mgr.id,
            status="active"
        )
        db.session.add(res)
        db.session.commit()

    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    # 1. Structural titles and institutional framing
    assert "Fair, Accountable Access to University Labs &amp; Equipment" in html or "Fair, Accountable Access to University Labs & Equipment" in html
    assert "Active Campus Resources" in html
    assert "Evaluation &amp; Demo Ready" in html or "Evaluation & Demo Ready" in html

    # 2. Hero search form presence
    assert 'name="q"' in html
    assert "Search Catalogue" in html

    # 3. Verify absence of generic AI tropes
    assert "gradient-text" not in html
    assert "window-dots" not in html
    assert "dot red" not in html
    assert "Current Milestone: Stage 1" not in html


def test_redesigned_about_page_and_milestones(client, app):
    """Verify about page renders updated 8-stage architecture and technical specifications."""
    resp = client.get('/about')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    # Pillars
    assert "The Four Pillars of Trust" in html
    assert "Technical Architecture &amp; Implementation" in html or "Technical Architecture & Implementation" in html

    # Framework specs
    assert "Python 3 + Flask" in html
    assert "Flask-SQLAlchemy" in html
    assert "SQLite" in html

    # All milestones completed
    assert "Stage 1" in html
    assert "Stage 8" in html
    assert "Frontend Redesign" in html


def test_redesigned_auth_pages_and_demo_helpers(client, app):
    """Verify login and registration pages render accessible inputs and evaluation personas."""
    # Login page
    login_resp = client.get('/login')
    assert login_resp.status_code == 200
    login_html = login_resp.data.decode('utf-8')
    assert "Hackathon 1-Click Demo Profiles" in login_html
    assert 'data-role="Student"' in login_html
    assert 'data-role="Manager"' in login_html
    assert 'data-role="Admin"' in login_html
    assert "toggle-password" in login_html

    # Register page
    reg_resp = client.get('/register')
    assert reg_resp.status_code == 200
    reg_html = reg_resp.data.decode('utf-8')
    assert "Campus Role Protection" in reg_html
    assert "Student Member" in reg_html
    assert "Campus Fair-Use Code" in reg_html


def test_redesigned_catalogue_and_detail_two_column(client, app):
    """Verify resource discovery and detail view two-column layout."""
    with app.app_context():
        mgr = User("Lead Technician", "tech@campus.edu", "TechPass123!", role="manager")
        db.session.add(mgr)
        db.session.commit()
        r = Resource(
            name="Sony FX3 Cinema Package",
            description="Full-frame cinema camera with 24-70mm f/2.8 GM lens and audio handle.",
            category="Cameras & AV Equipment",
            resource_type="equipment",
            location="Media Center Cage B",
            availability_info="Daily 09:00 - 18:00",
            owner_id=mgr.id,
            training_required=True,
            training_details="Cinema Camera Handling Safety",
            supervision_required=False,
            status="active"
        )
        db.session.add(r)
        db.session.commit()
        r_id = r.id

    # Catalogue check
    cat_resp = client.get('/resources')
    assert cat_resp.status_code == 200
    cat_html = cat_resp.data.decode('utf-8')
    assert "Campus Resource Discovery" in cat_html
    assert "Sony FX3 Cinema Package" in cat_html
    assert "filter-safety-pills" in cat_html

    # Detail check
    det_resp = client.get(f'/resources/{r_id}')
    assert det_resp.status_code == 200
    det_html = det_resp.data.decode('utf-8')
    assert "detail-layout-grid" in det_html
    assert "Mandatory Training Prerequisite" in det_html
    assert "Cinema Camera Handling Safety" in det_html
    assert "Registry Provenance" in det_html
    assert "sticky-panel" in det_html
