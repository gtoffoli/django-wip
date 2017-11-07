# -*- coding: utf-8 -*-"""

import sys
if (sys.version_info > (3, 0)):
    from urllib import parse as urlparse
else:
    import urlparse

import json

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt, requires_csrf_token
from .models import Proxy, Site, Webpage, BlockInPage

def dummy(url, xpath):
    pass

# try to find a WIP proxy from a page url
def url_to_proxy(url):
    parsed_url = urlparse.urlparse(url)
    # print ('parsed_url: ', parsed_url)
    path = parsed_url.path
    splitted_path = path.split('/')
    # print ('splitted_path: ', splitted_path)
    if len(splitted_path) >= 3:
        path = '/' + '/'.join(splitted_path[3:])
        site_prefix = splitted_path[1]
        # print ('site_prefix: ', site_prefix)
        sites = Site.objects.filter(path_prefix=site_prefix)
        if sites.count()==1:
            site = sites[0]
            language_code = splitted_path[2]
            # print ('language_code: ', language_code)
            proxies = Proxy.objects.filter(site=site, language_id=language_code)
            if proxies.count()==1:
                return proxies[0], path
    return None, ''

# @csrf_exempt
def send_fragment(request):
    """
    url: tells us from where the request was sent
    """
    if not request.method == 'POST':
        return HttpResponseBadRequest()
    request_host = request.META.get('HTTP_HOST', '')
    # print ('request_host: ', request_host)
    # json_data = json.loads(request.body)
    json_data = json.loads(request.body.decode())
    # print ('JSON data: ', json_data)
    url = json_data.get('url', '') 
    source = json_data.get('source', '')
    start = json_data.get('start', 0)
    end = json_data.get('end', 0)

    data = {}
    # identify site and proxy
    proxy, path = url_to_proxy(url)
    if proxy:
        site = proxy.site
        data['site'] = site.name
        data['language'] = proxy.language_id
        # add the fragment as a subsegment in the TM for the site at hand
        fragment = source[start:end]
        string, added = site.add_fragment(fragment, path=path)
        print('HTML fragment: ', fragment)
        data['status'] = 'ok'
        data['added'] = added
    else:
        data = { 'status': 'ko' }
    return HttpResponse(json.dumps(data), content_type='application/json')
send_fragment.csrf_exempt = True

# @csrf_exempt
def send_block(request):
    """
    url: tells us from where the request was sent
    xpath: identifies the selected block
    """
    if not request.method == 'POST':
        return HttpResponseBadRequest()
    request_host = request.META.get('HTTP_HOST', '')
    # print ('request_host: ', request_host)
    # json_data = json.loads(request.body)
    json_data = json.loads(request.body.decode())
    url = json_data.get('url', '') 
    xpath = json_data.get('xpath', '')
    # print ('url: ', url)
    # print ('xpath: ', xpath)

    data = {}
    # identify site and proxy
    proxy, path = url_to_proxy(url)
    if proxy:
        data['site'] = proxy.site.name
        data['language'] = proxy.language_id
        # fetch the page
        updated = proxy.site.fetch_page(path, extract_blocks=False, extract_block=xpath, verbose=True)
        data['updated_page'] = updated
        data['status'] = 'ok'
    else:
        data = { 'status': 'ko' }
    return HttpResponse(json.dumps(data), content_type='application/json')
send_block.csrf_exempt = True

# @csrf_exempt
def find_block(request):
    """
    url: tells us from where the request was sent
    xpath: identifies the selected block
    """
    if not request.method == 'POST':
        return HttpResponseBadRequest()
    request_host = request.META.get('HTTP_HOST', '')
    # print ('request_host: ', request_host)
    # json_data = json.loads(request.body)
    json_data = json.loads(request.body.decode())
    url = json_data.get('url', '') 
    xpath = json_data.get('xpath', '')
    # print ('url: ', url)
    # print ('xpath: ', xpath)

    data = { 'status': 'ko' }
    # identify site and proxy
    proxy, path = url_to_proxy(url)
    if proxy:
        site = proxy.site
        data['site'] = site.name
        data['language'] = proxy.language_id
        # find the page
        webpages = Webpage.objects.filter(site=site, path=path)
        if webpages.count():
            webpage = webpages[0]
            data['webpage'] = webpage.id
            blocks_in_page = BlockInPage.objects.filter(webpage=webpage, xpath=xpath).order_by('-time') 
            if blocks_in_page.count():
                block = blocks_in_page[0].block
                data['block'] = block.id
                data['status'] = 'ok'
    return HttpResponse(json.dumps(data), content_type='application/json')
find_block.csrf_exempt = True
