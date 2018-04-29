# -*- coding: utf-8 -*-"""

"""
see: Django's CBVs were a mistake
http://lukeplant.me.uk/blog/posts/djangos-cbvs-were-a-mistake/
"""

import sys
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
from collections import defaultdict

from haystack.query import SearchQuerySet
# from search_indexes import StringIndex
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, render_to_response, get_object_or_404
from django.db import connection
# from django.db.models import Q, Count
from django.db.models.expressions import RawSQL, Q
from django import forms
from django.views import View
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from actstream import action, registry

from .wip_nltk.tokenizers import NltkTokenizer
from .models import Language, Site, ServiceSubscription, Proxy, Webpage, PageVersion, TranslatedVersion
from .models import Block, BlockEdge, TranslatedBlock, BlockInPage
from .models import filter_blocks
from .models import Scan, Link, WordCount, SegmentCount
from .models import UserRole, Segment, Translation
from .models import segments_from_string, non_invariant_words
from .models import ID_ASC, TEXT_ASC, COUNT_DESC
from .models import ANY, TO_BE_TRANSLATED, TRANSLATED, PARTIALLY, REVISED, INVARIANT, ALREADY
from .models import ROLE_DICT, TRANSLATION_TYPE_DICT, TRANSLATION_SERVICE_CHOICES, TRANSLATION_SERVICE_DICT, GOOGLE, DEEPL, MICROSOFT, MYMEMORY
from .models import ADMINISTRATOR, OWNER, MANAGER, LINGUIST, TRANSLATOR, CLIENT
from .models import TM, MT, MANUAL
from .models import PARALLEL_FORMAT_NONE, PARALLEL_FORMAT_XLIFF, PARALLEL_FORMAT_TEXT
from .models import DISCOVER, CRAWL, BACKGROUND, FOREGROUND
from .models import get_or_set_user_role
from .models import get_segments, filter_segments
from .forms import DiscoverForm, CrawlForm
from .forms import SiteManageForm, ProxyManageForm, PageManageForm, PageSequencerForm, BlockEditForm, BlockSequencerForm
from .forms import SegmentSequencerForm, SegmentEditForm, SegmentTranslationForm, TranslationViewForm, TranslationSequencerForm
from .forms import TranslationServiceForm, FilterPagesForm
from .forms import UserRoleEditForm, ListSegmentsForm, ImportXliffForm
from .session import get_language, set_language, get_site, set_site, get_userrole, set_userrole
# from .utils import strings_from_html, elements_from_element, block_checksum
from .deepl import translate as ask_deepl
from .microsoft import translate as ask_microsofttranslator
from .utils import ask_mymemory, ask_gt, text_to_list # , non_invariant_words
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
    current_role = get_or_set_user_role(request)
    original_sites = [site for site in original_sites if site.can_view(current_role)]

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
    return render(request, 'homepage.html', var_dict)

def language(request, language_code):
    set_language(request, language_code or '')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def my_roles(request, site=None):
    qs = UserRole.objects.filter(user=request.user)
    if site:
        qs = qs.filter(site=site)
    return qs.order_by('role_type', 'site', 'target_language__code', '-level')

def user_role_select(request, role_id):
    get_object_or_404(UserRole, pk=role_id)
    set_userrole(request, int(role_id))
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def manage_roles(request):
    user = request.user
    post = request.method=='POST' and request.POST or None
    if post:
        delete_roles = post.get('delete-roles', '')
        if delete_roles:
            selection = post.getlist('selection')
            for role_id in selection:
                role = UserRole.objects.get(pk=role_id)
                role.delete()
    qs = UserRole.objects.none()
    my_role = get_or_set_user_role(request)
    role_type = my_role.role_type
    if role_type == ADMINISTRATOR:
        qs = UserRole.objects.all()
    elif role_type == OWNER:
        qs = UserRole.objects.filter(site=my_role.site, role_type__gt=role_type)
    else:
        qs = UserRole.objects.filter(user=user)
    user_roles = qs.order_by('role_type', 'site', 'target_language__code', '-level')
    var_dict = {}
    var_dict['user_roles'] = user_roles
    return render(request, 'manage_roles.html', var_dict)

def role_detail(request, role_id):
    user_role = UserRole.objects.get(pk=role_id)
    var_dict = {}
    var_dict['user_role'] = user_role
    var_dict['can_edit'] = request.user.is_superuser
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
            return render(request, 'role_edit.html', { 'form': form })
    else:
        if role_id:
            user_role = get_object_or_404(UserRole, pk=role_id)
            form = UserRoleEditForm(instance=user_role)
        else:
            form = UserRoleEditForm()
        return render(request, 'role_edit.html', { 'user_role': user_role, 'form': form })

def sites(request):
    var_dict = {}
    current_role = get_or_set_user_role(request)
    sites = Site.objects.all().order_by('name')
    sites = [site for site in sites if site.can_view(current_role)]
    var_dict['sites'] = sites
    return render(request, 'sites.html', var_dict)

def proxies(request):
    var_dict = {}
    proxies = Proxy.objects.all().order_by('site__name')
    var_dict['proxies'] = proxies
    return render(request, 'proxies.html', var_dict)

