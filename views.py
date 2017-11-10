# -*- coding: utf-8 -*-"""

"""
see: Django's CBVs were a mistake
http://lukeplant.me.uk/blog/posts/djangos-cbvs-were-a-mistake/
"""

import sys
"""
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)
"""

if (sys.version_info > (3, 0)):
    # Python 3 code in this block
    from importlib import reload
else:
    reload(sys)  
    sys.setdefaultencoding('utf8')

import os
import time
import datetime

import logging
logger = logging.getLogger('wip')

import re
from math import sqrt
from lxml import html, etree
import json

# from settings import BASE_DIR, USE_SCRAPY, USE_NLTK

from haystack.query import SearchQuerySet
# from search_indexes import StringIndex
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, render_to_response, get_object_or_404
from django.db import connection
# from django.db.models import Q, Count
from django.db.models.expressions import RawSQL, Q
from django import forms
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from actstream import action, registry

from .wip_nltk.tokenizers import NltkTokenizer
from .models import Language, Site, Proxy, Webpage, PageVersion, TranslatedVersion
from .models import Block, BlockEdge, TranslatedBlock, BlockInPage, String, Txu, TxuSubject #, TranslatedVersion
from .models import Scan, Link, WordCount, SegmentCount
from .models import UserRole, Segment, Translation
from .models import segments_from_string, non_invariant_words
from .models import STRING_TYPE_DICT, UNKNOWN, SEGMENT #, TERM, FRAGMENT
from .models import TEXT_ASC # , ID_ASC, DATETIME_DESC, DATETIME_ASC
from .models import ANY, TO_BE_TRANSLATED, TRANSLATED, PARTIALLY, INVARIANT, ALREADY
from .models import ROLE_DICT, TRANSLATION_TYPE_DICT, TRANSLATION_SERVICE_DICT, GOOGLE, MYMEMORY
from .models import OWNER, MANAGER, LINGUIST, REVISOR, TRANSLATOR, GUEST
from .models import TM, MT, MANUAL
from .models import PARALLEL_FORMAT_NONE, PARALLEL_FORMAT_XLIFF, PARALLEL_FORMAT_TEXT
from .forms import DiscoverForm
from .forms import SiteManageForm, ProxyManageForm, PageManageForm, PageSequencerForm, BlockEditForm, BlockSequencerForm
from .forms import SegmentSequencerForm, SegmentEditForm, SegmentTranslationForm, TranslationViewForm, TranslationSequencerForm
from .forms import StringSequencerForm, StringEditForm, StringsTranslationsForm, StringTranslationForm, TranslationServiceForm, FilterPagesForm
from .forms import UserRoleEditForm, ListSegmentsForm, ImportXliffForm
from .session import get_language, set_language, get_site, set_site, get_userrole, set_userrole
"""
from settings import PAGE_SIZE, PAGE_STEPS
from settings import DATA_ROOT, RESOURCES_ROOT, tagger_filename, BLOCK_TAGS, QUOTES, SEPARATORS, STRIPPED, DEFAULT_STRIPPED, EMPTY_WORDS, PAGES_EXCLUDE_BY_CONTENT
"""
from .utils import strings_from_html, elements_from_element, block_checksum, ask_mymemory, ask_gt, text_to_list # , non_invariant_words
from .utils import pageversion_diff, diff_style
from  wip import srx_segmenter
from .aligner import tokenize, best_alignment #, get_train_aligner

registry.register(Site)
registry.register(Proxy)
registry.register(Webpage)
registry.register(PageVersion)
registry.register(TranslatedVersion)
registry.register(Block)
registry.register(TranslatedBlock)
#     action.send(user, verb='Create', action_object=forum, target=project)

def robots(request):
    # response = render_to_response('robots.txt', {}, context_instance=RequestContext(request))
    response = render(request, 'robots.txt', {})
    response['Content-Type'] = 'text/plain; charset=utf-8'
    return response

def empty_page(request):
    # response = render_to_response('robots.txt', {}, context_instance=RequestContext(request))
    response = render(request, 'robots.txt', {})
    response['Content-Type'] = 'text/plain; charset=utf-8'
    return response

def steps_before(page):
    steps = list(settings.PAGE_STEPS)
    steps.reverse()
    steps = [page-step for step in steps if page-step >= 1 and page-step < page]
    if page > 1 and steps[0] > 1:
        steps = [1] + steps
    return steps

def steps_after(page, page_count):
    steps = [page+step for step in settings.PAGE_STEPS if page+step > page and page+step <= page_count]
    if page < page_count and steps[-1] < page_count:
        steps.append(page_count)
    return steps

def home(request):
    user = request.user
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
        site_dict['blocks_in_use'] = site.get_blocks_in_use()
        site_dict['translated_blocks'] = TranslatedBlock.objects.filter(block__site=site)
        proxies = site.get_proxies()
        site_dict['proxies'] = proxies
        sites.append(site_dict)
    var_dict['sites'] = sites
    # return render_to_response('homepage.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'homepage.html', var_dict)

def language(request, language_code):
    set_language(request, language_code or '')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def get_or_set_user_role(request, site=None, source_language=None, target_language=None):
    user_role_id = get_userrole(request)
    if user_role_id:
        user_role = UserRole.objects.get(pk=user_role_id)
    else:
        qs = UserRole.objects.filter(user=request.user)
        if site:
            qs = qs.filter(site=site)
        else:
            if source_language:
                qs = qs.filter(source_language=source_language)
            if target_language:
                qs = qs.filter(target_language=target_language)
        qs = qs.order_by('role_type')
        user_role = qs[0]
        set_userrole(request, user_role.id)
    return user_role

def my_roles(request, site=None):
    qs = UserRole.objects.filter(user=request.user)
    if site:
        qs = qs.filter(site=site)
    return qs.order_by('role_type', 'site', 'target_language__code', '-level')

def user_role_select(request, role_id):
    get_object_or_404(UserRole, pk=role_id)
    set_userrole(request, role_id)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def manage_roles(request):
    user = request.user
    qs = UserRole.objects.none()
    if user.is_superuser:
        qs = UserRole.objects.all()
    else:
        """
        role_id = get_or_set_user_role()
        my_role = get_object_or_404(UserRole, pk=role_id)
        """
        my_role = get_or_set_user_role()
        if my_role.role_type <= MANAGER:
            qs = UserRole.objects.filter(site=my_role.site, user_role__role_type__gt=my_role.role_type)
    user_roles = qs.order_by('role_type', 'site', 'target_language__code', '-level')
    var_dict = {}
    var_dict['user_roles'] = user_roles
    # return render_to_response('manage_roles.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'manage_roles.html', var_dict)

def role_detail(request, role_id):
    user_role = UserRole.objects.get(pk=role_id)
    var_dict = {}
    var_dict['user_role'] = user_role
    # return render_to_response('role_detail.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'role_detail.html', var_dict)

@staff_member_required
def role_edit(request, role_id=None):
    user_role = None
    if role_id:
        user_role = UserRole.objects.get(pk=role_id)
    if request.method == 'POST':
        form = UserRoleEditForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            role_id = data.get('id', '')
            if role_id:
                role_id = int(role_id)
                user_role = UserRole.objects.get(pk=role_id)
                form = UserRoleEditForm(request.POST, instance=user_role)
            else:
                form = UserRoleEditForm(request.POST)
            if request.POST.get('save', ''): 
                user_role = form.save()
                if role_id:
                    if not data.get('source_language'):
                        user_role.source_language = None
                    if not data.get('target_language'):
                        user_role.target_language = None
                    user_role.save()
                if not role_id:
                    user_role.creator = request.user
                    user_role.save()
                return HttpResponseRedirect('/role/%d/' % user_role.id)
            if request.POST.get('cancel', ''): 
                if role_id:
                    return HttpResponseRedirect('/role/%d/' % role_id)
                else:
                    return HttpResponseRedirect('/manage_roles/')
        else:
            # return render_to_response('role_edit.html', { 'form': form }, context_instance=RequestContext(request))
            return render(request, 'role_edit.html', { 'form': form })
    else:
        if role_id:
            user_role = get_object_or_404(UserRole, pk=role_id)
            form = UserRoleEditForm(instance=user_role)
        else:
            form = UserRoleEditForm()
        # return render_to_response('role_edit.html', { 'user_role': user_role, 'form': form }, context_instance=RequestContext(request))
        return render(request, 'role_edit.html', { 'user_role': user_role, 'form': form })

def sites(request):
    var_dict = {}
    sites = Site.objects.all().order_by('name')
    var_dict['sites'] = sites
    # return render_to_response('sites.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'sites.html', var_dict)

def proxies(request):
    var_dict = {}
    proxies = Proxy.objects.all().order_by('site__name')
    var_dict['proxies'] = proxies
    # return render_to_response('proxies.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'proxies.html', var_dict)

