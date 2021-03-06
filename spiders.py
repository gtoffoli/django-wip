# -*- coding: utf-8 -*-

import scrapy
from scrapy import signals
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.utils.log import configure_logging
from scrapy.exceptions import CloseSpider

from .models import Scan, Link, WordCount, SegmentCount
from .utils import text_to_list

# from http://stackoverflow.com/questions/11528739/running-scrapy-spiders-in-a-celery-task
# from multiprocessing import Process
# see https://github.com/celery/celery/issues/1709
from billiard.process import Process
from scrapy.crawler import CrawlerProcess

class WipCrawlItem(scrapy.Item):
    # site_id = scrapy.Field()
    url = scrapy.Field()
    status = scrapy.Field()
    encoding = scrapy.Field()
    size = scrapy.Field()
    body = scrapy.Field()
    title = scrapy.Field()

    def __repr__(self):
        return repr({'url': self['url']})

class WipCrawlSpider(CrawlSpider):
    custom_settings = {'ITEM_PIPELINES': {'wip.pipelines.WipCrawlPipeline': 300}}

    # see https://github.com/scrapy/scrapy/issues/1762
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(WipCrawlSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signals.spider_closed)
        return spider

    def spider_opened(self):
        pass
        print ('--- spider_opened for scan %d, %s ---' % (self.scan_id, self.name))

    def spider_closed(self):
        print ('--- spider_closed ---')
        scan = Scan.objects.get(pk=self.scan_id)
        scan.terminated = True
        scan.page_count = Link.objects.filter(scan=scan).count()
        scan.save()

    def parse_item(self, response):
        if self.page_count >= self.max_pages:
            raise CloseSpider(reason='max page count exceeded')
        item = WipCrawlItem()
        # item['site_id'] = self.site_id
        item['url'] = response.url
        item['status'] = response.status
        try:
            item['encoding'] = response.headers['Content-Type']
        except:
            item['encoding'] = ''
        item['body'] = response.body
        item['size'] = len(response.body)
        try:
            title = response.xpath('/html/head/title/text()').extract()
            title = title[0]
        except:
            title = ''
        item['title'] = title
        return item

class WipSiteCrawlerScript():
    """  creates and wraps a Scrapy CrawlerProcess:
    the crawl method creates a billiard Process whose target is an auxiliary method that
    defines a specialization of WipCrawlSpider class, instantiates it
    and pass it to the CrawlerProcess for execution """

    def __init__(self):
        self.crawler = CrawlerProcess()

    def _crawl(self, scan_id):
        scan = Scan.objects.get(pk=scan_id)
        rules = [Rule(LinkExtractor(allow=text_to_list(scan.allow), deny=text_to_list(scan.deny)), callback='parse_item', follow=True),]
        spider_class = type(str(scan.name),
                            (WipCrawlSpider,),
                            {'scan_id': scan_id, 'name': scan.name, 'max_pages': scan.max_pages, 'page_count': 0, 'allowed_domains': text_to_list(scan.allowed_domains), 'start_urls': text_to_list(scan.start_urls), 'rules': rules,})
        spider = spider_class()
        self.crawler.crawl(spider)
        self.crawler.start()

    def crawl(self, scan_id):
        p = Process(target=self._crawl, args=[scan_id])
        p.start()
        p.join()

class WipDiscoverItem(scrapy.Item):
    url = scrapy.Field()
    status = scrapy.Field()
    encoding = scrapy.Field()
    size = scrapy.Field()
    body = scrapy.Field()
    title = scrapy.Field()

    def __repr__(self):
        return repr({'url': self['url']})

class WipDiscoverSpider(CrawlSpider):
    custom_settings = {'ITEM_PIPELINES': {'wip.pipelines.WipDiscoverPipeline': 300}}

    # see https://github.com/scrapy/scrapy/issues/1762
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(WipDiscoverSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signals.spider_closed)
        return spider

    def spider_opened(self):
        pass
        print ('--- spider_opened for scan %d, %s ---' % (self.scan_id, self.name))

    def spider_closed(self):
        print ('--- spider_closed ---')
        scan = Scan.objects.get(pk=self.scan_id)
        scan.terminated = True
        scan.page_count = Link.objects.filter(scan=scan).count()
        if scan.count_words:
            scan.word_count = WordCount.objects.filter(scan=scan).count()
        if scan.count_segments:
            scan.segment_count = SegmentCount.objects.filter(scan=scan).count()
        scan.save()

    def parse_item(self, response):
        if self.page_count >= self.max_pages:
            raise CloseSpider(reason='max page count exceeded')
        item = WipDiscoverItem()
        item['url'] = response.url
        item['status'] = response.status
        try:
            item['encoding'] = response.headers['Content-Type']
        except:
            item['encoding'] = ''
        item['body'] = response.body
        item['size'] = len(response.body)
        try:
            title = response.xpath('/html/head/title/text()').extract()
            title = title[0]
        except:
            title = ''
        item['title'] = title
        return item

