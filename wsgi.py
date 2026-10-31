"""
ResourceBridge - Production WSGI Entrypoint
===========================================
Entrypoint for WSGI application servers (Gunicorn, Waitress, uWSGI).
Loads environment variables and initializes the production Flask instance.
"""

import os
from app import create_app

# Instantiate production application
app = create_app()

if __name__ == '__main__':
    # Local direct runner fallback
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
