# -*- coding: utf-8 -*-

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
# from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging

# from pipelines import WipCrawlPipeline

class WipCrawlItem(scrapy.Item):
    site_id = scrapy.Field()
    url = scrapy.Field()
    status = scrapy.Field()
    encoding = scrapy.Field()
    size = scrapy.Field()
    body = scrapy.Field()
    title = scrapy.Field()

class WipCrawlSpider(CrawlSpider):
    custom_settings = {'ITEM_PIPELINES': {'wip.pipelines.WipCrawlPipeline': 300}}

    def parse_item(self, response):
        print response.headers
        item = WipCrawlItem()
        item['site_id'] = self.site_id
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
        except:
            title = ''
        item['title'] = title
        return item

# from http://stackoverflow.com/questions/11528739/running-scrapy-spiders-in-a-celery-task
# from multiprocessing import Process
# see https://github.com/celery/celery/issues/1709
from billiard.process import Process
from scrapy.crawler import CrawlerProcess

class WipSiteCrawlerScript():

    def __init__(self):
        # settings = get_project_settings()
        self.crawler = CrawlerProcess()

    def _crawl(self, site_id, site_slug, site_name, allowed_domains, start_urls, deny):
        rules = [Rule(LinkExtractor(deny=deny), callback='parse_item', follow=True),]
        spider_class = type(str(site_slug),
                            (WipCrawlSpider,),
                            {'site_id': site_id, 'name':site_name, 'allowed_domains':allowed_domains, 'start_urls':start_urls, 'rules': rules,})
        spider = spider_class()
        self.crawler.crawl(spider)
        # scrapy.log.start()
        configure_logging({
                'LOG_ENABLEED' : True,
                'LOG_LEVEL' : 'ERROR',
                'LOG_STDOUT' : True})
        self.crawler.start()
        # self.crawler.stop()

    def crawl(self, site_id, site_slug, site_name, allowed_domains, start_urls, deny):
        p = Process(target=self._crawl, args=[site_id, site_slug, site_name, allowed_domains, start_urls, deny])
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
        print response.headers
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
        print item
        return item

class L2SchoolItem(scrapy.Item):
    url = scrapy.Field()
    status = scrapy.Field()
    title = scrapy.Field()
    address = scrapy.Field()
    phone = scrapy.Field()
    email = scrapy.Field()
    site = scrapy.Field()
    referent = scrapy.Field()
    phone_referent = scrapy.Field()
    email_referent = scrapy.Field()

class L2SchoolScraper(CrawlSpider):
    name = 'scuolemigranti_schools'
    custom_settings = {'ITEM_PIPELINES': {'wip.pipelines.L2SchoolPipeline': 300}}
    DOMAIN = 'www.scuolemigranti.org'
    URL = 'http://%s' % DOMAIN
    allowed_domains = (DOMAIN,)
    start_urls = (URL,)
    rules = [Rule(LinkExtractor(
                    allow=('^%s/sedi/.+/' % URL,), 
                    deny=('\.pdf', '\.doc', '\.docx', '\.xls', '\.xlsx', '\.ppt', '\.pptx', '\.ppsx', '\.rtf',)),
                    callback='parse_item',
                    follow=True),]

    def parse_item(self, response):
        print response.headers
        item = L2SchoolItem()
        item['url'] = response.url
        item['status'] = response.status
        item['title'] = response.xpath('/html/head/title/text()/text()').extract()
        return item
