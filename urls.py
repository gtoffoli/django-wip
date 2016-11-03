# -*- coding: utf-8 -*-

"""wip URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Import the include() function: from django.conf.urls import url, include
    3. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""

from settings import USE_SCRAPY, USE_NLTK
from django.conf.urls import include, url
from django.views.generic import TemplateView
from django.contrib import admin
from models import Site, Proxy
import views
import search_indexes
from api import find_block, send_block, send_fragment
# import scripts
from proxy import WipHttpProxy

urlpatterns = [
    # url(r'^dummy/(?P<url>.*)$', WipHttpProxy.as_view(rewrite_links=True)),
    url(r'^admin/', admin.site.urls),
    url(r'^tinymce/', include('tinymce.urls')),
    url(r"^$", views.home, name="home"),
    url(r'^api/find_block/$', find_block),
    url(r'^api/send_block/$', send_block),
    url(r'^api/send_fragment/$', send_fragment),
    url(r"^language/(?P<language_code>[\w-]*)/set/$", views.language, name="language"),
    url(r"^discover/$", views.discover, name="discover"),
    url(r"^discover/(?P<scan_id>[\d]+)/$", views.discover, name="discover"),
    url(r"^sites/$", views.sites, name="sites"),
    url(r"^site/(?P<site_slug>[\w-]+)/$", views.site, name="site"),
    url(r"^site/(?P<site_slug>[\w-]+)/pages/$", views.site_pages, name="site_pages"),
    url(r"^site/(?P<site_slug>[\w-]+)/blocks/$", views.site_blocks, name="site_blocks"),
    url(r"^page/(?P<page_id>[\d]+)/blocks/$", views.page_blocks, name="page_blocks"),
    url(r"^page/(?P<page_id>[\d]+)/extract_blocks/$", views.page_extract_blocks, name="page_extract_blocks"),
    url(r"^page/(?P<page_id>[\d]+)/cache_translation/(?P<language_code>[\w-]+)/$", views.page_cache_translation, name="page_cache_translation"),
    url(r"^page/(?P<page_id>[\d]+)/proxy/(?P<language_code>[\w-]+)/$", views.page_proxy, name="page_proxy"),
    url(r"^page/(?P<page_id>[\d]+)/$", views.page, name="page"),
    url(r"^block/(?P<block_id>[\d]+)/pages/$", views.block_pages, name="block_pages"),
    url(r"^block/(?P<block_id>[\d]+)/translate/(?P<target_code>[\w]+)/$", views.block_translate, name="block_translate"),
    url(r"^block/(?P<block_id>[\d]+)/$", views.block, name="block"),
    url(r"^string_add_by_language/(?P<language_code>[\w-]*)/$", views.string_edit, name="string_add_by_language"),
    url(r"^string_add_by_proxy/(?P<proxy_slug>[\w-]+)/$", views.string_edit, name="string_add_by_proxy"),
    url(r"^string_edit/(?P<string_id>[\d]+)/$", views.string_edit, name="string_edit"),
    url(r"^string_edit/$", views.string_edit, name="string_edit"),
    url(r"^string/(?P<string_id>[\d]+)/$", views.string_view, name="string_view"),
    url(r"^string_translate/(?P<string_id>[\d]+)/(?P<target_code>[\w]+)/$", views.string_translate, name="string_translate"),
    url(r"^strings/(?P<sources>[\w-]*)/(?P<state>[\w-]*)/(?P<targets>[\w-]*)/$", views.list_strings, name="list_strings"),
    url(r"^strings/(?P<sources>[\w-]*)/(?P<state>[\w-]*)/$", views.list_strings, name="list_strings_notarget"),
    url(r"^proxies/$", views.proxies, name="proxies"),
    url(r"^proxy/(?P<proxy_slug>[\w-]+)/translations/$", views.proxy_string_translations, name="proxy_string_translations"),
    url(r"^proxy/(?P<proxy_slug>[\w-]+)/$", views.proxy, name="proxy"),
    url(r"^add_translated_string/$", views.add_translated_string, name="add_translated_string"),
    url(r"^delete_translated_string/$", views.delete_translated_string, name="delete_translated_string"),
    url(r"^strings_translations/(?P<proxy_slug>[\w-]+)/$", views.strings_translations, name="strings_translations"),
    url(r"^strings_translations/$", views.strings_translations, name="strings_translations"),
    # url(r"^my_task/$", views.my_task, name="my_task"),
    url(r'^navigation_autocomplete$', search_indexes.navigation_autocomplete, name='navigation_autocomplete'),
    url(r"^test/$", TemplateView.as_view(template_name="test.html"), name="test"),
]

# urlpatterns += patterns('',
urlpatterns += (
    url(r'^accounts/', include('allauth.urls')),
    url(r'^accounts/profile/', TemplateView.as_view(template_name='accounts/profile.html'), name='welcome',),
)   


if USE_SCRAPY:
    urlpatterns += (
        url(r"^site/(?P<site_slug>[\w-]+)/crawl/$", views.site_crawl_by_slug, name="site_crawl"),
        url(r"^my_scans/$", views.user_scans, name="my_scans"),
        url(r"^user_scans/(?P<username>[\w-]+)/$", views.user_scans, name="user_scans"),
        url(r"^scan/(?P<scan_id>[\d]+)/delete/$", views.scan_delete, name="scan_delete"),
        url(r"^scan/(?P<scan_id>[\d]+)/$", views.scan_detail, name="scan_detail"),
        # url(r"^scan/(?P<scan_id>[\d]+)/$", views.scan_detail, name="scan_detail"),
        url(r"^crawler_progress/(?P<scan_id>[\d]+)/(?P<i_line>[\d]+)/$", views.crawler_progress, name="crawler_progress"),
        url(r"^stop_crawler/(?P<scan_id>[\d]+)/$", views.stop_crawler, name="stop_crawler"),
        # url(r"^view_file/(?P<task_id>[\d]+)/(?P<site_slug>[\w-]+)/(?P<file_name>[\w\.-]+)/(?P<i_line>[\d]+)/$", views.view_file, name="view_file"),
        url(r"^scan_download/(?P<scan_id>[\d]+)/$", views.scan_download, name="scan_download"),
        # url(r"^view_discovery/(?P<scan_id>[\d]+)/$", views.view_discovery, name="view_discovery"),
        # url(r"^discovery_settings/$", views.discovery_settings, name="discoveyr_settings"),
    )   
if USE_NLTK:
    urlpatterns += (
        url(r"^create_tagger/$", views.create_tagger, name="create_tagger"),
        url(r"^page_scan/(?P<fetched_id>[\d]+)/$", views.page_scan, name="page_scan"),
    )   

try:
    proxies = Proxy.objects.all()
    for proxy in proxies:
        prefix = '/%s' % str(proxy.base_path)
        base_url = str(proxy.site.url)
        regex = r'^' + proxy.base_path + r'/(?P<url>.*)$'
        url_entry = url(regex, WipHttpProxy.as_view(base_url=base_url, prefix=prefix, rewrite_links=True, proxy_id=proxy.id, language_code=proxy.language.code))
        urlpatterns.append(url_entry)
    sites = Site.objects.all()
    for site in sites:
        prefix = '/%s' % str(site.path_prefix)
        base_url = str(site.url)
        regex = r'^' + site.path_prefix + r'/(?P<url>.*)$'
        url_entry = url(regex, WipHttpProxy.as_view(base_url=base_url, prefix=prefix, rewrite_links=True, site_id=site.id))
        urlpatterns.append(url_entry)
except:
    pass