def site(request, site_slug):
    user = request.user
    current_role = get_or_set_user_role(request)
    site = get_object_or_404(Site, slug=site_slug)
    set_site(request, site_slug)
    var_dict = {}
    var_dict['site'] = site
    var_dict['can_manage'] = site.can_manage(user)
    var_dict['can_operate'] = site.can_operate(user)
    var_dict['can_view'] = site.can_view(current_role)
    var_dict['proxies'] =  proxies = site.get_proxies()
    var_dict['proxy_languages'] = proxy_languages = [proxy.language for proxy in proxies]
    words_distribution = site.get_token_frequency(lowercasing=True)
    var_dict['word_count'] = len(words_distribution)
    post = request.method=='POST' and request.POST or None
    if post:
        discovery = post.get('discover', '')
        site_crawl = post.get('site_crawl', '')
        extract_blocks = post.get('extract_blocks', '')
        purge_blocks = post.get('purge_blocks', '')
        refetch_pages = post.get('refetch_pages', '')
        refresh_segments_in_use = post.get('refresh_segments_in_use', '')
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
                # return discover(request, site=site)
                return HttpResponseRedirect('/discover/%s/' % site.slug)
            elif site_crawl:
                clear_pages = data['clear_pages']
                if clear_pages:
                    Webpage.objects.filter(site=site).delete()
                return HttpResponseRedirect('/crawl/%s/' % site.slug)
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
                    extracted_blocks = webpage.extract_blocks()
                    webpage.purge_bips(current_blocks=extracted_blocks)
                    webpage.create_blocks_dag()
            elif refetch_pages:
                """
                n_pages, n_updates, n_unfound = site.refetch_pages(verbose=verbose, user=request.user)
                messages.add_message(request, messages.INFO, 'Requested %d pages: %d updated, %d unfound' % (n_pages, n_updates, n_unfound))
                """
                n_pages, n_skipped, n_updated, n_unfound = site.refetch_pages(verbose=verbose, user=request.user)
                messages.add_message(request, messages.INFO, 'Requested %d pages: %d skipped, %d updated, %d unfound' % (n_pages, n_skipped, n_updated, n_unfound))
            elif refresh_segments_in_use:
                site.refresh_segments_in_use()
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
                    # download_list = []
                    segments_dict = defaultdict(int)
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
                    segments = page_version.page_version_get_segments(segmenter=segmenter)
                    if dry:
                        print (path)
                        continue
                    for s in segments:
                        if download_segments:
                            """
                            if not s in download_list:
                                # download_list.append(s)
                            """
                            segments_dict[s] += 1
                        else:
                            get_or_add_segment(request, s, language, site, add=True)
                        # sys.stdout.write('.')
                if download_segments:
                    # messages.add_message(request, messages.INFO, 'Downloaded %d segments.' % len(download_list))
                    download_list = sorted(segments_dict, key=segments_dict.get, reverse=True)
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
                                if Segment.objects.filter(site=site, text=line, is_invariant=True):
                                    d += 1
                                else:
                                    segment = Segment(language=language, site=site, text=line, is_invariant=True)
                                    segment.save()
                                    n += 1
                            except:
                                pass
                                # print ('error: ', i)
                    messages.add_message(request, messages.INFO, 'Imported %d invariants out of %d (%d repetitions).' % (n, m, d))
                else:
                    messages.add_message(request, messages.ERROR, 'Please, select a file to upload.')
            elif apply_invariants:
                blocks = Block.objects.filter(site=site, language__isnull=True, no_translate=False)
                if blocks:
                    segmenter = site.make_segmenter()
                    site_invariants = text_to_list(site.invariant_words)
                n_invariants = 0
                n_in_language = 0
                for block in blocks:
                    segments = block.block_get_segments(segmenter)
                    if block.apply_invariants(segmenter, segments=segments, site_invariants=site_invariants):
                        n_invariants += 1
                    elif block.apply_language(segmenter, segments=segments, site_invariants=site_invariants):
                        n_in_language += 1
                messages.add_message(request, messages.INFO, '%d blocks marked as invariant or in some language.' % n_invariants)
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
    post = request.method=='POST' and request.POST or None
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
                time_stamp = datetime.datetime.now().strftime('%y%m%d-%H-%M-%S')
                translation_state = int(data['translation_state'])
                parallel_format = int(data['parallel_format'])
                if parallel_format==PARALLEL_FORMAT_XLIFF: # XLIFF
                    data = proxy.build_xliff_export(translation_state=translation_state)
                    response = HttpResponse(data, content_type='application/xliff+xml')
                    filename = '%s_translations.%s.xlf' % (proxy.slug, time_stamp)
                elif parallel_format==PARALLEL_FORMAT_TEXT: # plain_text
                    data = proxy.build_parallel_text_export(translation_state=translation_state)
                    response = HttpResponse(data, content_type='text/plain')
                    filename = '%s_translations.%s.txt' % (proxy.slug, time_stamp)
                response['Content-Disposition'] = 'attachment; filename="%s"' % filename
                return response
            elif align_translations or evaluate_aligner:
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
                # n_ready, n_translated, n_partially = proxy.apply_translation_memory()
                n_ready, n_translated, n_partially = proxy.apply_tm()
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
    var_dict['segments_summary'] = proxy.segments_summary()
    
    var_dict['translated_pages_count'] = page_count = TranslatedVersion.objects.filter(webpage__site=site, language=language).count()
    # var_dict['translated_blocks_count'] = TranslatedBlock.objects.filter(block__site=site, language=language).count()
    var_dict['translated_blocks_count'] = translated_blocks_count = TranslatedBlock.objects.filter(block__site=site, state=TRANSLATED, language_id=proxy.language_id).count()
    var_dict['partially_blocks_count'] = partially_blocks_count = TranslatedBlock.objects.filter(block__site=site, state=PARTIALLY, language_id=proxy.language_id).count()
    var_dict['left_blocks_count'] = blocks_total - blocks_invariant - translated_blocks_count - partially_blocks_count
    var_dict['blocks_ready'] = blocks_ready = proxy.blocks_ready()
    var_dict['ready_count'] = len(blocks_ready)
    var_dict['manage_form'] = form # ProxyManageForm()
    return render(request, 'proxy.html', var_dict)

def import_xliff(request, proxy_slug):
    proxy = get_object_or_404(Proxy, slug=proxy_slug)
    site = proxy.site
    var_dict = {}
    var_dict['proxy'] = proxy
    post = request.method=='POST' and request.POST or None
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
    proxies = site.get_proxies()
    var_dict['proxy_languages'] = proxy_languages = [proxy.language for proxy in proxies]
    proxy_codes = [l.code for l in proxy_languages]
    var_dict['scans'] = PageVersion.objects.filter(webpage=webpage).order_by('-time')
    PageSequencerForm.base_fields['translation_languages'].queryset = Language.objects.filter(code__in=proxy_codes)
    save_page = apply_filter = goto = '' 
    fetch_page = purge_blocks = extract_blocks = ''
    post = request.method=='POST' and request.POST or None
    if post:
        save_page = post.get('save_page', '')
        fetch_page = post.get('fetch_page', '')
        purge_blocks = post.get('purge_blocks', '')
        extract_blocks = post.get('extract_blocks', '')
        # apply_filter = post.get('apply_filter', '')
        apply_filter = not (save_page or fetch_page or purge_blocks or extract_blocks)
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
            translation_codes = proxy_codes
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
    # previous, next = webpage.get_navigation(translation_state=translation_state, translation_codes=translation_codes)
    n, first, last, previous, next = webpage.get_navigation(translation_state=translation_state, translation_codes=translation_codes)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['last'] = last
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
    # qs = Block.objects.filter(site=site).order_by('xpath')
    qs = site.get_blocks_in_use().order_by('id')
    var_dict['block_count'] = qs.count()
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
    return render(request, 'blocks.html', var_dict)

