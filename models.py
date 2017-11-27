# -*- coding: utf-8 -*-"""

"""
Django models for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

import sys
if (sys.version_info > (3, 0)):
    # Python 3 code in this block
    from importlib import reload
    import urllib.request as urllib2
    from wip.aligner import split_alignment, normalized_alignment, proxy_symmetrize_alignments, proxy_eflomal_align
    from io import StringIO
else:
    reload(sys)  
    sys.setdefaultencoding('utf8')
    import urllib2
    import dill # required to pickle lambda functions
    import pickle
    # import StringIO
    from StringIO import StringIO

import logging
logger = logging.getLogger('wip')

# from collections import defaultdict
import os
import json
import time
import copy
import re, regex
import difflib
from collections import defaultdict
# import datetime
# from namedentities import unicode_entities
# from Levenshtein.StringMatcher import StringMatcher
from lxml import html, etree
from nltk.translate import AlignedSent, Alignment, IBMModel2, IBMModel3
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField, AutoSlugField
from django_dag.models import node_factory, edge_factory
from django_diazo.models import Theme
# from django_diazo.middleware import DjangoDiazoMiddleware
from wip.wip_nltk.tokenizers import NltkTokenizer
from wip.wip_sd.sd_algorithm import SDAlgorithm
from wip.lineardoc.Parser import Parse as LineardocParse
from wip.lineardoc.TextBlock import TextBlock, mergeSentences
from wip.lineardoc.Utils import addCommonTag
from .vocabularies import Language, Subject, ApprovalStatus
from .aligner import tokenize, best_alignment, aer

from .settings import RESOURCES_ROOT, BLOCK_TAGS, BLOCKS_EXCLUDE_BY_XPATH, SEPARATORS, STRIPPED, EMPTY_WORDS, BOTH_QUOTES
DEFAULT_USER = 1
from .utils import element_tostring, text_from_html, strings_from_html, elements_from_element, replace_element_content, element_signature
from .utils import normalize_string, replace_segment, string_checksum, text_to_list # , non_invariant_words
from .utils import is_invariant_word as is_base_invariant_word
# import wip.srx_segmenter
import wip.srx_segmenter as srx_segmenter

def is_linearblock_translated(block):
    return block.hasCommonTag('tx')
TextBlock.isTranslated = is_linearblock_translated

MYMEMORY = 1
MATECAT = 2
GOOGLE = 3
TRANSLATION_SERVICE_CHOICES = (
    (GOOGLE, _('GoogleTranslate')),
    (MYMEMORY, _('MyMemory')),
    # (MATECAT, _('Matecat')),
)
TRANSLATION_SERVICE_DICT = dict(TRANSLATION_SERVICE_CHOICES)

def code_to_language(code):
    return Language.objects.get(pk=code)

TO_BE_TRANSLATED = -1
ANY = NONE = 0
PARTIALLY = 1
TRANSLATED = 2
REVISED = 3
INVARIANT = 4
ALREADY = 5
TRANSLATION_STATE_CHOICES = (
    (ANY, _('any'),),
    (TO_BE_TRANSLATED, _('to be translated'),),
    (TRANSLATED,  _('translated'),),
    (REVISED,  _('revised'),),
    (INVARIANT,  _('invariant'),),
    (ALREADY,  _('already in target language'),),
)
TRANSLATION_STATE_DICT = dict(TRANSLATION_STATE_CHOICES)

STRING_TRANSLATION_STATE_CHOICES = (
    (ANY, _('any'),),
    (INVARIANT, _('invariant'),),
    (TO_BE_TRANSLATED, _('to be translated'),),
    (TRANSLATED,  _('translated'),),
    (REVISED,  _('revised'),),
)
STRING_TRANSLATION_STATE_DICT = dict(STRING_TRANSLATION_STATE_CHOICES)

UNKNOWN = 0
TERM = 1
SEGMENT = 2
FRAGMENT = 3
STRING_TYPE_CHOICES = (
    (UNKNOWN, _('unknown'),),
    (TERM, _('term'),),
    (SEGMENT, _('segment'),),
    (FRAGMENT,  _('fragment'),),
)
STRING_TYPE_DICT = dict(STRING_TYPE_CHOICES)

TEXT_ASC = 1
ID_ASC = 2
DATETIME_DESC = -3
DATETIME_ASC = 3
STRING_SORT_CHOICES = (
    (TEXT_ASC, _('text'),),
    (ID_ASC, _('id'),),
    (DATETIME_DESC, _('datetime inverse'),),
    (DATETIME_ASC,  _('datetime'),),
)
STRING_SORT_DICT = dict(STRING_SORT_CHOICES)

PARALLEL_FORMAT_NONE = 0
PARALLEL_FORMAT_XLIFF = 1
PARALLEL_FORMAT_TEXT = 2

class Site(models.Model):
    name = models.CharField(max_length=100)
    slug = AutoSlugField(unique=True, populate_from='name', editable=True)
    # language = models.ForeignKey(Language, null=True)
    language = models.ForeignKey(Language, null=True, related_name='language_site')
    path_prefix = models.CharField(max_length=20, default='')
    url = models.CharField(max_length=100)
    allowed_domains = models.TextField()
    start_urls = models.TextField()
    deny = models.TextField(verbose_name='Deny spyder', blank=True, null=True, help_text="Paths the spider should not follow")
    extract_deny = models.TextField(verbose_name='Deny extractor', blank=True, null=True, help_text="Paths of pages the string extractor should skip" )
    translate_deny = models.TextField(verbose_name='Deny translation', blank=True, null=True, help_text="Paths of pages not to be submitted to offline translation" )
    checksum_deny = models.TextField(verbose_name='Exclude from checksum', blank=True, null=True, help_text="Patterns identifying lines in body not affecting page checksum" )
    srx_rules = models.TextField(verbose_name='Custom SRX rules', blank=True, null=True, help_text="Custom SRX rules extending the standard set" )
    srx_initials = models.TextField(verbose_name='Custom initials', blank=True, null=True, help_text="Initials to be made explicit as SRX rules" )
    invariant_words = models.TextField(verbose_name='Custom invariant words', blank=True, null=True, help_text="Custom invariant words" )
    themes = models.ManyToManyField(Theme, through='SiteTheme', related_name='site', blank=True, verbose_name='diazo themes')

    def __init__(self, *args, **kwargs):
        super(Site, self).__init__(*args, **kwargs)
        self.segmenter = None

    def get_absolute_url(self):
        return '/site/%s/' % self.slug

    def get_filepath(self):
        return os.path.join(settings.SITES_ROOT, self.slug)

    def can_manage(self, user):
        return user.is_superuser

    def can_operate(self, user):
        return user.is_superuser

    def can_view(self, user):
        return user.is_authenticated()

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.__str__()

    def get_allowed_domains(self):
        return text_to_list(self.allowed_domains)

    def get_start_urls(self):
        return text_to_list(self.start_urls)

    def get_deny(self):
        # return ','.join(text_to_list(self.deny))
        return text_to_list(self.deny)

    def get_proxies(self):
        return Proxy.objects.filter(site=self).order_by('language__code')

    def get_proxy_languages(self):
        return Language.objects.filter(language_proxy__site=self)

    class Meta:
        verbose_name = _('project')
        verbose_name_plural = _('projects')

    def make_segmenter(self, verbose=False):
        if self.segmenter:
            print ('segmenter already exists')
            return self.segmenter
        srx_filepath = os.path.join(RESOURCES_ROOT, self.language.code, 'segment.srx')
        srx_rules = srx_segmenter.parse(srx_filepath)
        current_rules = srx_rules['Italian']
        if self.srx_initials:
            custom_rules_list = text_to_list(self.srx_initials)
            if len(custom_rules_list) == 1:
                beforebreak_text = '%s' % re.escape(custom_rules_list[0])
            else:
                # beforebreak_text = '(?%s)' % '|'.join([re.escape(item) for item in custom_rules_list])
                beforebreak_text = '\\b(%s)' % '|'.join([re.escape(item) for item in custom_rules_list])
            afterbreak_text = '\s'
            # print (beforebreak_text, afterbreak_text)
            non_breaks = current_rules['non_breaks']
            non_breaks.append((beforebreak_text, afterbreak_text))
            current_rules['non_breaks'] = non_breaks
            if verbose:
                for item in non_breaks:
                    print (item)
        if self.srx_rules:
            non_breaks = current_rules['non_breaks']
            custom_rules_list = text_to_list(self.srx_rules)
            for item in custom_rules_list:
                beforebreak_text, afterbreak_text = item.split(' ')
                non_breaks.append((beforebreak_text, afterbreak_text))
                if verbose:
                    print (beforebreak_text, afterbreak_text)
            current_rules['non_breaks'] = non_breaks
        # return srx_segmenter.SrxSegmenter(current_rules)
        self.segmenter = srx_segmenter.SrxSegmenter(current_rules)
        return self.segmenter

    def make_tokenizer(self, return_matches=False):
        """ create a tokenizer for the site language, with a list of custom regular expressions corresponding to
            acronyms and abbreviations, being derived from the site configuration parameter used for segmentation """
        custom_regexps = []
        if self.srx_initials:
            # custom_regexps = text_to_list(self.srx_initials)
            for item in self.srx_initials.splitlines():
                item = item.strip()
                if not item:
                    continue
                item = item.replace('.', '\\.')
                custom_regexps.append(item)
                if item[0].islower():
                    custom_regexps.append(item[0].upper() + item[1:])
            print ('custom_regexps:', custom_regexps)
        return NltkTokenizer(language=self.language.code, custom_regexps=custom_regexps, lowercasing=False, return_matches=return_matches)

    def pages_summary(self):
        pages = Webpage.objects.filter(site=self).order_by('path')
        proxy_codes = [proxy.language_id for proxy in Proxy.objects.filter(site=self)]
        proxy_list = [[code, {'partially': 0, 'translated': 0, 'revised': 0}] for code in proxy_codes]
        proxy_dict = dict(proxy_list)
        total = pages.count()
        invariant = 0
        for page in pages:
            if page.no_translate:
                invariant +=1
                continue
            translations = TranslatedVersion.objects.filter(webpage=page)
            for translation in translations:
                code = translation.language_id
                if translation.state == 2:
                    proxy_dict[code]['revised'] += 1
                elif translation.state == 1:
                    proxy_dict[code]['translated'] += 1
                else:
                    proxy_dict[code]['partially'] += 1
        sorted_list = sorted(proxy_dict.items())
        proxy_list = []
        for code, t_dict in sorted_list:
            language = code_to_language(code)
            left = total - invariant
            for value in t_dict.values():
                left -= value
            t_dict['left'] = left
            proxy_list.append([language, t_dict])
        return pages, total, invariant, proxy_list

    def blocks_summary(self):
        blocks = Block.objects.filter(block_in_page__webpage__site=self).order_by('checksum', '-time')
        last_ids = []
        checksum = '' 
        for block in blocks:
            if not (block.checksum==checksum):
                checksum = block.checksum
                last_ids.append(block.id)
        blocks = Block.objects.prefetch_related('source_block').filter(id__in=last_ids).order_by('-time')
        proxy_codes = [proxy.language_id for proxy in Proxy.objects.filter(site=self)]
        proxy_list = [[code, {'already': 0, 'partially': 0, 'translated': 0, 'revised': 0}] for code in proxy_codes]
        proxy_dict = dict(proxy_list)
        total = blocks.count()
        invariant = 0
        for block in blocks:
            if block.no_translate:
                invariant +=1
                continue
            if block.language_id in proxy_codes:
                proxy_dict[block.language_id]['already'] += 1
                continue
            translations = TranslatedBlock.objects.filter(block=block)
            for translation in translations:
                code = translation.language_id
                if translation.state == 2:
                    proxy_dict[code]['revised'] += 1
                elif translation.state == 1:
                    proxy_dict[code]['translated'] += 1
                else:
                    proxy_dict[code]['partially'] += 1
        sorted_list = sorted(proxy_dict.items())
        proxy_list = []
        for code, t_dict in sorted_list:
            language = code_to_language(code)
            left = total - invariant
            for value in t_dict.values():
                left -= value
            t_dict['left'] = left
            proxy_list.append([language, t_dict])
        return blocks, total, invariant, proxy_list

    def get_blocks_in_use(self):
        return Block.objects.filter(block_in_page__webpage__site=self).distinct()

    def page_checksum(self, body):
        if not self.slug == 'scuolemigranti':
            return string_checksum(body)
        # patterns = ['<div class="textwidget"><div id="flickr_recent_',]
        deny_list = text_to_list(self.checksum_deny)
        l_in = body.splitlines()
        l_out = []
        for l in l_in:
            should_skip = False
            for deny_pattern in deny_list:
                if l.count(deny_pattern):
                    should_skip = True
                    break
            if should_skip:
                continue
            l_out.append(l)
        # return string_checksum('\n'.join(l_out))
        return string_checksum('\n'.join(l_out).encode())

    # def fetch_page(self, path, webpage=None, extract_blocks=True, extract_segments=False, diff=False, dry=False, verbose=False):
    def fetch_page(self, path, webpage=None, extract_blocks=True, extract_block=None, extract_segments=False, diff=False, dry=False, verbose=False):
        site_id = self.id
        page_url = self.url + path
        if verbose:
            print (page_url)
        updated = False
        request = urllib2.Request(page_url)
        time_1 = time.time()
        try:
            response = urllib2.urlopen(request)
        # except (urllib2.HTTPError, e):
        except Exception as e:
            if verbose:
                print (page_url, ': error = ', e)
            if webpage:
                webpage.last_unfound = timezone.now()
            return -1
        time_2 = time.time()
        delay = int(round(time_2 - time_1))
        if verbose:
            print ('delay: ', delay)
        response_code = response.getcode()
        if webpage:
            webpage.last_checked = timezone.now()
            webpage.last_checked_response_code = response_code
        # body = response.read()
        body = response.read().decode()
        size = len(body)
        checksum = self.page_checksum(body)
        if not webpage:
            webpages = Webpage.objects.filter(site=self, path=path)
            webpage = webpages and webpages[0] or None
            if not dry and not webpage:
                webpage = Webpage(site=self, path=path, last_checked_response_code=response_code)
                webpage.save()
            if not webpage:
                return site_id, response_code, 0, path
        webpage_id = webpage.id
        page_versions = PageVersion.objects.filter(webpage=webpage).order_by('-time')
        page_version = page_versions and page_versions[0] or None
        if page_version:
            if verbose:
                print ('size: ', page_version.size, '->', size)
                print ('checksum: ', page_version.checksum, '->', checksum)
            """
            if diff:
                l_1 = page_version.body.splitlines()
                l_2 = body.splitlines()
                l_diff = difflib.Differ().compare(l_1, l_2)
                print ('\n'.join(l_diff))
            """
        # if not dry and (not page_version or size != page_version.size or checksum != page_version.checksum):
        if extract_block or (not dry and (not page_version or checksum != page_version.checksum)):
            page_version = PageVersion(webpage=webpage, delay=delay, response_code=response_code, size=size, checksum=checksum, body=body)
            page_version.save()
            updated = True
            if extract_block:
                webpage.extract_blocks(xpath=extract_block, verbose=verbose)
            elif extract_blocks:
                extracted_blocks = webpage.extract_blocks(verbose=verbose)
                if verbose:
                    print ('blocks extracted:', len(extracted_blocks))
                webpage.purge_bips(current_blocks=extracted_blocks, verbose=verbose)
                webpage.create_blocks_dag()
        if verbose:
            page_version_id = page_version and page_version.id or 0
            print (site_id, webpage_id, page_version_id)
        return updated

    def purge_bips(self, verbose=False):
        """ for all pages, delete all but last BlockInPage for each xpath """
        webpages = Webpage.objects.filter(site=self)
        n_purged = 0
        for webpage in webpages:
            n_purged += webpage.purge_bips(verbose=False)
        if verbose:
            print('purged %d old blocks' % n_purged)

    def refetch_pages(self, skip_deny_path=True, extract_blocks=True, extract_segments=False, dry=False, verbose=False):
        """ fetch known pages; for each, if content has changed, save the version and re-extract blocks """
        webpages = Webpage.objects.filter(site=self)
        n_updates = n_unfound = 0
        extract_deny_list = text_to_list(self.extract_deny)
        for webpage in webpages:
            path = webpage.path
            if skip_deny_path:
                should_skip = False
                for deny_path in extract_deny_list:
                    if path.count(deny_path):
                        should_skip = True
                        break
                if should_skip:
                    continue
            updated = self.fetch_page(path, webpage=webpage, extract_blocks=extract_blocks, extract_segments=extract_segments, dry=dry, verbose=verbose)
            if updated == -1:
                n_unfound += 1
            elif updated:
                n_updates += 1
            sys.stdout.write('.')
            time.sleep(1)
        return webpages.count(), n_updates, n_unfound

    def get_active_theme(self, request):
        """ see get_active_theme(request) in module django_diazo.utils"""
        if request.GET.get('theme', None):
            try:
                theme = request.GET.get('theme')
                return Theme.objects.get(pk=theme)
            except Theme.DoesNotExist:
                pass
            except ValueError:
                pass
        for theme in Theme.objects.filter(site_using_theme__site=self, enabled=True).order_by('sort'):
            if theme.available(request):
                return theme
        return None

    def add_fragment(self, text, path='', reliability=5):
        added = False
        """
        strings = String.objects.filter(text=text, language=self.language, site=self)
        if strings:
            string = strings[0]
        else:
            string = String(text=text, string_type=FRAGMENT, site=self, language=self.language, txu=None, path=path, reliability=reliability)
            string.save()
            added = True
        return string, added
        """
        segments = Segment.objects.filter(text=text, language=self.language, site=self)
        if segments:
            segment = segments[0]
        else:
            segment = Segment(text=text, is_fragment=True, site=self, language=self.language)
            segment.save()
            added = True
        return segment, added

    def get_segments(self, translation_state=ANY):
        # return String.objects.filter(site=self, language=self.language, string_type=SEGMENT)
        return Segment.objects.filter(site=self, language=self.language)
    
    def get_segment_count(self):
        return len(self.get_segments(translation_state=ANY))

    def get_token_frequency(self, lowercasing=True):
        tokenizer = NltkTokenizer(language=self.language_id, lowercasing=lowercasing)
        tokens_dict = defaultdict(int)
        segments = self.get_segments()
        for segment in segments:
            tokens = tokenizer.tokenize(segment.text)
            for token in tokens:
                if not is_invariant_word(token):
                    tokens_dict[token] += 1
        return tokens_dict

    def get_word_count(self, lowercasing=True):
        return len(self.get_token_frequency())

class SiteTheme(models.Model):
    site = models.ForeignKey(Site, related_name='theme_used_for_site')
    theme = models.ForeignKey(Theme, related_name='site_using_theme')

    class Meta:
        verbose_name = _('theme used for site')
        verbose_name_plural = _('themes used for site')

class Proxy(models.Model):
    name = models.CharField(max_length=100)
    slug = AutoSlugField(unique=True, populate_from='name', editable=True)
    site = models.ForeignKey(Site)
    # language = models.ForeignKey(Language)
    language = models.ForeignKey(Language, related_name='language_proxy')
    host = models.CharField(max_length=100)
    base_path = models.CharField(max_length=100)
    enable_live_translation = models.BooleanField(default=False)
    robots_txt = models.TextField(verbose_name='robots.txt', blank=True, null=True, help_text="The virtual content of the robots.txt page." )
    translate_deny = models.TextField(verbose_name='Deny translation', blank=True, null=True, help_text="Paths of pages not to processed online by the proxy" )

    class Meta:
        verbose_name = _('proxy site')
        verbose_name_plural = _('proxy sites')

    def get_absolute_url(self):
        return '/proxy/%s/' % self.slug

    def get_filepath(self):
        return os.path.join(self.site.get_filepath(), self.language_id)

    def can_manage(self, user):
        return user.is_superuser

    def can_operate(self, user):
        return user.is_superuser

    def can_view(self, user):
        return user.is_authenticated()

    def blocks_ready(self, min_state=TRANSLATED):
        """ return blocks "ready for translation" """
        site = self.site
        language = self.language
        # qs = Block.objects.filter(site=site, Block_child__isnull=True)
        qs = Block.objects.filter(site=site)
        qs = qs.annotate(n_pages = RawSQL("SELECT COUNT(*) FROM wip_blockinpage WHERE wip_blockinpage.block_id = wip_block.id", ()))
        qs = qs.order_by('-n_pages')
        blocks = []
        for block in qs:
            if block.no_translate:
                continue
            if block.compute_translation_state(language) >= min_state:
                continue
            children = block.get_children()
            ready = True
            if children:
                for child in children:
                    if child.compute_translation_state(language) < min_state:
                        ready = False
                        break
            if ready:
                blocks.append(block)
        return blocks

    def make_tokenizer(self, return_matches=False):
        """ create a tokenizer for the proxy target language ...
            possibly exploit knowledge related to the target language and/or the proxy itself """
        return NltkTokenizer(language=self.language.code, lowercasing=False, return_matches=return_matches)

    """
    def import_translations(self, file, request=None):
        user_id = request and request.user.id or 1
        reliability = 5
        target_code = target_language.code
    """
    def import_translations(self, xliff_file, request=None, user_role=None):
        if not user_role:
            pass # ma dovrebbe essere specificato 
        site = self.site
        source_language = site.language
        target_language = self.language
        source_code = source_language.code.split('-')[0]
        target_code = target_language.code.split('-')[0]
        # print (source_code, target_code)
        status = { 'found': 0, 'imported': 0 }
        tree = etree.iterparse(xliff_file, events=("start", "end"))
        for action, elem in tree:
            tag = elem.tag
            if tag.count('{') and tag.count('}'):
                tag = tag.split('}')[1]
            # if action == 'start' and 
            # print(action, tag)
            if tag=='xliff' and action=='start':
                xliff_version = elem.get('version')
                status['version'] = xliff_version
            elif tag=='file' and action=='start':
                xliff_source_language = elem.get('source-language')
                xliff_target_language = elem.get('target-language')
                # print ('source and target languages: ', xliff_source_language, xliff_target_language)
                if not elem.get('source-language').split('-')[0]==source_code:
                    status['error'] = "source language doesn't match"
                    break
                elif not elem.get('target-language').split('-')[0]==target_code:
                    status['error'] = "target language doesn't match"
                    break
            elif action=='start':
                continue
            text = elem.text
            if tag.endswith('source') and not tag.endswith('seg-source'):
                source = text
                mrk_text = None
            elif tag.endswith('seg-source'):
                mrk_text = None
            elif tag.endswith('mrk'):
                mrk_text = text
            elif tag.endswith('target'):
                if mrk_text is None:
                    target = text
                else:
                    target = mrk_text
            elif tag.endswith('trans-unit'):
                if not source or not target:
                    continue
                status['found'] += 1
                sys.stdout.write('.')
                """
                qs = String.objects.filter(text=source, language=source_language, site=site)
                print qs.count()
                if target_code == 'en':
                    qs = qs.filter(Q(txu__isnull=True) | Q(txu__en=False))
                elif target_code == 'es':
                    qs = qs.filter(Q(txu__isnull=True) | Q(txu__es=False))
                elif target_code == 'fr':
                    qs = qs.filter(Q(txu__isnull=True) | Q(txu__fr=False))
                elif target_code == 'it':
                    qs = qs.filter(Q(txu__isnull=True) | Q(txu__it=False))
                n_source = qs.count()
                print n_source
                if not n_source:
                    source_string = String(text=source, language=source_language, site=site, reliability=reliability)
                    source_string.save()
                elif n_source == 1:
                    source_string = qs[0]
                else:
                    continue
                txu = source_string.txu
                if not txu:
                    txu = Txu(provider=site.name, user_id=user_id)
                    txu.save()
                    source_string.txu = txu
                    source_string.save()
                target_string = String(text=target, language=target_language, site=site, txu=txu, reliability=reliability)
                target_string.save()
                """

                """
                segment, created = Segment.objects.get_or_create(text=source, language=source_language, site=site)
                translation, created = Translation.objects.get_or_create(segment=segment, text=target, language=target_language, translation_type=MANUAL, user_role=user_role)
                if created:
                    status['imported'] += 1
                """
                try:
                    segment = Segment.objects.get(text=source, language=source_language, site=site)
                    translation = Translation.objects.get(segment=segment, text=target, language=target_language)
                except:
                    status['imported'] += 1
                sys.stdout.write('+')
        return status

    def apply_translation_memory(self):
        site = self.site
        site_invariants = text_to_list(site.invariant_words)
        source_language = site.language
        source_code = site.language_id
        target_language = self.language
        target_code = target_language.code
        empty_words = EMPTY_WORDS[target_code]
        target_codes = [target_code]
        blocks_ready = self.blocks_ready()
        n_ready = len(blocks_ready)
        n_partially = 0
        n_translated = 0
        if blocks_ready:
            segmenter = site.make_segmenter()
        for block in blocks_ready:
            translated_block = block.get_last_translation(language=target_language)
            translated = True
            ok_segments = 0
            n_substitutions = 0
            if translated_block:
                body = translated_block.body
                segments = translated_block.translated_block_get_segments(segmenter)
            else:
                body = block.body
                segments = block.block_get_segments(segmenter)                
            body = normalize_string(body)
            if not segments:
                logger.info('block: %d no segments' % block.id)
                continue # ???
            segments.sort(key=lambda x: len(x), reverse=True)
            for segment in segments:
                words = segment.split()
                if not non_invariant_words(words, site_invariants=site_invariants):
                    ok_segments +=1
                    logger.info('block: %d invariant segment : %s' % (block.id, segment))
                    continue
                if Segment.objects.filter(is_invariant=True, language=source_language, site=site, text=segment):
                    ok_segments +=1
                    logger.info('block: %d invariant string, segment : %s' % (block.id, segment))
                    continue
                translated_segment = None
                translations = Translation.objects.filter(language=target_language, segment__site=site, segment__language=source_language, segment__text=segment).distinct().order_by('-translation_type', 'user_role__role_type', 'user_role__level')
                if translations:
                    translation = translations[0]
                    """ add here some test on reliability """
                    translated_segment = translation.text
                else:
                    translated = False
                    if not segment.startswith('Home'):
                        # logger.info('block: %d , n_matches: %d ,  segment: -%s-' % (block.id, n_matches, repr(segment)))
                        logger.info('block: %d , segment: -%s-' % (block.id, repr(segment)))
                if translated_segment:
                    if segment[0].isupper() and translated_segment[0].islower():
                        translated_segment = translated_segment[0].upper() + translated_segment[1:]
                    count = body.count(segment)
                    replaced = False
                    if count:
                        l_body = len(body)
                        # for m in re.finditer(segment, body):
                        for m in re.finditer(re.escape(segment), body):
                            start = m.start()
                            if start>0 and body[start-1] in BOTH_QUOTES:
                                continue
                            end = m.end()
                            if end<(l_body-1) and body[end] in BOTH_QUOTES:
                                continue          
                            # body = body[:start] + '<span tx auto>%s</span>' % translated_segment + body[end:]
                            body = body[:start] + '<span tx="auto">%s</span>' % translated_segment + body[end:]
                            replaced = True
                            n_substitutions += 1
                            break
                    if replaced:
                        continue
                    replaced = replace_segment(body, segment)
                    if replaced:
                        body = replaced
                        n_substitutions += 1
                        continue
                    translated = False
                    logger.info('block: %d , segment: -%s- , not replaced with: -%s-' % (block.id, segment, translated_segment))
            if n_substitutions:
                previous_state = translated_block and translated_block.state or 0
                if not translated_block:
                    translated_block = block.clone(target_language)
                if translated:
                    translated_block.state = TRANSLATED
                    n_translated += 1
                    logger.info('block: %d , %s TRANSLATED' % (block.id, not previous_state and 'new' or ''))
                else:
                    translated_block.state = PARTIALLY
                    n_partially += 1
                    logger.info('block: %d , %s PARTIALLY' % (block.id, not previous_state and 'new' or ''))
                translated_block.body = body
                translated_block.save()
            elif ok_segments and not translated_block:
                translated_block = block.clone(target_language)
                translated_block.state = PARTIALLY
                n_partially += 1
                translated_block.save()
                logger.info('block: %d , new, PARTIALLY' % block.id)
        return n_ready, n_translated, n_partially

    def translate_page_content(self, content):
        html_string = re.sub("(<!--(.*?)-->)", "", content, flags=re.MULTILINE)
        html_string = normalize_string(html_string)
        content_document = html.document_fromstring(html_string)
        translated_document, has_translation = translated_element(content_document, self.site, webpage=None, language=self.language, translate_live=self.enable_live_translation)
        if has_translation:
            content = element_tostring(translated_document)
        return content, has_translation

    def propagate_up_block_updates(self):
        site = self.site
        language = self.language
        # language_code = language.code
        n_new = 0
        n_updated = 0
        n_no_updated = 0
        blocks_ready = self.blocks_ready()
        for block in blocks_ready:
            label = block.get_label()
            translated_blocks = TranslatedBlock.objects.filter(block=block, language=language, state__gt=0).order_by('-modified')
            if translated_blocks:
                translated_block = translated_blocks[0]
                element = html.fromstring(translated_block.body)
            else:
                translated_block = None
                element = None                
            translated_element, translation_date = block.translated_block_element(language, element=element)
            if translation_date:
                if translated_block:
                    if translated_block.modified > translation_date:
                        # print ('no_updated') #, label
                        n_no_updated +=1
                        continue
                    else:
                        n_updated +=1
                        # print ('updated') #, label
                else:
                    translated_block = TranslatedBlock(block=block, language=language)
                    n_new +=1
                    # print ('new') #, label
                # translated_block.body = html.tostring(translated_element)
                translated_block.body = element_tostring(translated_element)
                translated_block.save()
        return n_new, n_updated, n_no_updated

    def replace_fragments(self, text, path):
        """ build a multi-pattern regular expression for single pass substitution of fragment translations 
            see: https://www.safaribooksonline.com/library/view/python-cookbook-2nd/0596007973/ch01s19.html """
        site = self.site
        language = self.language
        """
        qs = String.objects.filter(string_type=FRAGMENT, site=site, language=site.language, txu__string__language=self.language)
        # see: http://stackoverflow.com/questions/15465858/django-reverse-to-contains-icontains
        qs = qs.extra(where=['''%s LIKE wip_string.path'''], params=(path,),)
        if qs.count():
            adict = dict([[s.text, String.objects.filter(txu=s.txu, language=language)[0].text] for s in qs])
        """
        # qs = Segment.objects.filter(is_fragment=True, site=site, language=site.language, segment__language=language)
        qs = Segment.objects.filter(is_fragment=True, site=site, language=site.language, segment_translation__language=language)
        # see: http://stackoverflow.com/questions/15465858/django-reverse-to-contains-icontains
        """ > but the "path" field is missing in the Segment class !!!
        qs = qs.extra(where=['''%s LIKE wip_string.path'''], params=(path,),)
        > """
        if qs.count():
            adict = {}
            for segment in qs:
                translation = segment.get_language_translations(language)[0]
                adict[segment.text] = translation.text
            rx = re.compile('|'.join(map(re.escape, adict)))
            def one_xlat(match):
                return adict[match.group(0)]
            text = rx.sub(one_xlat, text)
        return text

    # def export_translations(self, outfile_1, outfile_2=None, outfile_3=None, parallel_format=PARALLEL_FORMAT_NONE, tokenizer_1=None, tokenizer_2=None, lowercasing=False, max_tokens=1000, max_fertility=1000, known_links_fwd=None, known_links_rev=None):
    def export_translations(self, outfile_1, outfile_2=None, outfile_3=None, parallel_format=PARALLEL_FORMAT_NONE, tokenizer_1=None, tokenizer_2=None, lowercasing=False, max_tokens=1000, max_fertility=1000, known_links_fwd=None, known_links_rev=None, evaluate=False, test_set_module=2, verbose=False):
        segments = Segment.objects.filter(site=self.site, is_invariant=False).order_by('id')
        if parallel_format == PARALLEL_FORMAT_XLIFF:
            pass
        if known_links_fwd and known_links_rev:
            known_links_fwd.write('%5d %d\n' % (0, max_tokens))
            known_links_rev.write('%5d %d\n' % (0, max_tokens))
        n_translations = 0
        for segment in segments:
            source_text = segment.text
            if tokenizer_1:
                source_tokens = tokenize(source_text, tokenizer=tokenizer_1, lowercasing=lowercasing)
                L = len(source_tokens)
                if L > max_tokens:
                    continue
                source_text = ' '.join(source_tokens)
            translations = Translation.objects.filter(segment=segment, language=self.language).order_by('id')
            for translation in translations:
                target_text = translation.text
                if tokenizer_2:
                    target_tokens = tokenize(target_text, tokenizer=tokenizer_2, lowercasing=lowercasing)
                    M = len(target_tokens)
                    if M>max_tokens or abs(M-L)>max_fertility:
                        continue
                    target_text = ' '.join(target_tokens)
                    if verbose:
                        try:
                            print(n_translations, len(target_tokens), ' + '.join(target_tokens))
                        except:
                            pass
                if parallel_format == PARALLEL_FORMAT_XLIFF:
                    pass
                elif parallel_format == PARALLEL_FORMAT_TEXT:
                    outfile_1.write('%s . ||| . %s\n' % (source_text, target_text))
                elif parallel_format == PARALLEL_FORMAT_NONE:
                    outfile_1.write('%s\n' % source_text)
                    outfile_2.write('%s\n' % target_text)
                    if known_links_fwd and known_links_rev:
                        fwd = rev = ''
                        if translation.alignment and translation.alignment_type==MANUAL:
                            # if evaluate and n_translations % 2 == 0:
                            if not evaluate or test_set_module == 0 or n_translations % test_set_module != 0:
                                fwd, rev = split_alignment(translation.alignment)
                        known_links_fwd.write('%s\n' % fwd)
                        known_links_rev.write('%s\n' % rev)
                if outfile_3:
                    outfile_3.write('%d\n' % translation.id)
                n_translations += 1
        if known_links_fwd and known_links_rev:
            known_links_fwd.seek(0)
            known_links_fwd.write('%5d %d\n' % (n_translations, max_tokens))
            known_links_rev.seek(0)
            known_links_rev.write('%5d %d\n' % (n_translations, max_tokens))

    def make_bitext(self, lowercasing=False, use_invariant=False, tokenizer=None, max_tokens=1000, max_fertility=1000):
        site = self.site
        target_language = self.language
        source_tokenizer = NltkTokenizer(site.language_id, lowercasing=lowercasing)
        target_tokenizer = NltkTokenizer(self.language_id, lowercasing=lowercasing)
        segments = Segment.objects.filter(site=site)
        bitext = []
        for segment in segments:
            segment_text = segment.text
            # source_tokens = tokenize(segment_text, tokenizer=tokenizer, lowercasing=lowercasing)
            source_tokens = tokenize(segment_text, tokenizer=source_tokenizer)
            L = len(source_tokens)
            if L > max_tokens:
                continue
            if segment.is_invariant:
                if use_invariant:
                    alignment = Alignment([(i, i) for i in range(L)])
                    bitext.append(AlignedSent(source_tokens, source_tokens, alignment))
            else:
                translations = Translation.objects.filter(segment=segment, language=target_language)
                for translation in translations:
                    translation_text = translation.text
                    # target_tokens = tokenize(translation_text, tokenizer=tokenizer, lowercasing=lowercasing)
                    target_tokens = tokenize(translation_text, tokenizer=target_tokenizer)
                    M = len(target_tokens)
                    if M>max_tokens or abs(M-L)>max_fertility:
                        continue
                    bitext.append(AlignedSent(source_tokens, target_tokens))
        return bitext

    # def get_train_aligner(self, bitext=None, ibm_model=2, train=False, iterations=5, tokenizer=None, lowercasing=False, use_invariant=False, max_tokens=1000, max_fertility=1000):
    def get_train_aligner(self, bitext=None, ibm_model=2, train=False, iterations=5, lowercasing=False, use_invariant=False, max_tokens=1000, max_fertility=1000):
        if not bitext:
            # bitext = self.make_bitext(lowercasing=lowercasing, tokenizer=tokenizer, use_invariant=use_invariant, max_tokens=max_tokens, max_fertility=max_fertility)
            bitext = self.make_bitext(lowercasing=lowercasing, use_invariant=use_invariant, max_tokens=max_tokens, max_fertility=max_fertility)
        site = self.site
        aligner_name = 'align_%s_%s%s.pickle' % (site.slug, site.language_id, self.language_id)
        aligner_path = os.path.join(settings.CACHE_ROOT, aligner_name)
        if not train:
            if (sys.version_info < (3, 0)):
                if os.path.isfile(aligner_path):
                    f = open(aligner_path, 'rb')
                    aligner = pickle.load(f)
                    f.close()
                    return aligner
        if ibm_model == 3:
            aligner = IBMModel3(bitext, iterations)
        else:
            aligner = IBMModel2(bitext, iterations)
        if train:
            if (sys.version_info < (3, 0)):
                f = open(aligner_path, 'wb')
                pickle.dump(aligner, f, pickle.HIGHEST_PROTOCOL)
                f.close()
        return aligner

    def clear_alignments(self):
        target_language = self.language
        segments = Segment.objects.filter(site=self.site)
        for segment in segments:
            translations = Translation.objects.filter(segment=segment, language=target_language)
            for translation in translations:
                if translation.alignment and not translation.alignment_type==MANUAL:
                    translation.alignment = ''
                    translation.save() 

    def align_translations(self, aligner=None, bitext=None, ibm_model=2, iterations=5, lowercasing=False, evaluate=False, verbose=False):
        if not evaluate:
            self.clear_alignments()
        source_tokenizer = NltkTokenizer(self.site.language_id, lowercasing=lowercasing)
        target_tokenizer = NltkTokenizer(self.language_id, lowercasing=lowercasing)
        if not aligner:
            # aligner = self.get_train_aligner(bitext=bitext, ibm_model=ibm_model, train=True, iterations=iterations, tokenizer=tokenizer, lowercasing=lowercasing)
            aligner = self.get_train_aligner(bitext=bitext, ibm_model=ibm_model, train=True, iterations=iterations, lowercasing=lowercasing)
        target_language = self.language
        if evaluate:
            aer_total = 0.0
            n_evaluated = 0
        n_translations = 0
        segments = Segment.objects.filter(site=self.site).order_by('id')
        for segment in segments:
            source_tokens = tokenize(segment.text, tokenizer=source_tokenizer)
            translations = Translation.objects.filter(segment=segment, language=target_language).order_by('id')
            for translation in translations:
                if evaluate or not translation.alignment_type==MANUAL:
                    target_tokens = tokenize(translation.text, tokenizer=target_tokenizer)
                    alignment = best_alignment(aligner, source_tokens, target_tokens)
                    """
                    translation.alignment = ' '.join(['%s-%s' % (str(couple[0]), couple[1] is not None and str(couple[1]) or '') for couple in alignment])
                    print ('translation.alignment: ', translation.alignment)
                    """
                    alignment = ' '.join(['%s-%s' % (str(couple[0]), couple[1] is not None and str(couple[1]) or '') for couple in alignment])
                    # print ('alignment: ', alignment)
                if evaluate:
                    if translation.alignment_type==MANUAL:
                        aer_total += aer(alignment, translation.alignment)
                        n_evaluated += 1
                else:
                    if not translation.alignment_type==MANUAL:
                        translation.alignment = alignment
                        translation.alignment_type = MT
                        translation.save()
                n_translations += 1
        if evaluate and n_evaluated:
            evaluation = aer_total/n_evaluated
            if verbose:
                print ('evaluation: ', evaluation)
            return evaluation
    
    def eflomal_align_translations(self, lowercasing=False, max_tokens=1000, max_fertility=100, symmetrize=True, use_know_links=True, test_set_module=2, evaluate=False, verbose=False, debug=False):
        if not evaluate:
            self.clear_alignments()
        proxy_code = '%s_%s' % (self.site.slug, self.language_id)
        base_path = os.path.join(settings.BASE_DIR, 'sandbox')
        translation_ids = StringIO()
        # proxy_eflomal_align(self, base_path=base_path, lowercasing=lowercasing, max_tokens=max_tokens, max_fertility=max_fertility, translation_ids=translation_ids)
        proxy_eflomal_align(self, base_path=base_path, lowercasing=lowercasing, max_tokens=max_tokens, max_fertility=max_fertility, translation_ids=translation_ids, use_know_links=use_know_links, evaluate=evaluate, test_set_module=test_set_module, verbose=verbose, debug=debug)
        if verbose:
            print ('proxy_eflomal_align returned')
        if symmetrize:
            proxy_symmetrize_alignments(self)
            links_sym_filename = os.path.join(base_path, '%s_links_sym.txt' % proxy_code)
            alignment_file = open(links_sym_filename, 'r')
        else:
            all_filename = os.path.join(base_path, '%s_all.txt' % proxy_code)
            alignment_file = open(all_filename, 'r', encoding="utf-8")
        if verbose:
            print ('proxy_eflomal_align 2')
        translation_ids.seek(0)
        if verbose:
            print ('proxy_eflomal_align 3')
        if evaluate:
            aer_total = 0.0
            n_evaluated = 0
        n_translations = 0
        for line in alignment_file:
            translation_id = int(translation_ids.readline().replace('\n', ''))
            translation = Translation.objects.get(id=translation_id)
            if verbose:
                print (translation_id)
            if symmetrize:
                alignment = line.replace('\n', '')
            else:
                stop = line.find(')')
                alignment = line[1:stop]
            if verbose:
                print (alignment)
            if evaluate:
                if translation.alignment_type==MANUAL:
                    if verbose:
                        print ('--- fixed and computed alignment for translation # %d' % translation.id)
                        print (translation.alignment)
                        print (alignment)
                    # if n_translations % 2 == 1:
                    if test_set_module == 0 or n_translations % test_set_module == 0:
                        aer_total += aer(alignment, translation.alignment)
                        n_evaluated += 1
            else:
                if not translation.alignment_type==MANUAL:
                    translation.alignment = alignment
                    translation.alignment_type = MT
                    translation.save()
            n_translations += 1
        alignment_file.close()
        if verbose:
            print ('proxy_eflomal_align 4', evaluate, n_evaluated)
        if evaluate and n_evaluated:
            evaluation = aer_total/n_evaluated
            if verbose:
                print ('evaluation: ', evaluation)
            return evaluation

    def get_translations(self, translation_type=ANY):
        translations = Translation.objects.filter(segment__site=self.site, language=self.language)
        if translation_type:
            translations = translations.filter(translation_type=translation_type)
        return translations
    
    def get_translation_count(self):
        return len(self.get_translations(translation_type=ANY))

    def get_token_frequency(self, lowercasing=True):
        # tokenizer = NltkTokenizer(lowercasing=lowercasing)
        tokenizer = NltkTokenizer(language=self.language_id, lowercasing=lowercasing)
        tokens_dict = defaultdict(int)
        translations = self.get_translations()
        for translation in translations:
            tokens = tokenizer.tokenize(translation.text)
            for token in tokens:
                if not is_invariant_word(token):
                    tokens_dict[token] += 1
        return tokens_dict

