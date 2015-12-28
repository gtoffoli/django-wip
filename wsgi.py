"""
WSGI config for wip project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os, sys

# see: http://stackoverflow.com/questions/10752031/django-1-4-with-apache-virtualhost-path-problems
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print sys.path
print path
if path not in sys.path:
    sys.path.append(path)
path = '/home/ubuntu/fv/lib/python2.7/site-packages'
if path not in sys.path:
    sys.path.append(path)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wip.settings")

application = get_wsgi_application()
