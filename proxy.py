# -*- coding: utf-8 -*-

import urlparse
from httpproxy.views import HttpProxy
from models import Proxy, Webpage, PageVersion, TranslatedVersion

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

        self.original_request_path = request.path
        request = self.normalize_request(request)
        if self.mode == 'play':
            response = self.play(request)
            # TODO: avoid repetition, flow of logic could be improved
            if self.rewrite:
                response = self.rewrite_response(request, response)
            return response

        response = super(HttpProxy, self).dispatch(request, *args, **kwargs)

        # content_type = response.headers['Content-Type']
        trailer = response.content[:100]
        if trailer.count('<') and trailer.lower().count('html'):
            if self.proxy_id and self.language_code:
                self.translate(response)
            else:
                if self.mode == 'record':
                    self.record(response)
                if self.rewrite:
                    response = self.rewrite_response(request, response)
            if self.rewrite_links:
                response = self.replace_links(response)
        return response

    def replace_links(self, response):
        response.content = response.content.replace(self.base_url, self.prefix)
        return response

    def translate(self, response):
        content = response.content
        if self.proxy:
            proxy = self.proxy
            site = self.site
        else:
            proxy = Proxy.objects.get(pk=self.proxy_id)
            site = proxy.site
        path = urlparse.urlparse(self.url).path
        webpages = Webpage.objects.filter(site=site, path=path).order_by('-created')
        if webpages:
            webpage = webpages[0]
            if not webpage.no_translate:
                content, has_translation = webpage.get_translation(self.language_code)
                if has_translation:
                    response.content = content
        return response