class Webpage(models.Model):
    site = models.ForeignKey(Site)
    path = models.CharField(max_length=200)
    language = models.ForeignKey(Language, null=True, blank=True, help_text="Possibly overrides the site language")
    no_translate = models.BooleanField('NoTr', default=False) # 'Do not translate'
    created = CreationDateTimeField()
    # referer = models.ForeignKey('self', related_name='page_referer', blank=True, null=True)
    encoding = models.CharField(max_length=200, blank=True, null=True)
    last_modified = ModificationDateTimeField()
    last_checked = models.DateTimeField(null=True, help_text="Last time the page fetched with success")
    last_checked_response_code = models.IntegerField('Code') # 'Response code'
    last_unfound = models.DateTimeField(null=True, help_text="Last time the page wasn't found")
    blocks = models.ManyToManyField('Block', through='BlockInPage', related_name='page', blank=True, verbose_name='blocks')

    class Meta:
        verbose_name = _('original page')
        verbose_name_plural = _('original pages')
        ordering = ('path',)

    def __str__(self):
        return self.path

    def __unicode__(self):
        return self.__str__()

    def title_or_path(self):
        return self.path

    def get_region(self):
        page_versions = PageVersion.objects.filter(webpage=self).order_by('-time')
        last = page_versions and page_versions[0] or None
        return last and last.get_region()

    def get_blocks_in_use(self, sort=False):
        if sort:
            bips = BlockInPage.objects.filter(webpage=self).order_by('xpath')
        else:
            bips = Block.objects.filter(block_in_page__webpage=self).distinct()
        return bips

    def get_translated_blocks_count(self):
        proxies = Proxy.objects.filter(site=self.site).order_by('language__code')   
        languages = [proxy.language for proxy in proxies]
        language_blocks_translations = []
        for language in languages:
            language_blocks_translations.append([language, TranslatedBlock.objects.filter(block__page=self, language=language).values('block_id').distinct().count()])
        return language_blocks_translations

    def fetch_live(self):
        page_url = self.site.url + self.path
        request = urllib2.Request(page_url)
        response = urllib2.urlopen(request)
        body = response.read()
        return body

    def fetch(self, extract_blocks=True, extract_segments=False, dry=False, verbose=False):
        """ fetch known page; if content has changed, save the version and re-extract blocks """
        path = self.path
        updated = self.site.fetch_page(path, webpage=self, extract_blocks=extract_blocks, extract_segments=extract_segments, dry=dry, verbose=verbose)
        return updated

    def get_versions(self):
        return PageVersion.objects.filter(webpage=self).order_by('-time')

    def get_last_version(self):
        versions = self.get_versions()
        return versions and versions[0] or None

    def get_translation(self, language_code, use_cache=True, cache=False):
        content = None
        has_translation = False
        site = self.site
        language = get_object_or_404(Language, code=language_code)
        """
        proxy = Proxy.objects.get(site=site, language=language)
        if proxy.enable_live_translation:
            content = self.fetch_live()
            content_document = html.document_fromstring(content)
            # translated_document, has_translation = translated_element(content_document, site, self, language)
            translated_document, has_translation = translated_element(content_document, site, webpage=self, language=language)
            if has_translation:
                content = element_tostring(translated_document)
                return content, has_translation
        """
        if not cache:
            translated_versions = TranslatedVersion.objects.filter(webpage=self, language=language).order_by('-modified')
            translated_version = translated_versions and translated_versions[0] or None
        # if translated_version:
        if not cache and translated_version:
            return translated_version.body, True        
        versions = PageVersion.objects.filter(webpage=self).order_by('-time')
        last_version = versions and versions[0] or None
        if last_version:
            content = last_version.body
            content_document = html.document_fromstring(content)
            # translated_document, has_translation = translated_element(content_document, site, self, language)
            translated_document, has_translation = translated_element(content_document, site, webpage=self, language=language)
            if has_translation:
                # content = html.tostring(translated_document)
                content = element_tostring(translated_document)
        return content, has_translation

    def cache_translation(self, language_code):
        if not self.no_translate:
            content, has_translation = self.get_translation(language_code, cache=True)
            if has_translation:
                user = User.objects.get(pk=DEFAULT_USER)
                translated_page = TranslatedVersion(webpage=self, language_id=language_code, user=user)
                translated_page.body = content
                translated_page.save()

    def get_navigation(self, translation_state='', translation_codes=[], order_by='id'):
        qs = Webpage.objects.filter(site=self.site)
        if translation_state == INVARIANT: # block is language independent
            qs = qs.filter(no_translate=True)
        elif translation_state == TRANSLATED:
            if translation_codes:
                qs = qs.filter(webpage__language_id__in=translation_codes)
            else:
                qs = qs.filter(webpage__isnull=False) # at least 1
        elif translation_state == TO_BE_TRANSLATED:
            if translation_codes:
                qs = qs.annotate(nt = RawSQL("SELECT COUNT(*) FROM wip_translatedversion WHERE webpage_id = wip_webpage.id and language_id IN ('%s')" % "','".join(translation_codes), ())).filter(nt=0)
            else:
                qs = qs.filter(webpage__isnull=True).exclude(no_translate=True) # none
        if order_by == 'id':
            id = self.id
            qs_before = qs.filter(id__lt=id)
            qs_after = qs.filter(id__gt=id)
        elif order_by == 'path':
            path = self.path
            qs_before = qs.filter(path__lt=path)
            qs_after = qs.filter(path__gt=path)
        qs_before = qs_before.order_by('-'+order_by)
        qs_after = qs_after.order_by(order_by)
        previous = qs_before.count() and qs_before[0] or None
        next = qs_after.count() and qs_after[0] or None
        return previous, next

    def blocks_summary(self):
        site = self.site
        site_code = site.language_id
        blocks = Block.objects.filter(block_in_page__webpage=self).order_by('checksum', '-time')
        last_ids = []
        checksum = ''
        body = ''
        for block in blocks:
            """ this (new: 171018) filter is too restrictive ?
            if not (block.checksum==checksum and block.body==body):
            """
            if not block.checksum == checksum:
                checksum = block.checksum
                body = block.body
                last_ids.append(block.id)
        blocks = Block.objects.prefetch_related('source_block').filter(id__in=last_ids).order_by('-time')
        proxy_codes = [proxy.language_id for proxy in Proxy.objects.filter(site=self.site)]
        proxy_list = [[code, {'already': 0, 'partially': 0, 'translated': 0, 'revised': 0}] for code in proxy_codes]
        proxy_dict = dict(proxy_list)
        total = blocks.count()
        invariant = 0
        for block in blocks:
            if block.no_translate:
                invariant +=1
                continue
            if block.language_id in proxy_codes:
                proxy_dict[block.language_id]['already'] += 1
                continue
            translations = TranslatedBlock.objects.filter(block=block, language_id__in=proxy_codes)
            for translation in translations:
                code = translation.language_id
                if translation.state == 2:
                    proxy_dict[code]['revised'] += 1
                elif translation.state == 1:
                    proxy_dict[code]['translated'] += 1
                else:
                    proxy_dict[code]['partially'] += 1
        sorted_list = sorted(proxy_dict.items())
        proxy_list = []
        for code, t_dict in sorted_list:
            language = code_to_language(code)
            left = total - invariant
            for value in t_dict.values():
                left -= value
            t_dict['left'] = left
            proxy_list.append([language, t_dict])
        return blocks, total, invariant, proxy_list

    def extract_blocks(self, dry=False, xpath=None, verbose=False):
        """ if xpath is specified, extract only one block """
        site = self.site
        versions = PageVersion.objects.filter(webpage=self).order_by('-time')
        if verbose:
            print ('versions: ', versions)
        if not versions:
            return [] # , 0, 0
        last_version = versions[0]
        html_string = last_version.body
        # http://stackoverflow.com/questions/1084741/regexp-to-strip-html-comments
        html_string = re.sub("(<!--(.*?)-->)", "", html_string, flags=re.MULTILINE)
        html_string = normalize_string(html_string)
        html_string = html_string.replace('encoding="utf-8"', '')
        if not html_string:
            return []
        doc = html.document_fromstring(html_string)
        tree = doc.getroottree()
        top_els = doc.getchildren()
        if verbose:
            print ('top_els: ', top_els)
        n_1 = n_2 = n_3 = 0
        done = False
        current_blocks = []
        for top_el in top_els:
            if done:
                break
            for el in elements_from_element(top_el):
                if el.tag in BLOCK_TAGS and el.tag != 'br':
                    # save_failed = False
                    n_1 += 1 # number of block elements
                    """ NO [1] element index in xpath address !!!
                    el_xpath = tree.getpath(el)
                    """
                    el_xpath = tree.getpath(el).replace('[1]','')
                    if False: # verbose:
                        print (xpath, el_xpath)
                    if xpath and not el_xpath==xpath:
                        continue
                    checksum = element_signature(el)
                    string = etree.tostring(el)
                    matching_blocks = Block.objects.filter(site=site, checksum=checksum).order_by('-time')
                    if matching_blocks:
                        block = matching_blocks[0]
                    else:
                        block = Block(site=site, checksum=checksum, body=string)
                        if not dry:
                            block.save()
                            n_2 += 1 # number of new saved blocks
                        """
                        except:
                            print ('--- save error in page ---', self.id)
                            save_failed = True
                        """
                    block.xpath = el_xpath # xpath volatile value only for local use !!!
                    current_blocks.append(block)
                    if not dry:
                        this_block_in_page = BlockInPage.objects.filter(block=block, xpath=el_xpath, webpage=self).count()
                        if not this_block_in_page: # save_failed:
                            if matching_blocks: # purge BIPs for this xpath if BIP with new block is being created
                                blocks_in_page = BlockInPage.objects.filter(xpath=el_xpath, webpage=self)
                                blocks_in_page.delete()
                            n_3 += 1 # number of new blocks in page
                            block_in_page = BlockInPage(block=block, xpath=el_xpath, webpage=self)
                            block_in_page.save()
                    if xpath and el_xpath==xpath:
                        done = True
                        break
        # return n_1, n_2, n_3
        return current_blocks # , n_2, n_3

    # BIP = block in page
    def purge_bips(self, current_blocks=None, verbose=False):
        """ delete BIPs not maching any current page block
            current_blocks include a volatile xpath attribute !!!
        """
        if current_blocks:
            blocks_dict = {}
            for block in current_blocks:
                blocks_dict[block.checksum] = block.xpath
            bips = BlockInPage.objects.filter(webpage=self)
            for bip in bips:
                xpath = blocks_dict.get(bip.block.checksum, None)
                if not (xpath and bip.xpath == xpath):
                    bip.delete()
        """ delete all but last BIP for each xpath """
        bips = list(BlockInPage.objects.filter(webpage=self).order_by('xpath', '-time'))
        n_purged = 0
        previous_xpath = None
        for bip in bips:
            xpath = bip.xpath
            if xpath == previous_xpath:
                bip.delete()
                n_purged +=1
            previous_xpath = xpath
        if verbose:
            print('purged %d old blocks' % n_purged)
        return n_purged

    def create_blocks_dag(self, verbose=False):
        # BlockEdge.objects.all().delete()
        blocks_in_page = list(BlockInPage.objects.filter(webpage=self).order_by('xpath'))
        blocks = [None]
        xpaths = ['no-xpath']
        m = 0
        n = 0
        i = 0
        for bip in blocks_in_page:
            block = bip.block
            xpath = bip.xpath
            for j in range(i, -1, -1):
                # if xpath.startswith(xpaths[j]) and not xpath==xpaths[j]:
                if xpath.startswith(xpaths[j]) and (len(xpath.split('/')) > len(xpaths[j].split('/'))):
                    parent = blocks[j]
                    m += 1
                    if not BlockEdge.objects.filter(parent=parent, child=block):
                        try:
                            parent.add_child(block)
                            n += 1
                        except:
                            print ('create_blocks_dag error:', xpaths[j], xpath)
                    break
            i += 1
            blocks.append(block)
            xpaths.append(xpath)
        if verbose:
            print (m, n)

