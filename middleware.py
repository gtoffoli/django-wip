import sys
from .models import Proxy

# see: https://stackoverflow.com/questions/42232606/django-exception-middleware-typeerror-object-takes-no-parameters
class ProxyMiddleware(object):

    if (sys.version_info > (3, 0)):
        def __init__(self, get_response):
            self.get_response = get_response
        def __call__(self, request):
            return self.get_response(request)

    def process_request(self, request):
        """
        Rewrites the proxy headers so that only the most
        recent proxy is used.
        for field in FORWARDED_FOR_FIELDS:
            if field in request.META:
                if ',' in request.META[field]:
                    parts = request.META[field].split(',')
                    request.META[field] = parts[-1].strip()
                    print request.META[field]
        """
        host = request.META.get('HTTP_HOST', '')
        for proxy in Proxy.objects.all():
            if proxy.host and host.count(proxy.host):
                request.urlconf = 'wip.proxy_urls'
                break