def site_translated_blocks(request, site_slug):
    var_dict = {}
    site = get_object_or_404(Site, slug=site_slug)
    var_dict['site'] = site
    var_dict['translated_blocks'] = blocks = TranslatedBlock.objects.filter(block__site=site)
    var_dict['translated_blocks_count'] = blocks.count()
    return render(request, 'translated_blocks.html', var_dict)

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
    if translation_type:
        translations = translations.filter(translation_type=translation_type)
    if translations:
        translation = translations[0]
    else:
        translation = Translation(segment=segment, text=text, language=language, translation_type=translation_type, user_role=user_role, timestamp=timezone.now())
        if len(segment.text.split())==1 and len(text.split())==1:
            translation.alignment = '0-0'
            translation.alignment_type = MANUAL
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
    first_block = block = None
    site_slug = request.GET.get('site', '')
    if int(block_id) == 0:
        filter = request.GET.get('filter', '')
        target_code = request.GET.get('lang', '')
        webpage_id = request.GET.get('page', '')
        translation_state = None
        translation_codes = []
        if filter:
            webpage = None
            sequencer_context = request.session.get('sequencer_context', {})
            if site_slug:
                site = get_object_or_404(Site, slug=site_slug)
                sequencer_context['project_site_id'] = site.id
                sequencer_context['webpage'] = None
            elif webpage_id:
                webpage = get_object_or_404(Webpage, pk=webpage_id)
                site = webpage.site
                sequencer_context['project_site_id'] = site.id
                sequencer_context['webpage'] = webpage.id
            if target_code:
                sequencer_context['translation_codes'] = translation_codes = [target_code]
            if filter == 'invariant':
                sequencer_context['translation_state'] = translation_state = INVARIANT
            elif filter == 'already' and target_code:
                sequencer_context['translation_state'] = translation_state = ALREADY
            elif filter == 'to_be_translated' and target_code:
                sequencer_context['translation_state'] = translation_state = TO_BE_TRANSLATED
            elif filter == 'partially' and target_code:
                sequencer_context['translation_state'] = translation_state = PARTIALLY
            elif filter == 'translated' and target_code:
                sequencer_context['translation_state'] = translation_state = TRANSLATED
            elif filter == 'revised' and target_code:
                sequencer_context['translation_state'] = REVISED
            sequencer_context['source_text_filter'] = ''
            request.session['sequencer_context'] = sequencer_context
            blocks = filter_blocks(site=site, webpage=webpage, translation_state=translation_state, translation_codes=[target_code])
            if blocks:
                first_block = block = blocks.order_by('id')[0]
    else:
        block = get_object_or_404(Block, pk=block_id)
    site = block.site
    proxy_languages = block and [proxy.language for proxy in block.site.get_proxies()] or []
    proxy_codes = [l.code for l in proxy_languages]
    target_languages = [l for l in proxy_languages if not l == block.language]
    BlockSequencerForm.base_fields['translation_languages'].queryset = Language.objects.filter(code__in=proxy_codes)
    save_block = apply_filter = goto = create = modify = '' 
    post = request.method=='POST' and request.POST or None
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
                # print ('2 save_block', language, no_translate)
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
        sequencer_context = request.session.get('sequencer_context', {})
        # if sequencer_context and not site_slug:
        if sequencer_context:
            webpage_id = sequencer_context.get('webpage', None)
            block_age = sequencer_context.get('block_age', '')
            project_site_id = sequencer_context.get('project_site_id', None) or block.site.id
            translation_state = sequencer_context.get('translation_state', TO_BE_TRANSLATED)
            translation_codes = sequencer_context.get('translation_codes', [])
            translation_age = sequencer_context.get('translation_age', '')
            source_text_filter = sequencer_context.get('source_text_filter', '')
            list_pages = sequencer_context.get('list_pages', False)
            request.session['sequencer_context'] = {}
            print ('post:', post)
        else:
            webpage_id = None
            block_age = ''
            project_site_id = block.site.id
            translation_state = TO_BE_TRANSLATED
            translation_codes = [proxy.language.code for proxy in block.site.get_proxies()]
            translation_age = ''
            source_text_filter = ''
            list_pages = False
        webpage_id = request.GET.get('webpage', webpage_id)
        translation_languages = translation_codes and Language.objects.filter(code__in=translation_codes) or []
    sequencer_context = {}
    sequencer_context['block'] = block and block.id or None
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
    # n, previous, next = block.get_navigation(site=site, webpage=webpage, translation_state=translation_state, translation_codes=translation_codes, source_text_filter=source_text_filter)
    n, first, last, previous, next = block.get_navigation(site=site, webpage=webpage, translation_state=translation_state, translation_codes=translation_codes, source_text_filter=source_text_filter)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['last'] = last
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
    if request.GET.get('dry', ''):
        """
        var_dict['lineardoc'] = block.block_get_lineardoc()
        var_dict['segments_tokens'] = block.apply_tm(use_lineardoc=False)
        segments_tokens, translated_body = block.apply_tm(use_lineardoc=True)
        """
        state, n_invariants, n_substitutions, body, lineardoc, linearsentences, segments_tokens, n_translations, translated_sentences, translated_body = block.apply_tm(dry=True)
        var_dict['state']  = state
        var_dict['n_invariants']  = n_invariants
        var_dict['n_substitutions']  = n_substitutions
        var_dict['body']  = body
        var_dict['lineardoc']  = lineardoc
        var_dict['linearsentences']  = linearsentences
        var_dict['segments_tokens']  = segments_tokens
        var_dict['n_translations']  = n_translations
        var_dict['translated_sentences']  = translated_sentences
        var_dict['translated_body']  = translated_body
    return render(request, 'block.html', var_dict)

