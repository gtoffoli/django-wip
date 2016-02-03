# -*- coding: utf-8 -*-"""

"""
Django views for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

try:
    import cPickle as pickle
except:
    import pickle

import os
import re
import StringIO
from lxml import html, etree
from scrapy.spiders import Rule #, CrawlSpider
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerProcess

from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404

from models import Site, Proxy, Webpage, PageVersion, Block, BlockInPage #, TranslatedVersion
from spiders import WipSiteCrawlerScript, WipCrawlSpider

from settings import DATA_ROOT, RESOURCES_ROOT, tagger_filename, BLOCK_TAGS
from utils import strings_from_html, blocks_from_block, block_checksum
import srx_segmenter

def home(request):
    var_dict = {}
    return render_to_response('homepage.html', var_dict, context_instance=RequestContext(request))

def sites(request):
    var_dict = {}
    sites = Site.objects.all()
    var_dict['sites'] = sites
    return render_to_response('sites.html', var_dict, context_instance=RequestContext(request))

def proxies(request):
    var_dict = {}
    proxies = Proxy.objects.all()
    var_dict['proxies'] = proxies
    return render_to_response('proxies.html', var_dict, context_instance=RequestContext(request))

def site(request, site_slug):
    site = get_object_or_404(Site, slug=site_slug)
    var_dict = {}
    var_dict['site'] = site
    proxies = Proxy.objects.filter(site=site)
    var_dict['proxies'] = proxies
    page_count = Webpage.objects.filter(site=site).count()
    var_dict['page_count'] = page_count
    return render_to_response('site.html', var_dict, context_instance=RequestContext(request))

def site_crawl(site_pk):
    crawler = WipSiteCrawlerScript()
    site = Site.objects.get(pk=site_pk)
    crawler.crawl(
      site.id,
      site.slug,
      site.name,
      site.get_allowed_domains(),
      site.get_start_urls(),
      site.get_deny()
      )

def site_crawl_by_slug(request, site_slug):
    site = get_object_or_404(Site, slug=site_slug)
    notask = request.GET.get('notask', False)
    if notask:
        site_name = site.name
        allowed_domains = site.get_allowed_domains()
        start_urls = site.get_start_urls()
        deny = site.get_deny()
        rules = [Rule(LinkExtractor(deny=deny), callback='parse_item', follow=True),]
        spider_class = type(str(site_slug), (WipCrawlSpider,), {'site_id': site.id, 'name':site_name, 'allowed_domains':allowed_domains, 'start_urls':start_urls, 'rules': rules})
        spider = spider_class()
        process = CrawlerProcess()
        process.crawl(spider)
        process.start() # the script will block here until the crawling is finished
        process.stop()
    else:
        print 'site_crawl_by_slug : ', site_slug
        """
        crawl_site.apply_async(args=(site.id,))
        """
        t = crawl_site.delay(site.id)
        print 'task id: ', t
    # return home(request)
    return HttpResponseRedirect('/site/%s/' % site_slug)

from celery.utils.log import get_task_logger
from celery_apps import app

@app.task()
def crawl_site(site_pk):
    logger = get_task_logger(__name__)
    logger.info('Crawling site {0}'.format(site_pk))
    return site_crawl(site_pk)

"""
@app.task(ignore_result=True)
def my_task(request):
    print('executing my_task')
    logger = get_task_logger(__name__)
    logger.debug('executing my_task')
    var_dict = {}
    return render_to_response('homepage.html', var_dict, context_instance=RequestContext(request))
"""

def site_pages(request, site_slug):
    var_dict = {}
    site = get_object_or_404(Site, slug=site_slug)
    var_dict['site'] = site
    pages = Webpage.objects.filter(site=site)
    var_dict['pages'] = pages
    var_dict['page_count'] = pages.count()
    return render_to_response('pages.html', var_dict, context_instance=RequestContext(request))

"""
def proxy(request, proxy_slug):
    proxy = get_object_or_404(Proxy, slug=proxy_slug)
    var_dict = {}
    var_dict['proxy'] = proxy
    return render_to_response('proxy.html', var_dict, context_instance=RequestContext(request))