class WipDiscoverScript(object):

    def __init__(self):
        self.crawler = CrawlerProcess()

    def _crawl(self, scan_id):
        scan = Scan.objects.get(pk=scan_id)
        rules = [Rule(LinkExtractor(allow=text_to_list(scan.allow), deny=text_to_list(scan.deny)), callback='parse_item', follow=True),]
        spider_class = type(str(scan.name),
                            (WipDiscoverSpider,),
                            {'name': scan.get_label(), 'scan_id': scan_id, 'max_pages': scan.max_pages, 'page_count': 0, 'allowed_domains': text_to_list(scan.allowed_domains), 'start_urls': text_to_list(scan.start_urls), 'rules': rules,})
        spider = spider_class()
        self.crawler.crawl(spider)
        self.crawler.start()
        # print ('--- end scan ---')

    def crawl(self, scan_id):
        p = Process(target=self._crawl, args=[scan_id])
        p.start()
        p.join()

class L2MemberItem(scrapy.Item):
    url = scrapy.Field()
    status = scrapy.Field()
    name = scrapy.Field()
    description = scrapy.Field()
    address = scrapy.Field()
    phone = scrapy.Field()
    email = scrapy.Field()
    web = scrapy.Field()
    facebook = scrapy.Field()
    twitter = scrapy.Field()
    youtube = scrapy.Field()
    referent = scrapy.Field()
    referent_phone = scrapy.Field()
    referent_email = scrapy.Field()

class L2MemberScraper(CrawlSpider):
    name = 'scuolemigranti_members'
    custom_settings = {'ITEM_PIPELINES': {'wip.pipelines.L2MemberPipeline': 300}}
    DOMAIN = 'www.scuolemigranti.org'
    URL = 'http://%s' % DOMAIN
    allowed_domains = (DOMAIN,)
    start_urls = ('%s/aderenti/' % URL,)
    rules = [Rule(LinkExtractor(
                    allow=('^%s/aderenti/.+/' % URL,), 
                    deny=('\.pdf', '\.doc', '\.docx', '\.xls', '\.xlsx', '\.ppt', '\.pptx', '\.ppsx', '\.rtf',)),
                    callback='parse_item',
                    follow=True),]


    def parse_item(self, response):
        # print (response.headers)
        item = L2MemberItem()
        item['url'] = response.url
        item['status'] = response.status
        name = response.xpath('//h1/text()').extract()
        item['name'] = name and name[0].strip() or ''
        description = response.xpath('//h2/text()').extract()
        item['description'] = ' '.join([s.replace(':', '.').strip() for s in description])      
        address = response.xpath('//div[@class="col-xs-12 col-sm-8 col-md-8 info-aderente"]//div[i[@class="fa fa-map-marker"]][1]/following-sibling::div[1]/a/text()').extract()
        item["address"] = address and address[0].strip() or ''
        phone = response.xpath('//div[@class="col-xs-12 col-sm-8 col-md-8 info-aderente"]//div[i[@class="fa fa-phone"]][1]/following-sibling::div[1]/a/text()').extract()
        item['phone'] = phone and phone[0].strip() or ''
        email = response.xpath('//div[@class="col-xs-12 col-sm-8 col-md-8 info-aderente"]//div[i[@class="fa fa-envelope"]][1]/following-sibling::div[1]/a/text()').extract()
        item['email'] = email and email[0].strip() or ''
        web = response.xpath('//div[@class="col-xs-12 col-sm-8 col-md-8 info-aderente"]//div[i[@class="fa fa-globe"]][1]/following-sibling::div[1]/a/text()').extract()
        item['web'] = web and web[0].strip() or ''
        referent = response.xpath('//div[@class="col-xs-12 col-sm-8 col-md-8 info-aderente"]//div[i[@class="fa fa-user"]][1]/following-sibling::div[1]/text()').extract()
        item['referent'] = referent and referent[0].strip() or ''
        referent_phone = response.xpath('//div[@class="col-xs-12 col-sm-8 col-md-8 info-aderente"]//div[i[@class="fa fa-phone"]][2]/following-sibling::div[1]/a/text()').extract()
        item['referent_phone'] = referent_phone and referent_phone[0].strip() or ''
        referent_email = response.xpath('//div[@class="col-xs-12 col-sm-8 col-md-8 info-aderente"]//div[i[@class="fa fa-envelope"]][2]/following-sibling::div[1]/a/text()').extract()
        item['referent_email'] = referent_email and referent_email[0].strip() or ''
        facebook = response.xpath('//div[@class="col-xs-12 col-sm-8 col-md-8 info-aderente"]//a[@title="Facebook Fan Page"]/@href').extract()
        item['facebook'] = facebook and facebook[0].strip() or ''
        twitter = response.xpath('//div[@class="col-xs-12 col-sm-8 col-md-8 info-aderente"]//a[@title="Twitter Fan Page"]/@href').extract()
        item['twitter'] = twitter and twitter[0].strip() or ''
        youtube = response.xpath('//div[@class="col-xs-12 col-sm-8 col-md-8 info-aderente"]//a[@title="Youtube Channel"]/@href').extract()
        item['youtube'] = youtube and youtube[0].strip() or ''
        # print (item)
        return item

