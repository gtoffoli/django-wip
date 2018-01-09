# -*- coding: utf-8 -*-

import sys
if (sys.version_info > (3, 0)):
    from urllib import parse as urlparse
else:
    import urlparse

import os
import re
import logging

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic.base import ContextMixin
from django.utils.cache import patch_response_headers
from django.core.cache import caches
from django.conf import settings
from httpproxy.views import HttpProxy
from revproxy.views import ProxyView as RevProxy
from revproxy.response import  get_django_response
import revproxy
revproxy.MIN_STREAMING_LENGTH = 1024 * 1024 * 1024 #  4 * 1024  # 4KB

from .models import Site, Proxy, Webpage

from lxml import etree
from lxml.etree import tostring
from repoze.xmliter.serializer import XMLSerializer
from repoze.xmliter.utils import getHTMLSerializer
from diazo.wsgi import DiazoMiddleware
from diazo.utils import quote_param
from diazo.compiler import compile_theme
from django_diazo.settings import DOCTYPE
# from django_diazo.utils import get_active_theme, check_themes_enabled, should_transform
if settings.PROXY_APP == 'revproxy':
    from io import StringIO
    from django.template.base import Template
    from diazo.compiler import compile_theme
    from revproxy.transformer import DiazoTransformer
    from revproxy.utils import get_charset, is_html_content_type


# REWRITE_REGEX = re.compile(r'((?:src|action|href)=["\'])/(?!\/)')
REWRITE_REGEX = re.compile(r'((?:action)=["\'])/(?!\/)')
# RESOURCES_REGEX = re.compile(r'(\.(css|js|png|jpg|gif|pdf|ppt|pptx|doc|docx|xls|xslx|odt|woff))', re.IGNORECASE)
RESOURCES_REGEX = re.compile(r'(\.(css|js|png|jpg|gif|pdf|ppt|pptx|doc|docx|xls|xslx|odt|woff|ttf))', re.IGNORECASE)
BODY_REGEX = re.compile(r'(\<body.*?\>)', re.IGNORECASE)

# hreflang_template = '<link rel="alternate" hreflang="%s" href="%s" />'
hreflang_template = '<%s>; rel="alternate"; hreflang="%s"'

info = {
  'en': """
<div align="center">%sThis is an experimental partial translation of the website <a href="%s">%s</a></div>""",
  'es': """
<div align="center">%sEsta es una traducción experimental y parcial del sitio web <a href="%s">%s</a></div>""",
}