def block_translate(request, block_id, target_code):
    block = get_object_or_404(Block, pk=block_id)
    site = block.site
    proxy_languages = [proxy.language for proxy in block.site.get_proxies()]
    proxy_codes = [proxy.language_id for proxy in block.site.get_proxies()]
    source_language = block.get_language()
    target_language = get_object_or_404(Language, code=target_code)
    BlockSequencerForm.base_fields['translation_languages'].queryset = Language.objects.filter(code__in=proxy_codes)
    save_block = apply_filter = goto = extract = '' 
    create = modify = delete = ''
    translated_blocks = TranslatedBlock.objects.filter(block=block, language=target_language).order_by('-modified')
    translated_block = translated_blocks.count() and translated_blocks[0] or None
    if translated_block:
        segments = translated_block.translated_block_get_segments(None)
    else:
        segments = block.block_get_segments(None)
    segments = [segment.strip() for segment in segments]
    extract_strings = False
    post = request.method=='POST' and request.POST or None
    if post:
        save_block = post.get('save_block', '')
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
                elif key.startswith('delete-'):
                    delete = key.split('-')[1]
        apply_filter = not (save_block or segment or string or extract or goto or create or modify or delete)
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
            children = block.get_children()
            n_children = len(children)
            if n_children: 
                translation_state = block.compute_translation_state(target_language)
                print ('children:', len(children), 'state:', translation_state)
                body = block.body
                n_substitutions = 0
                for child in children:
                    if body.count(child.body):
                        if not child.no_translate:
                            translation = child.get_last_translation(target_language)
                            if translation:
                                body = body.replace(child.body, translation.body)
                                n_substitutions += 1
                segments = get_segments(body, site, None)
                if n_substitutions or not len(segments):
                    translated_block = block.clone(target_language)
                    translated_block.body = body
                    if len(segments):
                        translation_state = PARTIALLY
                    else:
                        translation_state = TRANSLATED
                    translated_block.state = translation_state
                    translated_block.save()
                    print ('n_substitutions:', n_substitutions, 'state:', translation_state)
            else:
                # block.apply_tm()
                block.apply_tm(target_language=target_language)
                translated_blocks = TranslatedBlock.objects.filter(block=block, language=Language.objects.get(code=create)).order_by('-modified')
                translated_block = translated_blocks.count() and translated_blocks[0] or None
                segments = translated_block and translated_block.translated_block_get_segments(None) or []
        elif modify:
            translated_blocks = TranslatedBlock.objects.filter(block=block, language=Language.objects.get(code=modify)).order_by('-modified')
            if translated_blocks:
                translated_block = translated_blocks[0]
            else:
                translated_block = block.clone(target_language)
            translated_block.body = post.get('translation-%s' % modify)
            translated_block.save()
            segments = translated_block.translated_block_get_segments(None)
            if not segments:
                translated_block.state=TRANSLATED
                translated_block.save()
        elif delete:
            translated_block = TranslatedBlock.objects.filter(block=block, language=Language.objects.get(code=delete)).order_by('-modified')[0]
            translated_block.delete()
            translated_block = None
            segments = block.block_get_segments(None)
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
                segment_string = get_or_add_segment(request, segment, source_language, block.site, add=True)
        elif segment:
            segment_string = get_or_add_segment(request, segment, source_language, block.site, add=True)
        elif string:
            segment_string = get_or_add_segment(request, string, source_language, site=block.site, add=True)
            return HttpResponseRedirect('/segment_translate/%d/%s/' % (segment_string.id, target_code))
    if (not post) or save_block or create or modify or delete or extract or segment or string:
        sequencer_context = request.session.get('sequencer_context', {})
        if sequencer_context:
            project_site_id = sequencer_context.get('project_site_id', None) or block.site.id
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
            project_site_id = block.site.id
            translation_state = TO_BE_TRANSLATED
            translation_codes = [proxy.language.code for proxy in block.site.get_proxies()]
            translation_age = ''
            source_text_filter = ''
            extract_strings = False
        webpage_id = request.GET.get('webpage', webpage_id)
        translation_languages = translation_codes and Language.objects.filter(code__in=translation_codes) or []
    sequencer_context = {}
    sequencer_context['block'] = block.id
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
        if Segment.objects.filter(is_invariant=True, site=site, text=segment):
            continue
        if Segment.objects.filter(language=target_language, site=site, text=segment):
            continue
        if source_language == target_language:
            continue
        segment_string = get_or_add_segment(request, segment, source_language, block.site, add=False)
        if segment_string:
            like_strings = find_like_segments(segment_string, max_segments=5)
            # print (segment_string, like_strings)
            source_strings.append(like_strings)
            # translations = Translation.objects.filter(segment=segment_string, language=target_language)
            translations = Translation.objects.filter(segment=segment_string, language=target_language).order_by('-translation_type')
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
    var_dict['body'] = translated_block and translated_block.body or block.body
    webpage = webpage_id and Webpage.objects.get(pk=webpage_id) or None
    # n, previous, next = block.get_navigation(site=site, webpage=webpage, translation_state=translation_state, translation_codes=translation_codes, source_text_filter=source_text_filter)
    n, first, last, previous, next = block.get_navigation(site=site, webpage=webpage, translation_state=translation_state, translation_codes=translation_codes, source_text_filter=source_text_filter)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['last'] = last
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
    var_dict['translation_state'] = translated_block and translated_block.state or TO_BE_TRANSLATED
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

"""
# srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
srx_filepath = os.path.join(settings.RESOURCES_ROOT, 'it', 'segment.srx')
srx_rules = srx_segmenter.parse(srx_filepath)
italian_rules = srx_rules['Italian']
segmenter = srx_segmenter.SrxSegmenter(italian_rules)
re_parentheses = re.compile(r'\(([^)]+)\)')
"""

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
    return render(request, 'block_pages.html', var_dict)

@staff_member_required
def segment_view(request, segment_id):
    var_dict = {}
    var_dict['segment'] = segment = get_object_or_404(Segment, pk=segment_id)
    var_dict['source_language'] = source_language = segment.language
    var_dict['other_languages'] = other_languages = segment.site.get_proxy_languages()

    SegmentSequencerForm.base_fields['translation_languages'].queryset = other_languages
    segment_context = request.session.get('segment_context', {})
    if segment_context:
        project_site_id = segment_context.get('project_site', None)
        in_use = segment_context.get('in_use', None)
        translation_state = segment_context.get('translation_state', TO_BE_TRANSLATED)
        translation_codes = segment_context.get('translation_codes', [l.code for l in other_languages])
        translation_sources = segment_context.get('translation_sources', [])
        translation_subjects = segment_context.get('translation_subjects', [])
        order_by = segment_context.get('order_by', ID_ASC)
        show_similar = segment_context.get('show_similar', False)
    else:
        project_site_id = segment.site.id
        in_use = 'Y'
        translation_state = TO_BE_TRANSLATED
        translation_codes = [l.code for l in other_languages]
        translation_sources = []
        translation_subjects = []
        order_by = ID_ASC
        show_similar = False
    translation_languages = Language.objects.filter(code__in=translation_codes)
    project_site = project_site_id and Site.objects.get(pk=project_site_id) or None

    apply_filter = goto = '' 
    post = request.method=='POST' and request.POST or None
    if post:
        apply_filter = post.get('apply_filter', '')
        if not (apply_filter):
            for key in post.keys():
                if key.startswith('goto-'):
                    goto = int(key.split('-')[1])
                    segment = get_object_or_404(Segment, pk=goto)
        form = SegmentSequencerForm(post)
        if form.is_valid():
            data = form.cleaned_data
            project_site = data['project_site']
            in_use = data['in_use']
            project_site_id = project_site and project_site.id or ''
            translation_state = int(data['translation_state'])
            translation_languages = data['translation_languages']
            translation_codes = [l.code for l in translation_languages]
            translation_sources = data['translation_sources']
            translation_sources = [int(ts) for ts in translation_sources]
            order_by = int(data['order_by'])
            show_similar = data['show_similar']
        else:
            pass
            # print ('error', form.errors)
    segment_context['translation_state'] = translation_state
    segment_context['translation_codes'] = translation_codes
    segment_context['translation_sources'] = translation_sources
    segment_context['project_site'] = project_site_id
    segment_context['in_use'] = in_use
    segment_context['order_by'] = order_by
    segment_context['show_similar'] = show_similar
    request.session['segment_context'] = segment_context
    if goto:
        return HttpResponseRedirect('/segment/%d/' % segment.id)        
    # n, first, last, previous, next = segment.get_navigation(site=project_site, in_use=in_use, translation_state=translation_state, translation_languages=translation_languages, translation_sources=translation_sources, order_by=order_by)
    n, first, last, previous, next = segment.get_navigation(site=project_site, in_use=in_use, translation_state=translation_state, target_languages=translation_languages, translation_sources=translation_sources, order_by=order_by)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['last'] = last
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['translations'] = segment.get_translations()
    var_dict['similar_segments'] = show_similar and find_like_segments(segment, max_segments=10) or []
    var_dict['sequencer_form'] = SegmentSequencerForm(initial={'project_site': project_site, 'in_use': in_use, 'translation_state': translation_state, 'translation_languages': translation_languages, 'translation_sources': translation_sources, 'order_by': order_by, 'show_similar': show_similar})
    var_dict['TRANSLATION_TYPE_DICT'] = TRANSLATION_TYPE_DICT
    var_dict['TRANSLATION_SERVICE_DICT'] = TRANSLATION_SERVICE_DICT   
    var_dict['ROLE_DICT'] = ROLE_DICT
    sequencer_context = request.session.get('sequencer_context', {})
    var_dict['block_id'] = sequencer_context.get('block', None)
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
        order_by = translation_context.get('order_by', ID_ASC)
        translation_type = translation_context.get('translation_type', ANY)
        alignment_type = translation_context.get('alignment_type', ANY)
    else:
        order_by = ID_ASC
        translation_type = ANY
        alignment_type = ANY

    apply_filter = goto = '' 
    post = request.method=='POST' and request.POST or None
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
                translation_type = int(data['translation_type'])
                alignment_type = int(data['alignment_type'])
            else:
                pass
                # print ('error', form.errors)

    translation_context['order_by'] = order_by
    translation_context['translation_type'] = translation_type
    translation_context['alignment_type'] = alignment_type
    request.session['translation_context'] = translation_context
    if goto:
        return HttpResponseRedirect('/translation_align/%d/' % translation.id)        
    # n, first, last, previous, next = translation.get_navigation(order_by=order_by, alignment_type=alignment_type)
    n, first, last, previous, next = translation.get_navigation(order_by=order_by, translation_type=translation_type, alignment_type=alignment_type)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['last'] = last
    var_dict['previous'] = previous
    var_dict['next'] = next

    var_dict['translation_align_form'] = TranslationViewForm(initial={'compute_alignment': compute_alignment,})
    if post and alignment:
        if alignment=='-':
            alignment = ''
        translation.alignment = alignment
        if post.get('save_draft_alignment'):
            translation.alignment_type = MT
        elif post.get('save_confirmed_alignment') or post.get('save_confirmed_and_return'):
            translation.alignment_type = MANUAL
        translation.save()
    else:
        alignment = translation.alignment
    var_dict['alignment'] = alignment
    var_dict['alignment_type'] = translation.alignment_type==MANUAL and 'manual' or ''
    var_dict['can_edit'] = True
    var_dict['sequencer_form'] = TranslationSequencerForm(initial={'order_by': order_by, 'translation_type': translation_type, 'alignment_type': alignment_type})
    sequencer_context = request.session.get('sequencer_context', {})
    var_dict['block_id'] = block_id = sequencer_context.get('block', None)
    if block_id and post and post.get('save_confirmed_and_return'):
        return HttpResponseRedirect('/block/%d/translate/%s/' % (block_id, translation.language.code))
    return render(request, 'translation_align.html', var_dict)

