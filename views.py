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
from haystack.indexes import SearchIndex
from haystack.query import SearchQuerySet
from wip.search_indexes import StringIndex

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404

from models import Language, Site, Proxy, Webpage, PageVersion, TranslatedVersion, Block, TranslatedBlock, BlockInPage, String, Txu #, TranslatedVersion
from forms import PageBlockForm
from spiders import WipSiteCrawlerScript, WipCrawlSpider

from settings import DATA_ROOT, RESOURCES_ROOT, tagger_filename, BLOCK_TAGS, EMPTY_WORDS
from utils import strings_from_html, elements_from_element, block_checksum
import srx_segmenter

def home(request):
    var_dict = {}
    var_dict['original_sites'] = original_sites = Site.objects.all().order_by('name')
    sites = []
    for site in original_sites:
        site_dict = {}
        site_dict['name'] = site.name
        site_dict['slug'] = site.slug
        site_dict['source_pages'] = Webpage.objects.filter(site=site)
        site_dict['page_versions'] = PageVersion.objects.filter(webpage__site=site)
        site_dict['translated_versions'] = TranslatedVersion.objects.filter(webpage__site=site)
        site_dict['source_blocks'] = Block.objects.filter(site=site)
        site_dict['translated_blocks'] = TranslatedBlock.objects.filter(block__site=site)
        sites.append(site_dict)
    var_dict['sites'] = sites
    var_dict['source_strings'] = find_strings(source_languages=['it'])
    var_dict['untraslated_strings'] = {
       'en': find_strings(source_languages=['it'], target_languages=['en'], translated=False),
       'fr': find_strings(source_languages=['it'], target_languages=['fr'], translated=False),
       'es': find_strings(source_languages=['it'], target_languages=['es'], translated=False),
       }
    # var_dict['translated_strings'] = StringTranslation.objects.all()
    return render_to_response('homepage.html', var_dict, context_instance=RequestContext(request))

def sites(request):
    var_dict = {}
    sites = Site.objects.all().order_by('name')
    var_dict['sites'] = sites
    return render_to_response('sites.html', var_dict, context_instance=RequestContext(request))

def proxies(request):
    var_dict = {}
    proxies = Proxy.objects.all().order_by('site__name')
    var_dict['proxies'] = proxies
    return render_to_response('proxies.html', var_dict, context_instance=RequestContext(request))

def site(request, site_slug):
    site = get_object_or_404(Site, slug=site_slug)
    var_dict = {}
    var_dict['site'] = site
    var_dict['proxies'] =  proxies = Proxy.objects.filter(site=site)
    var_dict['page_count'] = page_count = Webpage.objects.filter(site=site).count()
    var_dict['block_count'] = block_count = Block.objects.filter(site=site).count()
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
    var_dict['proxies'] =  proxies = Proxy.objects.filter(site=site)
    var_dict['pages'] = pages = Webpage.objects.filter(site=site)
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
    var_dict['blocks'] = page.blocks.all()
    return render_to_response('page.html', var_dict, context_instance=RequestContext(request))

def page_blocks(request, page_id):
    var_dict = {}
    var_dict['page'] = page = get_object_or_404(Webpage, pk=page_id)
    var_dict['site'] = site = page.site
    var_dict['blocks'] = blocks = page.blocks.all()
    var_dict['blocks_count'] = blocks.count()
    return render_to_response('page_blocks.html', var_dict, context_instance=RequestContext(request))

def page_proxy(request, page_id, language_code):
    page = get_object_or_404(Webpage, pk=page_id)
    content, has_translation = page.get_translation(language_code)
    if content:
        return HttpResponse(content, content_type="text/html")
    else:
        return HttpResponseRedirect('/page/%d/' % page_id)
  
def proxy(request, proxy_slug):
    proxy = get_object_or_404(Proxy, slug=proxy_slug)
    var_dict = {}
    var_dict['proxy'] = proxy
    var_dict['site'] = proxy.site
    return render_to_response('proxy.html', var_dict, context_instance=RequestContext(request))

def site_blocks(request, site_slug):
    var_dict = {}
    site = get_object_or_404(Site, slug=site_slug)
    var_dict['site'] = site
    var_dict['proxies'] = proxies = Proxy.objects.filter(site=site).order_by('language__code')   
    var_dict['blocks'] = blocks = Block.objects.filter(site=site)
    var_dict['block_count'] = blocks.count()
    return render_to_response('blocks.html', var_dict, context_instance=RequestContext(request))

