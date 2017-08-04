# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import sys
if (sys.version_info > (3, 0)):
    from urllib import parse as urlparse
else:
    import urlparse

import time
import urllib2, json
import re
from collections import defaultdict

# from scrapy.xlib.pydispatch import dispatcher
# from scrapy import signals
# from scrapy.exporters import JsonLinesItemExporter

import django
django.setup()

from django.utils import timezone
from django.conf import settings
# from settings import PAGES_EXCLUDE_BY_CONTENT
from .models import Site, Webpage, PageVersion
from .models import Scan, Link, WordCount, SegmentCount
from .utils import is_invariant_word, strings_from_html, normalize_string, make_segmenter, segments_from_string

from wip.wip_nltk.tokenizers import NltkTokenizer
tokenizer = NltkTokenizer()
segmenter = make_segmenter('it')

class WipDiscoverPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    """
    def __init__(self):
        dispatcher.connect(self.spider_opened, signals.spider_opened)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
    """

    def spider_opened(self, spider):
        # self.exporter = JsonLinesItemExporter(sys.stdout)
        """
        self.output_file = open(spider.file_path, "w", 0)
        self.exporter = JsonLinesItemExporter(self.output_file)
        self.exporter.start_exporting()
        """
        print '--- spider_opened for scan %d, %s ---' % (spider.scan_id, spider.name)

    def spider_closed(self, spider):
        """
        self.exporter.finish_exporting()
        self.output_file.close()
        """
        print '--- spider_closed ---'
        scan = Scan.objects.get(pk=spider.scan_id)
        scan.terminated = True
        scan.save()

    def process_item(self, item, spider):
        """
        self.exporter.export_item(item)
        """
        scan_id = spider.scan_id
        scan = Scan.objects.get(pk=scan_id)
        link = Link(scan=scan, url=item['url'], status=item['status'], encoding=item['encoding'], size=item['size'], title=item['title'])
        link.save()
        spider.page_count += 1
        if not (scan.count_words or scan.count_segments):
            return item
        body = item['body']
        html_string = re.sub("(<!--(.*?)-->)", "", body, flags=re.MULTILINE)
        html_string = normalize_string(html_string)
        if not html_string:
            return item
        tokens_dict = defaultdict(int)
        segments_dict = defaultdict(int)
        for s in strings_from_html(html_string):
            if scan.count_words:
                tokens = tokenizer.tokenize(s)
                for token in tokens:
                    if not is_invariant_word(token):
                        tokens_dict[token] += 1
            if scan.count_segments:
                segments = segments_from_string(s, segmenter)
                for segment in segments:
                    segments_dict[segment] += 1
        if scan.count_words:
            for word, count in tokens_dict.items():
                try:
                    word_count = WordCount.objects.get(scan=scan, word=word)
                    word_count.count += count
                except:
                    word_count = WordCount(scan=scan, word=word, count=count)
                word_count.save()
        if scan.count_segments:
            for segment, count in segments_dict.items():
                try:
                    segment_count = SegmentCount.objects.get(scan=scan, segment=segment)
                    segment_count.count += count
                except:
                    segment_count = SegmentCount(scan=scan, segment=segment, count=count)
                segment_count.save()
        return item

class WipCrawlPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        site = Site.objects.get(pk=item['site_id'])
        for content in settings.PAGES_EXCLUDE_BY_CONTENT.get(site.slug, []):
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
