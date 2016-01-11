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
    title = scrapy.Field()

class WipCrawlSpider(CrawlSpider):
    custom_settings = {'ITEM_PIPELINES': {'wip.pipelines.WipCrawlPipeline': 300}}

    """
    def __init__(self, *a, **kw):
        self.pipeline = WipCrawlPipeline.from_crawler(self)
        super(WipCrawlSpider, self).__init__(*a, **kw)
    """

    def parse_item(self, response):
        item = WipCrawlItem()
        item['site_id'] = self.site_id
        item['url'] = response.url
        item['status'] = response.status
        try:
            title = response.xpath('/html/head/title/text()').extract()
        except:
            title = ''
        item['title'] = title
        return item

# from http://stackoverflow.com/questions/11528739/running-scrapy-spiders-in-a-celery-task
from multiprocessing import Process
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
                'LOG_LEVEL' : 'DEBUG',
                'LOG_STDOUT' : True})
        self.crawler.start()
        # self.crawler.stop()

    def crawl(self, site_id, site_slug, site_name, allowed_domains, start_urls, deny):
        p = Process(target=self._crawl, args=[site_id, site_slug, site_name, allowed_domains, start_urls, deny])
        p.start()
        p.join()
