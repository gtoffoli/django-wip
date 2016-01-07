# -*- coding: utf-8 -*-

import re
from httpproxy.views import HttpProxy

class WipHttpProxy(HttpProxy):
    prefix = ''
    rewrite_links = False

    def dispatch(self, request, url, *args, **kwargs):
        print 'url = ', url
        print 'prefix = ', self.prefix
        print 'rewrite_links = ', self.rewrite_links
        # return super(WipHttpProxy, self).dispatch(request, url, *args, **kwargs)
        self.url = url
        print 'original_request_path = ', request.path
        self.original_request_path = request.path
        print 'request = ', request
        request = self.normalize_request(request)
        print 'normalized_request = ', request
        if self.mode == 'play':
            response = self.play(request)
            # TODO: avoid repetition, flow of logic could be improved
            if self.rewrite:
                response = self.rewrite_response(request, response)
            return response

        response = super(HttpProxy, self).dispatch(request, *args, **kwargs)
        if self.mode == 'record':
            self.record(response)
        if self.rewrite:
            response = self.rewrite_response(request, response)
        if self.rewrite_links:
            response = self.replace_links(response)
        return response

    def replace_links(self, response):
        """
        """
        response.content = response.content.replace(self.base_url, self.prefix)
        return response