@staff_member_required
def segment_edit(request, segment_id=None, language_code='', proxy_slug=''):
    user = request.user
    if not user.is_superuser:
        return empty_page(request)
    var_dict = {}
    segment = segment_id and get_object_or_404(Segment, pk=segment_id) or None
    proxy = proxy_slug and get_object_or_404(Proxy, slug=proxy_slug) or None
    post = request.method=='POST' and request.POST or None
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

def filtered_translation_services(site):
    filtered_services = []
    now = timezone.now()
    for service in ServiceSubscription.objects.filter(site=site):
        if not service.service_type in filtered_services:
            if (not service.start_date or service.start_date < now) and (not service.end_date or now < service.end_date):
                filtered_services.append(service.service_type)
    return filtered_services

def segment_translate(request, segment_id, target_code):
    if not request.user.is_superuser:
        return empty_page(request);
    var_dict = {}
    var_dict['segment'] = segment = get_object_or_404(Segment, pk=segment_id)
    var_dict['source_language'] = source_language = segment.language
    var_dict['target_code'] = target_code
    var_dict['target_language'] = target_language = Language.objects.get(code=target_code)
    var_dict['other_languages'] = other_languages = segment.site.get_proxy_languages()
    var_dict['user_role'] = user_role = get_or_set_user_role(request, site=segment.site, source_language=source_language, target_language=target_language)
    translation_languages= other_languages
    translation_codes = [l.code for l in translation_languages]
    sequencer_context = request.session.get('sequencer_context', {})
    var_dict['block_id'] = block_id = sequencer_context.get('block', None)

    SegmentSequencerForm.base_fields['translation_languages'].queryset = translation_languages
    SegmentSequencerForm.base_fields['translation_sources'].choices = TRANSLATION_SERVICE_CHOICES[1:]

    segment_context = request.session.get('segment_context', {})
    if segment_context:
        project_site_id = segment_context.get('project_site', None)
        in_use = segment_context.get('in_use', None)
        translation_state = segment_context.get('translation_state', TO_BE_TRANSLATED)
        translation_codes = segment_context.get('translation_codes', [l.code for l in other_languages])
        translation_sources = segment_context.get('translation_sources', [])
        order_by = segment_context.get('order_by', ID_ASC)
        show_similar = segment_context.get('show_similar', False)
    else:
        project_site_id = segment.site.id
        in_use = 'Y'
        translation_state = TO_BE_TRANSLATED
        translation_codes = [l.code for l in other_languages]
        translation_sources = []
        order_by = ID_ASC
        show_similar = False
    translation_languages = Language.objects.filter(code__in=translation_codes)
    project_site = project_site_id and Site.objects.get(pk=project_site_id) or None

    translation_form = SegmentTranslationForm()
    translation_service_form = TranslationServiceForm()
    translation_service_form.fields['translation_services'].choices = \
        [[s, TRANSLATION_SERVICE_DICT[s]] for s in filtered_translation_services(project_site)]
    apply_filter = goto = save_translation = '' 
    post = request.method=='POST' and request.POST or None
    if post:
        apply_filter = post.get('apply_filter', '')
        ask_service = post.get('ask_service', '')
        batch_translate = post.get('batch_translate', '')
        if not (apply_filter or ask_service or batch_translate):
            for key in post.keys():
                if key.startswith('goto-'):
                    goto = int(key.split('-')[1])
                    segment = get_object_or_404(Segment, pk=goto)
                elif key.startswith('save_return-'):
                    save_translation = key.split('-')[1]
                    save_return = True
                elif key.startswith('save-'):
                    save_translation = key.split('-')[1]
                    save_return = False
        if ask_service or batch_translate:
            translation_service_form = TranslationServiceForm(request.POST)
            translation_service_form.fields['translation_services'].choices = \
                [[s, TRANSLATION_SERVICE_DICT[s]] for s in filtered_translation_services(project_site)]
            if translation_service_form.is_valid():
                data = translation_service_form.cleaned_data
                translation_services = data['translation_services']
                subscriptions = ServiceSubscription.objects.filter(site=segment.site, service_type__in=translation_services)
                if ask_service:
                    external_translations = []
                    for subscription in subscriptions:
                        if subscription.service_type == GOOGLE:
                            response = ask_gt(segment.text, target_code, subscription)
                            if response.get('detectedSourceLanguage', '').startswith(source_language.code):
                                external_translations = [{ 'segment': response.get('input', ''), 'translation': response.get('translatedText', ''), 'service_type': GOOGLE }]
                        elif subscription.service_type == DEEPL:
                            source_code = source_language.code.upper()
                            translations = ask_deepl(segment.text, target_code, subscription, source_code=source_code)
                            for translation in translations:
                                if translation.get('detected_source_language', '').startswith(source_code):
                                    external_translations.append({ 'segment': segment.text, 'translation': translation.get('text'), 'service_type': DEEPL })
                        elif subscription.service_type == MICROSOFT:
                            source_code = source_language.code
                            translation = ask_microsofttranslator(segment.text, target_code, subscription, source_code=source_code)
                            external_translations = [{ 'segment': segment.text, 'translation': translation, 'service_type': MICROSOFT }]
                        elif subscription.service_type == MYMEMORY:
                            langpair = '%s|%s' % (source_language.code, target_code)
                            status, translatedText, mymemory_translations = ask_mymemory(segment.text, langpair, subscription)
                            for external_translation in mymemory_translations:
                                external_translation['service_type'] = MYMEMORY
                                external_translations.append(external_translation)
                    var_dict['external_translations'] = external_translations
                elif batch_translate and subscriptions.count()==1:
                    subscription = subscriptions[0]
                    max_segments = int(data['max_segments'])
                    n_segments = 0
                    ## segments = segment.get_navigation(site=project_site, in_use=in_use, translation_state=translation_state, translation_languages=translation_languages, translation_sources=translation_sources, order_by=order_by, return_segments=True)
                    # segments = segment.get_navigation(site=project_site, in_use=in_use, translation_state=translation_state, target_languages=translation_languages, translation_sources=translation_sources, order_by=order_by, return_segments=True)
                    segments = filter_segments(site=project_site, in_use=in_use, translation_state=translation_state, target_languages=translation_languages, translation_sources=translation_sources, order_by=order_by)
                    for segment in segments[:max_segments]:
                        if subscription.service_type == GOOGLE:
                            response = ask_gt(segment.text, target_code, subscription)
                            text = response.get('translatedText', '')
                            if text:
                                translation = Translation(segment=segment, language_id=target_code, text=text, translation_type=MT, service_type=GOOGLE, timestamp=timezone.now())
                                translation.save()
                                n_segments += 1
                        elif subscription.service_type == DEEPL:
                            source_code = source_language.code.upper()
                            translations = ask_deepl(segment.text, target_code, subscription, source_code=source_code)
                            for translation in translations:
                                text = translation.get('text', '')
                                if text:
                                    translation = Translation(segment=segment, language_id=target_code, text=translation.get('text'), translation_type=MT, service_type=DEEPL, timestamp=timezone.now())
                                    translation.save()
                                    n_segments += 1
                        elif subscription.service_type == MICROSOFT:
                            source_code = source_language.code
                            text = ask_microsofttranslator(segment.text, target_code, subscription, source_code=source_code)
                            if text:
                                translation = Translation(segment=segment, language_id=target_code, text=text, translation_type=MT, service_type=MICROSOFT, timestamp=timezone.now())
                                translation.save()
                                n_segments += 1
                        if n_segments >= max_segments:
                            break
            else:
                pass
            translation_form = SegmentTranslationForm()
        elif save_translation:
            translation_form = SegmentTranslationForm(request.POST)
            if translation_form.is_valid():
                data = translation_form.cleaned_data
                translation_source = data['translation_source']
                translation_text = data['translation']
                translation_type = MANUAL
                timestamp = timezone.now()
                selection = post.getlist('selection')
                if selection:
                    for translation_id in selection:
                        translation = Translation.objects.get(pk=int(translation_id))
                        if not translation.user_role or user_role==translation.user_role:
                            translation.text = translation_text
                            translation.translation_type = translation_type
                            if translation_source:
                                translation.service_type = int(translation_source)
                            translation.user_role = user_role
                            translation.timestamp = timestamp
                            translation.save()
                else:
                    translation = Translation(segment=segment, text=translation_text, language=target_language, translation_type=translation_type, user_role=user_role, timestamp=timestamp)
                    if translation_source:
                        translation.service_type = int(translation_source)
                    translation.save()
                if save_return:
                    return HttpResponseRedirect('/block/%d/translate/%s/' % (block_id, target_code))
            else:
                # print ('error', translation_form.errors)
                return render(request, 'segment_translate.html', {'translation_form': translation_form,})
            translation_service_form = TranslationServiceForm()
            translation_service_form.fields['translation_services'].choices = \
                [[s, TRANSLATION_SERVICE_DICT[s]] for s in filtered_translation_services(project_site)]
        else: # apply_filter
            form = SegmentSequencerForm(post)
            if form.is_valid():
                data = form.cleaned_data
                project_site = data['project_site']
                in_use = data['in_use']
                project_site_id = project_site and project_site.id or ''
                translation_state = int(data['translation_state'])
                translation_languages = data['translation_languages']
                translation_codes = [l.code for l in translation_languages]
                translation_sources = data['translation_sources']
                translation_sources = [int(ts) for ts in translation_sources]
                order_by = int(data['order_by'])
                show_similar = data['show_similar']
            else:
                print(form.errors)
    segment_context['project_site'] = project_site_id
    segment_context['in_use'] = in_use
    segment_context['translation_state'] = translation_state
    segment_context['translation_codes'] = translation_codes
    segment_context['translation_sources'] = translation_sources
    segment_context['order_by'] = order_by
    segment_context['show_similar'] = show_similar
    request.session['segment_context'] = segment_context
    if goto:
        return HttpResponseRedirect('/segment_translate/%d/%s/' % (segment.id, target_code))
    # n, first, last, previous, next = segment.get_navigation(site=project_site, in_use=in_use, translation_state=translation_state, translation_languages=translation_languages, translation_sources=translation_sources, order_by=order_by)
    n, first, last, previous, next = segment.get_navigation(site=project_site, in_use=in_use, translation_state=translation_state, target_languages=translation_languages, translation_sources=translation_sources, order_by=order_by)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['last'] = last
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['similar_segments'] = show_similar and find_like_segments(segment, translation_languages=[target_language], with_translations=True, max_segments=10) or []
    var_dict['translations'] = segment.get_translations()
    var_dict['sequencer_form'] = SegmentSequencerForm(initial={ 'project_site': project_site, 'in_use': in_use, 'translation_state': translation_state, 'translation_languages': translation_languages, 'translation_sources': translation_sources, 'order_by': order_by, 'show_similar': show_similar})
    var_dict['translation_form'] = SegmentTranslationForm()
    var_dict['translation_service_form'] = translation_service_form
    var_dict['TRANSLATION_TYPE_DICT'] = TRANSLATION_TYPE_DICT
    var_dict['TRANSLATION_SERVICE_DICT'] = TRANSLATION_SERVICE_DICT   
    var_dict['ROLE_DICT'] = ROLE_DICT
    var_dict['translation_state'] = translation_state
    return render(request, 'segment_translate.html', var_dict)

