# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import urlparse
from datetime import datetime 
from scrapy.exceptions import DropItem

from models import Site, Webpage

class WipCrawlPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        site = Site.objects.get(pk=item['site_id'])
        path = urlparse.urlparse(item['url']).path
        if path and not path.endswith('/') and not path.count('?'):
            path += '/'
        pages = Webpage.objects.filter(site=site, path=path)
        if pages:
            page = pages[0]
        else:
            page = Webpage(site=site, path=path)
            page.path = path
        page.last_checked = datetime.now()
        page.last_checked_response_code = item['status']
        page.save()
        # raise DropItem()
        return item

        