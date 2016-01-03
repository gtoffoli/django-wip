# -*- coding: utf-8 -*-

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.utils.project import get_project_settings

class WipItem(scrapy.Item):
    url = scrapy.Field()
    status = scrapy.Field()

class WipCrawlSpider(CrawlSpider):
    rules = [Rule(LinkExtractor(deny=['\.pdf', '\.doc', '\.xls',])),]

    def __init__(self, *a, **kw):
        cls = self.get_class()
        name = cls.name
        allowed_domains = cls.allowed_domains
        start_urls = cls.start_urls
        # rules = [Rule(LinkExtractor(deny=cls.deny))]
        super(WipCrawlSpider, self).__init__(*a, **kw)

    @classmethod
    def get_class(cls):
        return cls

    """
    def parse_item(self, response):
        self.logger.info('Hi, this is an item page! %s', response.url)
        item = WipItem()
        item['url'] = response.url
        item['status'] = response.status
        item['title'] = response.xpath('/html/head/title/text()').extract()
        return item
    """

# from http://stackoverflow.com/questions/11528739/running-scrapy-spiders-in-a-celery-task
from multiprocessing import Process
from scrapy.crawler import CrawlerProcess

class WipSiteCrawlerScript():

    def __init__(self):
        settings = get_project_settings()
        print 'settings: ', settings
        self.crawler = CrawlerProcess()
        # self.crawler.install()
        # self.crawler.configure()

    def _crawl(self, site_slug, site_name, allowed_domains, start_urls, deny):
        spider_class = type(str(site_slug),
                            (WipCrawlSpider,),
                            {'name':site_name, 'allowed_domains':allowed_domains, 'start_urls':start_urls, 'deny': deny})
        spider = spider_class()
        self.crawler.crawl(spider)
        self.crawler.start()
        self.crawler.stop()

    def crawl(self, site_slug, site_name, allowed_domains, start_urls, deny):
        p = Process(target=self._crawl, args=[site_slug, site_name, allowed_domains, start_urls, deny])
        p.start()
        p.join()
