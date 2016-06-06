"""
WSGI config for wip project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os, sys

# see: http://stackoverflow.com/questions/10752031/django-1-4-with-apache-virtualhost-path-problems
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.append(path)
path = '/home/ubuntu/fv/lib/python2.7/site-packages'
if path not in sys.path:
    sys.path.append(path)

from django.core.wsgi import get_wsgi_application

"""
# see: http://stackoverflow.com/questions/11383176/problems-hosting-multiple-django-sites-settings-cross-over
# change the env variable where django looks for the settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wip.settings")
"""
"""
import django.conf
django.conf.ENVIRONMENT_VARIABLE = "DJANGO_WIP_SETTINGS_MODULE"
os.environ.setdefault("DJANGO_WIP_SETTINGS_MODULE", "wip.settings")
"""
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wip.settings")

application = get_wsgi_application()
