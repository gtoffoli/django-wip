'''
Created on 02/gen/2016
http://stackoverflow.com/questions/11528739/running-scrapy-spiders-in-a-celery-task
'''

from celery import task
from .celery import app as celery_app  # noqa

app@task()
def crawl_domain(domain_pk):
    pass