class WipHttpProxy(HttpProxy):
    """ subclasses httpproxy.views.HttpProxy in order to reuse auxiliary methods, such as record and play:
        main ones (dispatch and rewrite_response) are completely redefined """

    # new class attributes
    prefix = ''
    site_id = ''
    proxy_id = ''
    language_code = ''
    proxy = None

    def __init__(self, *args,**kwargs):
        """ see __init__ method of DjangoDiazoMiddleware in module django_diazo.middleware """
        super(WipHttpProxy, self).__init__(*args,**kwargs)
        self.app = None
        self.theme_id = None
        self.diazo = None
        self.transform = None
        self.params = {}
        self.log = logging.getLogger('wip')
        self.log.info("WipHttpProxy created")

    def dispatch(self, request, url, *args, **kwargs):
        """ redefines the dispatch method of httpproxy.views.HttpProxy """
        # anticipating next 3 statements from method of superclass shouldn't harm
        self.url = url
        self.original_request_path = request.path
        request = self.normalize_request(request)

        # new stuff below concerns proxies and sites in the WIP model
        self.host = self.request.get_host() # Returns the originating host of the request using information from the HTTP_X_FORWARDED_HOST (if USE_X_FORWARDED_HOST is enabled) and HTTP_HOST headers, in that order
        self.online = False
        for proxy in Proxy.objects.all():
            if proxy.host and self.host.count(proxy.host):
                self.proxy = proxy
                self.proxy_id = proxy.id
                self.language_code = proxy.language.code
                site = proxy.site
                self.site = site
                self.base_url = site.url
                self.online = True
                break
        if not self.proxy:
            if self.proxy_id:
                self.proxy = proxy = Proxy.objects.get(pk=self.proxy_id)
                self.site = site = proxy.site
                self.base_url = site.url
            elif self.site_id:
                self.site = site = Site.objects.get(pk=self.site_id)

        """ test on mode "play" shouldn't harm, even if unused - CAN RETURN >
        if self.mode == 'play':
            response = self.play(request)
            # TODO: avoid repetition, flow of logic could be improved
            if self.rewrite:
                # response = self.rewrite_response(request, response)
                if hasattr(self.content, 'decode'):
                    self.content = response.content.decode('utf-8')
                self.rewrite_response(request)
                if hasattr(self.content, 'encode'):
                    response.content = self.content.encode('utf-8')
            return response
        < test on mode "play" """

        # 1st part of stuff below concerns caching of "resources", such as media files - CAN RETURN
        key = '%s-%s' % (proxy.site.path_prefix, url)
        should_cache_resource = False
        resource_match = RESOURCES_REGEX.search(url)
        if resource_match is not None:
            resources_cache = caches['resources']
            cached_response = resources_cache.get(key, None)
            if cached_response:
                cache_seconds = 7 * 24 * 3600
                patch_response_headers(cached_response, cache_timeout=cache_seconds)
                return cached_response
            else:
                should_cache_resource = True

        response = super(HttpProxy, self).dispatch(request, *args, **kwargs) # <----- call method of superclass
        # response = super(WipHttpProxy, self).dispatch(request, *args, **kwargs) # <----- call method of superclass
        """ test on mode "record" shouldn't harm, even if unused >
        if self.mode == 'record':
            self.record(response)
        > test on mode "record" """

        # 2-nd part of stuff below concerns caching of "resources", such as media files - CAN RETURN
        if resource_match is not None:
            cache_seconds = 7 * 24 * 3600
            patch_response_headers(response, cache_timeout=cache_seconds)
        if should_cache_resource:
            resources_cache.set(key, response)
            return response

        # handle requests for robots.txt
        parsed_url = urlparse.urlparse(url)
        self.path = parsed_url.path
        if self.proxy and self.path == 'robots.txt':
            response.content = self.proxy.robots_txt.encode('utf-8')
            return response

        # apply various transformations on the response content only if the "html" tag is found at the beginning (?)
        trailer = response.content[:100]
        # if trailer.count('<') and trailer.lower().count('html'):
        if trailer.count('<'.encode('utf-8')) and trailer.lower().count('html'.encode('utf-8')):
            self.content = response.content.decode('utf-8')

            # DIAZO transform
            self.transform_response(request, response)

            # apply specific proxy-translation transformation
            if self.proxy_id and self.language_code:
                self.translate_response(request)

            # test on self.rewrite
            if self.rewrite:
                self.replace_links()
                self.rewrite_response(request)
            response.content = self.content.encode('utf-8')

        if self.proxy:
            # add language-related headers
            headers = []
            # original_url = '%s/%s' % (self.site.url, self.path)
            protocol = 'http://'
            for proxy in Proxy.objects.filter(site=self.site):
                if self.online and proxy.host:
                    proxy_url = '%s%s/%s' % (protocol, proxy.host, self.path)
                else:
                    proxy_url = '%slocalhost:8000/%s/%s' % (protocol, proxy.base_path, self.path)
                headers.append(hreflang_template % (proxy_url, proxy.language_id))
            link = ', '.join(headers)
            response['Link'] = link

        return response

    def transform_response(self, request, response):
        """ see process_response method of DjangoDiazoMiddleware in module django_diazo.middleware
        Transform the response with Diazo if transformable
        """
        theme = self.site.get_active_theme(request)
        if not theme:
            return response
        content = response
        rules_file = os.path.join(theme.theme_path(), 'rules.xml')
        compiled_file = os.path.join(theme.theme_path(), 'compiled.xsl')
        if not os.path.exists(compiled_file) or theme.debug:
            self.theme_id = theme.id
            read_network = False
            access_control = etree.XSLTAccessControl(read_file=True, write_file=False, create_dir=False, read_network=read_network, write_network=False)
            theme_parser = etree.HTMLParser()
            rules_parser = etree.XMLParser(recover=False)
            compiled_theme = compile_theme(
                rules_file,
                theme=None,
                includemode='document',
                access_control=access_control,
                read_network=read_network,
                parser=theme_parser,
                rules_parser=rules_parser,
                xsl_params={})
            out_file = open(compiled_file, 'w')
            # out_file.write(etree.tostring(compiled_theme))
            out_file.write(etree.tostring(compiled_theme).decode())
            out_file.close()
        else:
            in_file = open(compiled_file, 'r')
            compiled_theme = etree.fromstring(in_file.read())
            in_file.close
        self.transform = etree.XSLT(compiled_theme)
        if isinstance(response, etree._Element):
            response = HttpResponse()
        else:
            parser = etree.HTMLParser(remove_blank_text=True, remove_comments=True)
            content = etree.fromstring(response.content, parser)
        result = self.transform(content, **self.params)
        response.content = XMLSerializer(result, doctype=DOCTYPE).serialize()
        if isinstance(response, etree._Element):
            response = HttpResponse('<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(content))
        return response

    def translate_response(self, request):
        if self.proxy:
            proxy = self.proxy
            site = self.site
        else:
            proxy = Proxy.objects.get(pk=self.proxy_id)
            site = proxy.site
        path = urlparse.urlparse(self.url).path
        transformed = False
        if request.GET or request.POST:
            self.content, transformed = proxy.translate_page_content(self.content)
        else:
            webpages = Webpage.objects.filter(site=site, path=path).order_by('-created')
            if webpages:
                webpage = webpages[0]
                if not webpage.no_translate:
                    self.content, transformed = webpage.get_translation(self.language_code)
            if not transformed and proxy.enable_live_translation:
                self.content, transformed = proxy.translate_page_content(self.content)
        # replace text or HTML fragment on the fly (new)
        if hasattr(self.content, 'decode'):
            self.content = self.content.decode()
        self.content = proxy.replace_fragments(self.content, path)

    def replace_links(self):
        """
        Rewrites unconditionally the links in the HTML
        removing the base url of the original site (if any) when in online mode
        or replacing it with the proxy prefix
        """
        if self.online:
            self.content = self.content.replace(self.base_url, '')
        else:
            self.content = self.content.replace(self.base_url, self.prefix)

    def rewrite_response(self, request):
        """
        Rewrites the response to fix references to resources loaded from HTML
        files (images, etc.).
        .. note:
            The rewrite logic uses a fairly simple regular expression to look for
            "src", "href" and "action" attributes with a value starting with "/"
        """
        proxy_root = self.original_request_path.rsplit(request.path, 1)[0]
        self.content = REWRITE_REGEX.sub(r'\1{}/'.format(proxy_root), self.content)
        site_url = self.base_url
        extra = ''
        if request.user.is_superuser:
            webpages = Webpage.objects.filter(site=self.site, path=self.path).order_by('-created')
            if webpages:
                extra = '<a href="/page/%s/">@</a> ' % webpages[0].id
        if self.proxy and self.online:
            self.content = BODY_REGEX.sub(r'\1' + info[self.language_code] % (extra, site_url, site_url.split('//')[1]), self.content)

class WipRevProxy(RevProxy, ContextMixin):
    html5 = False

    # new class attributes
    prefix = ''
    site_id = ''
    proxy_id = ''
    language_code = ''
    proxy = None


    def __init__(self, *args,**kwargs):
        """ see __init__ method of DjangoDiazoMiddleware in module django_diazo.middleware """
        super(WipRevProxy, self).__init__(*args,**kwargs)
        self.log = logging.getLogger('wip')
        self.log.info("WipRevProxy created")


    def dispatch(self, request, path):
        """ redefines the dispatch method of revproxy.views.ProxyView """

        # custom stuff
        self.url = path
        self.original_request_path = request.path
        parsed_url = urlparse.urlparse(path)
        self.path = parsed_url.path

 
        self.request_headers = self.get_request_headers()

        redirect_to = self._format_path_to_redirect(request)
        if redirect_to:
            return redirect(redirect_to)

        proxy_response = self._created_proxy_response(request, path)

        self._replace_host_on_redirect_location(request, proxy_response)
        self._set_content_type(request, proxy_response)

        # custom stuff below concerns proxies and sites in the WIP model
        self.host = self.request.get_host() # Returns the originating host of the request using information from the HTTP_X_FORWARDED_HOST (if USE_X_FORWARDED_HOST is enabled) and HTTP_HOST headers, in that order
        self.online = False
        for proxy in Proxy.objects.all():
            if proxy.host and self.host.count(proxy.host):
                self.proxy = proxy
                self.proxy_id = proxy.id
                self.language_code = proxy.language.code
                site = proxy.site
                self.site = site
                self.base_url = site.url
                self.online = True
                break
        if not self.proxy:
            if self.proxy_id:
                self.proxy = proxy = Proxy.objects.get(pk=self.proxy_id)
                self.site = site = proxy.site
                self.base_url = site.url
            elif self.site_id:
                self.site = site = Site.objects.get(pk=self.site_id)
                self.base_url = site.url
        self.log.info("request host: %s", self.host)
        self.log.info("host: %s", self.proxy.host)
        self.log.info("prefix: %s", str(self.prefix))
        self.log.info("base_url: %s", self.base_url)
        self.log.info("online: %s", str(self.online))

        # 1st part of custom stuff below concerns caching of "resources", such as media files - CAN RETURN
        key = '%s-%s' % (proxy.site.path_prefix, path)
        should_cache_resource = False
        resource_match = RESOURCES_REGEX.search(path)
        if resource_match is not None:
            resources_cache = caches['resources']
            cached_response = resources_cache.get(key, None)
            if cached_response:
                cache_seconds = 7 * 24 * 3600
                patch_response_headers(cached_response, cache_timeout=cache_seconds)
                return cached_response
            else:
                should_cache_resource = True

        response = get_django_response(proxy_response,
                                       strict_cookies=self.strict_cookies)

        # 2-nd part of custom stuff below concerns caching of "resources", such as media files - CAN RETURN
        if resource_match is not None:
            cache_seconds = 7 * 24 * 3600
            patch_response_headers(response, cache_timeout=cache_seconds)
        if should_cache_resource:
            resources_cache.set(key, response)
            return response

        # custom: apply various transformations on the response content only if the "html" tag is found at the beginning (?)
        if hasattr(response, 'content'):
            trailer = response.content[:100]
            if trailer.count('<'.encode('utf-8')) and trailer.lower().count('html'.encode('utf-8')):

                # apply DIAZO transform
                theme = self.site.get_active_theme(request)
                if theme:
                    self.log.info("apply theme: %s", theme.name)
                    response = self.transform_response(request, response)
    
                # apply specific proxy-translation transformation
                self.content = response.content.decode()
                if self.proxy_id and self.language_code:
                    self.log.info("translate to language: %s", self.language_code)
                    self.translate_response(request)
    
                self.replace_links()
                self.rewrite_response(request)
                response.content = self.content.encode('utf-8')

        self.log.debug("RESPONSE RETURNED: %s", response)
        return response

    def transform_response(self, request, response):
        theme = self.site.get_active_theme(request)
        if not theme:
            return response
        rules_filename = os.path.join(theme.theme_path(), 'rules.xml')
        theme_filename = os.path.join(theme.theme_path(), 'theme.html')
        self.log.info("theme and rules from: %s and %s", theme_filename, rules_filename)
        with open(theme_filename, encoding='utf-8') as f:
            theme = f.read()

        context_data = self.get_context_data()
        diazo = DiazoTransformer(request, response)
        response = diazo.transform(rules_filename, theme_filename,
                                   self.html5, context_data, theme=theme)
        return response

WipRevProxy.translate_response = WipHttpProxy.translate_response
WipRevProxy.replace_links = WipHttpProxy.replace_links
WipRevProxy.rewrite_response = WipHttpProxy.rewrite_response
