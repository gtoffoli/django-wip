# -*- coding: utf-8 -*-"""

import sys
if (sys.version_info > (3, 0)):
    from urllib import parse as urlparse
else:
    import urlparse

import json
from lxml import html

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import Proxy, Site, Webpage, Block, BlockInPage
from .utils import text_to_list, element_signature

def dummy(url, xpath):
    pass

# try to find a WIP proxy from a page url
def url_to_proxy(url):
    parsed_url = urlparse.urlparse(url)
    path = parsed_url.path
    splitted_path = path.split('/')
    if len(splitted_path) >= 3:
        path = '/' + '/'.join(splitted_path[3:])
        site_prefix = splitted_path[1]
        sites = Site.objects.filter(path_prefix=site_prefix)
        if sites.count()==1:
            site = sites[0]
            language_code = splitted_path[2]
            proxies = Proxy.objects.filter(site=site, language_id=language_code)
            if proxies.count()==1:
                return proxies[0], path
    return None, ''

@login_required
@csrf_exempt
def send_fragment(request):
    """
    url: tells us from where the request was sent
    """
    if not request.method == 'POST':
        return HttpResponseBadRequest()
    json_data = json.loads(request.body.decode())
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
        data['status'] = 'ok'
        data['added'] = added
    else:
        data = { 'status': 'ko' }
    return HttpResponse(json.dumps(data), content_type='application/json')

@login_required
@csrf_exempt
def send_block(request):
    """
    url: tells us from where the request was sent
    xpath: identifies the selected block
    """
    if not request.method == 'POST':
        return HttpResponseBadRequest()
    json_data = json.loads(request.body.decode())
    url = json_data.get('url', '') 
    xpath = json_data.get('xpath', '')
    data = {}
    # identify site and proxy
    proxy, path = url_to_proxy(url)
    if proxy:
        data['site'] = proxy.site.name
        data['language'] = proxy.language_id
        # fetch the block in page page
        # updated = proxy.site.fetch_page(path, extract_blocks=False, extract_block=xpath, verbose=True)
        updated = proxy.site.fetch_page(path, xpath=xpath, verbose=True)
        data['updated_page'] = updated
        data['status'] = 'ok'
    else:
        data = { 'status': 'ko' }
    return HttpResponse(json.dumps(data), content_type='application/json')

@login_required
@csrf_exempt
def add_block(request):
    """
    url: tells us from where the request was sent
    xpath: identifies the selected block
    body: the body of the block itself
    """
    if not request.method == 'POST':
        return HttpResponseBadRequest()
    json_data = json.loads(request.body.decode())
    url = json_data.get('url', '') 
    xpath = json_data.get('xpath', '')
    body = json_data.get('body', '').strip()
    data = {}
    # identify site and proxy
    proxy, path = url_to_proxy(url)
    if proxy:
        site = proxy.site
        data['site'] = site.name
        data['language'] = proxy.language_id
        # look for a block with the same checksum
        doc = html.document_fromstring(body)
        top_els = doc.getchildren()
        block = None
        if len(top_els) == 1:
            el = top_els[0]
            checksum = element_signature(el)
            blocks = Block.objects.filter(site=site, checksum=checksum).order_by('-time')
            blocks = [b for b in blocks if b.body.strip()==body]
            if not len(blocks):
                block = Block(site=site, xpath=xpath, checksum=checksum, body=body, last_seen=timezone.now())
                block.save()
                webpages = Webpage.objects.filter(site=site, path=path)
                if webpages.count():
                    webpage = webpages[0]
                    data['webpage'] = webpage.id
                    variable_regions = [region.split() for region in text_to_list(site.variable_regions)]
                    variable_xpaths = [variable_region[1] for variable_region in variable_regions if variable_region[0]==path]
                    in_variable_xpath = False
                    for variable_xpath in variable_xpaths:
                        if xpath.startswith(variable_xpath):
                            in_variable_xpath = True
                            break
                    if not in_variable_xpath:
                        block_in_page = BlockInPage(block=block, xpath=xpath, webpage=webpage)
                        block_in_page.save()
            data['new_block'] = block and True or False
            data['status'] = 'ok'
        else:
            data = { 'status': 'ko' }
    else:
        data = { 'status': 'ko' }
    return HttpResponse(json.dumps(data), content_type='application/json')

@login_required
@csrf_exempt
def find_block(request):
    """
    url: tells us from where the request was sent
    xpath: identifies the selected block
    """
    if not request.method == 'POST':
        return HttpResponseBadRequest()
    json_data = json.loads(request.body.decode())
    url = json_data.get('url', '') 
    xpath = json_data.get('xpath', '')
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
