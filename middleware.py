from models import Proxy

class ProxyMiddleware(object):

    def process_request(self, request):
        host = request.META.get('HTTP_HOST', ''),
        print host, request.path_info
        for proxy in Proxy.objects.all():
            if proxy.host == host:
                request.path_info = '/%s%s' % (proxy.base_path, request.path_info)
                break
