# -*- coding: utf-8 -*-

import sys
if (sys.version_info > (3, 0)):
    from urllib import parse as urlparse
else:
    import urlparse

import os
import re
from logging import getLogger

from django.http import HttpResponse
from django.utils.cache import patch_response_headers
from django.core.cache import caches
from httpproxy.views import HttpProxy

from .models import Site, Proxy, Webpage

"""
from lxml import etree
from lxml.etree import tostring
from repoze.xmliter.serializer import XMLSerializer
from repoze.xmliter.utils import getHTMLSerializer
"""
from diazo.wsgi import DiazoMiddleware
from diazo.utils import quote_param
from diazo.compiler import compile_theme
from django_diazo.settings import DOCTYPE
# from django_diazo.utils import get_active_theme, check_themes_enabled, should_transform

# REWRITE_REGEX = re.compile(r'((?:src|action|href)=["\'])/(?!\/)')
REWRITE_REGEX = re.compile(r'((?:action)=["\'])/(?!\/)')
RESOURCES_REGEX = re.compile(r'(\.(css|js|png|jpg|gif|pdf|ppt|pptx|doc|docx|xls|xslx|odt|woff))', re.IGNORECASE)
BODY_REGEX = re.compile(r'(\<body.*?\>)', re.IGNORECASE)

# hreflang_template = '<link rel="alternate" hreflang="%s" href="%s" />'
hreflang_template = '<%s>; rel="alternate"; hreflang="%s"'

info = {
  'en': """
<div align="center">%sThis is an experimental partial translation of the website <a href="%s">%s</a></div>""",
  'es': """
<div align="center">%sEsta es una traducción experimental y parcial del sitio web <a href="%s">%s</a></div>""",
}
backdoor = """
"""

