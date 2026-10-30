"""
seed_demo.py - Standalone Script for Demo Database Seeding
=========================================================
Run this standalone script anytime to initialize or reset the database
with preconfigured, role-based demonstration accounts and realistic
fictional campus resources for presentations and evaluation.

Usage:
    python seed_demo.py
"""

from app import app, seed_demo_users, seed_demo_resources, seed_demo_bookings
from models import User, Resource, Booking, ConditionReport, Incident, BookingAuditLog

if __name__ == '__main__':
    print("Initializing ResourceBridge database and seeding demo data...")
    with app.app_context():
        user_count = seed_demo_users(app)
        resource_count = seed_demo_resources(app)
        booking_count = seed_demo_bookings(app)
        total_users = User.query.count()
        total_resources = Resource.query.count()
        total_bookings = Booking.query.count()
        total_condition_reports = ConditionReport.query.count()
        total_incidents = Incident.query.count()
        total_audit_logs = BookingAuditLog.query.count()

        print(f"Successfully configured {user_count} demonstration accounts.")
        print(f"Total registered users in database: {total_users}")
        print(f"Successfully configured {resource_count} demonstration resources.")
        print(f"Total catalogued resources in database: {total_resources}")
        print(f"Successfully configured {booking_count} demonstration bookings.")
        print(f"Total bookings in database: {total_bookings}")
        print(f"Total condition reports in database: {total_condition_reports}")
        print(f"Total incidents in database: {total_incidents}")
        print(f"Total audit log events in database: {total_audit_logs}")

        print("\n--- Demonstration Credentials ---")
        print("1. Student Account:")
        print("   Email:    student@campus.edu")
        print("   Password: StudentPass123!")
        print("   Role:     student (Verified)")
        print("\n2. Manager Account:")
        print("   Email:    manager@campus.edu")
        print("   Password: ManagerPass123!")
        print("   Role:     manager (Verified)")
        print("\n3. Administrator Account:")
        print("   Email:    admin@campus.edu")
        print("   Password: AdminPass123!")
        print("   Role:     admin (Verified)")
        print("---------------------------------\n")
