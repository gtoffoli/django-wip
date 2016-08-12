# -*- coding: utf-8 -*-"""

import json
import urlparse
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from models import Site, Webpage, Proxy

def dummy(url, xpath):
    pass

@csrf_exempt
def send_block(request):
    """
    url: tells us from where the request was sent
    xpath: identifies the selected block
    """
    if not request.method == 'POST':
        return HttpResponseBadRequest()
    request_host = request.META.get('HTTP_HOST', '')
    print 'request_host: ', request_host
    json_data = json.loads(request.body)
    url = json_data.get('url', '') 
    xpath = json_data.get('xpath', '')
    print 'url: ', url
    print 'xpath: ', xpath

    # identify site and proxy
    proxy = site = None
    data = {}
    parsed_url = urlparse.urlparse(url)
    print 'parsed_url: ', parsed_url
    path = parsed_url.path
    splitted_path = path.split('/')
    print 'splitted_path: ', splitted_path
    if len(splitted_path) >= 3:
        path = '/' + '/'.join(splitted_path[3:])
        site_prefix = splitted_path[1]
        print 'site_prefix: ', site_prefix
        sites = Site.objects.filter(path_prefix=site_prefix)
        if sites.count()==1:
            site = sites[0]
            data['site'] = site.name
            language_code = splitted_path[2]
            print 'language_code: ', language_code
            proxies = Proxy.objects.filter(site=site, language_id=language_code)
            if proxies.count()==1:
                proxy = proxies[0]
                data['language'] = language_code
    if site and proxy:
        # fetch the page
        updated = site.fetch_page(path, extract_blocks=False, extract_block=xpath, verbose=True)
        data['updated_page'] = updated
        data['status'] = 'ok'
    else:
        data = { 'status': 'ko' }
    return HttpResponse(json.dumps(data), content_type='application/json')