def raw_tokens(text, language_code):
    tokens = re.split(" |\'", text)
    raw_tokens = []
    for token in tokens:
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

def list_segments(request, state=None):
    """
    list translations from source language (code) to target language (code)
    """
    if not request.user.is_superuser:
        return empty_page(request)
    current_role = get_or_set_user_role(request)
    tm_edit_context = request.session.get('tm_edit_context', {})
    translation_state = state or tm_edit_context.get('translation_state', 0)
    id = request.GET.get('id', None)
    segment = id and Segment.objects.get(pk=id) or None
    project_site = segment and segment.site or None
    if not project_site:
        project_site_id = tm_edit_context.get('project_site', None)
        project_site = project_site_id and Site.objects.get(pk=project_site_id) or None
    """
    if not project_site.can_view(current_role):
    """ 
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
    translation_source = tm_edit_context.get('translation_source', '')
    in_use = tm_edit_context.get('in_use', 'Y')
    show_other_targets = tm_edit_context.get('show_other_targets', False)
    show_alignments = tm_edit_context.get('show_alignments', False)
    order_by = tm_edit_context.get('order_by', ID_ASC)
    tm_edit_context['project_site'] = project_site_id
    tm_edit_context['source_language'] = source_language_code
    tm_edit_context['target_language'] = target_language_code
    tm_edit_context['translation_source'] = translation_source
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
        elif post.get('make-in-target', ''):
            if target_language:
                selection = post.getlist('selection')
                for segment_id in selection:
                    segment = Segment.objects.get(pk=int(segment_id))
                    segment.language = target_language
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
            translation_source = int(data['translation_source'])
            tm_edit_context['translation_source'] = translation_source
            tm_edit_context['source_text_filter'] = source_text_filter = data['source_text_filter']
            tm_edit_context['target_text_filter'] = target_text_filter = data['target_text_filter']
            tm_edit_context['in_use'] = in_use = data['in_use']
            tm_edit_context['show_other_targets'] = show_other_targets = data['show_other_targets']
            tm_edit_context['show_alignments'] = show_alignments = data['show_alignments']
            tm_edit_context['order_by'] = order_by = int(data['order_by'])
            request.session['tm_edit_context'] = tm_edit_context
            """
            if project_site and target_language:
                proxies = Proxy.objects.filter(site=project_site, language=target_language)
                proxy = proxies and proxies[0] or None
            """
            if post.get('add-segment', '') and project_site and source_language and source_text_filter:
                segment, created = Segment.objects.get_or_create(site=project_site, language=source_language, text=source_text_filter)
    else:
        form = ListSegmentsForm(initial={'project_site': project_site, 'in_use': in_use, 'translation_state': translation_state, 'source_language': source_language, 'target_language': target_language, 'translation_source': translation_source, 'source_text_filter': source_text_filter, 'target_text_filter': target_text_filter, 'show_other_targets': show_other_targets, 'order_by': order_by })

    if translation_state == TRANSLATED:
        translated = True
    elif translation_state == TO_BE_TRANSLATED:
        translated = False
    else:
        translated = None

    var_dict = {}
    var_dict['site'] = project_site_id and Site.objects.get(pk=project_site_id) or None
    var_dict['state'] = translation_state
    var_dict['source_language'] = source_language
    var_dict['target_language'] = target_language
    var_dict['in_use'] = in_use
    var_dict['show_other_targets'] = show_other_targets
    var_dict['show_alignments'] = show_alignments
    var_dict['other_languages'] = Language.objects.exclude(code=target_language_code).order_by('code')
    var_dict['order_by'] = order_by

    """
    if project_site and translation_state == INVARIANT:
        qs = Segment.objects.filter(site=project_site, is_invariant=True)
    elif project_site and translation_state == ALREADY:
        qs = Segment.objects.filter(site=project_site, language=target_language)
    else:
        qs = find_segments(source_languages=[source_language], target_languages=[target_language], site=project_site, translated=translated, order_by='')
    if in_use == 'Y':
        qs = qs.exclude(in_use=0)
    elif in_use == 'N':
        qs = qs.filter(in_use=0)
    """
    source_languages = source_language and [source_language] or []
    target_languages = target_language and [target_language] or []
    translation_sources = translation_source and [translation_source] or []
    qs = filter_segments(site=project_site, in_use=in_use, translation_state=translation_state, source_languages=source_languages, target_languages=target_languages, translation_sources=translation_sources)
    if source_text_filter:
        qs = qs.filter(text__icontains=source_text_filter)
    if target_text_filter:
        qs = qs.filter(segment_translation__text__icontains=target_text_filter)
    if order_by == TEXT_ASC:
        qs = qs.order_by('text')
    elif order_by == COUNT_DESC:
        qs = qs.order_by('-in_use')
    else:
        qs = qs.order_by('id')
        
    segment_count = qs.count()
    var_dict['segment_count'] = segment_count
    if id:
        index = qs.filter(text__lt=segment.text).count()
        page = index/settings.PAGE_SIZE + 1
        # print ('index, page =', index, page)
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
        target_language = Language.objects.get(code=target_code)
        user_role = get_or_set_user_role(request, site=segment.site, source_language=segment.language, target_language=target_language)
        if not user_role:
            pass # eccezione
        if translation_id:
            Translation.objects.filter(pk=translation_id).update(text=target_text, translation_type=MANUAL, user_role=user_role, timestamp=timezone.now())
            if len(segment.text.split())==1 and len(target_text.split())==1:
                translation = Translation.objects.get(pk=translation_id)
                if  not translation.alignment:
                    translation.alignment = '0-0'
                    translation.alignment_type = MANUAL
                    translation.save()
            return JsonResponse({"data": "modify",})
        else:
            translation = Translation(segment=segment, language_id=target_code, text=target_text, translation_type=MANUAL, user_role=user_role, timestamp=timezone.now())
            if len(segment.text.split())==1 and len(target_text.split())==1:
                translation.alignment = '0-0'
                translation.alignment_type = MANUAL
            translation.save()
            translation_id = translation.id
            return JsonResponse({"data": "add","translation_id": translation_id,})
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
            if len(target_languages)==1:
                qs = qs.exclude(language=target_languages[0])
        qs = qs.exclude(is_invariant=True)
    if order_by is None:
        qs = qs.order_by('language', 'text')
    elif order_by:
        qs = qs.order_by(order_by)
    return qs

