# -*- coding: utf-8 -*-
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

class Spider_LinkExtractor(CrawlSpider):
    """
    def __init__(self, *args, **kwargs):
        # print kwargs
        allowed_domains = kwargs['allowed_domains']
        start_urls = kwargs['start_urls']
        rules = [Rule(LinkExtractor(deny=kwargs['deny']))]
        setattr(Spider_LinkExtractor, 'allowed_domains', allowed_domains)
        setattr(Spider_LinkExtractor, 'start_urls', start_urls)
        setattr(Spider_LinkExtractor, 'rules', rules)
    """
    pass

