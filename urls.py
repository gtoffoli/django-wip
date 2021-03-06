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

from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import TemplateView
from django.contrib import admin

from .models import Site, Proxy
from wip import views
# from wip import search_indexes
from .api import find_block, send_block, add_block, send_fragment
from .proxy import WipHttpProxy, get_locale_switch
from .proxy import WipRevProxy

urlpatterns = i18n_patterns(
    url(r"^$", views.home, name="home"),
    url(r'^admin/', admin.site.urls),
)

urlpatterns += (
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^api/find_block/$', find_block),
    url(r'^api/send_block/$', send_block),
    url(r'^api/add_block/$', add_block),
    url(r'^api/send_fragment/$', send_fragment),
    url(r'^get_locale_switch/(?P<site_prefix>[\w-]+)/(?P<language_code>[\w-]*)/$', get_locale_switch),
    url(r'^get_locale_switch/(?P<site_prefix>[\w-]+)/$', get_locale_switch),
    url(r'^get_locale_switch/$', get_locale_switch),
)   

# urlpatterns = (
urlpatterns += (
    url(r'^tinymce/', include('tinymce.urls')),
    url(r"^manage_roles/$", views.manage_roles, name="manage_roles"),
    url(r"^role/(?P<role_id>[\d]+)/select/$", views.user_role_select, name="user_role_select"),
    url(r"^role/(?P<role_id>[\d]+)/edit/$", views.role_edit, name="role_edit"),
    url(r"^role/edit/$", views.role_edit, name="role_edit"),
    url(r"^role/(?P<role_id>[\d]+)/$", views.role_detail, name="role_detail"),
    url(r"^language/(?P<language_code>[\w-]*)/set/$", views.language, name="language"),
    url(r'^discover/(?:(?P<scan_id>[\d]+)/)?$', views.Discover.as_view(), name="discover"),
    url(r'^discover/(?:(?P<site_slug>[\w-]+)/)?$', views.Discover.as_view(), name="discover"),
    url(r"^discover/$", views.Discover.as_view(), name="discover"),
    url(r'^crawl/(?P<site_slug>[\w-]+)/$', views.Crawl.as_view(), name="crawl"),
    url(r"^sites/$", views.sites, name="sites"),
    url(r"^site/(?P<site_slug>[\w-]+)/$", views.site, name="site"),
    url(r"^site/(?P<site_slug>[\w-]+)/pages/$", views.site_pages, name="site_pages"),
    url(r"^site/(?P<site_slug>[\w-]+)/blocks/$", views.site_blocks, name="site_blocks"),
    url(r"^page/(?P<page_id>[\d]+)/versions/$", views.page_versions, name="page_versions"),
    url(r"^page/(?P<page_id>[\d]+)/blocks/$", views.page_blocks, name="page_blocks"),
    url(r"^page/(?P<page_id>[\d]+)/extract_blocks/$", views.page_extract_blocks, name="page_extract_blocks"),
    url(r"^page/(?P<page_id>[\d]+)/cache_translation/(?P<language_code>[\w-]+)/$", views.page_cache_translation, name="page_cache_translation"),
    url(r"^page/(?P<page_id>[\d]+)/proxy/(?P<language_code>[\w-]+)/$", views.page_proxy, name="page_proxy"),
    url(r"^page/(?P<page_id>[\d]+)/$", views.page, name="page"),
    url(r"^block/(?P<block_id>[\d]+)/pages/$", views.block_pages, name="block_pages"),
    url(r"^block/(?P<block_id>[\d]+)/translate/(?P<target_code>[\w]+)/$", views.block_translate, name="block_translate"),
    url(r"^block/(?P<block_id>[\d]+)/$", views.block, name="block"),
    url(r"^proxies/$", views.proxies, name="proxies"),
    url(r"^proxy/(?P<proxy_slug>[\w-]+)/$", views.proxy, name="proxy"),
    url(r"^import_xliff/(?P<proxy_slug>[\w-]+)/$", views.import_xliff, name="import_xliff"),
    url(r"^add_update_translation/$", views.add_update_translation, name="add_update_translation"),
    url(r"^list_segments/(?P<segment_id>[\d]+)/$", views.list_segments_by_id, name="list_segments_by_id"),
    url(r"^list_segments/(?P<proxy_slug>[\w-]+)/$", views.list_segments_by_proxy, name="list_segments_by_proxy"),
    url(r"^list_segments/$", views.list_segments, name="list_segments"),
    url(r"^segment_add_by_proxy/(?P<proxy_slug>[\w-]+)/$", views.segment_edit, name="segment_add_by_proxy"),
    url(r"^add_segment_translation/$", views.add_segment_translation, name="add_segment_translation"),
    url(r"^segment_edit/(?P<segment_id>[\d]+)/$", views.segment_edit, name="segment_edit"),
    url(r"^segment/(?P<segment_id>[\d]+)/$", views.segment_view, name="segment_view"),
    url(r"^segment_translate/(?P<segment_id>[\d]+)/(?P<target_code>[\w]+)/$", views.segment_translate, name="segment_translate"),
    url(r"^translation_align/(?P<translation_id>[\d]+)/$", views.translation_align, name="translation_align"),
    # url(r'^navigation_autocomplete$', search_indexes.navigation_autocomplete, name='navigation_autocomplete'),
    url(r"^test/$", TemplateView.as_view(template_name="test.html"), name="test"),
)
# )