def get_strings(text, language, site=None):
    if site:
        strings = String.objects.filter(text=text, language=language, site=site)
    else:
        strings = String.objects.filter(text=text, language=language)
    return strings

class PageVersion(models.Model):
    webpage = models.ForeignKey(Webpage)
    time = CreationDateTimeField()
    delay = models.IntegerField(default=0)
    response_code = models.IntegerField('Code')
    size = models.IntegerField()
    checksum = models.CharField(max_length=32, blank=True, null=True)
    body = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('page version')
        verbose_name_plural = _('page versions')
        ordering = ('webpage__site', 'webpage__path', '-time')

    def get_region(self):
        sd = SDAlgorithm()
        try:
            return sd.wip_analyze_page(self.body)
        except:
            return None

    def page_version_get_segments(self, segmenter=None, exclude_TM_invariants=True):
        if not segmenter:
            segmenter = self.webpage.site.make_segmenter()
        site = self.webpage.site
        exclude_xpaths = BLOCKS_EXCLUDE_BY_XPATH.get(site.slug, [])
        html_string = re.sub("(<!--(.*?)-->)", "", self.body, flags=re.MULTILINE)
        html_string = normalize_string(html_string)
        segments = []
        for string in list(strings_from_html(html_string, fragment=False, exclude_xpaths=exclude_xpaths)):
            if string and string[0]=='{' and string[-1]=='}':
                continue
            segments.extend(segments_from_string(string, site, segmenter, exclude_TM_invariants=exclude_TM_invariants))
        return segments

