# -*- coding: utf-8 -*-

import urlparse
from httpproxy.views import HttpProxy
from utils import strings_from_html, blocks_from_block, block_checksum
from models import Language, Site, Proxy, Webpage, PageVersion, TranslatedVersion, Block, TranslatedBlock

class WipHttpProxy(HttpProxy):
    prefix = ''
    rewrite_links = False
    proxy_id = ''
    language_code = ''

    def dispatch(self, request, url, *args, **kwargs):
        self.url = url
        self.original_request_path = request.path
        request = self.normalize_request(request)
        if self.mode == 'play':
            response = self.play(request)
            # TODO: avoid repetition, flow of logic could be improved
            if self.rewrite:
                response = self.rewrite_response(request, response)
            return response

        response = super(HttpProxy, self).dispatch(request, *args, **kwargs)
        """
        content_type = response.headers['Content-Type']
        """
        trailer = response.content[:100]
        if trailer.count('<') and trailer.lower().count('html'):
            print 'base_url: ', self.base_url
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
        language = Language.objects.get(code=self.language_code)
        proxy = Proxy.objects.get(pk=self.proxy_id)
        site = proxy.site
        path = '/%s' % urlparse.urlparse(self.url).path
        print 'path: ', path
        pages = Webpage.objects.filter(site=site, path=path).order_by('-created')
        if pages:
            print 'pages: ', list(pages)
            webpage=pages[0]
            versions = PageVersion.objects.filter(webpage=webpage).order_by('-time')
            if versions:
                print 'versions: ', list(versions)
                last_version = versions[0]
            translated_versions = TranslatedVersion.objects.filter(webpage=webpage, language=language).order_by('-modified')
            if translated_versions:
                print 'translated versions: ', list(translated_versions)
                last_translated = translated_versions[0]
            response.content = content
        return response

