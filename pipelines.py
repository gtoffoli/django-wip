# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
import urlparse
from datetime import datetime 
from scrapy.exceptions import DropItem
from scrapy.utils.misc import md5sum

import logging
logger = logging.getLogger('wip.views')

import django
django.setup()

from django.utils import timezone
from models import Site, Webpage, Fetched

class WipCrawlPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        site = Site.objects.get(pk=item['site_id'])
        path = urlparse.urlparse(item['url']).path
        pages = Webpage.objects.filter(site=site, path=path)
        if pages:
            page = pages[0]
        else:
            page = Webpage(site=site, path=path)
            page.path = path
            page.encoding = item['encoding']
        page.last_checked = timezone.now()
        page.last_checked_response_code = item['status']
        page.save()
        buf = BytesIO(item['body'])
        checksum = md5sum(buf)
        fetched_pages = Fetched.objects.filter(webpage=page).order_by('-time')
        last = fetched_pages and fetched_pages[0] or None
        # if not last or checksum!=last.checksum:
        if not last:
            body = item['encoding'].count('text/') and item['body'] or ''
            fetched = Fetched(webpage=page, response_code=item['status'], size=item['size'], checksum=checksum, body=body)
            fetched.save()
        return item
        # raise DropItem()

        