class TranslatedVersion(models.Model):
    webpage = models.ForeignKey(Webpage)
    language = models.ForeignKey(Language)
    body = models.TextField(blank=True, null=True)
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    # approval_status = models.ForeignKey(ApprovalStatus)
    state = models.IntegerField(default=0)
    user = models.ForeignKey(User, null=True)
    comments = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('translated version')
        verbose_name_plural = _('translated versions')
# ContentType, currently not used, could be Site, Webpage or Block
class Txu(models.Model):
    provider = models.CharField(verbose_name='txu source', max_length=100, blank=True, null=True)
    entry_id = models.CharField(verbose_name='id by provider', max_length=100, blank=True, null=True)
    subjects = models.ManyToManyField('Subject', through='TxuSubject', related_name='txu', blank=True, verbose_name='subjects')
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    user = models.ForeignKey(User, null=True)
    comments = models.TextField(blank=True, null=True)
    en = models.BooleanField(default=False)
    es = models.BooleanField(default=False)
    fr = models.BooleanField(default=False)
    it = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('translation unit')
        verbose_name_plural = _('translation units')
        ordering = ('-created',)

    def __str__(self):
        return self.entry_id or str(self.id)

    def __unicode__(self):
        return self.__str__()

    def update_languages(self):
        strings = String.objects.filter(txu=self)
        l_dict = { 'en': False, 'es': False, 'fr': False, 'it': False, }
        for s in strings:
            l_dict[s.language_id] = True
        updated = False
        for code in l_dict.keys():
            if getattr(self, code) != l_dict[code]:
                setattr(self, code, l_dict[code])
                updated = True
        if updated:
            self.save()
        return updated