def site_translated_blocks(request, site_slug):
    var_dict = {}
    site = get_object_or_404(Site, slug=site_slug)
    var_dict['site'] = site
    var_dict['translated_blocks'] = blocks = TranslatedBlock.objects.filter(block__site=site)
    var_dict['translated_blocks_count'] = blocks.count()
    return render_to_response('translated_blocks.html', var_dict, context_instance=RequestContext(request))

def block(request, block_id):
    var_dict = {}
    var_dict['page_block'] = block = get_object_or_404(Block, pk=block_id)
    var_dict['site'] = site = block.site
    var_dict['translations'] = TranslatedBlock.objects.filter(block=block)
    var_dict['pages'] = block.webpages.all()
    return render_to_response('block.html', var_dict, context_instance=RequestContext(request))

def block_pages(request, block_id):
    var_dict = {}
    var_dict['page_block'] = block = get_object_or_404(Block, pk=block_id)
    var_dict['site'] = site = block.site
    var_dict['proxies'] =  proxies = Proxy.objects.filter(site=site)
    var_dict['pages'] = pages = block.webpages.all()
    var_dict['pages_count'] = pages.count()
    return render_to_response('block_pages.html', var_dict, context_instance=RequestContext(request))

def add_and_index_string(text, language):
    if isinstance(language, str):
        language = Language.objects.get(code=language)
    # text = text.lower()
    try:
        string = String.objects.get(text=text, language=language)
    except:
        string = String(text=text, language=language)
        string.save()
    StringIndex().update_object(string)
    return string

def block_translate(request, block_id):
    block = get_object_or_404(Block, pk=block_id)
    go_previous = go_next = save_block = ''
    skip_no_translate = skip_translated = True
    exclude_language = include_language = None
    extract_strings = False
    post = request.POST
    if post:
        # print post.keys()
        save_block = request.POST.get('save_block', '')
        go_previous = request.POST.get('prev', '')
        go_next = request.POST.get('next', '')
        form = PageBlockForm(request.POST)
        if form.is_valid():
            print 'form is valid'
            data = form.cleaned_data
            print 'data: ', data
            skip_no_translate = data['skip_no_translate']
            skip_translated = data['skip_translated']
            exclude_language = data['exclude_language']
            # include_language = None # data['include_language']
            extract_strings = data['extract_strings']
            language = data['language']
            no_translate = data['no_translate']
        else:
            print 'error', form.errors
    var_dict = {}
    var_dict['site'] = site = block.site
    var_dict['proxies'] = proxies = Proxy.objects.filter(site=site).order_by('language_id')
    var_dict['target_languages'] = target_languages = [proxy.language for proxy in proxies]
    var_dict['extract_strings'] = extract_strings
    previous, next = block.get_previous_next(exclude_language=exclude_language, include_language=include_language)
    var_dict['previous'] = previous
    var_dict['next'] = next
    if go_previous or go_next:
        if go_previous and previous:
            block = previous
        elif go_next and next:
            block = next
        block_id = block.id
    elif save_block:
        block.language = language
        block.no_translate = no_translate
        block.save()
    elif post:
        for key in post.keys():
            if key.startswith('create-'):
                code = key.split('-')[1]
                name = 'translation-%s' % code
                text = post.get(name).strip()
                translated_block = TranslatedBlock(block=block, body=text, language_id=code, editor=request.user)
                translated_block.save()
                propagate_block_translation(request, block, translated_block)
            elif key.startswith('modify-'):
                code = key.split('-')[1]
                translated_block = TranslatedBlock.objects.get(block=block, language_id=code)
                name = 'translation-%s' % code
                text = post.get(name).strip()
                translated_block.body = text
                translated_block.editor = request.user
                translated_block.save()
                propagate_block_translation(request, block, translated_block)
    var_dict['page_block'] = block
    var_dict['source_language'] = source_language = block.get_language()
    # source_language_code = source_language.code
    source_segments = block.get_strings()
    source_segments = [segment.strip(' .,;:*+-').lower() for segment in source_segments]
    source_strings = []
    for segment in source_segments:
        if not segment:
            continue
        segment_string = add_and_index_string(segment, source_language)
        if not extract_strings or source_language in target_languages:
            source_strings.append([])
            continue
        """
        tokens = segment.split()
        tokens = re.split(" |\'", segment)
        filtered_tokens = []
        for token in tokens:
            token = token.strip(' .,;:*')
            if not token:
                continue
            n_chars = len(token)
            if n_chars < 5:
                continue
            if token in EMPTY_WORDS[source_language_code]:
                continue
            filtered_tokens.append(token)
        qs = None
        strings = []
        qs = SearchQuerySet().more_like_this(segment_string)
        print 'like_this: ', qs
        for token in filtered_tokens:
            qs = SearchQuerySet().filter(language_code=source_language_code, content=token).values_list('text', flat=True)
            if qs:
                min_length = 100
                for string in qs:
                    length = len(string.split())
                    if length < min_length:
                        min_length = length
                n = 0
                for string in qs:
                    length = len(string.split())
                    if length > min_length:
                        continue
                    n += 1
                    if n >= 2:
                        break
                    strings.append(string)
        source_strings.append(strings)
        """
        source_strings.append(find_like_strings(segment_string))
    source_segments = zip(source_segments, source_strings)
    var_dict['source_segments'] = source_segments
    target_list = []
    for proxy in proxies:
        target_language = proxy.language
        try:
            translated_block = TranslatedBlock.objects.get(block=block, language=target_language)
        except:
            translated_block = None
        target_strings = []
        for segment_strings in source_strings:
            translated_strings = []
            for s in segment_strings:
                try:
                    string = String.objects.get(language=source_language, text=s)
                    translations = Txu.objects.filter(source=string, target__language=target_language)
                    for translation in translations:
                        text = translation.target.text
                        if not text in translated_strings:
                            translated_strings.append(text)
                except:
                    pass
            target_strings.append(translated_strings)
        target_list.append([target_language, translated_block, target_strings])
    var_dict['target_list'] = target_list
    var_dict['form'] = PageBlockForm(initial={'language': block.language, 'no_translate': block.no_translate, 'skip_translated': skip_translated, 'skip_no_translate': skip_no_translate, 'exclude_language': exclude_language, 'extract_strings': extract_strings,})
    return render_to_response('block_translate.html', var_dict, context_instance=RequestContext(request))

