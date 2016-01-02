"""
Django views for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

from django.template import RequestContext
from django.http import HttpResponse #, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404

from models import Site, Proxy, Webpage # , Fetched, Translated
# import scrapy
# from scrapy.spiders import CrawlSpider, Rule
# from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerProcess
from spiders import WipCrawlSpider
 
def home(request):
    var_dict = {}
    return render_to_response('homepage.html', var_dict, context_instance=RequestContext(request))

def sites(request):
    var_dict = {}
    sites = Site.objects.all()
    var_dict['sites'] = sites
    return render_to_response('sites.html', var_dict, context_instance=RequestContext(request))

def proxies(request):
    var_dict = {}
    proxies = Proxy.objects.all()
    var_dict['proxies'] = proxies
    return render_to_response('proxies.html', var_dict, context_instance=RequestContext(request))

def site(request, site_slug):
    site = get_object_or_404(Site, slug=site_slug)
    var_dict = {}
    var_dict['site'] = site
    proxies = Proxy.objects.filter(site=site)
    var_dict['proxies'] = proxies
    return render_to_response('site.html', var_dict, context_instance=RequestContext(request))

def site_crawl(request, site_slug):
    site = get_object_or_404(Site, slug=site_slug)
    spider_class = type(str(site_slug), (WipCrawlSpider,), {'site':site})
    spider = spider_class()
    process = CrawlerProcess({
      'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })
    process.crawl(spider)
    process.start() # the script will block here until the crawling is finished
    content = str(spider)
    response = HttpResponse(content)
    response['Content-Type'] = 'text/plain; charset=utf-8'
    return response

def site_pages(request, site_slug):
    var_dict = {}
    site = get_object_or_404(Site, slug=site_slug)
    var_dict['site'] = site
    pages = Webpage.filter(site=site)
    var_dict['pages'] = pages
    var_dict['page_count'] = pages.count()
    return render_to_response('pages.html', var_dict, context_instance=RequestContext(request))

"""
def proxy(request, proxy_slug):
    proxy = get_object_or_404(Proxy, slug=proxy_slug)
    var_dict = {}
    var_dict['proxy'] = proxy
    return render_to_response('proxy.html', var_dict, context_instance=RequestContext(request))
"""
