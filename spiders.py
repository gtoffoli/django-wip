# -*- coding: utf-8 -*-

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

class WipItem(scrapy.Item):
    url = scrapy.Field()
    status = scrapy.Field()

class WipCrawlSpider(CrawlSpider):

    def __init__(self, *a, **kw):
        cls = self.get_class()
        self.site = site = cls.site
        self.name = site.name
        self.allowed_domains = site.get_allowed_domains()
        self.start_urls = site.get_start_urls()
        self.rules = [Rule(LinkExtractor(deny=site.get_deny()))]
        super(WipCrawlSpider, self).__init__(*a, **kw)

    @classmethod
    def get_class(cls):
        return cls

    def parse_item(self, response):
        self.logger.info('Hi, this is an item page! %s', response.url)
        item = WipItem()
        item['url'] = response.url
        item['status'] = response.status
        item['title'] = response.xpath('/html/head/title/text()').extract()
        return item