def get_language(language_code):
    return Language.objects.get(code=language_code)

def list_scans(request, user=None, site=None):
    if request.method == 'POST':
        post = request.POST
        if post.get('delete-scan', ''):
            selection = post.getlist('selection')
            # print ('delete-scan', selection)
            for scan_id in selection:
                scan = Scan.objects.get(pk=int(scan_id))
                scan.delete()
    data_dict = {}
    if user:
        scans = Scan.objects.filter(user=user).order_by('-created')
    elif site:
        scans = Scan.objects.filter(site=site).order_by('-created')
    else:
        scans = Scan.objects.all().order_by('-created')
    data_dict['user'] = user  
    data_dict['site'] = site  
    data_dict['scans'] = scans  
    return render(request, 'list_scans.html', data_dict)

def site_scans(request, site_slug):
    site = get_object_or_404(Site, slug=site_slug)
    return list_scans(request, site=site)

"""
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
    return render(request, 'user_scans.html', data_dict)
"""
def user_scans(request, username):
    user = User.objects.get(username=username)
    return list_scans(request, user=user)

def my_scans(request):
    # return user_scans(request, username=request.user.username)
    return list_scans(request, user=request.user)

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
    return render(request, 'scan_segments.html', data_dict)

def scan_delete(request, scan_id):
    scan = Scan.objects.get(pk=scan_id)
    user = scan.user
    links = Link.objects.filter(scan=scan)
    for link in links:
        link.delete()
    scan.delete()
    return HttpResponseRedirect('/user_scans/%s/' % user.username)    
    
