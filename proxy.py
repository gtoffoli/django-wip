# -*- coding: utf-8 -*-

import sys
if (sys.version_info > (3, 0)):
    from urllib import parse as urlparse
    from urllib import error
else:
    import urlparse

import os
import re
import datetime
import logging

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic.base import ContextMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.cache import patch_response_headers
from django.core.cache import caches
from django.conf import settings
from httpproxy.views import HttpProxy
from revproxy.views import ProxyView as RevProxy
from revproxy.response import  get_django_response
import revproxy
revproxy.MIN_STREAMING_LENGTH = 1024 * 1024 * 1024 #  4 * 1024  # 4KB

from .models import Site, Proxy, Webpage
from .models import url_to_site_proxy

from lxml import etree
from lxml.etree import tostring
from repoze.xmliter.serializer import XMLSerializer
from repoze.xmliter.utils import getHTMLSerializer
from diazo.wsgi import DiazoMiddleware
from diazo.utils import quote_param
from diazo.compiler import compile_theme
from django_diazo.settings import DOCTYPE
# from django_diazo.utils import get_active_theme, check_themes_enabled, should_transform
if settings.PROXY_APP == 'revproxy':
    from io import StringIO
    from django.template.base import Template
    from diazo.compiler import compile_theme
    from revproxy.transformer import DiazoTransformer
    from revproxy.utils import get_charset, is_html_content_type


REWRITE_REGEX = re.compile(r'((?:src|action|href)=["\'])/(?!\/)')
# REWRITE_REGEX = re.compile(r'((?:action)=["\'])/(?!\/)')
# RESOURCES_REGEX = re.compile(r'(\.(css|js|png|jpg|gif|pdf|ppt|pptx|doc|docx|xls|xslx|odt|woff))', re.IGNORECASE)
RESOURCES_REGEX = re.compile(r'(\.(css|js|png|jpg|gif|pdf|ppt|pptx|doc|docx|xls|xslx|odt|woff|ttf))', re.IGNORECASE)
BODY_REGEX = re.compile(r'(\<body.*?\>)', re.IGNORECASE)

# hreflang_template = '<%s>; rel="alternate"; hreflang="%s"'

info = {
  'en': """
<div style="text-align: center;">%sThis is an experimental partial translation of the website <a href="%s">%s</a></div>""",
  'es': """
<div style="text-align: center;">%sEsta es una traducción experimental y parcial del sitio web <a href="%s">%s</a></div>""",
  'ar': """
<div style="direction: rtl;">%s هذه ترجمة جزئية تجريبية للموقع <a href="%s">%s</a></div>""",
}