class TxuSubject(models.Model):
    txu = models.ForeignKey(Txu, related_name='txu')
    subject = models.ForeignKey(Subject, related_name='subject')

    class Meta:
        verbose_name = _('txu subject')
        verbose_name_plural = _('txu subjects')

class String(models.Model):
    string_type = models.IntegerField(choices=STRING_TYPE_CHOICES, default=UNKNOWN, null=True, verbose_name='string type')
    invariant = models.BooleanField(default=False)
    language = models.ForeignKey(Language)
    site = models.ForeignKey(Site, null=True)
    path = models.CharField(max_length=200, default='/', blank=True)
    txu = models.ForeignKey(Txu, blank=True, null=True, related_name='string')
    reliability = models.IntegerField(default=1)
    text = models.TextField()
    created = CreationDateTimeField(null=True)
    modified = ModificationDateTimeField(null=True)
    user = models.ForeignKey(User, null=True)
    is_fragment = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('string')
        verbose_name_plural = _('strings')
        ordering = ('-id',)

    def __str__(self):
        return self.text

    def __unicode__(self):
        return self.__str__()

    def language_code(self):
        return self.language.code

    def tokens(self):
        return self.text.split()

    def get_translations(self, target_languages=[]):
        if not target_languages:
            target_languages = Language.objects.exclude(code=self.language.code).distinct().order_by('code')
        translations = []
        has_translations = False
        txu = self.txu
        for language in target_languages:
            strings = String.objects.filter(txu=txu, language_id=language.code)
            if strings:
                has_translations = True
            translations.append([language, strings])
        return has_translations and translations or []

    def get_navigation(self, string_types=[], site=None, translation_state='', translation_codes=[], order_by=TEXT_ASC):
        # print ('order_by: ', order_by)
        text = self.text
        id = self.id
        modified = self.modified
        qs = String.objects.filter(language_id=self.language_id)
        # print (1, qs.count())
        if string_types:
            qs = qs.filter(string_type__in=string_types)
            # print (2, qs.count())
        if site:
            qs = qs.filter(site=site)
        if translation_state == INVARIANT:
            qs = qs.filter(invariant=True)
        elif translation_state == TRANSLATED:
            qs = qs.exclude(invariant=True)
            qs = qs.filter(txu__string__language_id__in=translation_codes)
        elif translation_state == TO_BE_TRANSLATED:
            qs = qs.exclude(invariant=True)
            """
            qs = qs.exclude(txu__string__language_id__in=translation_codes)
            """
            if 'en' in translation_codes:
                qs = qs.filter(txu__en=False)
            if 'es' in translation_codes:
                qs = qs.filter(txu__es=False)
            if 'fr' in translation_codes:
                qs = qs.filter(txu__fr=False)
            if 'it' in translation_codes:
                qs = qs.filter(txu__it=False)
            # print (3, qs.count())
            # print (4, translation_codes)
        first = last = previous = next = None
        n = qs.count()
        # print (n, order_by, TEXT_ASC, order_by == TEXT_ASC, 1 == 1)
        if n:
            if order_by == TEXT_ASC:
                qs = qs.order_by('text')
                qs_before = qs.filter(text__lt=text).order_by('-text')
                qs_after = qs.filter(text__gt=text).order_by('text')
                # print (order_by, qs_before.count())
            elif order_by == ID_ASC:
                qs = qs.order_by('id')
                qs_before = qs.filter(id__lt=id).order_by('-id')
                qs_after = qs.filter(id__gt=id).order_by('id')
                # print (order_by, qs_before.count())
            elif order_by == DATETIME_ASC:
                qs = qs.order_by('modified')
                qs_before = qs.filter(modified__lt=modified).order_by('-modified')
                qs_after = qs.filter(modified__gt=modified).order_by('modified')
                # print (order_by, qs_before.count())
            elif order_by == DATETIME_DESC:
                qs = qs.order_by('-modified')
                qs_before = qs.filter(modified__gt=modified).order_by('modified')
                qs_after = qs.filter(modified__lt=modified).order_by('-modified')
                # print (order_by, qs_before.count())
            previous = qs_before.count() and qs_before[0] or None
            next = qs_after.count() and qs_after[0] or None
            first = qs[0]
            first = not first.id==id or None
            last = qs.reverse()[0]
            last = not last.id==id or None
        # return previous, next
        return n, first, last, previous, next

