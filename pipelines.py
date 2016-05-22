# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

"""
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
"""
import time
import urlparse
import urllib2, json
# from scrapy.exceptions import DropItem
# from scrapy.utils.misc import md5sum
from utils import string_checksum

import logging
logger = logging.getLogger('wip.views')

import django
django.setup()

from django.utils import timezone
from models import Site, Webpage, PageVersion
from settings import PAGES_EXCLUDE_BY_CONTENT

class WipCrawlPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        site = Site.objects.get(pk=item['site_id'])
        for content in PAGES_EXCLUDE_BY_CONTENT.get(site.slug, []):
            if item['body'].count(content):
                return item
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
        """
        buf = BytesIO(item['body'])
        checksum = md5sum(buf)
        """
        # checksum = string_checksum(item['body'])
        checksum = site.page_checksum(item['body'])
        fetched_pages = PageVersion.objects.filter(webpage=page).order_by('-time')
        last = fetched_pages and fetched_pages[0] or None
        # if not last:
        if not last or checksum!=last.checksum:
            body = item['encoding'].count('text/') and item['body'] or ''
            fetched = PageVersion(webpage=page, response_code=item['status'], size=item['size'], checksum=checksum, body=body)
            fetched.save()
        return item
        # raise DropItem()

class L2MemberPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        phones = []
        emails = []
        if item['phone']:
            phones.append(item['phone'])
        if item['email']:
            emails.append(item['email'])
        if item['referent']:
            if item['referent_phone']:
                phones.append('%s (%s)' % (item['referent_phone'], item['referent']))
            if item['referent_email']:
                emails.append('%s (%s)' % (item['referent_email'], item['referent']))
        webs = []
        if item['web']:
            webs.append(item['web'])
        if item['facebook']:
            webs.append('%s pagina Facebook' % item['facebook'])
        if item['twitter']:
            webs.append('%s pagina Twitter' % item['twitter'])
        if item['youtube']:
            webs.append(item['youtube'])
        poi_dict = {
          "fw_core": {
            "source": {'name': 'FairVillage crawler', 'id': time.time()},
            "category": "0635045140",
            "name": item['name'],
            "description": {"_def": "it", "it": item['description']},
          },
          "fw_contact": {
            "phone": '|'.join(phones),
            "mailto": '|'.join(emails),
            "postal": item['address'] and [item['address']] or []
          },
          "fw_fairvillage": {
           "web": '|'.join(webs),
          }
        }
        data = json.dumps(poi_dict)
        url = "http://www.romapaese.it/add_poi/"
        urllib2.urlopen(url, data) # use the optional arg data to specify the POST method 
        return item
   
class L2SchoolPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        webs = []
        if item['web']:
            webs.append("%s informazione sull'organizzazione" %item['web'])
        if item['url']:
            webs.append("%s informazione sui corsi" % item['url'])
        text = "<div>(verifica sempre l'informazione sui siti in riferimento)</div>"
        if item['organizer']:
            text += "<div>Corsi organizzati da %s</div>" % item['organizer']
        text += item['text']
        poi_dict = {
          "fw_core": {
            "source": 'FairVillage crawler',
            "category": "0532039401",
            "name": item['name'],
            "description": {"_def": "it", "it": item['description']},
          },
          "fw_contact": {
            "phone": item['phone'],
            "mailto": item['email'],
            "postal": item['address'] and [item['address']] or []
          },
          "fw_fairvillage": {
            "web": '|'.join(webs),
            "text": {"_def": "it", "it": text}
          }
        }
        data = json.dumps(poi_dict)
        url = "http://www.romapaese.it/add_poi/"
        urllib2.urlopen(url, data) # use the optional arg data to specify the POST method 
        return item