def propagate_block_translation(request, block, translated_block):
    similar_blocks = Block.objects.filter(site=block.site, checksum=block.checksum)
    for similar_block in similar_blocks:
        if not similar_block.body == block.body:
            continue
        translated_blocks = TranslatedBlock.objects.filter(block=similar_block).order_by('-modified')
        if translated_blocks:
            similar_block_translation = translated_blocks[0]
            similar_block_translation.body = translated_block.body
            similar_block_translation.editor = translated_block.editor
        else:
            similar_block_translation = translated_block
            similar_block_translation.pk = None
            similar_block_translation.block = similar_block
        similar_block_translation.save()

srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
srx_rules = srx_segmenter.parse(srx_filepath)
italian_rules = srx_rules['Italian']
# print italian_rules
segmenter = srx_segmenter.SrxSegmenter(italian_rules)
re_parentheses = re.compile(r'\(([^)]+)\)')

"""
srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
srx_rules = srx_segmenter.parse(srx_filepath)
italian_rules = srx_rules['Italian']
# print italian_rules
segmenter = srx_segmenter.SrxSegmenter(italian_rules)
re_parentheses = re.compile(r'\(([^)]+)\)')
"""

def page_scan(request, fetched_id, language='it'):
    string = request.GET.get('strings', False)
    tag = request.GET.get('tag', False)
    chunk = request.GET.get('chunk', False)
    ext = request.GET.get('ext', False)
    string = tag = chunk = True
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
        if request.GET.get('region', False):
            region = page.get_region()
            var_dict['text_xpath'] = region and region.root
            var_dict['page_text'] = region and region.full_text.replace("\n"," ") or ''
        if string:
            var_dict['strings'] = [s for s in strings_from_html(fetched.body)]
        if chunk or tag:
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
            # var_dict['strings'] = strings
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
    # http://stackoverflow.com/questions/1084741/regexp-to-strip-html-comments
    html_string = re.sub("(<!--(.*?)-->)", "", html_string, flags=re.MULTILINE)
    doc = html.document_fromstring(html_string)
    tree = doc.getroottree()
    top_els = doc.getchildren()
    n_1 = n_2 = n_3 = 0
    for top_el in top_els:
        for el in elements_from_element(top_el):
            if el.tag in BLOCK_TAGS:
                save_failed = False
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
                        save_failed = True
                    print n_2, checksum, xpath
                blocks_in_page = BlockInPage.objects.filter(block=block, webpage=page)
                if not blocks_in_page and not save_failed:
                    n_3 += 1
                    blocks_in_page = BlockInPage(block=block, webpage=page)
                    blocks_in_page.save()
    return n_1, n_2, n_3

def strings(request):
    return render_to_response('strings.html', {}, context_instance=RequestContext(request))

def string_view(request, string_id):
    var_dict = {}
    var_dict['string'] = string = get_object_or_404(String, pk=string_id)
    var_dict['source_language'] = source_language = string.language
    var_dict['other_languages'] = other_languages = Language.objects.exclude(code=source_language.code).order_by('code')
    var_dict['translations'] = string.get_translations()
    var_dict['similar_strings'] = find_like_strings(string, min_chars=5, max_strings=10)
    return render_to_response('string_view.html', var_dict, context_instance=RequestContext(request))