def site(request, site_slug):
    user = request.user
    site = get_object_or_404(Site, slug=site_slug)
    set_site(request, site_slug)
    var_dict = {}
    var_dict['site'] = site
    var_dict['can_manage'] = site.can_manage(user)
    var_dict['can_operate'] = site.can_operate(user)
    var_dict['can_view'] = site.can_view(user)
    var_dict['proxies'] =  proxies = site.get_proxies()
    var_dict['proxy_languages'] = proxy_languages = [proxy.language for proxy in proxies]
    words_distribution = site.get_token_frequency(lowercasing=True)
    var_dict['word_count'] = len(words_distribution)
    post = request.POST
    if post:
        discovery = post.get('discover', '')
        site_crawl = post.get('site_crawl', '')
        extract_blocks = post.get('extract_blocks', '')
        purge_blocks = post.get('purge_blocks', '')
        refetch_pages = post.get('refetch_pages', '')
        extract_segments = post.get('extract_segments', '')
        download_segments = post.get('download_segments', '')
        download_words_distribution = post.get('download_words_distribution', '')
        import_invariants = post.get('import_invariants', '')
        apply_invariants = post.get('apply_invariants', '')
        delete_site = post.get('delete_site', '')
        guess_blocks_language = post.get('guess_blocks_language', '')
        form = SiteManageForm(post, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            verbose = data['verbose']
            if discovery:
                # return discovery_settings(request, site=site)
                return discover(request, site=site)
            elif site_crawl:
                clear_pages = data['clear_pages']
                if clear_pages:
                    Webpage.objects.filter(site=site).delete()
                # task_id = crawl_site.delay(site.id)
                run_worker_process()
                task_id = crawl_site_task.delay(site.id)
                print ('site_crawl : ', site.name, 'task id: ', task_id)
            elif purge_blocks:
                site.purge_bips(verbose=False)
            elif extract_blocks:
                clear_blocks = data['clear_blocks']
                if clear_blocks:
                    Block.objects.filter(site=site).delete()
                    BlockInPage.objects.filter(block__site=site).delete()
                    BlockEdge.objects.filter(parent__site=site).delete()
                webpages = Webpage.objects.filter(site=site).exclude(no_translate=True)
                extract_deny_list = text_to_list(site.extract_deny)
                translate_deny_list = text_to_list(site.translate_deny)
                for webpage in webpages:
                    if webpage.last_unfound and (webpage.last_unfound > webpage.last_checked):
                        continue
                    should_skip = False
                    path = webpage.path
                    for deny_path in extract_deny_list:
                        if path.count(deny_path):
                            should_skip = True
                            break
                    if should_skip:
                        continue
                    should_skip = False
                    for deny_path in translate_deny_list:
                        if path.count(deny_path):
                            should_skip = True
                            break
                    if should_skip:
                        continue
                    # try:
                    if True:
                        # n_1, n_2, n_3 = webpage.extract_blocks()
                        extracted_blocks = webpage.extract_blocks()
                        webpage.purge_bips(current_blocks=extracted_blocks)
                        webpage.create_blocks_dag()
                    # except:
                    else:
                        print ('extract_blocks: error on page ', webpage.id)
            elif refetch_pages:
                n_pages, n_updates, n_unfound = site.refetch_pages(verbose=verbose)
                messages.add_message(request, messages.INFO, 'Requested %d pages: %d updated, %d unfound' % (n_pages, n_updates, n_unfound))
            elif extract_segments or download_segments:
                segmenter = site.make_segmenter()
                dry = False
                language = site.language
                language_code = language.code
                webpages = Webpage.objects.filter(site=site)
                extract_deny_list = text_to_list(site.extract_deny)
                if dry:
                    print (extract_deny_list)
                if download_segments:
                    download_list = []
                for webpage in webpages:
                    path = webpage.path
                    if webpage.last_unfound and (webpage.last_unfound > webpage.last_checked):
                        continue
                    should_skip = False
                    for deny_path in extract_deny_list:
                        if path.count(deny_path):
                            should_skip = True
                            break
                    if should_skip:
                        continue
                    page_versions = PageVersion.objects.filter(webpage=webpage).order_by('-time')
                    if not page_versions:
                        continue
                    page_version = page_versions[0]
                    skip_page = False
                    for content in settings.PAGES_EXCLUDE_BY_CONTENT.get(site.slug, []):
                        if len(path)>1 and page_version.body.count(content):
                            skip_page = True
                            break
                    if skip_page:
                        continue
                    """
                    try:
                        segments = page_version.page_version_get_segments()
                    except: # Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
                        print '- error on ', path
                        continue
                    """
                    segments = page_version.page_version_get_segments(segmenter=segmenter)
                    if dry:
                        print (path)
                        continue
                    for s in segments:
                        if download_segments:
                            if not s in download_list:
                                download_list.append(s)
                        else:
                            # is_model_instance, string = get_or_add_string(request, s, language, string_type=SEGMENT, add=True, txu=None, site=site, reliability=0)
                            get_or_add_segment(request, s, language, site)
                        sys.stdout.write('.')
                if download_segments:
                    # messages.add_message(request, messages.INFO, 'Downloaded %d segments.' % len(download_list))
                    data = u'\r\n'.join(download_list)
                    response = HttpResponse(data, content_type='application/octet-stream')
                    time_stamp = datetime.datetime.now().strftime('%y%m%d-%H-%M-%S')
                    filename = u'%s-segments.%s.txt' % (site.slug, time_stamp)
                    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
                    return response
            elif download_words_distribution:
                sorted_words_distribution = sorted(words_distribution.items(), key=lambda item: item[1], reverse=True)
                data = u'\r\n'.join(['%s %d' % (item[0], item[1]) for item in sorted_words_distribution])
                response = HttpResponse(data, content_type='application/octet-stream')
                time_stamp = datetime.datetime.now().strftime('%y%m%d-%H-%M-%S')
                filename = u'%s-%s-words.%s.txt' % (site.slug, site.language_id, time_stamp)
                response['Content-Disposition'] = 'attachment; filename="%s"' % filename
                return response
            elif delete_site:
                delete_confirmation = data['delete_confirmation']
                if delete_confirmation:
                    site.delete()
                    return HttpResponseRedirect('/')
            elif import_invariants:
                language = site.language
                clear_invariants = data['clear_invariants']
                if clear_invariants:
                    """
                    strings = String.objects.filter(invariant=True, site=site)
                    for string in strings:
                        string.delete()
                    """
                    segments = Segment.objects.filter(is_invariant=True, site=site)
                    for segment in segments:
                        segment.delete()
                f = request.FILES.get('file', None)
                if f:
                    i = 0
                    m = 0
                    n = 0
                    d = 0
                    for line in f:
                        line = line.strip()
                        i += 1
                        if line:
                            m += 1
                            try:
                                # if String.objects.filter(site=site, text=line, invariant=True):
                                if Segment.objects.filter(site=site, text=line, is_invariant=True):
                                    d += 1
                                else:
                                    """
                                    string = String(txu=None, language=language, site=site, text=line, reliability=0, invariant=True)
                                    string.save()
                                    """
                                    segment = Segment(language=language, site=site, text=line, is_invariant=True)
                                    segment.save()
                                    n += 1
                            except:
                                print ('error: ', i)
                    messages.add_message(request, messages.INFO, 'Imported %d invariants out of %d (%d repetitions).' % (n, m, d))
                else:
                    messages.add_message(request, messages.ERROR, 'Please, select a file to upload.')
            elif apply_invariants:
                blocks = Block.objects.filter(site=site, language__isnull=True, no_translate=False)
                if blocks:
                    """
                    srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
                    srx_rules = srx_segmenter.parse(srx_filepath)
                    italian_rules = srx_rules['Italian']
                    segmenter = srx_segmenter.SrxSegmenter(italian_rules)
                    """
                    segmenter = site.make_segmenter()
                n_invariants = 0
                for block in blocks:
                    if block.apply_invariants(segmenter):
                        n_invariants += 1
                messages.add_message(request, messages.INFO, '%d blocks marked as invariant.' % n_invariants)
            elif guess_blocks_language:
                from wip.utils import guess_block_language
                blocks = Block.objects.filter(site=site, language__isnull=True)
                if proxy_languages:
                    proxy_codes = [l.code for l in proxy_languages]
                    for block in blocks:
                        if block.language_id or block.no_translate:
                            continue
                        code = guess_block_language(block)
                        if code in proxy_codes:
                            block.language_id = code
                            block.save()
            else:
                for key in post.keys():
                    if key.startswith('addproxy-'):
                        code = key.split('-')[1]
                        proxy = Proxy(site=site, language_id=code, name='%s %s' % (site.name, code.upper()), base_path='%s/%s' % (site.path_prefix, code))
                        proxy.save()
                        break
    missing_languages = Language.objects.exclude(code=site.language_id)
    missing_languages = missing_languages.exclude(code__in=[l.code for l in proxy_languages])
    var_dict['missing_languages'] = missing_languages
    webpages = Webpage.objects.filter(site=site).order_by('id')
    var_dict['page_count'] = page_count = webpages.count()
    var_dict['first_page'] = webpages and webpages[0] or None
    blocks = Block.objects.filter(site=site).order_by('id')
    var_dict['block_count'] = block_count = blocks.count()
    var_dict['blocks_in_use'] = site.get_blocks_in_use()
    var_dict['first_block'] = blocks and blocks[0] or None
    pages, pages_total, pages_invariant, pages_proxy_list = site.pages_summary()
    var_dict['pages_total'] = pages_total
    var_dict['pages_invariant'] = pages_invariant
    var_dict['pages_proxy_list'] = pages_proxy_list
    blocks, blocks_total, blocks_invariant, blocks_proxy_list = site.blocks_summary()
    var_dict['blocks_total'] = blocks_total
    var_dict['blocks_invariant'] = blocks_invariant
    var_dict['blocks_proxy_list'] = blocks_proxy_list
    var_dict['manage_form'] = SiteManageForm()
    # return render_to_response('site.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'site.html', var_dict)

def proxy(request, proxy_slug):
    user = request.user
    proxy = get_object_or_404(Proxy, slug=proxy_slug)
    var_dict = {}
    var_dict['proxy'] = proxy
    var_dict['can_manage'] = proxy.can_manage(user)
    var_dict['can_operate'] = proxy.can_operate(user)
    var_dict['can_view'] = proxy.can_view(user)
    var_dict['site'] = site = proxy.site
    var_dict['language'] = language = proxy.language
    words_distribution = proxy.get_token_frequency(lowercasing=True)
    var_dict['word_count'] = len(words_distribution)
    post = request.POST
    if post:
        # print ('request.POST: ', post)
        delete_pages = post.get('delete_pages', '')
        delete_blocks = post.get('delete_blocks', '')
        delete_proxy = post.get('delete_proxy', '')
        import_translations = post.get('import_translations', '')
        export_translations = post.get('export_translations', '')
        download_words_distribution = post.get('download_words_distribution', '')
        apply_tm = post.get('apply_tm', '')
        align_translations = post.get('align_translations', '')
        evaluate_aligner = post.get('evaluate_aligner', '')
        propagate_up = post.get('propagate_up', '')
        form = ProxyManageForm(post)
        if form.is_valid():
            data = form.cleaned_data
            if delete_pages:
                delete_pages_confirmation = data['delete_pages_confirmation']
                if delete_pages_confirmation:
                    TranslatedVersion.objects.filter(webpage__site=site, language=language).delete()
            elif delete_blocks:
                delete_blocks_confirmation = data['delete_blocks_confirmation']
                if delete_blocks_confirmation:
                    TranslatedBlock.objects.filter(block__site=site, language=language).delete()
            elif delete_proxy:
                delete_proxy_confirmation = data['delete_proxy_confirmation']
                if delete_proxy_confirmation:
                    proxy.delete()
                    messages.add_message(request, messages.INFO, 'Proxy deleted.')
                    return HttpResponseRedirect('/site/%s/' % site.slug)
            elif import_translations:
                f = request.FILES.get('file', None)
                if f:
                    m, n = proxy.import_translations(f, request=request)
                    messages.add_message(request, messages.INFO, '%d translations read, %d translations added.' % (m, n))
            elif export_translations:
                parallel_format = int(data['parallel_format'])
                lines = []
                segments = Segment.objects.filter(site=proxy.site, is_invariant=False)
                for segment in segments:
                    source_text = segment.text
                    translations = Translation.objects.filter(segment=segment, language=proxy.language)
                    for translation in translations:
                        target_text = translation.text
                        if parallel_format==PARALLEL_FORMAT_XLIFF: # XLIFF
                            pass
                        elif parallel_format==PARALLEL_FORMAT_TEXT: # plain_text
                            lines.append('%s . ||| . %s' % (source_text, target_text))
                data = '\n'.join(lines)
                if parallel_format==PARALLEL_FORMAT_XLIFF: # XLIFF
                    response = HttpResponse(data, content_type='application/xliff+xml')
                    filename = '%s_translations.xlf' % proxy.slug
                elif parallel_format==PARALLEL_FORMAT_TEXT: # plain_text
                    response = HttpResponse(data, content_type='text/plain')
                    filename = '%s_translations.txt' % proxy.slug
                response['Content-Disposition'] = 'attachment; filename="%s"' % filename
                return response
            elif align_translations or evaluate_aligner:
                """
                lowercasing = True
                tokenizer = NltkTokenizer(lowercasing=lowercasing)
                # aligner = get_train_aligner(proxy, train=True, tokenizer=tokenizer, lowercasing=lowercasing)
                aligner = proxy.get_train_aligner(train=True, tokenizer=tokenizer, lowercasing=lowercasing)
                segments = Segment.objects.filter(site=proxy.site, is_invariant=False)
                for segment in segments:
                    source_tokens = tokenize(segment.text, tokenizer=tokenizer, lowercasing=lowercasing)
                    translations = Translation.objects.filter(segment=segment, language=proxy.language).exclude(alignment_type=MANUAL)
                    for translation in translations:
                        target_tokens = tokenize(translation.text, tokenizer=tokenizer, lowercasing=lowercasing)
                        alignment = best_alignment(aligner, source_tokens, target_tokens)
                        translation.alignment = ' '.join(['%s-%s' % (str(couple[0]), couple[1] is not None and str(couple[1]) or '') for couple in alignment])
                        print 'translation.alignment: ', translation.alignment
                        translation.alignment_type = MT
                        translation.save()
                """
                aligner = int(data['aligner'])
                use_known_links = data['use_known_links']
                test_set_module = int(data['test_set_module'])
                verbose = data['verbose']
                debug = data['debug']
                if aligner == 1: # eflomal
                    # proxy.eflomal_align_translations(evaluate=evaluate_aligner)
                    evaluation = proxy.eflomal_align_translations(evaluate=evaluate_aligner, use_know_links=use_known_links, test_set_module=test_set_module, verbose=verbose, debug=debug)
                    if evaluate_aligner:
                        var_dict['evaluation'] = evaluation
                elif aligner == 2: # NLTK IBM models
                    proxy.align_translations(ibm_model=2, iterations=5, evaluate=evaluate_aligner)                
            elif download_words_distribution:
                sorted_words_distribution = sorted(words_distribution.items(), key=lambda item: item[1], reverse=True)
                data = u'\r\n'.join(['%s %d' % (item[0], item[1]) for item in sorted_words_distribution])
                response = HttpResponse(data, content_type='application/octet-stream')
                time_stamp = datetime.datetime.now().strftime('%y%m%d-%H-%M-%S')
                filename = u'%s-%s-words.%s.txt' % (site.slug, proxy.language_id, time_stamp)
                response['Content-Disposition'] = 'attachment; filename="%s"' % filename
                return response
            elif apply_tm:
                n_ready, n_translated, n_partially = proxy.apply_translation_memory()
                messages.add_message(request, messages.INFO, 'TM applied to %d blocks: %d fully translated, %d partially translated.' % (n_ready, n_translated, n_partially))
            elif propagate_up:
                # print ('propagate_up')
                n_new, n_updated, n_no_updated = proxy.propagate_up_block_updates()
                messages.add_message(request, messages.INFO, 'Up propagation: %d new, %d updated, %d not updated blocks' % (n_new, n_updated, n_no_updated))
    else:
        form = ProxyManageForm(initial={ 'use_known_links': True, 'test_set_module': 2, 'verbose': False, 'debug': False })
    webpages = Webpage.objects.filter(site=site).order_by('id')
    var_dict['page_count'] = page_count = webpages.count()
    var_dict['first_page'] = webpages and webpages[0] or None
    blocks = Block.objects.filter(site=site).order_by('id')
    var_dict['block_count'] = block_count = blocks.count()
    var_dict['blocks_in_use'] = site.get_blocks_in_use()
    var_dict['first_block'] = blocks and blocks[0] or None
    pages, pages_total, pages_invariant, pages_proxy_list = site.pages_summary()
    var_dict['pages_total'] = pages_total
    var_dict['pages_invariant'] = pages_invariant
    var_dict['pages_proxy_list'] = pages_proxy_list
    blocks, blocks_total, blocks_invariant, blocks_proxy_list = site.blocks_summary()
    var_dict['blocks_total'] = blocks_total
    var_dict['blocks_invariant'] = blocks_invariant
    var_dict['blocks_proxy_list'] = blocks_proxy_list
    
    var_dict['translated_pages_count'] = page_count = TranslatedVersion.objects.filter(webpage__site=site, language=language).count()
    # var_dict['translated_blocks_count'] = TranslatedBlock.objects.filter(block__site=site, language=language).count()
    var_dict['translated_blocks_count'] = translated_blocks_count = TranslatedBlock.objects.filter(block__site=site, state=TRANSLATED, language_id=proxy.language_id).count()
    var_dict['partially_blocks_count'] = partially_blocks_count = TranslatedBlock.objects.filter(block__site=site, state=PARTIALLY, language_id=proxy.language_id).count()
    var_dict['left_blocks_count'] = blocks_total - blocks_invariant - translated_blocks_count - partially_blocks_count
    var_dict['blocks_ready'] = blocks_ready = proxy.blocks_ready()
    var_dict['ready_count'] = len(blocks_ready)
    var_dict['manage_form'] = form # ProxyManageForm()
    # return render_to_response('proxy.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'proxy.html', var_dict)

def import_xliff(request, proxy_slug):
    proxy = get_object_or_404(Proxy, slug=proxy_slug)
    site = proxy.site
    var_dict = {}
    var_dict['proxy'] = proxy
    post = request.POST
    if post:
        if post.get('cancel', ''):
            messages.add_message(request, messages.INFO, 'operation was canceled.')
            return HttpResponseRedirect('/proxy/%s/' % proxy_slug)        
        form = ImportXliffForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            # xliff_file = request.FILES.get('file', None)
            xliff_file = data['file']
            file_name = xliff_file.name
            file_size = xliff_file.size
            charset = xliff_file.charset
            # print (file_name, file_size, charset)
            msg = 'XLIFF file: %s - size: %d' % (file_name, file_size)
            user_role = data['user_role']
            status = proxy.import_translations(xliff_file, request=request, user_role=user_role)
            if status.get('error', None):
                msg += ' - Error: %s.' % status['error']
            else:
                msg += ' - %d translations found, %d translations imported.' % (status['found'], status['imported'])
            messages.add_message(request, messages.INFO, msg)
            return HttpResponseRedirect('/proxy/%s/' % proxy_slug)        
    else:
        form = ImportXliffForm()
        qs = UserRole.objects.filter(site=site)
        qs = qs.filter(Q(source_language__isnull=True) | Q(source_language=site.language))
        qs = qs .filter(Q(target_language__isnull=True) | Q(target_language=proxy.language))
        qs = qs.order_by('-role_type', 'level')
        form.fields['user_role'].queryset = qs
    var_dict['form'] = form
    # return render_to_response('import_xliff.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'import_xliff.html', var_dict)

def site_pages(request, site_slug):
    var_dict = {}
    site = get_object_or_404(Site, slug=site_slug)
    var_dict['site'] = site

    filter_pages_context = request.session.get('filter_pages_context', {})
    path_filter = filter_pages_context.get('path_filter', '')
    from_start = filter_pages_context.get('from_start', False)
    if request.method == 'POST':
        form = FilterPagesForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            filter_pages_context['path_filter'] = path_filter = data['path_filter']
            filter_pages_context['from_start'] = at_start = data['from_start']
            request.session['filter_pages_context'] = filter_pages_context
    else:
        form = FilterPagesForm(initial={ 'path_filter': path_filter, 'from_start': from_start, })
    var_dict['filter_pages_form'] = form

    var_dict['proxies'] =  proxies = Proxy.objects.filter(site=site)
    qs = Webpage.objects.filter(site=site)
    if path_filter:
        if from_start:
            qs = qs.filter(path__istartswith=path_filter)
        else:
            qs = qs.filter(path__icontains=path_filter)
    var_dict['page_count'] = page_count = qs.count()
    paginator = Paginator(qs, settings.PAGE_SIZE)
    page = request.GET.get('page', 1)
    try:
        site_pages = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page = 1
        site_pages = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page = paginator.num_pages
        site_pages = paginator.page(paginator.num_pages)
    var_dict['page_size'] = settings.PAGE_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    var_dict['site_pages'] = site_pages
    # return render_to_response('pages.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'pages.html', var_dict)

def page(request, page_id):
    var_dict = {}
    first_page = None
    if int(page_id) == 0:
        site_slug = request.GET.get('site', '')
        filter = request.GET.get('filter', '')
        if site_slug and filter:
            site = get_object_or_404(Site, slug=site_slug)
            webpages = Webpage.objects.filter(site=site)
            if filter == 'no_translate':
                webpages = webpages.filter(no_translate=True)
            if webpages:
                first_page = webpage = webpages.order_by('id')[0]
    else:
        webpage = get_object_or_404(Webpage, pk=page_id)
        var_dict['site'] = site = webpage.site
    var_dict['proxy_languages'] = proxy_languages = [proxy.language for proxy in site.get_proxies()]
    proxy_codes = [proxy.language_id for proxy in site.get_proxies()]
    var_dict['scans'] = PageVersion.objects.filter(webpage=webpage).order_by('-time')
    PageSequencerForm.base_fields['translation_languages'].queryset = Language.objects.filter(code__in=proxy_codes)
    save_page = apply_filter = goto = '' 
    fetch_page = purge_blocks = extract_blocks = ''
    post = request.POST
    if post:
        save_page = post.get('save_page', '')
        fetch_page = post.get('fetch_page', '')
        purge_blocks = post.get('purge_blocks', '')
        extract_blocks = post.get('extract_blocks', '')
        apply_filter = post.get('apply_filter', '')
        # if not (save_page or fetch_page or apply_filter):
        for key in post.keys():
            if key.startswith('goto-'):
                goto = int(key.split('-')[1])
                webpage = get_object_or_404(Webpage, pk=goto)
        if fetch_page:
            webpage.fetch(verbose=True)
        elif purge_blocks:
            extracted_blocks = webpage.extract_blocks(dry=True, verbose=True)
            # print ('extracted bocks:', len(extracted_blocks))
            webpage.purge_bips(current_blocks=extracted_blocks, verbose=True)
        elif extract_blocks:
            webpage.extract_blocks(verbose=True)
        elif save_page:
            form = PageManageForm(post)
            if form.is_valid():
                data = form.cleaned_data
                no_translate = data['no_translate']
                webpage.no_translate = no_translate
                webpage.save()
        elif (apply_filter or goto):
            form = PageSequencerForm(post)
            if form.is_valid():
                data = form.cleaned_data
                page_age = data['page_age']
                translation_state = int(data['translation_state'])
                translation_languages = data['translation_languages']
                translation_codes = [l.code for l in translation_languages]
                translation_age = data['translation_age']
                list_blocks = data['list_blocks']
    # if not post or save_page:
    if not post or not (apply_filter or goto):
        translation_state = None
        translation_codes = []
        if not post and first_page:
            if filter == 'no_translate':
                translation_state = INVARIANT
        sequencer_context = request.session.get('page_sequencer_context', {})
        if sequencer_context:
            page_age = sequencer_context.get('page_age', '')
            translation_state = translation_state or sequencer_context.get('translation_state', TO_BE_TRANSLATED)
            translation_codes = sequencer_context.get('translation_codes', [])
            translation_age = sequencer_context.get('translation_age', '')
            list_blocks = sequencer_context.get('list_blocks', False)
            request.session['page_sequencer_context'] = {}
        else:
            page_age = ''
            translation_state = translation_state or TO_BE_TRANSLATED
            translation_codes = [proxy.language.code for proxy in site.get_proxies()]
            translation_age = ''
            list_blocks = False
        translation_languages = translation_codes and Language.objects.filter(code__in=translation_codes) or []
    sequencer_context = {}
    sequencer_context['page_age'] = page_age
    sequencer_context['translation_state'] = translation_state
    sequencer_context['translation_codes'] = translation_codes
    sequencer_context['translation_age'] = translation_age
    sequencer_context['list_blocks'] = list_blocks
    request.session['page_sequencer_context'] = sequencer_context
    var_dict['webpage'] = webpage
    previous, next = webpage.get_navigation(translation_state=translation_state, translation_codes=translation_codes)
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['site'] = site
    if save_page or goto:
        return HttpResponseRedirect('/page/%d/' % webpage.id)        
    var_dict['edit_form'] = PageManageForm(initial={'no_translate': webpage.no_translate,})
    var_dict['sequencer_form'] = PageSequencerForm(initial={'page_age': page_age, 'translation_state': translation_state, 'translation_languages': translation_languages, 'translation_age': translation_age, 'list_blocks': list_blocks, })
    blocks, total, invariant, proxy_list = webpage.blocks_summary()
    # print total, invariant, proxy_list
    var_dict['blocks'] = blocks
    var_dict['list_blocks'] = list_blocks
    var_dict['total'] = total
    var_dict['block_count'] = total
    var_dict['blocks_in_use'] = webpage.get_blocks_in_use()
    var_dict['invariant'] = invariant
    var_dict['proxy_list'] = proxy_list
    # return render_to_response('page.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'page.html', var_dict)

def page_versions(request, page_id):
    var_dict = {}
    var_dict['webpage'] = webpage = get_object_or_404(Webpage, pk=page_id)
    var_dict['site'] = webpage.site
    var_dict['versions'] = versions = PageVersion.objects.filter(webpage=webpage).order_by('-time')
    var_dict['version_count'] = version_count = versions.count()
    version = request.GET.get('version', '')
    if version_count >= 2 and version:
        version = int(version)-1
        var_dict['diff'] = pageversion_diff(versions[version], versions[version+1], html='table', wrap=80);
        var_dict['diff_style'] = diff_style
    return render(request, 'page_versions.html', var_dict)

def page_blocks(request, page_id):
    var_dict = {}
    var_dict['webpage'] = webpage = get_object_or_404(Webpage, pk=page_id)
    var_dict['site'] = site = webpage.site
    qs = BlockInPage.objects.filter(webpage=webpage).order_by('xpath', '-time')
    var_dict['block_count'] = qs.count()
    paginator = Paginator(qs, settings.PAGE_BIG_SIZE)
    page = request.GET.get('page', 1)
    try:
        page_blocks = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page = 1
        page_blocks = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page = paginator.num_pages
        page_blocks = paginator.page(paginator.num_pages)
    var_dict['page_size'] = settings.PAGE_BIG_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_BIG_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    var_dict['page_blocks'] = page_blocks
    # return render_to_response('page_blocks.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'page_blocks.html', var_dict)

def page_extract_blocks(request, page_id):
    webpage = get_object_or_404(Webpage, pk=page_id)
    webpage.extract_blocks()
    webpage.create_blocks_dag()
    return page(request, page_id)

def page_cache_translation(request, page_id, language_code):
    webpage = get_object_or_404(Webpage, pk=page_id)
    webpage.cache_translation(language_code)
    return page(request, page_id)

def page_proxy(request, page_id, language_code):
    page = get_object_or_404(Webpage, pk=page_id)
    content, has_translation = page.get_translation(language_code)
    if content:
        return HttpResponse(content, content_type="text/html")
    else:
        return HttpResponseRedirect('/page/%d/' % page_id)

def site_blocks(request, site_slug):
    var_dict = {}
    site = get_object_or_404(Site, slug=site_slug)
    var_dict['site'] = site
    var_dict['proxies'] = proxies = Proxy.objects.filter(site=site).order_by('language__code')   
    qs = Block.objects.filter(site=site).order_by('xpath')
    var_dict['block_count'] = block_count = qs.count()
    paginator = Paginator(qs, settings.PAGE_SIZE)
    page = request.GET.get('page', 1)
    try:
        site_blocks = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page = 1
        site_blocks = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page = paginator.num_pages
        site_blocks = paginator.page(paginator.num_pages)
    var_dict['page_size'] = settings.PAGE_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    var_dict['site_blocks'] = site_blocks
    # return render_to_response('blocks.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'blocks.html', var_dict)

def site_translated_blocks(request, site_slug):
    var_dict = {}
    site = get_object_or_404(Site, slug=site_slug)
    var_dict['site'] = site
    var_dict['translated_blocks'] = blocks = TranslatedBlock.objects.filter(block__site=site)
    var_dict['translated_blocks_count'] = blocks.count()
    # return render_to_response('translated_blocks.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'translated_blocks.html', var_dict)

def get_or_add_string(request, text, language, site=None, string_type=UNKNOWN, add=False, txu=None, reliability=1):
    if isinstance(language, str):
        language = Language.objects.get(code=language)
    is_model_instance = False
    if site:
        strings = String.objects.filter(text=text, language=language, site=site)
    else:
        strings = String.objects.filter(text=text, language=language)
    if strings:
        is_model_instance = True
        string = strings[0]
    else:
        if add:
            string = String(text=text, language=language, txu=txu, site=site, string_type=string_type, reliability=reliability, user=request.user)
            string.save()
            is_model_instance = True
        else:
            string = String(text=text, language=language, site=site)
    return is_model_instance, string

# def get_or_add_segment(request, text, language, site, is_fragment=False):
def get_or_add_segment(request, text, language, site, add=False, is_fragment=False):
    if isinstance(language, str):
        language = Language.objects.get(code=language)
    segments = Segment.objects.filter(text=text, language=language, site=site)
    if segments:
        segment = segments[0]
    else:
        segment = Segment(text=text, language=language, site=site, is_fragment=is_fragment)        
        if add:
            segment.save()
    return segment

def get_or_add_translation(request, segment, text, language, translation_type=MANUAL, user_role=None):
    if isinstance(language, str):
        language = Language.objects.get(code=language)
    if not user_role:
        """
        user_role_id = get_userrole(request)
        user_role = UserRole.objects.get(pk=user_role_id)
        """
        user_role = get_or_set_user_role(request, site=segment.site, source_language=segment.language, target_language=language)
    translations = Translation.objects.filter(segment=segment, text=text, language=language)
    if translations:
        translation = translations[0]
    else:
        # translation = Translation(segment=segment, text=text, language=language, user=request.user)
        translation = Translation(segment=segment, text=text, language=language, translation_type=translation_type, user_role=user_role, timestamp=timezone.now())
        translation.save()
    return translation

def block(request, block_id):
    """
    view block specified and allow moving back and forth among blocks of the same site filtered by:
    - : more than  days old if  is positive, less than if  is negative
    - target_languages: one or more translation language (a subset of the proxy languages)
    - translation_: as , but with reference to the translated blocks
    - state: translated (at least one language), untranslated (at least one language), all
    """
    first_block = None
    if int(block_id) == 0:
        site_slug = request.GET.get('site', '')
        filter = request.GET.get('filter', '')
        target_code =request.GET.get('lang', '')
        if site_slug and filter:
            site = get_object_or_404(Site, slug=site_slug)
            blocks = Block.objects.filter(site=site)
            if filter == 'no_translate':
                blocks = blocks.filter(no_translate=True)
            elif filter == 'already' and target_code:
                blocks = blocks.filter(language_id=target_code)
            elif filter == 'partially' and target_code:
                pass
            elif filter == 'translated' and target_code:
                pass
            elif filter == 'revised' and target_code:
                pass
            if blocks:
                first_block = block = blocks.order_by('id')[0]
    else:
        block = get_object_or_404(Block, pk=block_id)
    proxy_languages = [proxy.language for proxy in block.site.get_proxies()]
    proxy_codes = [l.code for l in proxy_languages]
    target_languages = [l for l in proxy_languages if not l == block.language]
    BlockSequencerForm.base_fields['translation_languages'].queryset = Language.objects.filter(code__in=proxy_codes)
    save_block = apply_filter = goto = create = modify = '' 
    post = request.POST
    if post:
        save_block = post.get('save_block', '')
        # apply_filter = post.get('apply_filter', '')
        if not (save_block or apply_filter):
            for key in post.keys():
                if key.startswith('goto-'):
                    goto = int(key.split('-')[1])
                    block = get_object_or_404(Block, pk=goto)
        apply_filter = not (save_block or goto)
        if save_block:
            form = BlockEditForm(post)
            if form.is_valid():
                data = form.cleaned_data
                language = data['language']
                no_translate = data['no_translate']
                block.language = language
                block.no_translate = no_translate
                block.save()
        elif (apply_filter or goto):
            form = BlockSequencerForm(post)
            if form.is_valid():
                data = form.cleaned_data
                project_site = data['project_site']
                project_site_id = project_site and project_site.id or ''
                webpage_id = data['webpage']
                block_age = '' # data['block_age']
                translation_state = int(data['translation_state'])
                translation_languages = data['translation_languages']
                translation_codes = [l.code for l in translation_languages]
                translation_age = '' #data['translation_age']
                source_text_filter = data['source_text_filter']
                list_pages = False # data['list_pages']
    if not post or save_block or create or modify:
        translation_state = None
        translation_codes = []
        if not post and first_block:
            if filter == 'no_translate':
                translation_state = INVARIANT
            elif filter == 'already':
                translation_state = ALREADY
                translation_codes = [target_code]
        sequencer_context = request.session.get('sequencer_context', {})
        if sequencer_context:
            webpage_id = sequencer_context.get('webpage', None)
            block_age = sequencer_context.get('block_age', '')
            project_site_id = sequencer_context.get('project_site_id', '')
            translation_state = translation_state or sequencer_context.get('translation_state', TO_BE_TRANSLATED)
            translation_codes = translation_codes or sequencer_context.get('translation_codes', [])
            translation_age = sequencer_context.get('translation_age', '')
            source_text_filter = sequencer_context.get('source_text_filter', '')
            list_pages = sequencer_context.get('list_pages', False)
            request.session['sequencer_context'] = {}
        else:
            webpage_id = None
            block_age = ''
            project_site_id = ''
            translation_state = TO_BE_TRANSLATED
            translation_codes = [proxy.language.code for proxy in block.site.get_proxies()]
            translation_age = ''
            source_text_filter = ''
            list_pages = False
        webpage_id = request.GET.get('webpage', webpage_id)
        translation_languages = translation_codes and Language.objects.filter(code__in=translation_codes) or []
    sequencer_context = {}
    sequencer_context['webpage'] = webpage_id
    sequencer_context['block_age'] = block_age
    sequencer_context['project_site_id'] = project_site_id
    sequencer_context['translation_state'] = translation_state
    sequencer_context['translation_codes'] = translation_codes
    sequencer_context['translation_age'] = translation_age
    sequencer_context['source_text_filter'] = source_text_filter
    sequencer_context['list_pages'] = list_pages
    request.session['sequencer_context'] = sequencer_context
    var_dict = {}
    var_dict['page_block'] = block
    webpage = webpage_id and Webpage.objects.get(pk=webpage_id) or None
    n, previous, next = block.get_navigation(site=project_site_id, webpage=webpage, translation_state=translation_state, translation_codes=translation_codes, source_text_filter=source_text_filter)
    var_dict['n'] = n
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['site'] = site = block.site
    var_dict['language'] = block.language or site.language
    var_dict['target_languages'] = target_languages
    var_dict['pages'] = block.webpages.all()
    var_dict['list_pages'] = list_pages
    if save_block or goto:
        return HttpResponseRedirect('/block/%d/' % block.id)        
    var_dict['edit_form'] = BlockEditForm(initial={'language': block.language, 'no_translate': block.no_translate,})
    var_dict['sequencer_form'] = BlockSequencerForm(initial={'project_site': project_site_id, 'webpage': webpage_id, 'block_age': block_age, 'translation_state': translation_state, 'translation_languages': translation_languages, 'translation_age': translation_age, 'source_text_filter': source_text_filter, 'list_pages': list_pages, })
    # return render_to_response('block.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'block.html', var_dict)

# def block_translate(request, block_id):
def block_translate(request, block_id, target_code):
    block = get_object_or_404(Block, pk=block_id)
    proxy_languages = [proxy.language for proxy in block.site.get_proxies()]
    proxy_codes = [proxy.language_id for proxy in block.site.get_proxies()]
    source_language = block.get_language()
    target_language = get_object_or_404(Language, code=target_code)
    BlockSequencerForm.base_fields['translation_languages'].queryset = Language.objects.filter(code__in=proxy_codes)
    save_block = apply_filter = goto = extract = '' 
    create = modify = ''
    translated_blocks = TranslatedBlock.objects.filter(block=block, language=target_language).order_by('-modified')
    translated_block = translated_blocks.count() and translated_blocks[0] or None
    if translated_block:
        segments = translated_block.translated_block_get_segments(None)
    else:
        segments = block.block_get_segments(None)
    segments = [segment.strip() for segment in segments]
    # print (segments)
    extract_strings = False
    post = request.POST
    if post:
        save_block = post.get('save_block', '')
        # apply_filter = post.get('apply_filter', '')
        segment = request.POST.get('segment', '')
        string = request.POST.get('string', '')
        extract = request.POST.get('extract', '')
        if not save_block:
            for key in post.keys():
                if key.startswith('goto-'):
                    goto = int(key.split('-')[1])
                    block = get_object_or_404(Block, pk=goto)
                elif key.startswith('create-'):
                    create = key.split('-')[1]
                elif key.startswith('modify-'):
                    modify = key.split('-')[1]
        apply_filter = not (save_block or segment or string or extract or goto or create or modify)
        if save_block:
            form = BlockEditForm(post)
            if form.is_valid():
                data = form.cleaned_data
                language = data['language']
                no_translate = data['no_translate']
                block.language = language
                block.no_translate = no_translate
                block.save()
        elif create:
            translated_block = TranslatedBlock(block=block, language=Language.objects.get(code=create), state=PARTIALLY, editor=request.user)
            translated_block.body = post.get('translation-%s' % create)
            # print 'create: ', create, translation.body
            translated_block.save()
            segments = translated_block.translated_block_get_segments(None)
            if not segments:
                translated_block.state=TRANSLATED
                translated_block.save()
        elif modify:
            translated_block = TranslatedBlock.objects.filter(block=block, language=Language.objects.get(code=modify)).order_by('-modified')[0]
            translated_block.body = post.get('translation-%s' % modify)
            # print 'modify: ', modify, translation.body
            translated_block.save()
            segments = translated_block.translated_block_get_segments(None)
            if not segments:
                translated_block.state=TRANSLATED
                translated_block.save()
        elif (apply_filter or goto):
            form = BlockSequencerForm(post)
            if form.is_valid():
                data = form.cleaned_data
                project_site = data['project_site']
                project_site_id = project_site and project_site.id or ''
                webpage_id = data['webpage']
                block_age = '' # data['block_age']
                translation_state = int(data['translation_state'])
                translation_languages = data['translation_languages']
                translation_codes = [l.code for l in translation_languages]
                translation_age = '' #data['translation_age']
                source_text_filter = data['source_text_filter']
                extract_strings = False # data['extract_strings']
        elif extract:
            for segment in segments:
                # is_model_instance, segment_string = get_or_add_string(request, segment, source_language, site=block.site, string_type=SEGMENT, add=True)
                segment_string = get_or_add_segment(request, segment, source_language, block.site)
        elif segment:
            #is_model_instance, segment_string = get_or_add_string(request, segment, source_language, site=block.site, string_type=SEGMENT, add=True)
            segment_string = get_or_add_segment(request, segment, source_language, block.site)
        elif string:
            # is_model_instance, segment_string = get_or_add_string(request, string, source_language, site=block.site, add=True)
            segment_string = get_or_add_segment(request, string, source_language, site=block.site, add=True)
            # return HttpResponseRedirect('/segment_translate/%d/%s/' % (segment_string.id, proxy_codes[0]))
            return HttpResponseRedirect('/segment_translate/%d/%s/' % (segment_string.id, target_code))
    if (not post) or save_block or create or modify or extract or segment or string:
        sequencer_context = request.session.get('sequencer_context', {})
        if sequencer_context:
            project_site_id = sequencer_context.get('project_site_id', None)
            webpage_id = sequencer_context.get('webpage', None)
            block_age = sequencer_context['block_age']
            translation_state = sequencer_context.get('translation_state', TO_BE_TRANSLATED)
            translation_codes = sequencer_context.get('translation_codes', [proxy.language.code for proxy in block.site.get_proxies()])
            translation_age = sequencer_context.get('translation_age', '')
            source_text_filter = sequencer_context.get('source_text_filter', '')
            extract_strings = sequencer_context.get('extract_strings', False)
            request.session['sequencer_context'] = {}
        else:
            webpage_id = ''
            block_age = ''
            project_site_id = ''
            translation_state = TO_BE_TRANSLATED
            translation_codes = [proxy.language.code for proxy in block.site.get_proxies()]
            translation_age = ''
            source_text_filter = ''
            extract_strings = False
        webpage_id = request.GET.get('webpage', webpage_id)
        translation_languages = translation_codes and Language.objects.filter(code__in=translation_codes) or []
    sequencer_context = {}
    sequencer_context['webpage'] = webpage_id
    sequencer_context['block_age'] = block_age
    sequencer_context['project_site_id'] = project_site_id
    sequencer_context['translation_state'] = translation_state
    sequencer_context['translation_codes'] = translation_codes
    sequencer_context['translation_age'] = translation_age
    sequencer_context['source_text_filter'] = source_text_filter
    sequencer_context['extract_strings'] = extract_strings
    request.session['sequencer_context'] = sequencer_context
    source_segments = []
    source_strings = []
    source_translations = []
    site_invariants = text_to_list(block.site.invariant_words)
    for segment in segments:
        if not segment:
            continue
        if not non_invariant_words(segment.split(), site_invariants=site_invariants):
            continue
        if source_language == target_language:
            continue
        segment_string = get_or_add_segment(request, segment, source_language, block.site, add=False)
        if segment_string:
            like_strings = find_like_segments(segment_string, max_segments=5)
            # print (segment_string, like_strings)
            source_strings.append(like_strings)
            # translations = String.objects.filter(txu=segment_string.txu, language_id=target_code)
            translations = Translation.objects.filter(segment=segment_string, language=target_language)
            source_translations.append(translations)
        else:
            segment_string.id = 0
            source_strings.append([])
            source_translations.append([])
        source_segments.append(segment_string)
    source_segments = zip(source_segments, source_strings, source_translations)
    source_segments = list(source_segments)
    # print ('source_segments: ', source_segments)
    var_dict = {}
    var_dict['page_block'] = block
    webpage = webpage_id and Webpage.objects.get(pk=webpage_id) or None
    n, previous, next = block.get_navigation(site=project_site_id, webpage=webpage, translation_state=translation_state, translation_codes=translation_codes, source_text_filter=source_text_filter)
    var_dict['n'] = n
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['site'] = site = block.site
    var_dict['language'] = block.language or site.language
    var_dict['target_language'] = target_language
    var_dict['target_code'] = target_code
    other_codes = proxy_codes
    other_codes.remove(target_code) 
    var_dict['other_languages'] = Language.objects.filter(code__in=other_codes).order_by('code')
    if save_block or goto:
        return HttpResponseRedirect('/block/%d/translate/%s/' % (block.id, target_code) )       
    var_dict['edit_form'] = BlockEditForm(initial={'language': block.language, 'no_translate': block.no_translate,})
    var_dict['sequencer_form'] = BlockSequencerForm(initial={'project_site': project_site_id, 'webpage': webpage_id, 'block_age': block_age, 'translation_state': translation_state, 'translation_languages': translation_languages, 'translation_age': translation_age, 'source_text_filter': source_text_filter,})
    var_dict['source_segments'] = source_segments
    var_dict['translated_block'] = translated_block
    # return render_to_response('block_translate.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'block_translate.html', var_dict)

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

# srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
srx_filepath = os.path.join(settings.RESOURCES_ROOT, 'it', 'segment.srx')
srx_rules = srx_segmenter.parse(srx_filepath)
italian_rules = srx_rules['Italian']
segmenter = srx_segmenter.SrxSegmenter(italian_rules)
re_parentheses = re.compile(r'\(([^)]+)\)')

def block_pages(request, block_id):
    var_dict = {}
    var_dict['page_block'] = block = get_object_or_404(Block, pk=block_id)
    var_dict['site'] = site = block.site
    var_dict['proxies'] =  proxies = Proxy.objects.filter(site=site)
    qs = block.webpages.all()
    var_dict['page_count'] = page_count = qs.count()
    paginator = Paginator(qs, settings.PAGE_SIZE)
    page = request.GET.get('page', 1)
    try:
        block_pages = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page = 1
        block_pages = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page = paginator.num_pages
        block_pages = paginator.page(paginator.num_pages)
    var_dict['page_size'] = settings.PAGE_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    # return render_to_response('block_pages.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'block_pages.html', var_dict)

def string_view(request, string_id):
    if not request.user.is_superuser:
        return empty_page(request);
    # print (string_id)
    var_dict = {}
    var_dict['string'] = string = get_object_or_404(String, pk=string_id)
    var_dict['string_type'] = STRING_TYPE_DICT[string.string_type]
    var_dict['source_language'] = source_language = string.language
    var_dict['other_languages'] = other_languages = Language.objects.exclude(code=source_language.code).order_by('code')

    StringSequencerForm.base_fields['translation_languages'].queryset = other_languages
    string_context = request.session.get('string_context', {})
    if string_context:
        string_types = string_context.get('string_types', [])
        """
        project_site_id = string_context.get('project_site', None)
        """
        translation_state = string_context.get('translation_state', TO_BE_TRANSLATED)
        translation_codes = string_context.get('translation_codes', [l.code for l in other_languages])
        translation_subjects = string_context.get('translation_subjects', [])
        order_by = string_context.get('order_by', TEXT_ASC)
        show_similar = string_context.get('show_similar', False)
    else:
        string_types = []
        """
        project_site_id = string.site.id
        """
        translation_state = TO_BE_TRANSLATED
        translation_codes = [l.code for l in other_languages]
        translation_subjects = []
        order_by = TEXT_ASC
        show_similar = False
    translation_languages = Language.objects.filter(code__in=translation_codes)
    """
    project_site = project_site_id and Site.objects.get(pk=project_site_id) or None
    print 'project_site: ', project_site
    """

    apply_filter = goto = '' 
    post = request.POST
    if post:
        apply_filter = post.get('apply_filter', '')
        if not (apply_filter):
            for key in post.keys():
                if key.startswith('goto-'):
                    goto = int(key.split('-')[1])
                    string = get_object_or_404(String, pk=goto)
        # if (apply_filter or goto):
        form = StringSequencerForm(post)
        if form.is_valid():
            data = form.cleaned_data
            # print ('data: ', data)
            string_types = data['string_types']
            """
            project_site = data['project_site']
            project_site_id = project_site and project_site.id or ''
            """
            translation_state = int(data['translation_state'])
            translation_languages = data['translation_languages']
            translation_codes = [l.code for l in translation_languages]
            order_by = int(data['order_by'])
            show_similar = data['show_similar']
        else:
            print ('error', form.errors)
    """
    print 'project_site: ', project_site
    string_context['project_site'] = project_site_id
    """
    string_context['string_types'] = string_types
    string_context['translation_state'] = translation_state
    string_context['translation_codes'] = translation_codes
    string_context['order_by'] = order_by
    string_context['show_similar'] = show_similar
    request.session['string_context'] = string_context
    if goto:
        return HttpResponseRedirect('/string/%d/' % string.id)        
    """
    n, first, last, previous, next = string.get_navigation(string_types=string_types, site=project_site, translation_state=translation_state, translation_codes=translation_codes, order_by=order_by)
    """
    n, first, last, previous, next = string.get_navigation(string_types=string_types, translation_state=translation_state, translation_codes=translation_codes, order_by=order_by)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['last'] = last
    var_dict['translations'] = string.get_translations()
    var_dict['similar_strings'] = show_similar and find_like_strings(string, max_strings=10) or []
    """
    var_dict['sequencer_form'] = StringSequencerForm(initial={'string_types': string_types, 'project_site': project_site, 'translation_state': translation_state, 'translation_languages': translation_languages, 'order_by': order_by, 'show_similar': show_similar})
    """
    var_dict['sequencer_form'] = StringSequencerForm(initial={'string_types': string_types, 'translation_state': translation_state, 'translation_languages': translation_languages, 'order_by': order_by, 'show_similar': show_similar})
    # return render_to_response('string_view.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'string_view.html', var_dict)

@staff_member_required
def segment_view(request, segment_id):
    var_dict = {}
    var_dict['segment'] = segment = get_object_or_404(Segment, pk=segment_id)
    var_dict['source_language'] = source_language = segment.language
    # var_dict['other_languages'] = other_languages = source_language.get_other_languages()
    var_dict['other_languages'] = other_languages = segment.site.get_proxy_languages()

    SegmentSequencerForm.base_fields['translation_languages'].queryset = other_languages
    segment_context = request.session.get('segment_context', {})
    if segment_context:
        project_site_id = segment_context.get('project_site', None)
        translation_state = segment_context.get('translation_state', TO_BE_TRANSLATED)
        translation_codes = segment_context.get('translation_codes', [l.code for l in other_languages])
        translation_subjects = segment_context.get('translation_subjects', [])
        order_by = segment_context.get('order_by', TEXT_ASC)
        show_similar = segment_context.get('show_similar', False)
    else:
        project_site_id = segment.site.id
        translation_state = TO_BE_TRANSLATED
        translation_codes = [l.code for l in other_languages]
        translation_subjects = []
        order_by = TEXT_ASC
        show_similar = False
    translation_languages = Language.objects.filter(code__in=translation_codes)
    project_site = project_site_id and Site.objects.get(pk=project_site_id) or None

    apply_filter = goto = '' 
    post = request.POST
    if post:
        apply_filter = post.get('apply_filter', '')
        if not (apply_filter):
            for key in post.keys():
                if key.startswith('goto-'):
                    goto = int(key.split('-')[1])
                    segment = get_object_or_404(Segment, pk=goto)
        # if (apply_filter or goto):
        form = SegmentSequencerForm(post)
        if form.is_valid():
            data = form.cleaned_data
            project_site = data['project_site']
            project_site_id = project_site and project_site.id or ''
            translation_state = int(data['translation_state'])
            translation_languages = data['translation_languages']
            translation_codes = [l.code for l in translation_languages]
            order_by = int(data['order_by'])
            show_similar = data['show_similar']
        else:
            print ('error', form.errors)
    # print ('project_site: ', project_site)
    segment_context['translation_state'] = translation_state
    segment_context['translation_codes'] = translation_codes
    segment_context['project_site'] = project_site_id
    segment_context['order_by'] = order_by
    segment_context['show_similar'] = show_similar
    request.session['segment_context'] = segment_context
    if goto:
        return HttpResponseRedirect('/segment/%d/' % segment.id)        
    n, first, last, previous, next = segment.get_navigation(site=project_site, translation_state=translation_state, translation_languages=translation_languages, order_by=order_by)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['last'] = last
    var_dict['translations'] = segment.get_translations()
    var_dict['similar_segments'] = show_similar and find_like_segments(segment, max_segments=10) or []
    var_dict['sequencer_form'] = SegmentSequencerForm(initial={'project_site': project_site, 'translation_state': translation_state, 'translation_languages': translation_languages, 'order_by': order_by, 'show_similar': show_similar})
    var_dict['TRANSLATION_TYPE_DICT'] = TRANSLATION_TYPE_DICT
    var_dict['ROLE_DICT'] = ROLE_DICT
    return render(request, 'segment_view.html', var_dict)

@staff_member_required
def translation_align(request, translation_id):
    alignment = ''
    compute_alignment = False

    var_dict = {}
    var_dict['translation'] = translation = get_object_or_404(Translation, pk=translation_id)
    var_dict['segment'] = segment = translation.segment
    var_dict['source_language'] = segment.language
    var_dict['target_language'] = translation.language

    translation_context = request.session.get('translation_context', {})
    if translation_context:
        order_by = translation_context.get('order_by', TEXT_ASC)
        alignment_type = translation_context.get('alignment_type', ANY)
    else:
        order_by = TEXT_ASC
        alignment_type = ANY

    apply_filter = goto = '' 
    post = request.POST
    if post:
        # print('post')
        if post.get('alignment', ''):
            translation_align_form = TranslationViewForm(post)
            # print('alignment')
            if translation_align_form.is_valid():
                data = translation_align_form.cleaned_data
                alignment = data['alignment']
                # print('alignment: ', alignment)
                compute_alignment = data['compute_alignment']
        else:
            apply_filter = post.get('apply_filter', '')
            if not (apply_filter):
                for key in post.keys():
                    if key.startswith('goto-'):
                        goto = int(key.split('-')[1])
                        translation = get_object_or_404(Translation, pk=goto)
            form = TranslationSequencerForm(post)
            if form.is_valid():
                data = form.cleaned_data
                order_by = int(data['order_by'])
                alignment_type = int(data['alignment_type'])
            else:
                print ('error', form.errors)

    translation_context['order_by'] = order_by
    translation_context['alignment_type'] = alignment_type
    request.session['translation_context'] = translation_context
    if goto:
        return HttpResponseRedirect('/translation_align/%d/' % translation.id)        
    n, first, last, previous, next = translation.get_navigation(order_by=order_by, alignment_type=alignment_type)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['last'] = last

    var_dict['translation_align_form'] = TranslationViewForm(initial={'compute_alignment': compute_alignment,})
    if alignment:
        if alignment=='-':
            alignment = ''
        translation.alignment = alignment
        if post.get('save_draft_alignment'):
            translation.alignment_type = MT
        elif post.get('save_confirmed_alignment'):
            translation.alignment_type = MANUAL
        translation.save()
    else:
        alignment = translation.alignment
    var_dict['alignment'] = alignment
    var_dict['alignment_type'] = translation.alignment_type==MANUAL and 'manual' or ''
    var_dict['can_edit'] = True
    var_dict['sequencer_form'] = TranslationSequencerForm(initial={'order_by': order_by, 'alignment_type': alignment_type})
    return render(request, 'translation_align.html', var_dict)

@staff_member_required
def string_edit(request, string_id=None, language_code='', proxy_slug=''):
    user = request.user
    if not user.is_superuser:
        return empty_page(request)
    var_dict = {}
    string = string_id and get_object_or_404(String, pk=string_id) or None
    proxy = proxy_slug and get_object_or_404(Proxy, slug=proxy_slug) or None
    post = request.POST
    # print 'post: ', post
    if post:
        if post.get('cancel', ''):
            if string_id:
                return HttpResponseRedirect('/string/%s/' % string_id)
            elif proxy_slug:
                return HttpResponseRedirect('/proxy/%s/translations/' % proxy_slug)
        elif post.get('save', '') or post.get('continue', ''):
            if string:
                string_edit_form = StringEditForm(post, instance=string)
            else:
                string_edit_form = StringEditForm(post)
            if string_edit_form.is_valid():
                string = string_edit_form.save()
                if not string.user == user:
                    string.user = user
                    string.save()
                if post.get('save', ''):
                    return HttpResponseRedirect('/string/%d/' % string.id)
    else:
        if string:
            string_edit_form = StringEditForm(instance=string)
        else:
            string_type = SEGMENT
            if proxy_slug:
                proxy = get_object_or_404(Proxy, slug=proxy_slug)
                site = proxy.site
                language = site.language
            elif language_code:
                site = None
                language = get_object_or_404(Language, code=language_code)
            else:
                site = None
                language = None
            reliability = 5
            text = ''
            path = ''
            user = request.user           
            string_edit_form = StringEditForm(initial={'string_type': string_type, 'site': site, 'language': language, 'reliability': reliability, 'text': text, 'path': path, 'user': user })
    var_dict['string'] = string
    var_dict['proxy'] = proxy
    var_dict['translations'] = string and string.get_translations() or []
    var_dict['string_edit_form'] = string_edit_form
    # return render_to_response('string_edit.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'string_edit.html', var_dict)

def string_translate(request, string_id, target_code):
    if not request.user.is_superuser:
        return empty_page(request);
    var_dict = {}
    var_dict['string'] = string = get_object_or_404(String, pk=string_id)
    var_dict['string_type'] = STRING_TYPE_DICT[string.string_type]
    var_dict['source_language'] = source_language = string.language
    var_dict['target_code'] = target_code
    var_dict['target_language'] = target_language = Language.objects.get(code=target_code)
    translation_codes = [target_code]
    translation_languages = Language.objects.filter(code=target_code)

    StringSequencerForm.base_fields['translation_languages'].queryset = translation_languages

    string_context = request.session.get('string_context', {})
    if string_context:
        string_types = string_context.get('string_types', [])
        project_site_id = string_context.get('project_site', None)
        translation_state = string_context.get('translation_state', TO_BE_TRANSLATED)
        translation_codes = string_context.get('translation_codes', [target_code])
        translation_services = string_context.get('translation_services', [])
        translation_subjects = string_context.get('translation_subjects', [])
        order_by = string_context.get('order_by', TEXT_ASC)
        show_similar = string_context.get('show_similar', False)
    else:
        string_types = []
        project_site_id = string.site.id
        translation_state = TO_BE_TRANSLATED
        translation_codes = [target_code]
        translation_services = []
        translation_subjects = []
        order_by = TEXT_ASC
        show_similar = False
    project_site = project_site_id and Site.objects.get(pk=project_site_id) or None

    translation_form = StringTranslationForm()
    translation_service_form = TranslationServiceForm()
    apply_filter = goto = save_translation = '' 
    post = request.POST
    if post:
        apply_filter = post.get('apply_filter', '')
        ask_service = post.get('ask_service', '')
        """
        save_translation = post.get('save_translation', '')
        if not (apply_filter or ask_service or save_translation):
        """
        if not (apply_filter or ask_service):
            for key in post.keys():
                if key.startswith('goto-'):
                    goto = int(key.split('-')[1])
                    string = get_object_or_404(String, pk=goto)
                elif key.startswith('save-'):
                    save_translation = key.split('-')[1]
        if ask_service:
            translation_service_form = TranslationServiceForm(request.POST)
            if translation_service_form.is_valid():
                data = translation_service_form.cleaned_data
                translation_services = data['translation_services']
                if str(MYMEMORY) in translation_services:
                    langpair = '%s|%s' % (source_language.code, target_code)
                    status, translatedText, external_translations = ask_mymemory(string.text, langpair)
                    var_dict['external_translations'] = external_translations
                    var_dict['translation_service'] = TRANSLATION_SERVICE_DICT[MYMEMORY]
            else:
                print ('error', translation_service_form.errors)
            translation_form = StringTranslationForm()
        elif save_translation:
            translation_form = StringTranslationForm(request.POST)
            if translation_form.is_valid():
                data = translation_form.cleaned_data
                # print (data)
                translation = data['translation']
                site = data['translation_site']
                translation_subjects = data['translation_subjects']
                same_txu = data['same_txu']
                txu = string.txu
                if txu and same_txu:
                    target_txu = string.txu
                else:
                    provider = site and site.name or ''
                    target_txu = Txu(provider=provider, user=request.user)
                    target_txu.save()
                is_model_instance, target = get_or_add_string(request, translation, target_language, site=project_site, string_type=string.string_type, add=True, txu=target_txu, reliability=5)
                if not txu or not same_txu:
                    string.txu = target_txu
                    string.reliability = 5
                    string.save()
                for subject in translation_subjects:
                    try:
                        txu_subject = TxuSubject.objects.get(txu=txu, subject=subject)
                    except:
                        txu_subject = TxuSubject(txu=target_txu, subject=subject)
                        txu_subject.save()
            else:
                print ('error', translation_form.errors)
                # return render_to_response('string_translate.html', {'translation_form': translation_form,}, context_instance=RequestContext(request))
                return render(request, 'string_translate.html', {'translation_form': translation_form,})
            translation_service_form = TranslationServiceForm()
        else: # apply_filter
            form = StringSequencerForm(post)
            if form.is_valid():
                data = form.cleaned_data
                string_types = data['string_types']
                project_site = data['project_site']
                project_site_id = project_site and project_site.id or ''
                translation_state = int(data['translation_state'])
                translation_languages = data['translation_languages']
                translation_codes = [l.code for l in translation_languages]
                order_by = int(data['order_by'])
                show_similar = data['show_similar']
    string_context['project_site'] = project_site_id
    string_context['translation_state'] = translation_state
    string_context['translation_codes'] = translation_codes
    string_context['translation_subjects'] = translation_subjects
    string_context['order_by'] = order_by
    string_context['show_similar'] = show_similar
    request.session['string_context'] = string_context
    if goto:
        return HttpResponseRedirect('/string_translate/%d/%s/' % (string.id, target_code))
    # previous, next = string.get_navigation(translation_state=translation_state, translation_codes=translation_codes)
    n, first, last, previous, next = string.get_navigation(string_types=string_types, site=project_site, translation_state=translation_state, translation_codes=translation_codes, order_by=order_by)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['last'] = last
    var_dict['similar_strings'] = show_similar and find_like_strings(string, translation_languages=[target_language], with_translations=True, max_strings=10) or []
    # var_dict['translations'] = string.get_translations(target_languages=[target_language])
    var_dict['translations'] = string.get_translations()
    # var_dict['sequencer_form'] = StringSequencerForm(initial={'translation_state': translation_state, 'translation_languages': translation_languages, })
    var_dict['sequencer_form'] = StringSequencerForm(initial={'string_types': string_types, 'project_site': project_site, 'translation_state': translation_state, 'translation_languages': translation_languages, 'order_by': order_by, 'show_similar': show_similar})
    # var_dict['translation_form'] = StringTranslationForm(initial={'translation_site': translation_site, 'translation_subjects': translation_subjects,})
    var_dict['translation_form'] = StringTranslationForm(initial={'translation_site': project_site, 'translation_subjects': translation_subjects,})
    var_dict['translation_service_form'] = translation_service_form
    # return render_to_response('string_translate.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'string_translate.html', var_dict)

@staff_member_required
def segment_edit(request, segment_id=None, language_code='', proxy_slug=''):
    user = request.user
    if not user.is_superuser:
        return empty_page(request)
    var_dict = {}
    segment = segment_id and get_object_or_404(Segment, pk=segment_id) or None
    proxy = proxy_slug and get_object_or_404(Proxy, slug=proxy_slug) or None
    post = request.POST
    # print 'post: ', post
    if post:
        if post.get('cancel', ''):
            if segment_id:
                return HttpResponseRedirect('/segment/%s/' % segment_id)
            elif proxy_slug:
                return HttpResponseRedirect('/proxy/%s/translations/' % proxy_slug)
        elif post.get('save', '') or post.get('continue', ''):
            if segment:
                segment_edit_form = SegmentEditForm(post, instance=segment)
            else:
                segment_edit_form = SegmentEditForm(post)
            if segment_edit_form.is_valid():
                segment = segment_edit_form.save()
                if post.get('save', ''):
                    return HttpResponseRedirect('/segment/%d/' % segment.id)
    else:
        if segment:
            segment_edit_form = SegmentEditForm(instance=segment)
        else:
            if proxy_slug:
                proxy = get_object_or_404(Proxy, slug=proxy_slug)
                site = proxy.site
                language = site.language
            elif language_code:
                site = None
                language = get_object_or_404(Language, code=language_code)
            else:
                site = None
                language = None
            text = ''
            user = request.user           
            segment_edit_form = SegmentEditForm(initial={'site': site, 'text': text })
    var_dict['segment'] = segment
    var_dict['proxy'] = proxy
    var_dict['translations'] = segment and segment.get_translations() or []
    var_dict['segment_edit_form'] = segment_edit_form
    return render(request, 'segment_edit.html', var_dict)

def segment_translate(request, segment_id, target_code):
    if not request.user.is_superuser:
        return empty_page(request);
    var_dict = {}
    var_dict['segment'] = segment = get_object_or_404(Segment, pk=segment_id)
    var_dict['source_language'] = source_language = segment.language
    var_dict['target_code'] = target_code
    var_dict['target_language'] = target_language = Language.objects.get(code=target_code)
    """
    var_dict['other_languages'] = source_language.get_other_languages()
    translation_codes = [target_code]
    translation_languages = Language.objects.filter(code=target_code)
    """
    var_dict['other_languages'] = other_languages = segment.site.get_proxy_languages()
    translation_languages= other_languages
    translation_codes = [l.code for l in translation_languages]

    SegmentSequencerForm.base_fields['translation_languages'].queryset = translation_languages

    segment_context = request.session.get('segment_context', {})
    if segment_context:
        project_site_id = segment_context.get('project_site', None)
        translation_state = segment_context.get('translation_state', TO_BE_TRANSLATED)
        translation_codes = segment_context.get('translation_codes', [l.code for l in other_languages])
        order_by = segment_context.get('order_by', TEXT_ASC)
        show_similar = segment_context.get('show_similar', False)
    else:
        project_site_id = segment.site.id
        translation_state = TO_BE_TRANSLATED
        translation_codes = [l.code for l in other_languages]
        order_by = TEXT_ASC
        show_similar = False
    translation_languages = Language.objects.filter(code__in=translation_codes)
    project_site = project_site_id and Site.objects.get(pk=project_site_id) or None

    translation_form = SegmentTranslationForm()
    translation_service_form = TranslationServiceForm()
    apply_filter = goto = save_translation = '' 
    post = request.POST
    if post:
        apply_filter = post.get('apply_filter', '')
        ask_service = post.get('ask_service', '')
        if not (apply_filter or ask_service):
            for key in post.keys():
                if key.startswith('goto-'):
                    goto = int(key.split('-')[1])
                    segment = get_object_or_404(Segment, pk=goto)
                elif key.startswith('save-'):
                    save_translation = key.split('-')[1]
        if ask_service:
            translation_service_form = TranslationServiceForm(request.POST)
            if translation_service_form.is_valid():
                data = translation_service_form.cleaned_data
                translation_services = data['translation_services']
                external_translations = []
                if str(GOOGLE) in translation_services:
                    response = ask_gt(segment.text, target_code)
                    if response.get('detectedSourceLanguage', '').startswith(source_language.code):
                        external_translations = [{ 'segment': response.get('input', ''), 'translation': response.get('translatedText', ''), 'service': TRANSLATION_SERVICE_DICT[GOOGLE] }]
                if str(MYMEMORY) in translation_services:
                    langpair = '%s|%s' % (source_language.code, target_code)
                    """
                    status, translatedText, external_translations = ask_mymemory(segment.text, langpair)
                    var_dict['external_translations'] = external_translations
                    var_dict['translation_service'] = TRANSLATION_SERVICE_DICT[MYMEMORY]
                    """
                    status, translatedText, mymemory_translations = ask_mymemory(segment.text, langpair)
                    for external_translation in mymemory_translations:
                        external_translation['service'] = TRANSLATION_SERVICE_DICT[MYMEMORY]
                        external_translations.append(external_translation)
                var_dict['external_translations'] = external_translations
            else:
                print ('error', translation_service_form.errors)
            translation_form = SegmentTranslationForm()
        elif save_translation:
            translation_form = SegmentTranslationForm(request.POST)
            if translation_form.is_valid():
                data = translation_form.cleaned_data
                # print (data)
                translation_text = data['translation']
                translation = get_or_add_translation(request, segment, translation_text, target_language)
            else:
                print ('error', translation_form.errors)
                # return render_to_response('segment_translate.html', {'translation_form': translation_form,}, context_instance=RequestContext(request))
                return render(request, 'segment_translate.html', {'translation_form': translation_form,})
            translation_service_form = TranslationServiceForm()
        else: # apply_filter
            form = SegmentSequencerForm(post)
            if form.is_valid():
                data = form.cleaned_data
                project_site = data['project_site']
                project_site_id = project_site and project_site.id or ''
                translation_state = int(data['translation_state'])
                translation_languages = data['translation_languages']
                translation_codes = [l.code for l in translation_languages]
                order_by = int(data['order_by'])
                show_similar = data['show_similar']
    segment_context['project_site'] = project_site_id
    segment_context['translation_state'] = translation_state
    segment_context['translation_codes'] = translation_codes
    segment_context['order_by'] = order_by
    segment_context['show_similar'] = show_similar
    request.session['segment_context'] = segment_context
    if goto:
        return HttpResponseRedirect('/segment_translate/%d/%s/' % (segment.id, target_code))
    n, first, last, previous, next = segment.get_navigation(site=project_site, translation_state=translation_state, translation_languages=translation_languages, order_by=order_by)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['last'] = last
    var_dict['similar_segments'] = show_similar and find_like_segments(segment, translation_languages=[target_language], with_translations=True, max_segments=10) or []
    var_dict['translations'] = segment.get_translations()
    var_dict['sequencer_form'] = SegmentSequencerForm(initial={ 'project_site': project_site, 'translation_state': translation_state, 'translation_languages': translation_languages, 'order_by': order_by, 'show_similar': show_similar})
    var_dict['translation_form'] = SegmentTranslationForm()
    var_dict['translation_service_form'] = translation_service_form
    var_dict['TRANSLATION_TYPE_DICT'] = TRANSLATION_TYPE_DICT
    var_dict['ROLE_DICT'] = ROLE_DICT
    # return render_to_response('segment_translate.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'segment_translate.html', var_dict)

def raw_tokens(text, language_code):
    tokens = re.split(" |\'", text)
    raw_tokens = []
    for token in tokens:
        # token = token.strip(STRIPPED[language_code])
        token = token.strip(settings.DEFAULT_STRIPPED)
        if not token:
            continue
        raw_tokens.append(token)
    return raw_tokens     

def filtered_tokens(text, language_code, tokens=[], truncate=False, min_chars=10):
    """
    tokenize a text according to the language and strips some delimiter chars
    drop short tokens; remove last char
    """
    if not tokens:
        tokens = raw_tokens(text, language_code)
    filtered_tokens = []
    for token in tokens:
        n_chars = len(token)
        if n_chars < min_chars:
            continue
        if token in settings.EMPTY_WORDS[language_code]:
            continue
        filtered_tokens.append(token)
    return filtered_tokens

def find_like_strings(source_string, translation_languages=[], with_translations=False, min_chars=3, max_strings=10, min_score=0.4):
    """
    source_string is an object of type String
    we look for similar strings of the same language
    first we use fuzzy search (more_like_this)
    then we find strings containing some of the same tokens
    """
    min_chars_times_10 = min_chars*10
    language = source_string.language
    language_code = language.code
    hits = list(SearchQuerySet().more_like_this(source_string))
    if not hits:
        return []
    source_tokens = filtered_tokens(source_string.text, language_code, truncate=True, min_chars=min_chars)
    source_set = set(source_tokens)
    like_strings = []
    for hit in hits:
        if not hit.language_code == language_code:
            continue
        try: # the index could be not in sync
            string = String.objects.get(language=language, text=hit.text)
        except:
            continue
        if with_translations:
            translations = string.get_translations(target_languages=translation_languages)
            if not translations:
                continue
        text = string.text
        tokens = raw_tokens(text, language_code)
        l = len(tokens)
        tokens = filtered_tokens(text, language_code, tokens=tokens, truncate=True, min_chars=min_chars)
        l = float(len(source_tokens) + l + len(tokens))/3
        like_set = set(tokens)
        i = len(like_set.intersection(source_set))
        if not i:
            continue
        # core  formula
        similarity_score = float(i * sqrt(i)) / sqrt(l)
        # print similarity_score, text
        # add a small pseudo-random element to compensate for the bias in the results of more_like_this
        correction = float(len(text) % min_chars) / min_chars_times_10
        similarity_score += correction
        if similarity_score < min_score:
            continue
        if with_translations:
            like_strings.append([similarity_score, string, translations])
        else:
            like_strings.append([similarity_score, string])
    like_strings.sort(key=lambda x: x[0], reverse=True)
    return like_strings[:max_strings]

def find_like_segments(source_segment, translation_languages=[], with_translations=False, min_chars=3, max_segments=10, min_score=0.4):
    """
    source_segment is an object of type Segment; we look for similar segments of the same language
    first we use fuzzy search, then we find segments containing some of the same tokens
    """
    min_chars_times_10 = min_chars*10
    language = source_segment.language
    language_code = language.code
    hits = source_segment.more_like_this(target_languages=translation_languages, limit=max_segments)
    if not hits.count():
        return []
    source_tokens = filtered_tokens(source_segment.text, language_code, truncate=True, min_chars=min_chars)
    source_set = set(source_tokens)
    like_segments = []
    for segment in hits:
        if with_translations:
            translations = segment.get_translations(target_language=translation_languages)
        text = segment.text
        tokens = raw_tokens(text, language_code)
        l = len(tokens)
        tokens = filtered_tokens(text, language_code, tokens=tokens, truncate=True, min_chars=min_chars)
        l = float(len(source_tokens) + l + len(tokens))/3
        like_set = set(tokens)
        i = len(like_set.intersection(source_set))
        if not i:
            continue
        """ core  formula """
        similarity_score = float(i * sqrt(i)) / sqrt(l)
        # print similarity_score, text
        """ add a small pseudo-random element to compensate for the bias in the results of more_like_this """
        correction = float(len(text) % min_chars) / min_chars_times_10
        similarity_score += correction
        if similarity_score < min_score:
            continue
        if with_translations:
            like_segments.append([similarity_score, segment, translations])
        else:
            like_segments.append([similarity_score, segment])
    like_segments.sort(key=lambda x: x[0], reverse=True)
    return like_segments

def strings_translations(request, proxy_slug=None, state=None):
    """
    list translations from source language (code) to target language (code)
    NOW REPLACED BY function list_segments
    """
    if not request.user.is_superuser:
        return empty_page(request);
    # PAGE_SIZE = 100
    tm_edit_context = request.session.get('tm_edit_context', {})
    translation_state = state or tm_edit_context.get('translation_state', 0)
    proxy = proxy_slug and Proxy.objects.get(slug=proxy_slug) or None
    if proxy:
        project_site = proxy.site
        project_site_id = project_site.id
        source_language = project_site.language
        source_language_code = source_language.code
        target_language = proxy.language
        target_language_code = target_language.code
    else:
        project_site_id = tm_edit_context.get('project_site', None)
        project_site = project_site_id and Site.objects.get(pk=project_site_id) or None
        source_language_code = project_site and project_site.language_id or tm_edit_context.get('source_language', None)
        source_language = source_language_code and Language.objects.get(code=source_language_code) or None
        target_language_code = tm_edit_context.get('target_language', None)
        target_language = target_language_code and Language.objects.get(code=target_language_code) or None
        if project_site and target_language:
            proxies = Proxy.objects.filter(site=project_site, language=target_language)
            if proxies:
                proxy = proxies[0]
    source_text_filter = tm_edit_context.get('source_text_filter', '')
    target_text_filter = tm_edit_context.get('target_text_filter', '')
    show_other_targets = tm_edit_context.get('show_other_targets', False)
    tm_edit_context['project_site'] = project_site_id
    tm_edit_context['source_language'] = source_language_code
    tm_edit_context['target_language'] = target_language_code
    request.session['tm_edit_context'] = tm_edit_context
    if request.method == 'POST':
        post = request.POST
        form = StringsTranslationsForm(post)
        if post.get('delete-segment', ''):
            selection = post.getlist('selection')
            # print ('delete-segment', selection)
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                if txu:
                    for string in String.objects.filter(txu=txu):
                        string.delete()
                    txu.delete()
                else:
                    string.delete()
        elif post.get('delete-translation', ''):
            selection = post.getlist('selection')
            # print ('delete-translation', selection)
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                if txu:
                    translations = String.objects.filter(txu=txu, language=target_language)
                    for string in translations:
                        string.delete()
        elif post.get('make-invariant', ''):
            selection = post.getlist('selection')
            # print ('make-invariant', selection)
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                string.txu = None
                string.invariant = True
                string.save()
                if txu:
                    for string in String.objects.filter(txu=txu):
                        string.delete()
                    txu.delete()
        elif post.get('toggle-invariant', ''):
            selection = post.getlist('selection')
            # print ('toggle-invariant', selection)
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                if string.invariant:
                    string.invariant = False
                    string.save()
                    # print ('True-> False')
                elif not string.txu:
                    string.invariant = True
                    string.save()
                    # print ('False-> True')
        elif form.is_valid():
            data = form.cleaned_data
            tm_edit_context['translation_state'] = translation_state = int(data['translation_state'])
            project_site = data['project_site']
            tm_edit_context['project_site'] = project_site and project_site.id or None
            source_language = data['source_language']
            tm_edit_context['source_language'] = source_language and source_language.code or None
            target_language = data['target_language']
            tm_edit_context['target_language'] = target_language and target_language.code or None
            tm_edit_context['source_text_filter'] = source_text_filter = data['source_text_filter']
            tm_edit_context['target_text_filter'] = target_text_filter = data['target_text_filter']
            tm_edit_context['show_other_targets'] = show_other_targets = data['show_other_targets']
            request.session['tm_edit_context'] = tm_edit_context
            if project_site and target_language:
                proxies = Proxy.objects.filter(site=project_site, language=target_language)
                proxy = proxies and proxies[0] or None
    else:
        form = StringsTranslationsForm(initial={'project_site': project_site, 'translation_state': translation_state, 'source_language': source_language, 'target_language': target_language, 'source_text_filter': source_text_filter, 'target_text_filter': target_text_filter, 'show_other_targets': show_other_targets, })

    if translation_state == TRANSLATED:
        translated = True
    elif translation_state == TO_BE_TRANSLATED:
        translated = False
    else:
        translated = None

    var_dict = {}
    var_dict['proxy'] = proxy
    var_dict['site'] = project_site_id and Site.objects.get(pk=project_site_id) or None
    var_dict['state'] = translation_state
    var_dict['source_language'] = source_language
    var_dict['target_language'] = target_language
    var_dict['show_other_targets'] = show_other_targets

    if project_site and translation_state == INVARIANT:
        qs = String.objects.filter(site=project_site, invariant=True)
    else:
        qs = find_strings(source_languages=[source_language], target_languages=[target_language], site=project_site, translated=translated, order_by='')
    if source_text_filter:
        qs = qs.filter(text__icontains=source_text_filter)
    if target_text_filter:
        qs = qs.filter(txu__string__text__icontains=target_text_filter)
    qs = qs.order_by('text')
    string_count = qs.count()
    var_dict['string_count'] = string_count
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
    var_dict['page_size'] = settings.PAGE_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    var_dict['strings'] = strings
    var_dict['strings_translations_form'] = form
    # return render_to_response('strings_translations.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'strings_translations.html', var_dict)

# def list_segments(request, proxy_slug=None, state=None):
def list_segments(request, state=None):
    """
    list translations from source language (code) to target language (code)
    """
    if not request.user.is_superuser:
        return empty_page(request);
    # PAGE_SIZE = 100
    tm_edit_context = request.session.get('tm_edit_context', {})
    translation_state = state or tm_edit_context.get('translation_state', 0)
    """
    proxy = proxy_slug and Proxy.objects.get(slug=proxy_slug) or None
    if proxy:
        project_site = proxy.site
        project_site_id = project_site.id
        source_language = project_site.language
        source_language_code = source_language.code
        target_language = proxy.language
        target_language_code = target_language.code
    else:
        project_site_id = tm_edit_context.get('project_site', None)
        project_site = project_site_id and Site.objects.get(pk=project_site_id) or None
        source_language_code = project_site and project_site.language_id or tm_edit_context.get('source_language', None)
        source_language = source_language_code and Language.objects.get(code=source_language_code) or None
        target_language_code = tm_edit_context.get('target_language', None)
        target_language = target_language_code and Language.objects.get(code=target_language_code) or None
        if project_site and target_language:
            proxies = Proxy.objects.filter(site=project_site, language=target_language)
            if proxies:
                proxy = proxies[0]
    """
    id = request.GET.get('id', None)
    segment = id and Segment.objects.get(pk=id) or None
    project_site = segment and segment.site or None
    if not project_site:
        project_site_id = tm_edit_context.get('project_site', None)
        project_site = project_site_id and Site.objects.get(pk=project_site_id) or None
    if project_site:
        project_site_id = project_site.id
        source_language = project_site.language
    else:
        source_language = None
    if source_language:
        source_language_code = source_language.code
    else:
        source_language_code = tm_edit_context.get('source_language', None)
        source_language = source_language_code and Language.objects.get(code=source_language_code) or None
    target_language_code = tm_edit_context.get('target_language', None)
    target_language = target_language_code and Language.objects.get(code=target_language_code) or None

    source_text_filter = tm_edit_context.get('source_text_filter', '')
    target_text_filter = tm_edit_context.get('target_text_filter', '')
    show_other_targets = tm_edit_context.get('show_other_targets', False)
    show_alignments = tm_edit_context.get('show_alignments', False)
    tm_edit_context['project_site'] = project_site_id
    tm_edit_context['source_language'] = source_language_code
    tm_edit_context['target_language'] = target_language_code
    request.session['tm_edit_context'] = tm_edit_context
    if request.method == 'POST':
        post = request.POST
        form = ListSegmentsForm(post)
        if post.get('delete-segment', ''):
            selection = post.getlist('selection')
            for segment_id in selection:
                segment = Segment.objects.get(pk=int(segment_id))
                segment.delete()
        elif post.get('delete-translation', ''):
            selection = post.getlist('selection')
            for segment_id in selection:
                segment = Segment.objects.get(pk=int(segment_id))
                translations = segment.get_translations(target_language=target_language)
                for translation in translations:
                    translation.delete()
        elif post.get('make-invariant', ''):
            selection = post.getlist('selection')
            for segment_id in selection:
                segment = Segment.objects.get(pk=int(segment_id))
                segment.is_invariant = True
                segment.save()
        elif post.get('toggle-invariant', ''):
            selection = post.getlist('selection')
            for segment_id in selection:
                segment = Segment.objects.get(pk=int(segment_id))
                if segment.is_invariant:
                    segment.is_invariant = False
                else:
                    segment.is_invariant = True
                segment.save()
        elif form.is_valid():
            data = form.cleaned_data
            tm_edit_context['translation_state'] = translation_state = int(data['translation_state'])
            project_site = data['project_site']
            tm_edit_context['project_site'] = project_site and project_site.id or None
            source_language = data['source_language']
            tm_edit_context['source_language'] = source_language and source_language.code or None
            target_language = data['target_language']
            tm_edit_context['target_language'] = target_language and target_language.code or None
            tm_edit_context['source_text_filter'] = source_text_filter = data['source_text_filter']
            tm_edit_context['target_text_filter'] = target_text_filter = data['target_text_filter']
            tm_edit_context['show_other_targets'] = show_other_targets = data['show_other_targets']
            tm_edit_context['show_alignments'] = show_alignments = data['show_alignments']
            request.session['tm_edit_context'] = tm_edit_context
            """
            if project_site and target_language:
                proxies = Proxy.objects.filter(site=project_site, language=target_language)
                proxy = proxies and proxies[0] or None
            """
            if post.get('add-segment', '') and project_site and source_language and source_text_filter:
                segment, created = Segment.objects.get_or_create(site=project_site, language=source_language, text=source_text_filter)
    else:
        form = ListSegmentsForm(initial={'project_site': project_site, 'translation_state': translation_state, 'source_language': source_language, 'target_language': target_language, 'source_text_filter': source_text_filter, 'target_text_filter': target_text_filter, 'show_other_targets': show_other_targets, })

    if translation_state == TRANSLATED:
        translated = True
    elif translation_state == TO_BE_TRANSLATED:
        translated = False
    else:
        translated = None

    var_dict = {}
    # var_dict['proxy'] = proxy
    var_dict['site'] = project_site_id and Site.objects.get(pk=project_site_id) or None
    var_dict['state'] = translation_state
    var_dict['source_language'] = source_language
    var_dict['target_language'] = target_language
    var_dict['show_other_targets'] = show_other_targets
    var_dict['show_alignments'] = show_alignments
    var_dict['other_languages'] = Language.objects.exclude(code=target_language_code).order_by('code')

    if project_site and translation_state == INVARIANT:
        qs = Segment.objects.filter(site=project_site, is_invariant=True)
    else:
        qs = find_segments(source_languages=[source_language], target_languages=[target_language], site=project_site, translated=translated, order_by='')
    if source_text_filter:
        qs = qs.filter(text__icontains=source_text_filter)
    if target_text_filter:
        qs = qs.filter(segment_translation__text__icontains=target_text_filter)
    qs = qs.order_by('text')
    segment_count = qs.count()
    var_dict['segment_count'] = segment_count
    if id:
        index = qs.filter(text__lt=segment.text).count()
        page = index/settings.PAGE_SIZE + 1
        print ('index, page =', index, page)
    else:
        page = request.GET.get('page', 1)
    paginator = Paginator(qs, settings.PAGE_SIZE)
    try:
        segments = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page = 1
        segments = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page = paginator.num_pages
        segments = paginator.page(paginator.num_pages)
    var_dict['page_size'] = settings.PAGE_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    var_dict['segments'] = segments
    var_dict['list_segments_form'] = form
    # return render_to_response('list_segments.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'list_segments.html', var_dict)

def list_segments_by_proxy(request, proxy_slug):
    proxy = get_object_or_404(Proxy, slug=proxy_slug)
    tm_edit_context = request.session.get('tm_edit_context', {})
    tm_edit_context['project_site'] = proxy.site.id
    tm_edit_context['target_language'] = proxy.language.code
    request.session['tm_edit_context'] = tm_edit_context
    return HttpResponseRedirect('/list_segments/')    

def list_segments_by_id(request, segment_id):
    segment = get_object_or_404(Segment, pk=segment_id)
    # return list_segments(request, site=segment.site, id=segment_id)
    tm_edit_context = request.session.get('tm_edit_context', {})
    tm_edit_context['project_site'] = segment.site.id
    request.session['tm_edit_context'] = tm_edit_context
    return HttpResponseRedirect('/list_segments/?id='+segment_id)    

def add_update_translation(request):
    if request.is_ajax() and request.method == 'POST':
        form = request.POST
        site_id = int(form.get('site_id', 0))
        segment_id = int(form.get('segment_id'))
        source_code = form.get('source_code')
        target_code = form.get('target_code')
        translation_id = int(form.get('translation_id', 0))
        target_text = form.get('target_text')
        segment = Segment.objects.get(pk=segment_id)
        """
        user_role_id = get_userrole(request)
        if user_role_id:
            user_role = UserRole.objects.get(pk=user_role_id)
        else:
            user_role = None
            # user_roles = UserRole.objects.filter(user=request.user, source_language_id=source_code, target_language_id=target_code, role_type__lt=GUEST).order_by('role_type')
            user_roles = UserRole.objects.filter(user=request.user).order_by('role_type')
            for ur in user_roles:
                if ur.source_language and ur.source_language.id != source_code:
                    continue
                if ur.target_language and ur.target_language.id != target_code:
                    continue
                if not ur.site or (ur.site.id == site_id):
                    user_role = ur
                    break
        """
        target_language = Language.objects.get(code=target_code)
        user_role = get_or_set_user_role(request, site=segment.site, source_language=segment.language, target_language=target_language)
        if not user_role:
            pass # eccezione
        if translation_id:
            Translation.objects.filter(pk=translation_id).update(text=target_text, translation_type=MANUAL, user_role=user_role, timestamp=timezone.now())
            return JsonResponse({"data": "modify",})
        else:
            translation = Translation(segment=segment, language_id=target_code, text=target_text, translation_type=MANUAL, user_role=user_role, timestamp=timezone.now())
            translation.save()
            translation_id = translation.id
            return JsonResponse({"data": "add","translation_id": translation_id,})
    return empty_page(request);

def proxy_string_translations(request, proxy_slug=None, state=None):
    """
    list translations from source language (code) to target language (code)
    """
    if not request.user.is_superuser:
        return empty_page(request);
    # PAGE_SIZE = 100
    proxy = proxy_slug and Proxy.objects.get(slug=proxy_slug) or None

    tm_edit_context = request.session.get('tm_edit_context', {})
    translation_state = state or tm_edit_context.get('translation_state', 0)
    project_site_id = proxy and proxy.site.id or tm_edit_context.get('project_site', None)
    project_site = project_site_id and Site.objects.get(pk=project_site_id) or None
    source_language_code = project_site and project_site.language_id or tm_edit_context.get('source_language', None)
    source_language = source_language_code and Language.objects.get(code=source_language_code) or None
    target_language_code = proxy and proxy.language_id or tm_edit_context.get('target_language', None)
    target_language = target_language_code and Language.objects.get(code=target_language_code) or None
    source_text_filter = tm_edit_context.get('source_text_filter', '')
    target_text_filter = tm_edit_context.get('target_text_filter', '')
    show_other_targets = tm_edit_context.get('show_other_targets', False)
    if proxy:
        tm_edit_context['project_site'] = project_site_id
        tm_edit_context['source_language'] = source_language_code
        tm_edit_context['target_language'] = target_language_code
        request.session['tm_edit_context'] = tm_edit_context
    if request.method == 'POST':
        post = request.POST
        form = StringsTranslationsForm(post)
        if post.get('delete-segment', ''):
            selection = post.getlist('selection')
            # print ('delete-segment', selection)
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                if txu:
                    for string in String.objects.filter(txu=txu):
                        string.delete()
                    txu.delete()
                else:
                    string.delete()
        elif post.get('delete-translation', ''):
            selection = post.getlist('selection')
            # print ('delete-translation', selection)
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                if txu:
                    translations = String.objects.filter(txu=txu, language=target_language)
                    for string in translations:
                        string.delete()
        elif post.get('make-invariant', ''):
            selection = post.getlist('selection')
            # print ('make-invariant', selection)
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                string.txu = None
                string.invariant = True
                string.save()
                if txu:
                    for string in String.objects.filter(txu=txu):
                        string.delete()
                    txu.delete()
        elif post.get('toggle-invariant', ''):
            selection = post.getlist('selection')
            # print ('toggle-invariant', selection)
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                if string.invariant:
                    string.invariant = False
                    string.save()
                    # print ('True-> False')
                elif not string.txu:
                    string.invariant = True
                    string.save()
                    # print ('False-> True')
        elif form.is_valid():
            data = form.cleaned_data
            tm_edit_context['translation_state'] = translation_state = int(data['translation_state'])
            project_site = data['project_site']
            tm_edit_context['project_site'] = project_site and project_site.id or None
            source_language = data['source_language']
            tm_edit_context['source_language'] = source_language and source_language.code or None
            target_language = data['target_language']
            tm_edit_context['target_language'] = target_language and target_language.code or None
            tm_edit_context['source_text_filter'] = source_text_filter = data['source_text_filter']
            tm_edit_context['target_text_filter'] = target_text_filter = data['target_text_filter']
            tm_edit_context['show_other_targets'] = show_other_targets = data['show_other_targets']
            request.session['tm_edit_context'] = tm_edit_context
    else:
        form = StringsTranslationsForm(initial={'project_site': project_site, 'translation_state': translation_state, 'source_language': source_language, 'target_language': target_language, 'source_text_filter': source_text_filter, 'target_text_filter': target_text_filter, 'show_other_targets': show_other_targets, })

    if translation_state == TRANSLATED:
        translated = True
    elif translation_state == TO_BE_TRANSLATED:
        translated = False
    else:
        translated = None

    var_dict = {}
    var_dict['proxy'] = proxy
    var_dict['site'] = project_site_id and Site.objects.get(pk=project_site_id) or None
    var_dict['state'] = translation_state
    var_dict['source_language'] = source_language
    var_dict['target_language'] = target_language
    var_dict['show_other_targets'] = show_other_targets

    if project_site and translation_state == INVARIANT:
        qs = String.objects.filter(site=project_site, invariant=True)
    else:
        qs = find_strings(source_languages=[source_language], target_languages=[target_language], site=project_site, translated=translated, order_by='')
    if source_text_filter:
        qs = qs.filter(text__icontains=source_text_filter)
    if target_text_filter:
        qs = qs.filter(txu__string__text__icontains=target_text_filter)
    qs = qs.order_by('text')
    string_count = qs.count()
    var_dict['string_count'] = string_count
    paginator = Paginator(qs, settings.PAGE_SIZE)
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
    var_dict['page_size'] = settings.PAGE_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    var_dict['strings'] = strings
    var_dict['strings_translations_form'] = form
    # return render_to_response('proxy_string_translations.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'proxy_string_translations.html', var_dict)

def add_translated_string(request):
    user = request.user
    user_id = user.id
    if request.is_ajax() and request.method == 'POST':
        form = request.POST
        source_id = int(form.get('source_id'))
        translated_id = int(form.get('translated_id'))
        txu_id = int(form.get('txu_id'))
        translation = form.get('translation')
        target_language = form.get('t_l')
        source_language = form.get('s_l')
        site_name = form.get('site_name')
        target_language = Language.objects.get(name=target_language)
        source_language = Language.objects.get(name=source_language)
        reliability = 5
        if (txu_id == 0):
            # print ('txu non esiste')
            target_txu = Txu(provider=site_name, user=request.user)
            target_txu.save()
            target_txu_id = target_txu.id
            # print (target_txu_id)
            string = String.objects.filter(pk=source_id).update(txu=target_txu.id)
            string_new = String(text=translation, language=target_language, txu=target_txu, site=None, reliability=reliability, invariant=False)
            string_new.save()
            translated_new_id = string_new.id
            # print (translated_new_id)
            return JsonResponse({"data": "add-txt-string","txu_id": target_txu_id,"translated_id": translated_new_id,})
        else:
            string = String.objects.filter(pk=translated_id)
            if string:
                # print ('txu esiste update stringa')
                string.update(text=translation)
                return JsonResponse({"data": "modify-string",})
            else:
                # print ('txu esiste nuova stringa')
                string_new = String(txu_id=txu_id, language=target_language, site=None, text=translation, reliability=reliability, invariant=False)
                string_new.save()
                translated_new_id = string_new.id
                return JsonResponse({"data": "add-string","translated_id": translated_new_id,})
    return empty_page(request);

def add_segment_translation(request):
    if request.is_ajax() and request.method == 'POST':
        form = request.POST
        source_id = int(form.get('source_id'))
        translation_id = int(form.get('translation_id'))
        translated_text = form.get('translation')
        target_language = form.get('t_l')
        source_language = form.get('s_l')
        site_name = form.get('site_name')
        target_language = Language.objects.get(name=target_language)
        source_language = Language.objects.get(name=source_language)
        segment = Segment.objects.filter(pk=source_id)
        """
        user_role = get_userrole(request)
        if not user_role:
            user_role = UserRole.objects.filter(user=request.user, source_language=source_language, target_language=target_language).order_by('role_type')[0]
        """
        user_role = get_or_set_user_role(request, site=segment.site, source_language=source_language, target_language=target_language)
        try:
            translation = Translation.objects.get(segment=segment, language=target_language)
        except:
            translation = Translation(segment=segment, language=target_language)
        translation.text = translated_text
        translation.translation_type = MANUAL
        translation.user_role = user_role
        translation.timestamp = timezone.now()
        translation.save()
        return JsonResponse({"data": "segment-translation", "segment_id": segment.id,"translation_id": translation.id})
    return empty_page(request);

def delete_translated_string(request):
    if request.is_ajax() and request.method == 'GET':
        form = request.GET
        source_id = int(form.get('source_id'))
        translated_id = int(form.get('translated_id'))
        txu_id = int(form.get('txu_id'))
        # print (source_id)
        return JsonResponse({"data": "delete-string",})
    return empty_page(request);
    
def list_strings(request, sources, state, targets=[]):
    """
    list strings in the source languages with translations in the target languages
    """
    if not request.user.is_superuser:
        return empty_page(request);
    post = request.POST
    if post and post.get('delete_strings', ''):
        string_ids = post.getlist('delete')
        if string_ids:
            strings = String.objects.filter(id__in=string_ids)
            for string in strings:
                string.delete()
    # PAGE_SIZE = 100
    var_dict = {}
    var_dict['sources'] = sources
    var_dict['state'] = state
    var_dict['targets'] = targets
    source_languages = target_languages = []
    translated = None
    can_delete = False
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
        can_delete = not targets and request.user.is_superuser
    else:
        translated = None
    var_dict['can_delete'] = can_delete
    var_dict['source_languages'] = source_languages
    var_dict['target_languages'] = target_languages
    var_dict['target_codes'] = [l.code for l in target_languages]
    qs = find_strings(source_languages=source_languages, target_languages=target_languages, translated=translated)
    var_dict['string_count'] = qs.count()
    paginator = Paginator(qs, settings.PAGE_SIZE)
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
    var_dict['page_size'] = settings.PAGE_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    var_dict['strings'] = strings
    # return render_to_response('list_strings.html', var_dict, context_instance=RequestContext(request))
    return render(request, 'list_strings.html', var_dict)

# def find_strings(source_languages=[], target_languages=[], translated=None, site=None):
def find_strings(source_languages=[], target_languages=[], translated=None, site=None, order_by=None):
    if isinstance(source_languages, Language):
        source_languages = [source_languages]
    if isinstance(target_languages, Language):
        target_languages = [target_languages]
    source_codes = [l.code for l in source_languages]
    target_codes = [l.code for l in target_languages]
    qs = String.objects
    if site:
        qs = qs.filter(site=site)
    if source_languages:
        source_codes = [l.code for l in source_languages]
        qs = qs.filter(language_id__in=source_codes)
    if translated is None:
        if not source_languages:
            qs = qs.all()
    elif translated: # translated = True
        if target_languages:
            # qs = qs.filter(as_source__target_code__in=target_codes).distinct()
            qs = qs.filter(txu__string__language_id__in=target_codes).distinct()
        """
        else:
            qs = qs.filter(as_source__isnull=False)
        """
    else: # translated = False
        if target_languages:
            """
            qs = qs.exclude(txu__string__language_id__in=target_codes)
            """
            qs = qs.exclude(invariant=True)
            if 'en' in target_codes:
                qs = qs.filter(Q(txu__isnull=True) | Q(txu__en=False))
            if 'es' in target_codes:
                qs = qs.filter(Q(txu__isnull=True) | Q(txu__es=False))
            if 'fr' in target_codes:
                qs = qs.filter(Q(txu__isnull=True) | Q(txu__fr=False))
            if 'it' in target_codes:
                qs = qs.filter(Q(txu__isnull=True) | Q(txu__it=False))
        """
        else:
            qs = qs.filter(as_source__isnull=True)
        """
    # return qs.order_by('language', 'text')
    if order_by is None:
        qs = qs.order_by('language', 'text')
    elif order_by:
        qs = qs.order_by(order_by)
    return qs

def find_segments(source_languages=[], target_languages=[], translated=None, site=None, order_by=None):
    if isinstance(source_languages, Language):
        source_languages = [source_languages]
    if isinstance(target_languages, Language):
        target_languages = [target_languages]
    source_codes = [l.code for l in source_languages]
    target_codes = [l.code for l in target_languages]
    qs = Segment.objects
    if site:
        qs = qs.filter(site=site)
    if source_languages:
        source_codes = [l.code for l in source_languages]
        qs = qs.filter(language_id__in=source_codes)
    if translated is None:
        if not source_languages:
            qs = qs.all()
    elif translated: # translated = True
        if target_languages:
            qs = qs.filter(segment_translation__language_id__in=target_codes).distinct()
    else: # translated = False
        if target_languages:
            qs = qs.exclude(segment_translation__language_id__in=target_codes).distinct()
    if order_by is None:
        qs = qs.order_by('language', 'text')
    elif order_by:
        qs = qs.order_by(order_by)
    return qs

def get_language(language_code):
    return Language.objects.get(code=language_code)

def user_scans(request, username=None):
    if request.method == 'POST':
        post = request.POST
        if post.get('delete-scan', ''):
            selection = post.getlist('selection')
            # print ('delete-scan', selection)
            for scan_id in selection:
                scan = Scan.objects.get(pk=int(scan_id))
                scan.delete()
    data_dict = {}
    if username:
        user = User.objects.get(username=username)
        scans = Scan.objects.filter(user=user).order_by('-created')
    else:
        user = None
        scans = Scan.objects.all().order_by('-created')
    data_dict['user'] = user  
    data_dict['scans'] = scans  
    # return render_to_response('user_scans.html', data_dict, context_instance=RequestContext(request))
    return render(request, 'user_scans.html', data_dict)

def my_scans(request):
    return user_scans(request, username=request.user.username)

def scan_detail(request, scan_id):
    data_dict = {}
    scan = Scan.objects.get(pk=scan_id)
    links = Link.objects.filter(scan=scan).order_by('created')
    lines = []
    for link in links:
        line = {"url": link.url, "status": link.status, "title": link.title, "encoding": link.encoding, "size": link.size, "encoding": link.encoding}
        lines.append(line)
    data_dict['scan'] = scan
    data_dict['lines'] = lines
    # return render_to_response('scan_detail.html', data_dict, context_instance=RequestContext(request))
    return render(request, 'scan_detail.html', data_dict)

def scan_pages(request, scan_id):
    scan = Scan.objects.get(pk=scan_id)
    output = request.GET.get('output', '')
    links = Link.objects.filter(scan=scan).order_by('created')
    lines = []
    if output == 'csv':
        data = u'\r\n'.join(['%s\t%d\t%d\t%s\t%s' % (link.url, link.status, link.size, link.title, link.encoding) for link in links])
        response = HttpResponse(data, content_type='application/octet-stream')
        filename = u'%s_pages.csv' % (scan.get_label())
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response
    for link in links:
        line = {"url": link.url, "status": link.status, "title": link.title, "encoding": link.encoding, "size": link.size, "encoding": link.encoding}
        lines.append(line)
    data_dict = {}
    data_dict['scan'] = scan
    data_dict['lines'] = lines
    # return render_to_response('scan_pages.html', data_dict, context_instance=RequestContext(request))
    return render(request, 'scan_pages.html', data_dict)

def scan_words(request, scan_id):
    scan = Scan.objects.get(pk=scan_id)
    sort = request.GET.get('sort', 'frequency')
    output = request.GET.get('output', '')
    wordcounts = WordCount.objects.filter(scan=scan)
    if sort.lower().startswith('a'):
        wordcounts = wordcounts.order_by('word')
        sorted_by = 'sorted alphabetically'
    else:
        wordcounts = wordcounts.order_by('-count')
        sorted_by = 'by frequency'
    wordcounts = [wordcount for wordcount in wordcounts if len(wordcount.word)>1 and not re.sub('[\'\.\,\+\-\/\%\:\°]', '', wordcount.word).isdigit()]
    if output == 'csv':
        data = u'\r\n'.join(['%d\t%s' % (wordcount.count, wordcount.word) for wordcount in wordcounts])
        response = HttpResponse(data, content_type='application/octet-stream')
        filename = u'%s_words_%s.csv' % (scan.get_label(), sort)
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response
    lines = []
    for wordcount in wordcounts:
        line = {"count": wordcount.count, "word": wordcount.word}
        lines.append(line)
    data_dict = {}
    data_dict['scan'] = scan
    data_dict['sorted_by'] = sorted_by
    data_dict['lines'] = lines
    # return render_to_response('scan_words.html', data_dict, context_instance=RequestContext(request))
    return render(request, 'scan_words.html', data_dict)

def scan_segments(request, scan_id):
    scan = Scan.objects.get(pk=scan_id)
    sort = request.GET.get('sort', 'frequency')
    output = request.GET.get('output', '')
    segmentcounts = SegmentCount.objects.filter(scan=scan)
    if sort.lower().startswith('a'):
        segmentcounts = segmentcounts.order_by('segment')
        sorted_by = 'sorted alphabetically'
    else:
        segmentcounts = segmentcounts.order_by('-count')
        sorted_by = 'by frequency'
    if output == 'csv':
        data = u'\r\n'.join(['%d\t%s' % (segmentcount.count, segmentcount.segment) for segmentcount in segmentcounts])
        response = HttpResponse(data, content_type='application/octet-stream')
        filename = u'%s_segments_%s.csv' % (scan.get_label(), sort)
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response
    lines = []
    for segmentcount in segmentcounts:
        line = {"count": segmentcount.count, "segment": segmentcount.segment}
        lines.append(line)
    data_dict = {}
    data_dict['scan'] = scan
    data_dict['sorted_by'] = sorted_by
    data_dict['lines'] = lines
    # return render_to_response('scan_segmentss.html', data_dict, context_instance=RequestContext(request))
    return render(request, 'scan_segments.html', data_dict)

def scan_delete(request, scan_id):
    scan = Scan.objects.get(pk=scan_id)
    user = scan.user
    links = Link.objects.filter(scan=scan)
    for link in links:
        link.delete()
    scan.delete()
    return HttpResponseRedirect('/user_scans/%s/' % user.username)    
    
def crawler_progress(request, scan_id, i_line):
    i_line = int(i_line)
    scan = Scan.objects.get(pk=scan_id)
    links = Link.objects.filter(scan=scan).order_by('created')[i_line:]
    lines = []
    for link in links:
        if i_line >= scan.max_pages:
            scan.terminated = True
            scan.save()
            break
        i_line += 1
        line = {"url": link.url, "status": link.status, "title": link.title, "encoding": link.encoding, "size": link.size}
        lines.append(line)
    if scan.terminated:
        lines.append({"size": 0})
    return JsonResponse({'lines': lines,})

def scan_download(request, scan_id):
    scan = Scan.objects.get(pk=scan_id)
    lines = []
    links = Link.objects.filter(scan=scan).order_by('created')
    for link in links:
        line = '%s %d "%s" %d %s' % (link.url, link.status, link.title, link.size, link.encoding)
        lines.append(line)
    data = u'\r\n'.join(lines)
    response = HttpResponse(data, content_type='application/octet-stream')
    filename = u'%s.txt' % scan.get_label()
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response

from scrapy.spiders import Rule #, CrawlSpider
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerProcess
from .spiders import WipSiteCrawlerScript, WipDiscoverScript, WipCrawlSpider

from celery.utils.log import get_task_logger
from celery.task.control import revoke
from celery.bin import worker
from billiard.process import Process
from .celery_apps import app
from .utils import get_celery_worker_stats

def run_worker():
    w = worker.worker(app=app)
    options = {}
    w.run(**options)

def run_worker_process():
    i = 0
    pid = None
    stats = get_celery_worker_stats()
    for key, value in stats.items():
        if key.startswith('celery@'):
            pid = value.get('pid', None)
    if pid:
        print ('--- worker is running ---')
    else:
        print ('--- running worker ---')
        p = Process(target=run_worker, args=[])
        p.start()
        while not pid and i < 10:
            i += 1
            time.sleep(3)
            stats = get_celery_worker_stats()
            for key, value in stats.items():
                if key.startswith('celery@'):
                    pid = value.get('pid', None)
    return pid

def stop_crawler(request, scan_id):
    scan = Scan.objects.get(pk=scan_id)
    task_id = scan.task_id
    print ('--- stopping task %s ---' % task_id)
    revoke(task_id, terminate=True)
    scan.terminated = True
    scan.save()
    return JsonResponse({'status': 'ok',})

@app.task()
def discover_task(scan_id):
    crawler_script = WipDiscoverScript()
    return crawler_script.crawl(scan_id)

def discover(request, site=None, scan_id=None):
    user = request.user    # assert user.is_authenticated()
    assert user.is_authenticated()
    data_dict = {}
    post = request.POST
    if site or scan_id or not post:
        if site:
            initial = {'site': site, 'name': site.name, 'deny': site.deny, 'max_pages': 100,}
            allowed_domains = site.get_allowed_domains() or [site.url.split('//')[-1]]
            initial['allowed_domains'] = '\n'.join(allowed_domains)
            start_urls = site.get_start_urls() or [site.url]
            initial['start_urls'] =  '\n'.join(start_urls)
        elif scan_id:
            scan = Scan.objects.get(pk=scan_id)
            initial = {'site': scan.site, 'name': scan.name, 'allowed_domains': scan.allowed_domains, 'start_urls': scan.start_urls, 'deny': scan.deny, 'max_pages': scan.max_pages,}
        else:
            initial = {'max_pages': 100,}
        form = DiscoverForm(initial=initial)
    else:
        form = DiscoverForm(post)
        if form.is_valid():
            data = form.cleaned_data
            name = data['name'] or 'discover'
            site = data['site']
            allowed_domains = data['allowed_domains']
            start_urls = data['start_urls']
            allow = data['allow']
            deny = data['deny']
            max_pages = data['max_pages']
            count_words = data['count_words']
            count_segments = data['count_segments']
            run_worker_process()
            scan = Scan(name=name, allowed_domains=allowed_domains, start_urls=start_urls, allow=allow, deny=deny, max_pages=max_pages, count_words=count_words, count_segments=count_segments, task_id=0, user=user)
            scan.save()
            async_result = discover_task.delay(scan.pk)
            scan.task_id = async_result.task_id
            scan.save()
            data_dict['task_id'] = scan.task_id
            data_dict['scan_id'] = scan.pk
            data_dict['scan_label'] = scan.get_label()
            data_dict['i_line'] = 0
    data_dict['discover_form'] = form
    # return render_to_response('discover.html', data_dict, context_instance=RequestContext(request))
    return render(request, 'discover.html', data_dict)

def site_crawl(site_pk):
    crawler_script = WipSiteCrawlerScript()
    site = Site.objects.get(pk=site_pk)
    crawler_script.crawl(
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
        print ('site_crawl_by_slug : ', site_slug)
        """
        crawl_site.apply_async(args=(site.id,))
        """
        # task_id = crawl_site.delay(site.id)
        run_worker_process()
        task_id = crawl_site_task.delay(site.id)
        print ('task id: ', task_id)
    return HttpResponseRedirect('/site/%s/' % site_slug)

@app.task()
# def crawl_site(site_pk):
def crawl_site_task(site_pk):
    logger = get_task_logger(__name__)
    logger.info('Crawling site {0}'.format(site_pk))
    return site_crawl(site_pk)

if settings.USE_NLTK:

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
            filepath = os.path.join(settings.DATA_ROOT, filename)
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
            tagger = NltkTagger(language=language, tagger_input_file=os.path.join(settings.DATA_ROOT, settings.tagger_filename))
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
    
    def page_scan(request, fetched_id, language='it'):
        string = request.GET.get('strings', False)
        tag = request.GET.get('tag', False)
        chunk = request.GET.get('chunk', False)
        ext = request.GET.get('ext', False)
        string = tag = chunk = True
        if tag or chunk or ext:
            tagger = NltkTagger(language=language, tagger_input_file=os.path.join(settings.DATA_ROOT, settings.tagger_filename))
        if chunk or ext:
            chunker = NltkChunker(language='it')
        var_dict = {} 
        var_dict['scan'] = fetched = get_object_or_404(PageVersion, pk=fetched_id)
        var_dict['page'] = page = fetched.webpage
        var_dict['site'] = site = page.site
        page = fetched.webpage
        site = page.site
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
                    if string.count('window') and string.count('document'):
                        continue
                    if tag or chunk:
                        tagged_tokens = tagger.tag(text=string)
                        if tag:
                            tags.extend(tagged_tokens)
                    if chunk:
                        noun_chunks = chunker.main_chunker(tagged_tokens, chunk_tag='NP')
                        chunks.extend(noun_chunks)
                    if not (tag or chunk):
                        """
                        matches = []
                        if string.count('(') and string.count(')'):
                            matches = re_parentheses.findall(string)
                            if matches:
                                for match in matches:
                                    string = string.replace('(%s)' % match, '')
                        """
                        # strings.extend(segmenter.extract(string)[0])
                        strings.extend(segments_from_string(string, site, segmenter))
                        """
                        for match in matches:
                            strings.extend(segmenter.extract(match)[0])
                        """
                        if ext:
                            terms = extract_terms(string, language=language, tagger=tagger, chunker=chunker)
                            terms = ['- %s -' % term for term in terms]
                            strings.extend(terms)
                var_dict['tags'] = tags
                var_dict['chunks'] = chunks
        # return render_to_response('page_scan.html', var_dict, context_instance=RequestContext(request))
        return render(request, 'page_scan.html', var_dict)