# urlpatterns += (
urlpatterns += i18n_patterns(
    url(r'^accounts/', include('allauth.urls')),
    url(r'^accounts/profile/', TemplateView.as_view(template_name='accounts/profile.html'), name='welcome',),
)   

import wip.terms.urls

if settings.USE_SCRAPY:
    urlpatterns += (
        # url(r"^site/(?P<site_slug>[\w-]+)/crawl/$", views.site_crawl_by_slug, name="site_crawl"),
        url(r"^site_scans/(?P<site_slug>[\w-]+)/$", views.site_scans, name="site_scans"),
        url(r"^user_scans(?:/(?P<username>[\w\.-]+))?/$", views.user_scans, name="user_scans"),
        url(r"^my_scans/$", views.my_scans, name="my_scans"),
        url(r"^scan/(?P<scan_id>[\d]+)/delete/$", views.scan_delete, name="scan_delete"),
        url(r"^scan/(?P<scan_id>[\d]+)/$", views.scan_detail, name="scan_detail"),
        url(r"^scan/(?P<scan_id>[\d]+)/pages/$", views.scan_pages, name="scan_pages"),
        url(r"^scan/(?P<scan_id>[\d]+)/words/$", views.scan_words, name="scan_words"),
        url(r"^scan/(?P<scan_id>[\d]+)/segments/$", views.scan_segments, name="scan_segments"),
        url(r"^scan_progress/(?P<scan_id>[\d]+)/(?P<i_line>[\d]+)/$", views.scan_progress, name="scan_progress"),
        url(r"^stop_crawler/(?P<scan_id>[\d]+)/$", views.stop_crawler, name="stop_crawler"),
        url(r"^scan_download/(?P<scan_id>[\d]+)/$", views.scan_download, name="scan_download"),
    )   
if settings.USE_NLTK:
    urlpatterns += (
        url(r"^create_tagger/$", views.create_tagger, name="create_tagger"),
        url(r"^page_scan/(?P<fetched_id>[\d]+)/$", views.page_scan, name="page_scan"),
    )   

try:
    sites = Site.objects.all()
    proxies = Proxy.objects.all()
    for proxy in proxies:
        prefix = '/%s' % str(proxy.base_path)
        base_url = str(proxy.site.url)
        if settings.PROXY_APP == 'httpproxy':
            regex = r'^' + proxy.base_path + r'/(?P<url>.*)$'
            url_entry = url(regex, WipHttpProxy.as_view(base_url=base_url, prefix=prefix, rewrite=True, proxy_id=proxy.id, language_code=proxy.language.code))
        else:
            regex = r'^' + proxy.base_path + r'/(?P<path>.*)$'
            url_entry = url(regex, WipRevProxy.as_view(_upstream=base_url, prefix=prefix, proxy_id=proxy.id, language_code=proxy.language.code))
        urlpatterns.append(url_entry)
    sites = Site.objects.all()
    for site in sites:
        prefix = '/%s' % str(site.path_prefix)
        base_url = str(site.url)
        if settings.PROXY_APP == 'httpproxy':
            regex = r'^' + site.path_prefix + r'/(?P<url>.*)$'
            url_entry = url(regex, WipHttpProxy.as_view(base_url=base_url, prefix=prefix, rewrite=True, site_id=site.id))
        else:
            regex = r'^' + site.path_prefix + r'/(?P<path>.*)$'
            url_entry = url(regex, WipRevProxy.as_view(_upstream=base_url, prefix=prefix, site_id=site.id))
        urlpatterns.append(url_entry)
except:
    pass
