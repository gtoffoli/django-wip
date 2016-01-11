'''
Created on 02/gen/2016
from: http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
http://stackoverflow.com/questions/11528739/running-scrapy-spiders-in-a-celery-task
'''

from __future__ import absolute_import

from celery import Celery
# from celery import task

"""
# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wip.settings')
"""

from django.conf import settings  # noqa

app = Celery('wip')
# app = Celery()

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
# app.conf.update(CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend',)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

import sys
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

@app.task(bind=True)
def dump_context(self):
    print('Executing task id {0.id}, logfile: {0.logfile} args: {0.args!r} kwargs: {0.kwargs!r}'.format(self.request))
    logger.info('Executing task id {0.id}, logfile: {0.logfile} args: {0.args!r} kwargs: {0.kwargs!r}'.format(self.request))
    old_outs = sys.stdout, sys.stderr
    rlevel = self.app.conf.CELERY_REDIRECT_STDOUTS_LEVEL
    try:
        self.app.log.redirect_stdouts_to_logger(logger, rlevel)
        print('Executing task id {0.id}, logfile: {0.logfile} args: {0.args!r} kwargs: {0.kwargs!r}'.format(self.request))
    finally:
        sys.stdout, sys.stderr = old_outs