class WipHttpProxy(HttpProxy):
    prefix = ''
    # prefix = '/dummy'
    rewrite_links = False
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

    def dispatch(self, request, url, *args, **kwargs):
        self.url = url
        self.host = request.META.get('HTTP_HOST', '')

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
            elif self.site_id:
                self.site = site = Site.objects.get(pk=self.site_id)

        self.original_request_path = request.path
        request = self.normalize_request(request)
        if self.mode == 'play':
            response = self.play(request)
            # TODO: avoid repetition, flow of logic could be improved
            if self.rewrite:
                """
                response = self.rewrite_response(request, response)
                """
                if hasattr(self.content, 'decode'):
                    self.content = response.content.decode('utf-8')
                self.rewrite_response(request)
                if hasattr(self.content, 'encode'):
                    response.content = self.content.encode('utf-8')
            return response

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
        response = super(HttpProxy, self).dispatch(request, *args, **kwargs)
        if resource_match is not None:
            cache_seconds = 7 * 24 * 3600
            patch_response_headers(response, cache_timeout=cache_seconds)
        if should_cache_resource:
            resources_cache.set(key, response)
            return response

        parsed_url = urlparse.urlparse(url)
        self.path = parsed_url.path
        if self.proxy and self.path == 'robots.txt':
            # response.content = self.proxy.robots_txt
            response.content = self.proxy.robots_txt.encode('utf-8')
            return response

        trailer = response.content[:100]
        # if trailer.count('<') and trailer.lower().count('html'):
        if trailer.count('<'.encode('utf-8')) and trailer.lower().count('html'.encode('utf-8')):
            """
            response = self.transform_response(request, response)
            if self.proxy_id and self.language_code:
                self.translate_response(request, response)
            else:
                if self.mode == 'record':
                    self.record(response)
                if self.rewrite:
                    response = self.rewrite_response(request, response)
            if self.rewrite_links:
                response = self.replace_links(response)
                response = self.rewrite_response(request, response)
            """
            self.content = response.content.decode('utf-8')
            # self.transform_response(request, response)
            if self.proxy_id and self.language_code:
                self.translate_response(request)
            else:
                if self.mode == 'record':
                    self.record(response)
                if self.rewrite:
                    self.rewrite_response(request)
            if self.rewrite_links:
                self.replace_links()
                self.rewrite_response(request)
            response.content = self.content.encode('utf-8')

        if self.proxy:
            headers = []
            original_url = '%s/%s' % (self.site.url, self.path)
            protocol = 'http://'
            for proxy in Proxy.objects.filter(site=self.site):
                if self.online and proxy.host:
                    proxy_url = '%s%s/%s' % (protocol, proxy.host, self.path)
                else:
                    proxy_url = '%slocalhost:8000/%s/%s' % (protocol, proxy.base_path, self.path)
                headers.append(hreflang_template % (proxy_url, proxy.language_id))
            link = ', '.join(headers)
            # print ('link: ', link)
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
            """
            print ('self.theme_id: ', self.theme_id)
            print ('theme.id: ', theme.id)
            print ('os.path.exists(rules_file): ', os.path.exists(rules_file))
            print ('theme.debug: ', theme.debug)
            """
            self.theme_id = theme.id
            read_network = False
            access_control = etree.XSLTAccessControl(read_file=True, write_file=False, create_dir=False, read_network=read_network, write_network=False)
            compiler_parser = etree.XMLParser()
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
            out_file.write(etree.tostring(compiled_theme))
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
            # print ('parser: ', parser)
            content = etree.fromstring(response.content, parser)
        result = self.transform(content, **self.params)
        response.content = XMLSerializer(result, doctype=DOCTYPE).serialize()
        if isinstance(response, etree._Element):
            response = HttpResponse('<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(content))
        return response

    """
    def translate_response(self, request, response):
        request = self.request
        content = response.content
    """
    def translate_response(self, request):
        if self.proxy:
            proxy = self.proxy
            site = self.site
        else:
            proxy = Proxy.objects.get(pk=self.proxy_id)
            site = proxy.site
        transformed = False
        if request.GET or request.POST:
            """
            content, transformed = proxy.translate_page_content(content)
            """
            self.content, transformed = proxy.translate_page_content(self.content)
        else:
            path = urlparse.urlparse(self.url).path
            # print ('translate_response: ', path)
            # print ('enable_live_translation: ', proxy.enable_live_translation)
            webpages = Webpage.objects.filter(site=site, path=path).order_by('-created')
            if webpages:
                webpage = webpages[0]
                # print ('no_translate', webpage.no_translate)
                if not webpage.no_translate:
                    """
                    content, transformed = webpage.get_translation(self.language_code)
                    """
                    self.content, transformed = webpage.get_translation(self.language_code)
            if not transformed and proxy.enable_live_translation:
                # print ('no translation found: ', path)
                """
                content, transformed = proxy.translate_page_content(content)
                """
                self.content, transformed = proxy.translate_page_content(self.content)
        # replace text or HTML fragment on the fly (new)
        """
        content = proxy.replace_fragments(content, path)
        response.content = content
        return response
        """
        if hasattr(self.content, 'decode'):
            self.content = self.content.decode()
        self.content = proxy.replace_fragments(self.content, path)

    def replace_links(self):
    # def replace_links(self, response):
        """
        Rewrites unconditionally the links in the HTML
        removing the base url of the original site (if any) when in online mode
        or replacing it with the proxy prefix
        """
        """
        content = response.content
        content = content.replace(self.base_url, self.prefix)
        response.content = content
        return response
        """
        if self.online:
            self.content = self.content.replace(self.base_url, '')
        else:
            self.content = self.content.replace(self.base_url, self.prefix)

    # def rewrite_response(self, request, response):
    def rewrite_response(self, request):
        """
        Rewrites the response to fix references to resources loaded from HTML
        files (images, etc.).
        .. note:
            The rewrite logic uses a fairly simple regular expression to look for
            "src", "href" and "action" attributes with a value starting with "/"
        """
        proxy_root = self.original_request_path.rsplit(request.path, 1)[0]
        """
        content = response.content
        content = REWRITE_REGEX.sub(r'\1{}/'.format(proxy_root), content)
        """
        self.content = REWRITE_REGEX.sub(r'\1{}/'.format(proxy_root), self.content)
        site_url = self.base_url
        extra = ''
        if request.user.is_superuser:
            webpages = Webpage.objects.filter(site=self.site, path=self.path).order_by('-created')
            if webpages:
                extra = '<a href="/page/%s/">@</a> ' % webpages[0].id
        """
        if self.proxy and self.online:
            content = BODY_REGEX.sub(r'\1' + info[self.language_code] % (extra, site_url, site_url.split('//')[1]), content)
        response.content = content
        return response
        """
        if self.proxy and self.online:
            self.content = BODY_REGEX.sub(r'\1' + info[self.language_code] % (extra, site_url, site_url.split('//')[1]), self.content)
