from __future__ import absolute_import

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
# from .celery import app as celery_app  # noqa

from .settings import USE_SCRAPY

if USE_SCRAPY:
    from .celery_apps import app as celery_app  # noqa
