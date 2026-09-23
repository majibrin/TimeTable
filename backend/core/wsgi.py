"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()

# --- ADDED CODE TO AUTOMATICALLY CREATE THE SUPERUSER ---
try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(username='superadmin').exists():
        User.objects.create_superuser('superadmin', 'admin@example.com', 'super1234')
except Exception as e:
    print(f"Superuser creation error: {e}")
