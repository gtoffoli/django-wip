# -*- coding: utf-8 -*-

import re
import urlparse
from django.utils.cache import patch_response_headers
from django.core.cache import caches
from httpproxy.views import HttpProxy
from models import Proxy, Webpage

# REWRITE_REGEX = re.compile(r'((?:src|action|href)=["\'])/(?!\/)')
REWRITE_REGEX = re.compile(r'((?:action)=["\'])/(?!\/)')
RESOURCES_REGEX = re.compile(r'(\.(css|js|png|jpg|gif|pdf|ppt|pptx|doc|docx|xls|xslx|odt/woff))', re.IGNORECASE)
BODY_REGEX = re.compile(r'(\<body.*?\>)', re.IGNORECASE)

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
    proxy_id = ''
    language_code = ''
    proxy = None

    def dispatch(self, request, url, *args, **kwargs):
        self.url = url
        self.host = request.META.get('HTTP_HOST', '')
        # if self.prefix == '/dummy':
        for proxy in Proxy.objects.all():
            if proxy.host and self.host.count(proxy.host):
                self.proxy = proxy
                self.proxy_id = proxy.id
                self.language_code = proxy.language.code
                site = proxy.site
                self.site = site
                self.base_url = site.url
                break

        if not self.proxy:
            self.proxy = proxy = Proxy.objects.get(pk=self.proxy_id)
            self.site = site = proxy.site

        self.original_request_path = request.path
        request = self.normalize_request(request)
        if self.mode == 'play':
            response = self.play(request)
            # TODO: avoid repetition, flow of logic could be improved
            if self.rewrite:
                response = self.rewrite_response(request, response)
            return response

        key = '%s-%s' % (proxy.site.path_prefix, url)
        should_cache_resource = False
        resource_match = RESOURCES_REGEX.search(url)
        if resource_match is not None:
            resources_cache = caches['resources']
            cached_response = resources_cache.get(key, None)
            if cached_response:
                return cached_response
            else:
                should_cache_resource = True
        response = super(HttpProxy, self).dispatch(request, *args, **kwargs)
        if resource_match is not None:
            cache_seconds = 7 * 24 * 3600
            patch_response_headers(response, cache_timeout=cache_seconds)
            print 'Expires: ', response.get('Expires', '')
        if should_cache_resource:
            resources_cache.set(key, response)
            return response

        # content_type = response.headers['Content-Type']
        trailer = response.content[:100]
        if trailer.count('<') and trailer.lower().count('html'):
            self.path = urlparse.urlparse(self.url).path
            if self.proxy_id and self.language_code:
                self.translate(response)
            else:
                if self.mode == 'record':
                    self.record(response)
                if self.rewrite:
                    response = self.rewrite_response(request, response)
            if self.rewrite_links:
                response = self.replace_links(response)
                response = self.rewrite_response(request, response)
        return response

    def replace_links(self, response):
        content = response.content
        content = content.replace(self.base_url, self.prefix)
        if self.language_code == 'en':
            content = content.replace('Cerca corsi', 'Search courses').replace('Cerca...', 'Search...')
        if self.language_code == 'es':
            content = content.replace('Cerca corsi', 'Buscar cursos').replace('Cerca...', 'Buscar...')
        response.content = content
        return response

    def rewrite_response(self, request, response):
        """
        Rewrites the response to fix references to resources loaded from HTML
        files (images, etc.).
        .. note:
            The rewrite logic uses a fairly simple regular expression to look for
            "src", "href" and "action" attributes with a value starting with "/"
        """
        proxy_root = self.original_request_path.rsplit(request.path, 1)[0]
        content = response.content
        content = REWRITE_REGEX.sub(r'\1{}/'.format(proxy_root), content)
        site_url = self.base_url
        extra = ''
        if request.user.is_superuser:
            webpages = Webpage.objects.filter(site=self.site, path=self.path).order_by('-created')
            if webpages:
                extra = '<a href="/page/%s/">@</a> ' % webpages[0].id
        content = BODY_REGEX.sub(r'\1' + info[self.language_code] % (extra, site_url, site_url.split('//')[1]), content)
        response.content = content
        return response

    def translate(self, response):
        request = self.request
        content = response.content
        if self.proxy:
            proxy = self.proxy
            site = self.site
        else:
            proxy = Proxy.objects.get(pk=self.proxy_id)
            site = proxy.site
        has_translation = False
        if request.GET or request.POST:
            content, has_translation = proxy.translate_page_content(content)
        else:
            path = urlparse.urlparse(self.url).path
            webpages = Webpage.objects.filter(site=site, path=path).order_by('-created')
            if webpages:
                webpage = webpages[0]
                if not webpage.no_translate:
                    content, has_translation = webpage.get_translation(self.language_code)
        if has_translation:
            response.content = content
        return response

