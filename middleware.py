from models import Proxy

"""
FORWARDED_FOR_FIELDS = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_FORWARDED_HOST',
        'HTTP_X_FORWARDED_SERVER',
    ]
"""
class ProxyMiddleware(object):

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
        # print host, request.path_info
        for proxy in Proxy.objects.all():
            if proxy.host == host:
                request.path_info = '/%s%s' % (proxy.base_path, request.path_info)
                break