class Block(node_factory('BlockEdge')):
    site = models.ForeignKey(Site)
    xpath = models.CharField(max_length=200, blank=True, default='')
    body = models.TextField(blank=True, null=True)
    language = models.ForeignKey(Language, null=True, blank=True)
    no_translate = models.BooleanField(default=False)
    checksum = models.CharField(max_length=32)
    time = CreationDateTimeField()
    state = models.IntegerField(default=0)
    webpages = models.ManyToManyField(Webpage, through='BlockInPage', related_name='block', blank=True, verbose_name='pages')

    class Meta:
        verbose_name = _('page block')
        verbose_name_plural = _('page blocks')
        ordering = ('-time',)

    def get_label(self):
        label = text_from_html(self.body)
        if len(label) > 80:
            label = label[:80] + ' ...'
        return label

    def __str__(self):
        # return self.xpath
        return self.get_label()

    def __unicode__(self):
        return self.__str__()

    def normalized_body(self):
        return normalize_string(self.body)

    def pages_count(self):
        return self.webpages.all().count()

    def get_language(self):
        return self.language or self.site.language or Language.objects.get(code='it')

    def bips(self):
        return BlockInPage.objects.filter(block=self).distinct().count()

    def get_level(self):
        parents = self.parents()
        if parents:
            return 1 + parents[0].get_level()
        else:
            return 0

    def get_children(self):
        if not self.children.exists():
            return []
        down_edges = BlockEdge.objects.filter(parent=self) # .all()
        return [edge.child for edge in down_edges]

    def num_children(self):
        return len(self.get_children())

    def get_previous_next(self, include_language=None, exclude_language=None, order_by='id', skip_no_translate=None):
        site = self.site
        qs = Block.objects.filter(site=site)
        if skip_no_translate:
            qs = qs.exclude(no_translate=True)
        if order_by == 'id':
            id = self.id
            qs_before = qs.filter(id__lt=id)
            qs_after = qs.filter(id__gt=id)
        """
        elif order_by == 'xpath':
            xpath = self.xpath
            qs_before = qs.filter(xpath__lt=xpath)
            qs_after = qs.filter(xpath__gt=xpath)
        """
        qs_before = qs_before.order_by('-'+order_by)
        qs_after = qs_after.order_by(order_by)
        previous = qs_before.count() and qs_before[0] or None
        next = qs_after.count() and qs_after[0] or None
        return previous, next

    # alternative version of get_previous_next
    def get_navigation(self, site=None, webpage=None, translation_state='', translation_codes=[], source_text_filter='', order_by='id'):
        target_code = len(translation_codes)==1 and translation_codes[0] or None
        qs = Block.objects.filter(site=self.site)
        if webpage:
            qs = qs.filter(block_in_page__webpage=webpage).distinct()
        elif site:
            qs = qs.filter(block_in_page__webpage__site=site).distinct()
        if translation_state == INVARIANT: # block is language independent
            qs = qs.filter(no_translate=True)
        elif translation_state == ALREADY: # block is already in target language
            qs = qs.filter(language_id=target_code)
        elif translation_state == TRANSLATED:
            if translation_codes:
                # qs = qs.filter(source_block__language_id__in=translation_codes)
                for code in translation_codes:
                    qs = qs.filter(source_block__language_id=code)
            else:
                qs = qs.filter(source_block__isnull=False) # at least 1
        elif translation_state == TO_BE_TRANSLATED:
            if translation_codes:
                qs = qs.annotate(nt = RawSQL("SELECT COUNT(*) FROM wip_translatedblock WHERE block_id = wip_block.id and language_id IN ('%s')" % "','".join(translation_codes), ())).filter(nt=0)
            else:
                # qs = qs.filter(source_block__isnull=True).exclude(no_translate=True) # none
                qs = qs.filter(source_block__isnull=True) # none
            qs = qs.exclude(no_translate=True) # none
            if target_code:
                qs = qs.exclude(language_id=target_code)
        if source_text_filter:
            qs = qs.filter(body__icontains=source_text_filter)
        if order_by == 'id':
            id = self.id
            qs_before = qs.filter(id__lt=id)
            qs_after = qs.filter(id__gt=id)
        """
        elif order_by == 'xpath':
            xpath = self.xpath
            qs_before = qs.filter(xpath__lt=xpath)
            qs_after = qs.filter(xpath__gt=xpath)
        """
        qs_before = qs_before.order_by('-'+order_by)
        qs_after = qs_after.order_by(order_by)
        previous = qs_before.count() and qs_before[0] or None
        next = qs_after.count() and qs_after[0] or None
        return qs.count(), previous, next

    def clone(self, language):
        return TranslatedBlock(block=self, language=language, body=self.body)

    def get_last_translation(self, language):
        translations = TranslatedBlock.objects.filter(block=self, language=language).order_by('-modified')
        return translations.count() and translations[0] or None

    def get_last_translations(self, language=None):
        if language:
            languages = [language]
        else:
            proxies = Proxy.objects.filter(site=self.site).order_by('language__code')   
            languages = [proxy.language for proxy in proxies]
        language_translations = []
        has_translations = False
        for language in languages:
            translations = TranslatedBlock.objects.filter(block=self, language=language).order_by('-modified')
            language_translations.append([language.code, translations])
            if translations:
                has_translations = True
        return has_translations and language_translations or []

    def get_translation_states(self):
        """
        developed early for listing the blocks included in a page
        """
        proxy_languages = [proxy.language for proxy in self.site.get_proxies()]
        invariant = self.no_translate
        states = []
        for language in proxy_languages:
            if invariant:
                state = 'I'
            elif language == self.language:
                state = 'A'
            else:
                translations = TranslatedBlock.objects.filter(block=self, language=language).order_by('-modified')
                if not translations:
                    state = 'U'
                else:
                    translation = translations[0]
                    if translation.state == REVISED:
                        state = 'R'
                    elif translation.state == TRANSLATED:
                        state = 'T'
                    else:
                        state = 'P'
            states.append(state)
        return states

    def compute_translation_state(self, language):
        if self.no_translate:
            return INVARIANT
        last_translation = self.get_last_translation(language)
        if last_translation:
            return last_translation.state
        children = self.get_children()
        if not children:
            return NONE
        state = ALREADY
        for child in children:
            state = min(state, child.compute_translation_state(language))
        return state            

    def block_get_segments(self, segmenter):
        if not segmenter:
            segmenter = self.site.make_segmenter()
        return get_segments(self.body, self.site, segmenter)

    def make_rangeMappings(self, target_text, source_matches, target_matches, alignment):
        links = split_alignment(alignment, return_links=True)
        links.sort(key=lambda x: (x[1], x[0]))
        # lefts = [link[0] for link in links]
        rights = [link[1] for link in links]
        rangeMappings = []
        previous_left = None
        for link in links:
            left = link[0]
            right = link[1]
            """
            if lefts.count(left) > 1:
                continue
            """
            if rights.count(right) > 1:
                continue
            target_match = target_matches[right]
            targetRangeStart = target_match.span()[0]
            targetRangeLength = target_match.span()[1] - targetRangeStart
            target_range = { 'start': targetRangeStart, 'length': targetRangeLength}
            if left == previous_left:
                targetRangeLength += (targetRangeStart-rangeMappings[-1]['target']['start'])
                rangeMappings[-1]['target']['length'] = targetRangeLength
            else:
                source_match = source_matches[left]
                sourceRangeStart = source_match.span()[0]
                sourceRangeLength = source_match.span()[1] - sourceRangeStart
                source_range = { 'start': sourceRangeStart, 'length': sourceRangeLength }
                rangeMapping = { 'source': source_range, 'target': target_range }
                rangeMappings.append(rangeMapping)
            previous_left = left
        return rangeMappings

    def apply_tm(self, body=None, proxy=None, target_language=None, use_lineardoc=False, segmenter=None, source_tokenizer=None, target_tokenizer=None, dry=False):
        target_language = target_language or Language.objects.get(code='en')
        site = self.site
        source_language = site.language
        if not segmenter:
            segmenter = site.make_segmenter()
        range_mappings = []
        if not body:
            translated_block = self.get_last_translation(language=target_language)
            if translated_block:
                body = translated_block.body
            else:
                body = self.body
        html = re.sub("(<!--(.*?)-->)", "", body, flags=re.MULTILINE)
        html = normalize_string(html)
        lineardoc = LineardocParse(html)
        linearblock = lineardoc.getFirstBlock()
        print ('--- apply_tm - linearblock:\n', linearblock.dump())

        def getBoundaries(text):
            segments, boundaries, whitespaces = segmenter.extract(text)
            return boundaries

        linearsentences = linearblock.getSentences(getBoundaries)
        n_segments = len(linearsentences)
        print ('--- apply_tm - linearblock sentences:')
        for ls in linearsentences: print (ls.dump())
        return_matches = True
        if not source_tokenizer:
            source_tokenizer = site.make_tokenizer(return_matches=return_matches)
        if not target_tokenizer:
            if proxy: 
                target_tokenizer = proxy.make_tokenizer(return_matches=return_matches)
            else:
                target_tokenizer = NltkTokenizer(source_language.code, lowercasing=False, return_matches=return_matches)
        site_invariants = text_to_list(site.invariant_words)
        segments_tokens = []
        n_invariants = 0
        n_translations = 0
        n_substitutions = 0
        translated = True
        translated_sentences = []
        translated_sentence = None
        for i_segment in range(n_segments):
            if translated_sentence:
                pass
                translated_sentence = None
            translated_sentence = None
            linearsentence = linearsentences[i_segment]
            segment = linearsentence.getPlainText() # .strip()
            segment = segment.strip().replace('  ', ' ')
            # empty segment? do nothing
            if not segment:
                print ('--- empty:', i_segment, '"'+segment+'"')
                translated_sentences.append(linearsentence)
                continue
            print ('segment:', i_segment, '"'+segment+'"')
            source_matches = list(source_tokenizer.tokenize(segment))
            tokens = [segment[m.span()[0]:m.span()[1]] for m in source_matches]
            segments_tokens.append([segment, tokens])
            # first, test if no translation is required
            non_invariant_tokens = [t for t in tokens if not is_invariant_word(t, site_invariants=site_invariants)]
            if not non_invariant_tokens or Segment.objects.filter(is_invariant=True, language=source_language, site=site, text=segment):
                n_invariants += 1
                print ('--- invariant_segment:', i_segment, '"'+segment+'"')
                translated_sentences.append(linearsentence)
                continue
            # second, look for a translation
            translations = Translation.objects.filter(language=target_language, segment__site=site, segment__text=segment).distinct().order_by('-translation_type', 'user_role__role_type', 'user_role__level')
            print ('# translations:', len(translations))
            if not translations:
                translated_sentences.append(linearsentence)
                continue
            translation = translations[0]
            translated_segment = translation.text
            # try a simple text substitution
            textChunks = linearsentence.textChunks
            replaced = False
            for j in range(len(textChunks)):
                textChunk = textChunks[j]
                if len(textChunk.text) and textChunk.text==segment:
                    # linearsentence = linearsentence.replaceChunkText(j, translated_segment)
                    translated_sentence = copy.deepcopy(linearsentence)
                    translated_sentence.textChunks[j].text = translated_segment
                    translated_sentence.textChunks = addCommonTag (
                        translated_sentence.textChunks, {
                            'name': 'span',
                            'attributes': { 'tx': 'auto' }})
                    translated_sentences.append(translated_sentence)
                    n_substitutions += 1
                    print ('--- simple substitution:', i_segment)
                    replaced = True
                    break
            if replaced:
                continue
            # try with alignment and lineardoc
            alignment = translation.alignment 
            alignment = alignment and normalized_alignment(alignment)
            n_translations += 1
            if alignment and translation.alignment_type==MANUAL:
                target_matches = list(target_tokenizer.tokenize(translated_segment))
                range_mappings = self.make_rangeMappings(translated_segment, source_matches, target_matches, alignment)
                # print ('--- range_mappings', range_mappings)
                translated_sentence = linearsentence.translateTags(translated_segment, range_mappings)
                translated_sentence.textChunks = addCommonTag (
                    translated_sentence.textChunks, {
                        'name': 'span',
                        'attributes': { 'tx': 'auto' }})
                # print ('--- translated_sentence', i_segment, translated_sentence.getPlainText())
                translated_sentences.append(translated_sentence)
                n_substitutions += 1
                print ('--- substitution using alignment:', i_segment)
                continue

            translated_sentences.append(linearsentence)
            print ('--- original sentence:', i_segment, linearsentence)
            translated = False
        print ('--- apply_tm - translated sentences:')
        for ts in translated_sentences: print (ts.dump())
        translated_block = mergeSentences(translated_sentences)
        translated_block = translated_block.simplify()
        print ('--- apply_tm - translated block:\n', translated_block.dump())
        translated_body = translated_block.getHtml()
        if dry:
            return translated, n_invariants, n_substitutions, body, lineardoc, linearsentences, segments_tokens, n_translations, translated_sentences, translated_body
        else:
            return translated, n_invariants, n_substitutions

    def apply_invariants(self, segmenter):
        if self.no_translate:
            return False
        segments = self.block_get_segments(segmenter)
        site_invariants = text_to_list(self.site.invariant_words)
        invariant = True
        for segment in segments:
            # if not type(segment) == unicode:
            if not type(segment) == str:
                return False
            if not non_invariant_words(segment.split(), site_invariants=site_invariants):
                continue
            matches = Segment.objects.filter(site=self.site, text=segment, is_invariant=True)
            if not matches:
                invariant = False
                break
        if invariant:
            self.no_translate = True
            self.save()
        return invariant

    def real_translation_state(self, language):
        language_translations = self.get_last_translations(language=language)
        if language_translations:
            translations = language_translations.get(language.code, [])
            if not translations:
                return 0
        translated_block = translations[0]

    # def translated_element(element, site, webpage, language, xpath='/html'):
    def translated_block_element(self, language, element=None, webpage=None, xpath=None):
        site = self.site
        translation_date = None
        if xpath:
            translated_blocks = TranslatedBlock.objects.filter(block=self, language=language, state__gt=0).order_by('-modified')
            if translated_blocks:
                translated_block = translated_blocks[0]
                element = html.fromstring(translated_block.body)
                translation_date = translated_block.modified
                return element, translation_date
        if element is None:
            element = html.fromstring(self.body)
        if not webpage:
            blocks_in_page = BlockInPage.objects.filter(block=self, webpage__site=site)
            # block_in_page = sorted(blocks_in_page, cmp=lambda x,y: len(x.xpath) < len(y.xpath))[0]
            if not blocks_in_page.count():
                return None, None
            block_in_page = sorted(blocks_in_page, key=lambda x: len(x.xpath), reverse=True)[0]
            webpage = block_in_page.webpage
            xpath = block_in_page.xpath
        child_tags_dict_1 = {}
        child_tags_dict_2 = {}
        # build a dict with the number of occurrences of each type of block tag
        for child_element in element.getchildren():
            tag = child_element.tag
            if tag in BLOCK_TAGS:
                child_tags_dict_1[tag] = child_tags_dict_1.setdefault(tag, 0)+1
        # for each child element with a block tag, compute the incremental xpath (branch)
        # and replace it with its translation
        for child_element in element.getchildren():
            tag = child_element.tag
            if tag in BLOCK_TAGS:
                child_tags_dict_2[tag] = n = child_tags_dict_2.setdefault(tag, 0)+1
                branch = tag
                # NO [1] element index in xpath address !!!
                # if child_tags_dict_1[tag] > 1:
                if n>1 and child_tags_dict_1[tag] > 1:
                    branch += '[%d]' % n
                child_xpath = '%s/%s' % (xpath, branch)
                # print (child_xpath)
                blocks_in_page = BlockInPage.objects.filter(webpage=webpage, xpath=child_xpath).order_by('-block__time')
                # print (blocks_in_page.count(), webpage)
                if blocks_in_page:
                    child_block = blocks_in_page[0].block           
                    translated_child, child_translation_date = child_block.translated_block_element(language, element=child_element, webpage=webpage, xpath=child_xpath)
                    if child_translation_date:
                        element.replace(child, translated_child)
                        if translation_date:
                            translation_date = max(translation_date, child_translation_date)
                        else:
                            translation_date = child_translation_date
        # return the original element with translated sub-elements replaced in it
        return element, translation_date