"""

def page(request, page_id):
    var_dict = {}
    var_dict['page'] = page = get_object_or_404(Webpage, pk=page_id)
    var_dict['site'] = site = page.site
    var_dict['page_count'] = Webpage.objects.filter(site=site).count()
    var_dict['scans'] = PageVersion.objects.filter(webpage=page).order_by('-time')
    return render_to_response('page.html', var_dict, context_instance=RequestContext(request))

srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
srx_rules = srx_segmenter.parse(srx_filepath)
italian_rules = srx_rules['Italian']
# print italian_rules
segmenter = srx_segmenter.SrxSegmenter(italian_rules)
re_parentheses = re.compile(r'\(([^)]+)\)')

def page_scan(request, fetched_id, language='it'):
    tag = request.GET.get('tag', False)
    chunk = request.GET.get('chunk', False)
    ext = request.GET.get('ext', False)
    if tag or chunk or ext:
        tagger = NltkTagger(language=language, tagger_input_file=os.path.join(DATA_ROOT, tagger_filename))
    if chunk or ext:
        chunker = NltkChunker(language='it')
    var_dict = {} 
    var_dict['scan'] = fetched = get_object_or_404(PageVersion, pk=fetched_id)
    var_dict['page'] = page = fetched.webpage
    var_dict['site'] = site = page.site
    page = fetched.webpage
    if page.encoding.count('html'):
        if request.GET.get('npr', False):
            pass
        elif request.GET.get('region', False):
            region = page.get_region()
            var_dict['text_xpath'] = region and region.root
            var_dict['page_text'] = region and region.full_text.replace("\n"," ") or ''
        elif request.GET.get('strings', False):
            var_dict['strings'] = [s for s in strings_from_html(fetched.body)]
        else:
            strings = []
            tags = []
            chunks = []
            for string in strings_from_html(fetched.body):
                string = string.replace(u"\u2018", "'").replace(u"\u2019", "'")
                # string = filter_unicode(string)
                if string.count('window') and string.count('document'):
                    continue
                if tag or chunk:
                    tagged_tokens = tagger.tag(text=string)
                    if tag:
                        tags.extend(tagged_tokens)
                if chunk:
                    noun_chunks = chunker.main_chunker(tagged_tokens, chunk_tag='NP')
                    chunks.extend(noun_chunks)
                    """
                    for chunk in noun_chunks:
                        print chunk
                    """
                if not (tag or chunk):
                    matches = []
                    if string.count('(') and string.count(')'):
                        matches = re_parentheses.findall(string)
                        if matches:
                            print matches
                            for match in matches:
                                string = string.replace('(%s)' % match, '')
                    strings.extend(segmenter.extract(string)[0])
                    for match in matches:
                        strings.extend(segmenter.extract(match)[0])
                    if ext:
                        terms = extract_terms(string, language=language, tagger=tagger, chunker=chunker)
                        terms = ['- %s -' % term for term in terms]
                        strings.extend(terms)
            var_dict['strings'] = strings
            var_dict['tags'] = tags
            var_dict['chunks'] = chunks
    return render_to_response('page_scan.html', var_dict, context_instance=RequestContext(request))

import nltk
from wip.wip_nltk.corpora import NltkCorpus
from wip.wip_nltk.taggers import NltkTagger
from wip.wip_nltk.chunkers import NltkChunker
from wip.wip_nltk.util import filter_unicode

tagged_corpus_id = 'itwac'
file_ids = ['ITWAC-1.xml']
tagger_types = ['BigramTagger', 'UnigramTagger', 'AffixTagger', 'DefaultTagger',]
# default_tag = 'NOUN'
default_tag = None
filename = 'tagger'

def create_tagger(request, language='it', filename=''):
    corpus_loader = getattr(nltk.corpus, tagged_corpus_id)
    tagged_corpus = NltkCorpus(corpus_loader=corpus_loader, language=language)
    tagged_sents = tagged_corpus.corpus_loader.tagged_sents(fileids=file_ids, simplify_tags=True)
    tagger = NltkTagger(language=language, tagger_types=tagger_types, default_tag=default_tag, train_sents=tagged_sents)
    tagger.train()
    data = pickle.dumps(tagger.tagger)
    if not filename:
        filename = '.'.join(file_ids)
    ext = '.pickle'
    if not filename.endswith(ext):
        filename += ext
    if request.GET.get('auto', False):
        filepath = os.path.join(DATA_ROOT, filename)
        f = open(filepath, 'wb')
        f.write(data)
        return HttpResponseRedirect('/')
    else:
        content_type = 'application/octet-stream'
        response = HttpResponse(data, content_type=content_type)
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response

def extract_terms(text, language='it', tagger=None, chunker=None):
    if text.startswith(u'\ufeff'):
        text = text[1:]
    if not tagger:
        tagger = NltkTagger(language=language, tagger_input_file=os.path.join(DATA_ROOT, tagger_filename))
    tagged_tokens = tagger.tag(text=text)
    if not chunker:
        chunker = NltkChunker(language='it')
    noun_chunks = chunker.main_chunker(tagged_tokens, chunk_tag='NP')
    phrases = []
    for chunk in noun_chunks:
        """
        tag = chunk[0][1].split(u':')[0]
        if tag in [u'ART', u'ARTPRE', 'DET']:
            chunk = chunk[1:]
            tag = chunk[0][1].split(u':')[0]
            if tag in ['DET']:
                chunk = chunk[1:]
        """
        # phrase = u' '.join([tagged_token[0] for tagged_token in chunk])
        phrase = ' '.join([tagged_token[0] for tagged_token in chunk])
        phrases.append(phrase)
    return phrases

def extract_blocks(page_id):
    page = Webpage.objects.get(pk=page_id)
    site = page.site
    versions = PageVersion.objects.filter(webpage=page).order_by('-time')
    if not versions:
        return None
    last_version = versions[0]
    html_string = last_version.body
    """
    tree = html.fromstring(string)
    body = tree.find('body')
    """
    """
    parser = etree.HTMLParser()
    tree   = etree.parse(StringIO.StringIO(html_string), parser)
    root = tree.getroot()
    """
    # http://stackoverflow.com/questions/1084741/regexp-to-strip-html-comments
    html_string = re.sub("(<!--(.*?)-->)", "", html_string, flags=re.MULTILINE)
    doc = html.document_fromstring(html_string)
    tree = doc.getroottree()
    top_els = doc.getchildren()
    n_1 = n_2 = n_3 = 0
    for top_el in top_els:
        for el in blocks_from_block(top_el):
            if el.tag in BLOCK_TAGS:
                n_1 += 1
                xpath = tree.getpath(el)
                checksum = block_checksum(el)
                blocks = Block.objects.filter(site=site, xpath=xpath, checksum=checksum)
                if blocks:
                    block = blocks[0]
                else:
                    string = etree.tostring(el)
                    block = Block(site=site, xpath=xpath, checksum=checksum, body=string)
                    try:
                        block.save()
                        n_2 += 1
                    except:
                        print '--- save error in page ---', page_id
                    print n_2, checksum, xpath
                blocks_in_page = BlockInPage.objects.filter(block=block, webpage=page)
                if not blocks_in_page:
                    n_3 += 1
                    blocks_in_page = BlockInPage(block=block, webpage=page)
                    blocks_in_page.save()
    return n_1, n_2, n_3

            
        
