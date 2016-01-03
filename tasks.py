'''
Created on 02/gen/2016
from: http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
http://stackoverflow.com/questions/11528739/running-scrapy-spiders-in-a-celery-task
'''

from __future__ import absolute_import

import os

from celery import Celery
from celery import task

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wip.settings')

from django.conf import settings  # noqa

app = Celery('wip')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

"""
@task()
def crawl_site(site_pk):
    return site_crawl(site_pk)
"""