def scan_progress(request, scan_id, i_line):
    scan = Scan.objects.get(pk=scan_id)
    i_line = int(i_line)
    links = Link.objects.filter(scan=scan).order_by('created')[i_line:]
    lines = []
    for link in links:
        i_line += 1
        line = {"url": link.url, "status": link.status, "title": link.title, "encoding": link.encoding, "size": link.size}
        lines.append(line)
    print ('scan_progress', i_line, scan.terminated)
    if scan.terminated:
        if scan.scan_type == CRAWL:
            site = scan.site
            site.last_crawled = timezone.now()
            site.save()
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
        pass
        # print ('--- worker is running ---')
    else:
        # print ('--- running worker ---')
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
    # print ('--- stopping task %s ---' % task_id)
    revoke(task_id, terminate=True)
    scan.terminated = True
    scan.save()
    return JsonResponse({'status': 'ok',})

@app.task()
def discover_task(scan_id):
    crawler_script = WipDiscoverScript()
    return crawler_script.crawl(scan_id)

class Discover(View):
    form_class = DiscoverForm
    initial = {}
    template_name = 'discover.html'
    scan_id = None
    site_slug = ''

    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated():
            return HttpResponseForbidden()
        data_dict = {}
        data_dict['scan_id'] = scan_id = self.kwargs.get('scan_id', '')
        if scan_id:
            scan = Scan.objects.get(pk=scan_id)
            site = scan.site
            self.initial = {'site': scan.site, 'name': scan.name, 'scan_mode': scan.scan_mode, 'allowed_domains': scan.allowed_domains, 'start_urls': scan.start_urls, 'deny': scan.deny, 'max_pages': scan.max_pages, 'count_words': scan.count_words, 'count_segments': scan.count_segments, 'extract_blocks': scan.extract_blocks}
        else:
            site_slug = self.kwargs.get('site_slug', '')
            site = site_slug and get_object_or_404(Site, slug=site_slug) or None
            if site:
                scan_type = DISCOVER
                scan_mode = FOREGROUND
                max_pages = 100
                allowed_domains = site.allowed_domains or site.url.split('//')[-1]
                start_urls = site.start_urls or site.url
                extract_blocks = False
                self.initial = {'site': site, 'name': site.name, 'scan_type': scan_type, 'scan_mode': scan_mode, 'allowed_domains': allowed_domains, 'start_urls': start_urls, 'deny': site.deny, 'max_pages': max_pages, 'extract_blocks': extract_blocks}
                data_dict['site'] = site
        data_dict['form'] = self.form_class(initial=self.initial)
        return render(request, self.template_name, data_dict)

    def post(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated():
            return HttpResponseForbidden()
        data_dict = {}
        data_dict['form'] = self.form = self.form_class(request.POST)
        if self.form.is_valid():
            data = self.form.cleaned_data
            name = data['name'] or 'discover'
            data_dict['site'] = site = data['site']
            print('----- site:', site)
            scan_mode = int(data['scan_mode'])
            allowed_domains = data['allowed_domains']
            start_urls = data['start_urls']
            allow = data['allow']
            deny = data['deny']
            max_pages = data['max_pages']
            count_words = data['count_words']
            count_segments = data['count_segments']
            run_worker_process()
            scan = Scan(name=name, site=site, scan_type=DISCOVER, scan_mode=scan_mode, allowed_domains=allowed_domains, start_urls=start_urls, allow=allow, deny=deny, max_pages=max_pages, count_words=count_words, count_segments=count_segments, task_id=0, user=user)
            scan.save()
            async_result = discover_task.delay(scan.pk)
            scan.task_id = async_result.task_id
            scan.save()
            data_dict['scan_id'] = scan.pk
            data_dict['scan_label'] = scan.get_label()
            data_dict['foreground'] = (scan_mode == FOREGROUND)
        else:
            print(self.form.errors)
        return render(request, self.template_name, data_dict)


class Crawl(View):
    form_class = CrawlForm
    initial = {}
    template_name = 'crawl.html'
    scan_id = None

    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated():
            return HttpResponseForbidden()
        data_dict = {}
        site_slug = self.kwargs['site_slug']
        data_dict['site'] = site = get_object_or_404(Site, slug=site_slug)
        scan_mode = FOREGROUND
        max_pages = 100
        start_urls = site.start_urls or site.url
        extract_blocks = True
        self.initial = {'scan_mode': scan_mode, 'allowed_domains': site.allowed_domains, 'start_urls': start_urls, 'deny': site.deny, 'max_pages': max_pages, 'extract_blocks': extract_blocks}
        data_dict['form'] = self.form_class(initial=self.initial)
        return render(request, self.template_name, data_dict)

    def post(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated():
            return HttpResponseForbidden()
        data_dict = {}
        site_slug = self.kwargs['site_slug']
        data_dict['site'] = site = get_object_or_404(Site, slug=site_slug)
        data_dict['form'] = self.form = self.form_class(request.POST)
        if self.form.is_valid():
            data = self.form.cleaned_data
            scan_mode = int(data['scan_mode'])
            allowed_domains = data['allowed_domains']
            start_urls = data['start_urls']
            allow = data['allow']
            deny = data['deny']
            max_pages = data['max_pages']
            extract_blocks = data['extract_blocks']
            run_worker_process()
            scan = Scan(name=site.name, site=site, scan_type=CRAWL, scan_mode=scan_mode, extract_blocks=extract_blocks, allowed_domains=allowed_domains, start_urls=start_urls, allow=allow, deny=deny, max_pages=max_pages, task_id=0, user=user)
            scan.save()
            async_result = crawl_task.delay(scan.pk)
            scan.task_id = async_result.task_id
            scan.save()
            data_dict['scan'] = scan
            data_dict['foreground'] = (scan_mode == FOREGROUND)
        else:
            print(self.form.errors)
        return render(request, self.template_name, data_dict)

@app.task()
def crawl_task(scan_id):
    crawler_script = WipSiteCrawlerScript()
    return crawler_script.crawl(scan_id)
