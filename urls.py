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
from django.conf.urls import url
from django.contrib import admin
from models import Site
import views
from proxy import WipHttpProxy

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r"^$", views.home, name="home"),
    url(r"^sites/$", views.sites, name="sites"),
    url(r"^site/(?P<site_slug>[\w-]+)/$", views.site, name="site"),
    url(r"^site/(?P<site_slug>[\w-]+)/crawl/$", views.site_crawl_by_slug, name="site_crawl"),
    url(r"^site/(?P<site_slug>[\w-]+)/pages/$", views.site_pages, name="site_pages"),
    url(r"^page/(?P<page_id>[\d]+)/$", views.page, name="page"),
    url(r"^proxies/$", views.proxies, name="proxies"),
    # url(r"^my_task/$", views.my_task, name="my_task"),
]

sites = Site.objects.all()
for site in sites:
    prefix='/%s' % str(site.path_prefix)
    base_url = str(site.url)
    regex = r'^' + site.path_prefix + r'/(?P<url>.*)$'
    url_entry = url(regex, WipHttpProxy.as_view(base_url=base_url, prefix=prefix, rewrite_links=True))
    urlpatterns.append(url_entry)