class BlockInPage(models.Model):
    block = models.ForeignKey(Block, related_name='block_in_page')
    webpage = models.ForeignKey(Webpage, related_name='webpage')
    xpath = models.CharField(max_length=200, blank=True)
    time = CreationDateTimeField(null=True)

    class Meta:
        verbose_name = _('block in page')
        verbose_name_plural = _('blocks in page')
 
class TranslatedBlock(models.Model):
    language = models.ForeignKey(Language)
    block = models.ForeignKey(Block, related_name='source_block')
    body = models.TextField(blank=True, null=True)
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    editor = models.ForeignKey(User, null=True, blank=True, related_name='editor')
    state = models.IntegerField(default=0)
    revisor = models.ForeignKey(User, null=True, blank=True, related_name='revisor')
    comments = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('translated block')
        verbose_name_plural = _('translated blocks')

    def translated_block_get_segments(self, segmenter):
        return get_segments(self.body, self.block.site, segmenter)

    def normalized_body(self):
        return normalize_string(self.body)

class BlockEdge(edge_factory('Block', concrete = False)):
    created = CreationDateTimeField(_('created'))

    class Meta:
        verbose_name = _('block edge')
        verbose_name_plural = _('block edges')

# inspired by the algorithm of utils.elements_from_element
# def translated_element(element, site, webpage, language, xpath='/html'):
def translated_element(element, site, webpage=None, language=None, xpath='/html', translate_live=False):
    # print 'translated_element', xpath
    has_translation = False
    block = None
    blocks_in_page = webpage and BlockInPage.objects.filter(xpath=xpath, webpage=webpage).order_by('-time') or []
    if blocks_in_page:
        block = blocks_in_page[0].block
    elif not webpage and translate_live:
        checksum = element_signature(element)
        blocks = Block.objects.filter(site=site, checksum=checksum).order_by('-time')
        block = blocks and blocks[0] or None
        # if block: print ('checksum: ', checksum, 'block: ', block)
    if block:
        if block.no_translate:
            return element, True
        translated_blocks = TranslatedBlock.objects.filter(block=block, language=language, state__gt=0).order_by('-modified')
        # print 'translated_blocks : ', translated_blocks
        if translated_blocks:
            element = html.fromstring(translated_blocks[0].body)
            # return the complete translation of the block
            return element, True

    child_tags_dict_1 = {}
    child_tags_dict_2 = {}
    # build a dict with the number of occurrences of each type of block tag
    for child in element.getchildren():
        tag = child.tag
        if tag in BLOCK_TAGS:
            child_tags_dict_1[tag] = child_tags_dict_1.setdefault(tag, 0)+1
    # for each child element with a block tag, compute the incremental xpath (branch)
    # and replace it with its translation
    for child in element.getchildren():
        tag = child.tag
        if tag in BLOCK_TAGS:
            child_tags_dict_2[tag] = n = child_tags_dict_2.setdefault(tag, 0)+1
            branch = tag
            # NO [1] element index in xpath address !!!
            # if child_tags_dict_1[tag] > 1:
            if n>1 and child_tags_dict_1[tag] > 1:
                branch += '[%d]' % n
#           translated_child, child_has_translation = translated_element(child, site, webpage, language, xpath='%s/%s' % (xpath, branch))
            translated_child, child_has_translation = translated_element(child, site, webpage=webpage, language=language, xpath='%s/%s' % (xpath, branch), translate_live=translate_live)
            if child_has_translation:
                element.replace(child, translated_child)
                has_translation = True
    # return the original element with translated sub-elements replaced in it
    return element, has_translation

def get_segments(body, site, segmenter, fragment=True, exclude_tx=True, exclude_xpaths=False):
    if not segmenter:
        segmenter = site.make_segmenter()
    html_string = re.sub("(<!--(.*?)-->)", "", body, flags=re.MULTILINE)
    html_string = normalize_string(html_string)
    if not html_string:
        return []
    segments = []
    for string in list(strings_from_html(html_string, fragment=fragment, exclude_tx=exclude_tx, exclude_xpaths=exclude_xpaths)):
        if string and string[0]=='{' and string[-1]=='}':
            continue
        segments.extend(segments_from_string(string, site, segmenter))
    return segments

# def can_strip(word, site_invariants=[]):
def is_invariant_word(word, site_invariants=[]):
    """ word belongs to invariant classes: web addresses, email addresses, numbers """
    # return word.count('#') or word.count('@') or word.count('http') or word.replace(',', '.').isnumeric() or word in site_invariants
    return is_base_invariant_word(word) or word in site_invariants

def non_invariant_words(words, site_invariants=[]):
    non_invariant = []
    for word in words:
        if not is_invariant_word(word, site_invariants=site_invariants):
            non_invariant.append(word)
    return non_invariant      

re_eu_date = re.compile(r'(0?[1-9]|[1-2][0-9]|3[0-1])(-|/|\.)(0?[1-9]|1[0-2])(-|/|\.)([0-9]{4})') # es: 10/7/1953, 21-12-2015
re_decimal_thousands_separators = re.compile(r'[0-9](\.|\,)[0-9]')
re_spaces = re.compile(r'\b[\b]+')
def segments_from_string(string, site, segmenter, exclude_TM_invariants=True, include_boundaries=False):
    if string.count('window') and string.count('document'):
        return []
    if string.count('flickr'):
        return []
    site_invariants = text_to_list(site.invariant_words)
    # segments = segmenter.extract(string)[0]
    segments, boundaries, whitespaces = segmenter.extract(string)
    filtered = []
    filtered_boundaries = []
    # for s in segments:
    for i in range(len(segments)):
        s = segments[i]
        boundary = boundaries[i]
        """ REPLACE NON-BREAK SPACES """
        s = s.replace('\xc2\xa0', ' ')
        s = re_spaces.sub(' ', s)
        s = s.strip()
        """ REMOVE PSEUDO-BULLETS """
        if s.startswith(u'- ') or s.startswith(u'– '): s = s[2:]
        if s.endswith(u' -') or s.endswith(u' –'): s = s[:-3]
        s = s.strip()
        if len(s) < 3:
            continue
        # KEEP SEGMENTS CONTAINING: DATES, NUMBERS INCLUDING SEPARATORS, CURRENCY SYMBOLS
        # if re_eu_date.findall(s) or re_decimal_thousands_separators.findall(s) or regex.findall(ur'\p{Sc}', s):
        if re_eu_date.findall(s) or re_decimal_thousands_separators.findall(s) or regex.findall(r'\p{Sc}', s):
            filtered.append(s)
            continue
        """ REMOVE RESIDUOUS SEGMENTS NON INCLUDING ANY LETTER """
        if not re.search('[a-zA-Z]', s):
            continue
        """ THIS IS SPECIFIC TO BREADCRUMBS IN SCUOLEMIGRANTI """
        if s.startswith('Home'):
            continue
        if not s: continue
        """ STRIP PUNCTUATION MARKS, BRACKETS, ARITHMETIC OPERATORS ... 
        s = s.strip(SEPARATORS[language_code])
        if not s: continue
        """
        """ REMOVE STARTING OR ENDING QUOTES THAT HAVE MATCHING QUOTES
        for left, right in QUOTES:
            if s[0]==left and s.count(right)<=1:
                s = s[1:]
                if not s: break
                s = s.replace(right, '').strip()
                if not s: break
            if s[-1]==right and s.count(left)<=1:
                s = s[:-1]
                if not s: break
                s = s.replace(right, '').strip()
                if not s: break
        if not s: continue
        """
        """ REMOVE SEGMENTS INCLUDING ONLY WORDS BELONGING TO INVARIANT CLASSES """
        words = re.split(" |\'", s)
        if len(words) > 1:
            stripped = False
            while words and is_invariant_word(words[0], site_invariants=site_invariants):
                words = words[1:]
                stripped = True
            while words and is_invariant_word(words[-1], site_invariants=site_invariants):
                words = words[:-1]
                stripped = True
            if not words: continue
        if len(words) == 1: # 1 word at the start or as the result of stripping other words
            word = words[0]
            if is_invariant_word(word, site_invariants=site_invariants) or word.isupper() or word.lower() in EMPTY_WORDS[site.language.code]:
                continue
        """ REMOVE SEGMENT MATCHING SITE-ASSOCIATED INVARIANT STRINGS IN THE TM """
        if exclude_TM_invariants:
            # if String.objects.filter(site=site, language=site.language, text=s, invariant=True).count():
            if Segment.objects.filter(site=site, language=site.language, text=s, is_invariant=True).count():
                continue
        filtered.append(s)
        filtered_boundaries.append(boundary)
    # print ('segments_from_string - boundaries, filtered_boundaries:', boundaries, filtered_boundaries)
    if include_boundaries:
        return filtered, boundaries
    else:
        return filtered

class Scan(models.Model):
    name = models.CharField(max_length=20)
    site = models.ForeignKey(Site, null=True)
    language = models.ForeignKey(Language, null=True)
    start_urls = models.TextField()
    allowed_domains = models.TextField()
    allow = models.TextField()
    deny = models.TextField()
    max_pages = models.IntegerField()
    count_words = models.BooleanField(default=False)
    count_segments = models.BooleanField(default=False)
    page_count = models.IntegerField(default=0)
    word_count = models.IntegerField(default=0)
    segment_count = models.IntegerField(default=0)
    user = models.ForeignKey(User, null=True)
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    # task_id = models.IntegerField()
    task_id = models.CharField(max_length=100)
    terminated = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('discovery scan')
        verbose_name_plural = _('discovery scans')

    def get_label(self):
        return '%s-%s' % (self.name, self.created.strftime("%y%m%d-%H%M"))

    def get_links(self):
        return Link.objects.filter(scan=self)

