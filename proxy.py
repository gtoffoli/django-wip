# -*- coding: utf-8 -*-

from httpproxy.views import HttpProxy

class WipHttpProxy(HttpProxy):
    prefix = ''
    rewrite_links = False

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