class L2SchoolItem(scrapy.Item):
    url = scrapy.Field()
    status = scrapy.Field()
    name = scrapy.Field()
    address = scrapy.Field()
    referent = scrapy.Field()
    organizer = scrapy.Field()
    phone = scrapy.Field()
    email = scrapy.Field()
    web = scrapy.Field()
    description = scrapy.Field()
    text = scrapy.Field()
    
course_levels = ['Analfabeti', 'Base', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'Avanzato',]
course_levels_exclude = ['civica', 'Recupero', 'rinforzo', 'donne',]
week_days = ['LUN', 'MAR', 'MER', 'GIO', 'VEN', 'SAB', 'DOM',]
class L2SchoolScraper(CrawlSpider):
    name = 'scuolemigranti_schools'
    custom_settings = {'ITEM_PIPELINES': {'wip.pipelines.L2SchoolPipeline': 300}}
    DOMAIN = 'www.scuolemigranti.org'
    URL = 'http://%s' % DOMAIN
    allowed_domains = (DOMAIN,)
    start_urls = (
      URL,
      '%s/?s=all&comune=all-comune&municipio=all-roma&livello=Analfabeti&post_type=sedi' % URL,
      '%s/?s=all&comune=all-comune&municipio=all-roma&livello=Base&post_type=sedi' % URL,
      '%s/?s=all&comune=all-comune&municipio=all-roma&livello=A1&post_type=sedi' % URL,
      '%s/?s=all&comune=all-comune&municipio=all-roma&livello=A2&post_type=sedi' % URL,
      '%s/?s=all&comune=all-comune&municipio=all-roma&livello=B1&post_type=sedi' % URL,
      '%s/?s=all&comune=all-comune&municipio=all-roma&livello=B2&post_type=sedi' % URL,
      '%s/?s=all&comune=all-comune&municipio=all-roma&livello=C1&post_type=sedi' % URL,
      '%s/?s=all&comune=all-comune&municipio=all-roma&livello=C2&post_type=sedi' % URL,
      '%s/?s=all&comune=all-comune&municipio=all-roma&livello=Avanzato&post_type=sedi' % URL,
      )
    rules = [Rule(LinkExtractor(
                    allow=('^%s/sedi/.+/' % URL,), 
                    deny=('\.pdf', '\.doc', '\.docx', '\.xls', '\.xlsx', '\.ppt', '\.pptx', '\.ppsx', '\.rtf',)),
                    callback='parse_item',
                    follow=True),]

    def parse_item(self, response):
        # print (response.headers)
        item = L2SchoolItem()
        item['url'] = response.url
        item['status'] = response.status
        address = response.xpath('//h1/text()').extract()
        item['address'] = address and address[0].strip() or ''
        item['name'] = 'Italiano L2 a %s' % item['address']
        organizer = response.xpath('//h3/a/text()').extract()
        item['organizer'] = organizer and organizer[0].strip() or ''
        web = response.xpath('//h3/a/@href').extract()
        item['web'] = web and web[0].strip() or ''
        times = response.xpath('//div[@class="container-orari clearfix"]/descendant::*/text()').extract()
        text = ''
        for time in times: text = text+time
        levels = [level for level in course_levels if text.count(level)]
        item['description'] = levels and 'Corsi gratuiti di livello %s' % ', '.join(levels) or 'Corsi gratuiti di Italiano per stranieri'
        time_list = []
        if times:
            for time in times:
                time_words = time.split()
                if not time_words:
                    continue
                time_start = True
                for word in course_levels_exclude:
                    if word in time_words:
                        time_start = False
                        break
                if time_start:
                    time_start = False
                    for word in course_levels:
                        if word in time_words:
                            time_start = True
                            break
                if time_start:
                    if time_list:
                        time_list.append('</li>')
                    else:
                        time_list.append('<div><b>Orario dei corsi</b></div><ul>')
                    time_list.append('<li>')
                time = ' '.join(time_words)
                time = time.replace(' - ', '-'). replace(' – ', '–')
                time_list.append(time)
            if time_list:
                time_list.append('</li></ul>')
        item['text'] = time_list and ' '.join(time_list) or ''
        infos = response.xpath('//div[@class="col-md-12"]/descendant::*/text()').extract()
        words = []
        for info in infos:
            words.extend(info.strip().split())
        emails = []
        for word in words:
            if word.count('@') and word.count('.') and not word in emails:
                emails.append(word)
        while '-' in words: words.remove('-')
        while ';' in words: words.remove(';')
        item['email'] = emails and '\n'.join(emails) or ''
        phones = []
        n = len(words)
        for i in range(len(words)):
            if words[i] == 'Tel.':
                while i < (n-2):
                    prefix = words[i+1]
                    number = words[i+2]
                    if prefix.isdigit() and len(prefix)<=3 and number.isdigit() and len(number)>=5:
                        phones.append(prefix + ' ' + number)
                    i += 2                 
        item['phone'] = phones and '\n'.join(phones) or ''
        return item