class Link(models.Model):
    scan = models.ForeignKey(Scan)
    url = models.TextField()
    status = models.IntegerField()
    encoding = models.TextField()
    size = models.IntegerField()
    title = models.TextField()
    created = CreationDateTimeField()

    class Meta:
        verbose_name = _('followed link')
        verbose_name_plural = _('followed links')

class SegmentCount(models.Model):
    scan = models.ForeignKey(Scan)
    segment = models.CharField(max_length=1000)
    count = models.IntegerField()

    class Meta:
        verbose_name = _('segment count')
        verbose_name_plural = _('segment counts')

class WordCount(models.Model):
    scan = models.ForeignKey(Scan)
    word = models.CharField(max_length=100)
    count = models.IntegerField()

    class Meta:
        verbose_name = _('word count')
        verbose_name_plural = _('word counts')

def get_display_name(self):
    display_name = self.username
    if self.first_name and self.last_name:
        display_name = '%s %s' % (self.first_name, self.last_name)
    return display_name
User.get_display_name = get_display_name

OWNER = 0
MANAGER = 1
LINGUIST = 2
REVISOR = 3
TRANSLATOR = 4
GUEST = 5
ROLE_TYPE_CHOICES = (
    (OWNER, 'Site owner'),
    (MANAGER, 'Site manager'),
    (LINGUIST, 'Linguist'),
    (REVISOR,  'Revisor'),
    (TRANSLATOR,  'Translator'),
    (GUEST,  'Guest'),
)
ROLE_TYPE_DICT = dict(ROLE_TYPE_CHOICES)
ROLE_DICT = { OWNER: 'O', MANAGER: 'M', LINGUIST: 'L', REVISOR: 'R', TRANSLATOR: 'T', GUEST: 'G' }

class UserRole(models.Model):
    user = models.ForeignKey(User, verbose_name='role owner', related_name='role_user', help_text='whom this role was granted')
    role_type = models.IntegerField(choices=ROLE_TYPE_CHOICES, default=GUEST, verbose_name='role type')
    level = models.IntegerField(verbose_name='level', help_text=_('level of experience/reliability: let try to use the range 1 to 5 (top level)'))
    site = models.ForeignKey(Site, verbose_name='site/project', null=True, help_text="leave undefined for a global role")
    source_language = models.ForeignKey(Language, verbose_name='source language', related_name='source_language', null=True, help_text="leave undefined if role applies to any source language")
    target_language = models.ForeignKey(Language, verbose_name='target language', related_name='target_language', null=True, help_text="can be undefined only for some role types")
    creator = models.ForeignKey(User, verbose_name='role creator', related_name='creator_user', blank=True, null=True, help_text='who granted this role')
    created = CreationDateTimeField(verbose_name='role creation date')

    class Meta:
        verbose_name = _('user role')
        verbose_name_plural = _('user roles')

    def __str__(self):
        source_code = self.source_language and self.source_language.code or ''
        target_code = self.target_language and self.target_language.code or ''
        # return u'%s: %s of level %d for %s->%s couple and site %s' % (self.user.username, ROLE_TYPE_DICT[self.role_type], self.level, source_code, target_code, self.site.name)
        repr = [self.user.username, ROLE_TYPE_DICT[self.role_type]]
        if self.site.name:
            repr.append('site %s' % self.site.name)
        if source_code and target_code:
            repr.append('%s->%s' % (source_code, target_code))
        repr.append('level %d' % self.level)
        return ', '.join(repr)

    def __unicode__(self):
        return self.__str__()

    def get_user_name(self):
        return self.user.get_display_name()

    def get_type_name(self):
        return ROLE_TYPE_DICT[self.role_type]

    def get_label(self):
        label = '%s for %s' % (self.get_type_name(), self.site.name)
        if self.target_language:
            label += ' with %s as target' % self.target_language.name
        return label
   
class Segment(models.Model):
    site = models.ForeignKey(Site, verbose_name='source site')
    language = models.ForeignKey(Language, verbose_name='source language')
    is_fragment = models.BooleanField('fragment', default=False)
    is_invariant = models.BooleanField('invariant', default=False)
    text = models.TextField('plain text extracted', blank=True, null=True)
    html = models.TextField('original text with tags', blank=True, null=True)
    comment = models.TextField('comment', blank=True, null=True)
    is_comment_settled = models.BooleanField('comment is settled', default=False)
    created = CreationDateTimeField(verbose_name='creation date')

    class Meta:
        verbose_name = _('segment')
        verbose_name_plural = _('segments')

    def __str__(self):
        return self.text

    def __unicode__(self):
        return self.__str__()

    def more_like_this(self, target_languages=[], limit=5):
        """ to be redone with pg_trg """
        qs = Segment.objects.filter(text=self.text)
        if target_languages:
            qs = qs.filter(segment_translation__language__in=target_languages)
        if limit:
            qs = qs[:limit]
        return qs

    def get_translations(self, target_language=[]):
        """ now returns a dict, previously a list of lists """
        if not isinstance(target_language, (list, tuple)):
            return Translation.objects.filter(segment=self, language=target_language)
        source_language = self.language
        target_languages = target_language or [l for l in Language.objects.all().order_by('code') if not l==source_language]
        has_translations = False
        # language_translations = []
        language_translations = {}
        for language in target_languages:
            translations = Translation.objects.filter(segment=self, language=language)
            if translations:
                has_translations = True
                # language_translations.append([language, translations])
                language_translations[language.code] = translations
        # return has_translations and language_translations or []
        return has_translations and language_translations or {}

    def get_language_translations(self, target_language):
        return Translation.objects.filter(segment=self, language=target_language).order_by('-translation_type', 'user_role__role_type', 'user_role__level')

    def get_navigation(self, site=None, translation_state='', translation_languages=[], order_by=TEXT_ASC):
        id = self.id
        text = self.text
        created = self.created
        qs = Segment.objects.filter(language=self.language)
        if site:
            qs = qs.filter(site=site)
        if translation_state == INVARIANT:
            qs = qs.filter(is_invariant=True)
        elif translation_state == TRANSLATED:
            qs = qs.exclude(is_invariant=True)
            qs = qs.filter(segment_translation__language__in=translation_languages)
        elif translation_state == TO_BE_TRANSLATED:
            qs = qs.exclude(is_invariant=True)
            qs = qs.exclude(segment_translation__language__in=translation_languages)
        first = last = previous = next = None
        n = qs.count()
        # print (n, order_by, TEXT_ASC, order_by == TEXT_ASC, 1 == 1)
        if n:
            if order_by == TEXT_ASC:
                qs = qs.order_by('text')
                qs_before = qs.filter(text__lt=text).order_by('-text')
                qs_after = qs.filter(text__gt=text).order_by('text')
                # print (order_by, qs_before.count())
            elif order_by == ID_ASC:
                qs = qs.order_by('id')
                qs_before = qs.filter(id__lt=id).order_by('-id')
                qs_after = qs.filter(id__gt=id).order_by('id')
                # print (order_by, qs_before.count())
            elif order_by == DATETIME_ASC:
                qs = qs.order_by('created')
                qs_before = qs.filter(created__lt=created).order_by('-created')
                qs_after = qs.filter(created__gt=created).order_by('created')
                # print (order_by, qs_before.count())
            elif order_by == DATETIME_DESC:
                qs = qs.order_by('-created')
                qs_before = qs.filter(created__gt=created).order_by('created')
                qs_after = qs.filter(created__lt=created).order_by('-created')
                # print (order_by, qs_before.count())
            previous = qs_before.count() and qs_before[0] or None
            next = qs_after.count() and qs_after[0] or None
            first = qs[0]
            first = not first.id==id or None
            last = qs.reverse()[0]
            last = not last.id==id or None
        # return previous, next
        return n, first, last, previous, next

TM = 1
MT = 2
MANUAL = 3
TRANSLATION_TYPE_CHOICES = (
    (0, _('Unspecified'),),
    (TM, _('Translation Memory'),),
    (MT, _('Machine Translation'),),
    (MANUAL, _('Manual'),),
)
TRANSLATION_TYPE_DICT = dict(TRANSLATION_TYPE_CHOICES)

TRANSLATION_SOURCE_TYPE_CHOICES = (
    (TM, _('Translation Memory'),),
    (MT, _('Machine Translation'),),
)
TRANSLATION_SOURCE_TYPE_DICT = dict(TRANSLATION_SOURCE_TYPE_CHOICES)

class TranslationSource(models.Model):
    name = models.CharField(max_length=100)
    source_type = models.IntegerField(choices=TRANSLATION_SOURCE_TYPE_CHOICES, verbose_name='translation source type')

class Translation(models.Model):
    segment = models.ForeignKey(Segment, verbose_name='source segment', related_name='segment_translation')
    language = models.ForeignKey(Language, verbose_name='language')
    text = models.TextField('target text', blank=True, null=True)
    alignment = models.TextField('source to target alignment', blank=True, null=True)
    translation_type = models.IntegerField(choices=TRANSLATION_TYPE_CHOICES, default=0, verbose_name='translation type')
    translation_source = models.ForeignKey(TranslationSource, verbose_name='translation source', blank=True, null=True)
    alignment_type = models.IntegerField(choices=TRANSLATION_TYPE_CHOICES, default=0, verbose_name='alignment type')
    is_locked = models.BooleanField('locked', default=False)
    user_role = models.ForeignKey(UserRole, verbose_name='user role', blank=True, null=True)
    timestamp = models.DateTimeField()

    def get_navigation(self, order_by=TEXT_ASC, alignment_type=ANY):
        id = self.id
        text = self.segment.text
        segment = self.segment
        site = segment.site
        qs = Translation.objects.filter(language=self.language, segment__site=site)
        if alignment_type:
            qs = qs.filter(alignment_type=alignment_type)   
        first = last = previous = next = None
        n = qs.count()
        # print (n, order_by, TEXT_ASC, order_by == TEXT_ASC, 1 == 1)
        if n:
            if order_by == TEXT_ASC:
                qs = qs.order_by('segment__text', 'text')
                qs_before = qs.filter(segment__text__lt=text).order_by('-segment__text', '-text')
                qs_after = qs.filter(segment__text__gt=text).order_by('segment__text', 'text')
                # print (order_by, qs_before.count())
            elif order_by == ID_ASC:
                qs = qs.order_by('segment__id', 'id')
                qs_before = qs.filter(segment__id__lt=id).order_by('-segment__id', '-id')
                qs_after = qs.filter(segment__id__gt=id).order_by('segment__id', 'id')
                # print (order_by, qs_before.count())
            previous = qs_before.count() and qs_before[0] or None
            next = qs_after.count() and qs_after[0] or None
            first = qs[0]
            first = not first.id==id or None
            last = qs.reverse()[0]
            last = not last.id==id or None
        return n, first, last, previous, next

    def make_json(self):
        source_tokenizer = NltkTokenizer(language=self.segment.language_id, lowercasing=False)
        target_tokenizer = NltkTokenizer(language=self.language_id, lowercasing=False)
        source_tokens = tokenize(self.segment.text, tokenizer=source_tokenizer)
        target_tokens = tokenize(self.text, tokenizer=target_tokenizer)
        cells = []
        x = 10
        i = 0
        for token in source_tokens:
            y = i*50
            cells.append({
                'type': 'basic.Rect',
                'id': 'source-%d' % i,
                'position': { 'x': x, 'y': y },
                'attrs': {'text': {'text': '%d. %s' % (i, token), 'magnet': True }, 'nodetype': 'source',}
            })
            i += 1
        x = 400
        j = 0
        for token in target_tokens:
            y = j*50
            cells.append({
                'type': 'basic.Rect',
                'id': 'target-%d' % j,
                'position': { 'x': x, 'y': y },
                'attrs': {'text': {'text': '%d. %s' % (j, token) }, 'nodetype': 'target',}
            })
            j += 1
        if self.alignment:
            ijs = self.alignment.split()
            k = 0
            for ij in ijs:
                i, j = ij.split('-')
                if i and j:
                    cells.append({
                        'type': 'link',
                        'id': 'edge-%d' % k,
                        'source': {'id': 'source-%s' % i},
                        'target': {'id': 'target-%s' % j},
                    })
                k += 1
        return json.dumps({ 'cells': cells })

        