class WipHttpProxy(HttpProxy):
    """ subclasses httpproxy.views.HttpProxy in order to reuse auxiliary methods, such as record and play:
        main ones (dispatch and rewrite_response) are completely redefined """

    # new class attributes
    prefix = ''
    site_id = ''
    proxy_id = ''
    language_code = ''
    proxy = None

    def __init__(self, *args,**kwargs):
        """ see __init__ method of DjangoDiazoMiddleware in module django_diazo.middleware """
        super(WipHttpProxy, self).__init__(*args,**kwargs)
        self.app = None
        self.theme_id = None
        self.diazo = None
        self.transform = None
        self.params = {}
        self.log = logging.getLogger('wip')
        self.log.info("WipHttpProxy created")

    @csrf_exempt
    def dispatch(self, request, url, *args, **kwargs):
        """ redefines the dispatch method of httpproxy.views.HttpProxy """
        # anticipating next 3 statements from method of superclass shouldn't harm
        self.url = url
        self.original_request_path = request.path
        self.log.info('original_request_path: %s', request.path)
        request = self.normalize_request(request)
        self.log.info('request_path: %s', request.path)

        # new stuff below concerns proxies and sites in the WIP model
        self.host = self.request.get_host() # Returns the originating host of the request using information from the HTTP_X_FORWARDED_HOST (if USE_X_FORWARDED_HOST is enabled) and HTTP_HOST headers, in that order
        self.online = False
        for proxy in Proxy.objects.all():
            # if proxy.host and self.host.count(proxy.host):
            if proxy.host and self.host.count(proxy.host) and proxy.language_id==self.language_code:
                self.proxy = proxy
                self.proxy_id = proxy.id
                self.language_code = proxy.language.code
                site = proxy.site
                self.site = site
                self.base_url = site.url
                self.online = True
                break
        if not self.proxy:
            if self.proxy_id:
                self.proxy = proxy = Proxy.objects.get(pk=self.proxy_id)
                self.site = site = proxy.site
                self.base_url = site.url
            elif self.site_id:
                self.site = site = Site.objects.get(pk=self.site_id)

        """ removed tests on mode=='play' and mode=='record' (see http_proxy) """

        # 1st part of stuff below concerns caching of "resources", such as media files - CAN RETURN
        key = '%s-%s' % (proxy.site.path_prefix, url)
        should_cache_resource = False
        resource_match = RESOURCES_REGEX.search(url)
        if resource_match is not None:
            resources_cache = caches['resources']
            cached_response = resources_cache.get(key, None)
            if cached_response:
                cache_seconds = 7 * 24 * 3600
                patch_response_headers(cached_response, cache_timeout=cache_seconds)
                return cached_response
            else:
                should_cache_resource = True

        try:
            response = super(HttpProxy, self).dispatch(request, *args, **kwargs) # <----- call method of superclass
        except error.HTTPError as e:
            response_body = e.read()
            status = e.code
            # return HttpResponse(response_body, status=status)
            response = HttpResponse(response_body, status=status)

        # 2-nd part of stuff below concerns caching of "resources", such as media files - CAN RETURN
        if resource_match is not None:
            cache_seconds = 7 * 24 * 3600
            patch_response_headers(response, cache_timeout=cache_seconds)
        if should_cache_resource:
            resources_cache.set(key, response)
            return response

        # handle requests for robots.txt
        parsed_url = urlparse.urlparse(url)
        self.path = parsed_url.path
        if self.proxy and self.path == 'robots.txt':
            response.content = self.proxy.robots_txt.encode('utf-8')
            return response

        # apply various transformations on the response content only if the "html" tag is found at the beginning (?)
        trailer = response.content[:100]
        # if trailer.count('<') and trailer.lower().count('html'):
        if trailer.count('<'.encode('utf-8')) and trailer.lower().count('html'.encode('utf-8')):
            self.content = response.content.decode('utf-8')

            # DIAZO transform
            self.transform_response(request, response)

            # apply specific proxy-translation transformation
            if self.proxy_id and self.language_code:
                # self.translate_response(request)
                self.translate_response(request, path=self.path)

            # test on self.rewrite
            if self.rewrite:
                self.rewrite_response(request)
                self.replace_links()
                self.fix_body_top(request)
                self.fix_body_bottom()

            if self.proxy:
                self.add_language_links()
                self.add_locale_switch()
                self.test_locale_switch()

            response.content = self.content.encode('utf-8')

        return response

    def add_language_links(self):
        CANONICAL_REGEX = re.compile(r'\<link\s+rel="canonical"\s+href=".+?"\s*?\/?\>', re.IGNORECASE)
        links = []
        canonical_url = '%s/%s' % (self.site.url, self.path)
        canonical_link_match = CANONICAL_REGEX.search(self.content)
        if canonical_link_match:
            # pointers to replace original canonical link
            pointer_1 = canonical_link_match.start()
            pointer_2 = canonical_link_match.end()
        else:
            # pointers after <head> opening tag
            HEAD_REGEX = re.compile(r'\<head\>', re.IGNORECASE)
            head_match = HEAD_REGEX.search(self.content)
            pointer_1 = pointer_2 = head_match.end()
        # append new canonical link
        canonical_link = '<link rel="canonical" href="%s">' % canonical_url
        links.append(canonical_link)
        # append alternate link for canonical language
        links.append('<link rel="alternate" hreflang="%s" href="%s" />' % (self.site.language_id, canonical_url))
        for proxy in Proxy.objects.filter(site=self.site):
            alternate_url = '%s/%s' % (proxy.get_url(), self.path)
            # append alternate link for other language
            links.append('<link rel="alternate" hreflang="%s" href="%s" />' % (proxy.language_id, alternate_url))
        self.content = self.content[:pointer_1] + ''.join(links) + self.content[pointer_2:]
        # replace the value of the language attribute in the <html> opening tag
        LANG_REGEX = re.compile(r'(<html\s+lang=")((?:\w|-){2,5})(".*?\>)', re.IGNORECASE)
        self.content = LANG_REGEX.sub(r'\1%s\3' % self.proxy.language_id, self.content)

    def fix_body_top(self, request):
        """ add top message """
        site_url = self.base_url
        extra = ''
        if request.user.is_superuser:
            webpages = Webpage.objects.filter(site=self.site, path=self.path).order_by('-created')
            if webpages:
                extra = '<a href="/page/%s/">@</a> ' % webpages[0].id
        if self.proxy and self.online:
            self.content = BODY_REGEX.sub(r'\1' + info[self.language_code] % (extra, site_url, site_url.split('//')[1]), self.content)

    def fix_body_bottom(self):
        """ currently used to execute javascript on ready """
        if self.site.extra_body:
            self.content = self.content.replace('</body>', '\n%s\n</body>' % self.site.extra_body)

    def transform_response(self, request, response):
        """ see process_response method of DjangoDiazoMiddleware in module django_diazo.middleware
        Transform the response with Diazo if transformable
        """
        theme = self.site.get_active_theme(request)
        if not theme:
            return response
        content = response
        rules_file = os.path.join(theme.theme_path(), 'rules.xml')
        compiled_file = os.path.join(theme.theme_path(), 'compiled.xsl')
        if not os.path.exists(compiled_file) or theme.debug:
            self.theme_id = theme.id
            read_network = False
            access_control = etree.XSLTAccessControl(read_file=True, write_file=False, create_dir=False, read_network=read_network, write_network=False)
            theme_parser = etree.HTMLParser()
            rules_parser = etree.XMLParser(recover=False)
            compiled_theme = compile_theme(
                rules_file,
                theme=None,
                includemode='document',
                access_control=access_control,
                read_network=read_network,
                parser=theme_parser,
                rules_parser=rules_parser,
                xsl_params={})
            out_file = open(compiled_file, 'w')
            # out_file.write(etree.tostring(compiled_theme))
            out_file.write(etree.tostring(compiled_theme).decode('utf-8'))
            out_file.close()
        else:
            in_file = open(compiled_file, 'r')
            compiled_theme = etree.fromstring(in_file.read())
            in_file.close
        self.transform = etree.XSLT(compiled_theme)
        if isinstance(response, etree._Element):
            response = HttpResponse()
        else:
            parser = etree.HTMLParser(remove_blank_text=True, remove_comments=True)
            content = etree.fromstring(response.content, parser)
        result = self.transform(content, **self.params)
        response.content = XMLSerializer(result, doctype=DOCTYPE).serialize()
        if isinstance(response, etree._Element):
            response = HttpResponse('<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(content))
        return response

    def translate_response(self, request, path=''):
        if self.proxy:
            proxy = self.proxy
            site = self.site
        else:
            proxy = Proxy.objects.get(pk=self.proxy_id)
            site = proxy.site
        path = urlparse.urlparse(self.url).path
        transformed = False
        if request.GET or request.POST:
            # self.content, transformed = proxy.translate_page_content(self.content)
            self.content, transformed = proxy.translate_page_content(self.content, proxy=self.proxy, path=path)
        else:
            if not proxy.enable_live_translation:
                webpages = Webpage.objects.filter(site=site, path=path).order_by('-created')
                if webpages:
                    webpage = webpages[0]
                    if not webpage.no_translate:
                        self.content, transformed = webpage.get_translation(self.language_code)
            if not transformed and proxy.enable_live_translation:
                # self.content, transformed = proxy.translate_page_content(self.content, online=self.online)
                self.content, transformed = proxy.translate_page_content(self.content, online=self.online, proxy=self.proxy, path=path)
        self.content = proxy.replace_fragments(self.content, path)

    def replace_links(self):
        """
        Rewrites unconditionally the links in the HTML
        removing the base url of the original site (if any) when in online mode
        or replacing it with the proxy prefix
        """
        if self.online:
            if self.proxy and self.site.url.count(self.proxy.host):
                self.content = self.content.replace(self.base_url, '%s/%s' % (self.base_url, self.language_code))
                """
                ex: if https://www.linkroma.it includes www.linkroma.it
                    replace https://www.linkroma.it/sviluppo-applicazioni-web/
                       with https://www.linkroma.it/en/sviluppo-applicazioni-web/
                """
            else:
                self.content = self.content.replace(self.base_url, '')
                """
                ex: if http://www.scuolemegranti.org doesn't include en.scuolemigranti.it
                    replace http://www.scuolemegranti.org/rete/
                       with /rete/
                """
        else:
            self.content = self.content.replace(self.base_url, self.prefix)
            """
            ex: replace http://www.scuolemegranti.org/rete/ with /sm/en/rete/
            """
 
    """ (for <script> json code ..)
    print ('--- replace_links')
    print ('{0} -> {1}'.format(self.base_url, self.prefix))
    base_url = self.base_url.replace('/', '\\/')
    prefix = self.prefix.replace('/', '\\/')
    print ('{0} -> {1}'.format(base_url, prefix))
    self.content = self.content.replace(base_url, prefix)
    """

    def rewrite_response(self, request):
        """
        Rewrites the response to fix references to resources loaded from HTML files (images, etc.).
        .. original note:
            The rewrite logic uses a fairly simple regular expression to look for
            "src", "href" and "action" attributes with a value starting with "/"
            – your results may vary.
        proxy_root = self.original_request_path.rsplit(request.path, 1)[0] # example: /link/en
        self.content = REWRITE_REGEX.sub(r'\1{}/'.format(proxy_root), self.content)
        response.content = REWRITE_REGEX.sub(r'\1{}/'.format(proxy_root), response.content)
        return response
        """
        if self.online:
            if self.proxy and self.site.url.count(self.proxy.host): # example: https://www.linkroma.it and https://www.linkroma.it/en
                proxy_root = '/' + self.proxy.language_id
                self.content = REWRITE_REGEX.sub(r'\1{}/'.format(proxy_root), self.content)
            else:  # example: http://www.scuolemigranti.org and en.scuolemigranti.eu
                proxy_root = ''
        else: # example: /link/en
            proxy_root = self.original_request_path.rsplit(request.path, 1)[0] # example: /link/en
            self.content = REWRITE_REGEX.sub(r'\1{}/'.format(proxy_root), self.content)
        self.log.info('proxy_root: %s', proxy_root)
 
        """
        # next coded added by GT: possibly add a link to the WIP site
        site_url = self.base_url
        extra = ''
        if request.user.is_superuser:
            webpages = Webpage.objects.filter(site=self.site, path=self.path).order_by('-created')
            if webpages:
                extra = '<a href="/page/%s/">@</a> ' % webpages[0].id
        if self.proxy and self.online:
            self.content = BODY_REGEX.sub(r'\1' + info[self.language_code] % (extra, site_url, site_url.split('//')[1]), self.content)
        """

    def add_locale_switch(self):
        locale_switch = get_locale_switch(self.request, is_view=False, original_path=self.original_request_path)
        self.content = self.content.replace('</body>', '\n{}</body>'.format(locale_switch))

    def test_locale_switch(self):
        if self.online:
            html = '<div><a href="https://wip.fairvillage.eu/get_locale_switch/">test locale switch</a></div>'
        else:
            html = '<div><a href="http://localhost:8000/get_locale_switch/">test locale switch</a></div>'
        self.content = self.content.replace('</body>', '\n{}</body>'.format(html))

def get_locale_switch(request, is_view=True, original_path=''):
    """ could be an ajax request sent by original or translated page """
    if is_view:
        referer = request.META.get('HTTP_REFERER')
        parsed_referer = urlparse.urlparse(referer)
        host = parsed_referer.hostname
        path = parsed_referer.path
        site, proxy, path = url_to_site_proxy(host, path)
    else:
        host = request.get_host()
        site, proxy, path = url_to_site_proxy(host, original_path)
    script = """<script id="wip_locale_script">
function toggle_language(id) {
    el = document.getElementById(id);
    if (el.style.visibility == 'hidden') el.style.visibility = 'visible';
    else el.style.visibility = 'hidden';
}
"""
    function_toggle = 'function toggle_languages() {\n'
    html = '<ul id="wip_locale_switch" style="list-style: none; position: absolute; top: 100; left: auto; right: 0; overflow: hidden;" onclick="hide_languages();">\n'
    code = site.language_id
    label = code.upper()
    title = settings.LANGUAGES_DICT[code]
    if proxy:
        display = ' visibility: hidden;'
        background = ' background-color: darkgrey;'
        base_url = site.url
        a = '<a style="color: white;" target="_top" href="{0}/{1}" title="{2}">{3}</a>'.format(base_url, path, title, label)
        function_toggle += 'toggle_language("ls_{}");\n'.format(label)
    else:
        display = ' visibility: visible;'
        background = ' background-color: dimgrey;'
        a = """<a style="font-weight: bold; color: white;" onmouseover="toggle_languages();" title="{0}>{1}</a>""".format(title, label)
    html += '<li id="ls_{0}" style="height: 32px; width: 32px; background-color: dimgrey; text-align: center; margin: 0; {1}{2}">{3}</li>\n'.format(label, display, background, a)
    proxies = Proxy.objects.filter(site=site).order_by('language__code')
    for p in proxies:
        language = p.language
        code = language.code
        label = code.upper()
        title = settings.LANGUAGES_DICT[code]
        if p == proxy:
            display = ' visibility: visible;'
            background = ' background-color: dimgrey;'
            a = """<a style="font-weight: bold; color: white;" onmouseover="toggle_languages();" title="{0}">{1}</a>""".format(title, label)
        else:
            display = ' visibility: hidden;'
            background = ' background-color: darkgrey;'
            base_url = p.get_url()
            a = '<a style="color: white;" target="_top" href="{0}/{1}" title="{2}" >{3}</a>'.format(base_url, path, title, label)
            function_toggle += '    toggle_language("ls_{}");\n'.format(label)
        html += '<li id="ls_{0}" style="height: 32px; width: 32px; background-color: dimgrey; text-align: center; margin: 0; {1}{2}">{3}</li>\n'.format(label, display, background, a)
    html += '</ul>\n'
    function_toggle += '}\n'
    script +=  function_toggle + '</script>\n'
    locale_switch = script + html
    if is_view:
        return HttpResponse(locale_switch, content_type='text/plain')
    else:
        return locale_switch

class WipRevProxy(RevProxy, ContextMixin):
    html5 = False

    # new class attributes
    prefix = ''
    site_id = ''
    proxy_id = ''
    language_code = ''
    proxy = None


    def __init__(self, *args,**kwargs):
        """ see __init__ method of DjangoDiazoMiddleware in module django_diazo.middleware """
        super(WipRevProxy, self).__init__(*args,**kwargs)
        self.log = logging.getLogger('wip')
        time_stamp = datetime.datetime.now().strftime('%y%m%d-%H-%M-%S')
        self.log.info("WipRevProxy created: %s", time_stamp)


    def dispatch(self, request, path):
        """ redefines the dispatch method of revproxy.views.ProxyView """

        # custom stuff
        self.url = path
        self.original_request_path = request.path
        parsed_url = urlparse.urlparse(path)
        self.path = parsed_url.path

 
        self.request_headers = self.get_request_headers()

        redirect_to = self._format_path_to_redirect(request)
        if redirect_to:
            return redirect(redirect_to)

        proxy_response = self._created_proxy_response(request, path)

        self._replace_host_on_redirect_location(request, proxy_response)
        self._set_content_type(request, proxy_response)

        # custom stuff below concerns proxies and sites in the WIP model
        self.host = self.request.get_host() # Returns the originating host of the request using information from the HTTP_X_FORWARDED_HOST (if USE_X_FORWARDED_HOST is enabled) and HTTP_HOST headers, in that order
        self.online = False
        for proxy in Proxy.objects.all():
            if proxy.host and self.host.count(proxy.host):
                self.proxy = proxy
                self.proxy_id = proxy.id
                self.language_code = proxy.language.code
                site = proxy.site
                self.site = site
                self.base_url = site.url
                self.online = True
                break
        if not self.proxy:
            if self.proxy_id:
                self.proxy = proxy = Proxy.objects.get(pk=self.proxy_id)
                self.site = site = proxy.site
                self.base_url = site.url
            elif self.site_id:
                self.site = site = Site.objects.get(pk=self.site_id)
                self.base_url = site.url
        self.log.info("request host: %s", self.host)
        if self.proxy:
            self.log.info("host: %s", self.proxy.host)
        self.log.info("prefix: %s", str(self.prefix))
        self.log.info("base_url: %s", self.base_url)
        self.log.info("online: %s", str(self.online))

        # 1st part of custom stuff below concerns caching of "resources", such as media files - CAN RETURN
        key = '%s-%s' % (proxy.site.path_prefix, path)
        should_cache_resource = False
        resource_match = RESOURCES_REGEX.search(path)
        if resource_match is not None:
            resources_cache = caches['resources']
            cached_response = resources_cache.get(key, None)
            if cached_response:
                cache_seconds = 7 * 24 * 3600
                patch_response_headers(cached_response, cache_timeout=cache_seconds)
                return cached_response
            else:
                should_cache_resource = True

        response = get_django_response(proxy_response,
                                       strict_cookies=self.strict_cookies)

        # 2-nd part of custom stuff below concerns caching of "resources", such as media files - CAN RETURN
        if resource_match is not None:
            cache_seconds = 7 * 24 * 3600
            patch_response_headers(response, cache_timeout=cache_seconds)
        if should_cache_resource:
            resources_cache.set(key, response)
            return response

        # custom: apply various transformations on the response content only if the "html" tag is found at the beginning (?)
        if hasattr(response, 'content'):
            trailer = response.content[:100]
            if trailer.count('<'.encode('utf-8')) and trailer.lower().count('html'.encode('utf-8')):

                # apply DIAZO transform
                theme = self.site.get_active_theme(request)
                if theme:
                    self.log.info("apply theme: %s", theme.name)
                    response = self.transform_response(request, response)
    
                # apply specific proxy-translation transformation
                self.content = response.content.decode('utf-8')
                if self.proxy_id and self.language_code:
                    self.log.info("translate to language: %s", self.language_code)
                    self.translate_response(request)
    
                self.replace_links()
                self.rewrite_response(request)
                response.content = self.content.encode('utf-8')

        self.log.debug("RESPONSE RETURNED: %s", response)
        return response

    def transform_response(self, request, response):
        theme = self.site.get_active_theme(request)
        if not theme:
            return response
        rules_filename = os.path.join(theme.theme_path(), 'rules.xml')
        theme_filename = os.path.join(theme.theme_path(), 'theme.html')
        self.log.info("theme and rules from: %s and %s", theme_filename, rules_filename)
        with open(theme_filename, encoding='utf-8') as f:
            theme = f.read()

        context_data = self.get_context_data()
        diazo = DiazoTransformer(request, response)
        response = diazo.transform(rules_filename, theme_filename,
                                   self.html5, context_data, theme=theme)
        return response

WipRevProxy.translate_response = WipHttpProxy.translate_response
WipRevProxy.replace_links = WipHttpProxy.replace_links
WipRevProxy.rewrite_response = WipHttpProxy.rewrite_response