def string_translate(request, string_id, target_code):
    var_dict = {}
    var_dict['string'] = string = get_object_or_404(String, pk=string_id)
    var_dict['source_language'] = source_language = string.language
    var_dict['target_code'] = target_code
    var_dict['target_language'] = target_language = Language.objects.get(code=target_code)
    var_dict['translations'] = string.get_translations(target_languages=target_language)
    var_dict['similar_strings'] = find_like_strings(string, translation_language=target_language, with_translations=True, min_chars=5, max_strings=10)
    post = request.POST
    if post:
        pass
    return render_to_response('string_translate.html', var_dict, context_instance=RequestContext(request))

def filtered_tokens(text, language_code, truncate=False, min_chars=4):
    """
    tokenize a text according to the language and strips some delimiter chars
    drop short tokens; remove last char
    """
    tokens = re.split(" |\'", text)
    filtered_tokens = []
    for token in tokens:
        token = token.strip(' .,;:*')
        if not token:
            continue
        n_chars = len(token)
        if n_chars < min_chars:
            continue
        if token in EMPTY_WORDS[language_code]:
            continue
        if truncate:
            token = token[:n_chars-1]
        filtered_tokens.append(token)
    return filtered_tokens

def find_like_strings(source_string, translation_language=[], with_translations=False, min_chars=5, max_strings=10):
    """
    source_string is an object of type String
    we look for similar strings of the same language
    first we use fuzzy search (more_like_this)
    then we find strings containing some of the same tokens
    """
    language = source_string.language
    language_code = language.code
    hits = list(SearchQuerySet().more_like_this(source_string))
    if not hits:
        return []
    source_set = set(filtered_tokens(source_string.text, language_code, truncate=True))
    like_strings = []
    n_like = 0
    for hit in hits:
        if not hit.language_code == language_code:
            continue
        try: # the index could be not in sync
            string = String.objects.get(language=language, text=hit.text)
        except:
            continue
        if with_translations:
            string_translations = string.get_translations(target_languages=translation_language)
            if not string_translations:
                continue
        like_set = set(filtered_tokens(string.text, language_code, truncate=True))
        if like_set.intersection(source_set):
            if with_translations:
                like_strings.append([string, string_translations])
            else:
                like_strings.append(string)
            n_like +=1
            if n_like == max_strings:
                break
    return like_strings

def list_strings(request, sources, state, targets):
    PAGE_SIZE = 100
    var_dict = {}
    var_dict['sources'] = sources
    var_dict['state'] = state
    var_dict['targets'] = targets
    source_languages = target_languages = []
    translated = None
    if sources:
        source_codes = sources.split('-')
        source_languages = Language.objects.filter(code__in=source_codes).order_by('code')
    if targets:
        target_codes = targets.split('-')
        target_languages = Language.objects.filter(code__in=target_codes).order_by('code')
    if state == 'translated':
        translated = True
    elif state == 'untranslated':
        translated = False
    var_dict['source_languages'] = source_languages
    var_dict['target_languages'] = target_languages
    var_dict['target_codes'] = [l.code for l in target_languages]
    qs = find_strings(source_languages=source_languages, target_languages=target_languages, translated=translated)
    var_dict['string_count'] = qs.count()
    paginator = Paginator(qs, PAGE_SIZE)
    page = request.GET.get('page', 1)
    try:
        strings = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page = 1
        strings = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page = paginator.num_pages
        strings = paginator.page(paginator.num_pages)
    var_dict['page_size'] = PAGE_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * PAGE_SIZE
    var_dict['strings'] = strings
    return render_to_response('list_strings.html', var_dict, context_instance=RequestContext(request))

# translation state
def find_strings(source_languages=[], target_languages=[], translated=None):
    if isinstance(source_languages, Language):
        source_languages = [source_languages]
    if isinstance(target_languages, Language):
        target_languages = [target_languages]
    qs = String.objects
    if source_languages:
        qs = qs.filter(language__in=source_languages)
    if translated is None:
        if not source_languages:
            qs = qs.all()
    elif translated: # translated = True
        if target_languages:
            qs = qs.filter(as_source__target__language__in=target_languages).distinct()
        else:
            qs = qs.filter(as_source__isnull=False).distinct()
    else: # translated = False
        if target_languages:
            qs = qs.exclude(as_source__target__language__in=target_languages).distinct()
        else:
            qs = qs.filter(as_source__isnull=True).distinct()
    return qs.order_by('language', 'text')

def get_language(language_code):
    return Language.objects.get(code=language_code)
