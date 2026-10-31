"""
ResourceBridge - Production WSGI Entrypoint
===========================================
Entrypoint for WSGI application servers (Gunicorn, Waitress, uWSGI).
Loads environment variables and initializes the production Flask instance.
Ensures database tables and demo accounts exist on worker startup.
"""

import os
from app import (
    create_app,
    db,
    User,
    Resource,
    Booking,
    seed_demo_users,
    seed_demo_resources,
    seed_demo_bookings
)

# Instantiate production application
app = create_app()

# Auto-initialize database tables and seed baseline demo records if empty
with app.app_context():
    try:
        db.create_all()
        if User.query.count() == 0:
            seed_demo_users(app)
        if Resource.query.count() == 0:
            seed_demo_resources(app)
        if Booking.query.count() == 0:
            seed_demo_bookings(app)
    except Exception as e:
        app.logger.warning(f"WSGI startup database verification warning: {e}")

if __name__ == '__main__':
    # Local direct runner fallback
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
