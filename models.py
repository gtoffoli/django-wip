# -*- coding: utf-8 -*-"""

"""
Django models for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

import sys
reload(sys)  
sys.setdefaultencoding('utf8')

from collections import defaultdict
import os
import re
import datetime
# from Levenshtein.StringMatcher import StringMatcher
from lxml import html, etree
from django.db import models
from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField, AutoSlugField
from django_dag.models import node_factory, edge_factory

from vocabularies import Language, Subject, ApprovalStatus
from wip.wip_sd.sd_algorithm import SDAlgorithm

from settings import RESOURCES_ROOT, BLOCK_TAGS, BLOCKS_EXCLUDE_BY_XPATH, SEPARATORS, STRIPPED, EMPTY_WORDS
from utils import text_from_html, strings_from_html, elements_from_element, block_checksum
import srx_segmenter


MYMEMORY = 1
MATECAT = 2
GOOGLE = 3
TRANSLATION_SERVICE_CHOICES = (
    (MYMEMORY, _('MyMemory')),
    (MATECAT, _('Matecat')),
    (GOOGLE, _('GoogleTranslate')),
)
TRANSLATION_SERVICE_DICT = dict(TRANSLATION_SERVICE_CHOICES)

def text_to_list(text):
    lines = text.split('\n')
    output = []
    for line in lines:
        line = line.replace('\r','').strip()
        if line:
            output.append(line)
    return output

def code_to_language(code):
    return Language.objects.get(pk=code)

TO_BE_TRANSLATED = -1
PARTIALLY = 1
TRANSLATED = 2
REVISED = 3
INVARIANT = 4
ALREADY = 5
TRANSLATION_STATE_CHOICES = (
    (0, _('any'),),
    (TO_BE_TRANSLATED, _('to be translated'),),
    (TRANSLATED,  _('translated'),),
    (REVISED,  _('revised'),),
    (INVARIANT,  _('invariant'),),
    (ALREADY,  _('already in target language'),),
)
TRANSLATION_STATE_DICT = dict(TRANSLATION_STATE_CHOICES)

STRING_TRANSLATION_STATE_CHOICES = (
    (0, _('any'),),
    (TO_BE_TRANSLATED, _('to be translated'),),
    (TRANSLATED,  _('translated'),),
)
STRING_TRANSLATION_STATE_DICT = dict(STRING_TRANSLATION_STATE_CHOICES)

class Site(models.Model):
    name = models.CharField(max_length=100)
    slug = AutoSlugField(unique=True, populate_from='name', editable=True)
    language = models.ForeignKey(Language, null=True)
    path_prefix = models.CharField(max_length=20, default='')
    url = models.CharField(max_length=100)
    allowed_domains = models.TextField()
    start_urls = models.TextField()
    deny = models.TextField(verbose_name='Deny spyder', blank=True, null=True, help_text="Paths the spider should not follow")
    extract_deny = models.TextField(verbose_name='Deny extractor', blank=True, null=True, help_text="Paths of pages the string extractor should skip" )
    translate_deny = models.TextField(verbose_name='Deny translation', blank=True, null=True, help_text="Paths of pages not to be submitted to offline translation" )

    def __unicode__(self):
        return self.name

    def get_allowed_domains(self):
        return text_to_list(self.allowed_domains)

    def get_start_urls(self):
        return text_to_list(self.start_urls)

    def get_deny(self):
        # return ','.join(text_to_list(self.deny))
        return text_to_list(self.deny)

    def get_proxies(self):
        return Proxy.objects.filter(site=self).order_by('language__code')

    class Meta:
        verbose_name = _('original website')
        verbose_name_plural = _('original websites')

    def pages_summary(self):
        site_code = self.language_id
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
        site_code = self.language_id
        # blocks = Block.objects.filter(block_in_page__webpage__site=self).order_by('xpath', 'checksum', '-time')
        blocks = Block.objects.filter(block_in_page__webpage__site=self).order_by('checksum', '-time')
        last_ids = []
        # xpath = ''
        checksum = '' 
        for block in blocks:
            # if not (block.xpath==xpath and block.checksum==checksum):
            if not (block.checksum==checksum):
                # xpath = block.xpath
                checksum = block.checksum
                last_ids.append(block.id)
        # blocks = Block.objects.prefetch_related('source_block').filter(id__in=last_ids).order_by('xpath')
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

class Proxy(models.Model):
    name = models.CharField(max_length=100)
    slug = AutoSlugField(unique=True, populate_from='name', editable=True)
    site = models.ForeignKey(Site)
    language = models.ForeignKey(Language)
    host = models.CharField(max_length=100)
    base_path = models.CharField(max_length=100)
    enable_live_translation = models.BooleanField(default=False)
    translate_deny = models.TextField(verbose_name='Deny translation', blank=True, null=True, help_text="Paths of pages not to processed online by the proxy" )

    class Meta:
        verbose_name = _('proxy site')
        verbose_name_plural = _('proxy sites')

    def blocks_ready(self, min_state=TRANSLATED):
        """ return blocks "ready for translation" """
        site = self.site
        # qs = Block.objects.filter(site=site, Block_child__isnull=True)
        qs = Block.objects.filter(site=site)
        qs = qs.annotate(n_pages = RawSQL("SELECT COUNT(*) FROM wip_blockinpage WHERE wip_blockinpage.block_id = wip_block.id", ()))
        qs = qs.order_by('-n_pages')
        blocks = []
        for block in qs:
            if block.no_translate:
                continue
            if block.compute_translation_state(self.language) >= min_state:
                continue
            ready = True
            if ready:
                blocks.append(block)
        return blocks

    def apply_translation_memory(self):
        # string_matcher = StringMatcher()
        site = self.site
        language = self.language
        language_code = language.code
        empty_words = EMPTY_WORDS[language_code]
        target_codes = [language_code]
        blocks_ready = self.blocks_ready()
        n_ready = len(blocks_ready)
        n_partially = 0
        n_translated = 0
        if blocks_ready:
            srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
            srx_rules = srx_segmenter.parse(srx_filepath)
            italian_rules = srx_rules['Italian']
            segmenter = srx_segmenter.SrxSegmenter(italian_rules)
        for block in blocks_ready:
            last_translations = block.get_last_translations(language=language)
            translated_blocks = last_translations and dict(last_translations).get(language_code, []) or []
            translated = True
            n_substitutions = 0
            if translated_blocks:
                translated_block = translated_blocks[0]
                body = translated_block.body
                segments = translated_block.translated_block_get_segments(segmenter)
            else:
                translated_block = None
                segments = block.block_get_segments(segmenter)                
            if not segments:
                continue # ???
            for segment in segments:
                if segment.isnumeric() or segment.replace(',', '.').isnumeric():
                    continue
                if String.objects.filter(site=site, text=segment, invariant=True):
                    continue
                words = segment.split()
                translated_segment = None
                # matches = String.objects.filter(text__iexact=segment, txu__string__language_id__in=target_codes).distinct()
                matches = String.objects.filter(text=segment.upper(), txu__string__language_id=language_code).distinct()
                # if matches:
                if matches.count() == 1:
                    print 'segment: ', segment
                    match = matches[0]
                    translations = String.objects.filter(language=language, txu=match.txu)
                    if translations.count() == 1:
                        translated_segment = translations[0].text
                        print 'exact'
                elif len(words) == 1:
                    matches = String.objects.filter(text__istartswith=segment, txu__string__language_id__in=target_codes).distinct()
                    matches_count = matches.count()
                    if matches_count > 1:
                        print 'segment: ', segment, ', matches_count: ', matches_count
                        word_count_dict = defaultdict(int)
                        for match in matches:
                            if match.text.split()[0].lower() == segment.lower():
                                translations = String.objects.filter(language=language, txu=match.txu)
                                for translation in translations:
                                    for word in translation.text.split():
                                        if not word in empty_words:
                                            word_count_dict[word.lower()] += 1
                        if word_count_dict:
                            word_count_list = sorted(word_count_dict.items(), key=lambda tup: tup[1], reverse=True)
                            if len(word_count_list) > 1:
                                # print 'word_count_list: ', list(word_count_dict)
                                top_word_count = word_count_list[0]
                                top_word = top_word_count[0]
                                top_count = top_word_count[1]
                                second_count = word_count_list[1][1]
                                if top_count > second_count and top_count >= matches_count/2:
                                    translated_segment = top_word
                                    print 'fuzzy'
                if translated_segment:
                    if segment[0].isupper() and translated_segment[0].islower():
                        translated_segment = translated_segment[0].upper() + translated_segment[1:]
                    if not translated_block:
                        translated_block = block.clone(language)
                        body = translated_block.body
                    print 'translation: ', translated_segment
                    if body.count(segment):
                        body = body.replace(segment, '<span tx="auto">%s</span>' % translated_segment)
                        n_substitutions += 1
                        continue
                translated = False
            if n_substitutions:
                if translated:
                    translated_block.state = TRANSLATED
                    n_translated += 1
                else:
                    translated_block.state = PARTIALLY
                    n_partially += 1
                translated_block.body = body
                translated_block.save()
        return n_ready, n_translated, n_partially

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
                        print 'no_updated', label
                        n_no_updated +=1
                        continue
                    else:
                        n_updated +=1
                        print 'updated', label
                else:
                    translated_block = TranslatedBlock(block=block, language=language)
                    n_new +=1
                    print 'new', label
                translated_block.body = html.tostring(translated_element)
                translated_block.save()
        return n_new, n_updated, n_no_updated

class Webpage(models.Model):
    site = models.ForeignKey(Site)
    path = models.CharField(max_length=200)
    language = models.ForeignKey(Language, null=True, blank=True, help_text="Possibly overrides the site language")
    no_translate = models.BooleanField('Do not translate', default=False)
    created = CreationDateTimeField()
    # referer = models.ForeignKey('self', related_name='page_referer', blank=True, null=True)
    encoding = models.CharField(max_length=200, blank=True, null=True)
    last_modified = ModificationDateTimeField()
    last_checked = models.DateTimeField(null=True, help_text="Last time the page fetched with success")
    last_checked_response_code = models.IntegerField('Response code')
    last_unfound = models.DateTimeField(null=True, help_text="Last time the page wasn't found")
    blocks = models.ManyToManyField('Block', through='BlockInPage', related_name='page', blank=True, verbose_name='blocks')

    class Meta:
        verbose_name = _('original page')
        verbose_name_plural = _('original pages')
        ordering = ('path',)

    def __unicode__(self):
        return self.path

    def title_or_path(self):
        return self.path

    def get_region(self):
        page_versions = PageVersion.objects.filter(webpage=self).order_by('-time')
        last = page_versions and page_versions[0] or None
        return last and last.get_region()

    def get_translated_blocks_count(self):
        proxies = Proxy.objects.filter(site=self.site).order_by('language__code')   
        languages = [proxy.language for proxy in proxies]
        language_blocks_translations = []
        for language in languages:
            language_blocks_translations.append([language, TranslatedBlock.objects.filter(block__page=self, language=language).values('block_id').distinct().count()])
        return language_blocks_translations

    def get_translation(self, language_code):
        content = None
        has_translation = False
        language = get_object_or_404(Language, code=language_code)
        translated_versions = TranslatedVersion.objects.filter(webpage=self, language=language).order_by('-modified')
        translated_version = translated_versions and translated_versions[0] or None
        if translated_version:
            return translated_version.body, True        
        versions = PageVersion.objects.filter(webpage=self).order_by('-time')
        last_version = versions and versions[0] or None
        site = self.site
        if last_version:
            content = last_version.body
            content_document = html.document_fromstring(content)
            translated_document, has_translation = translated_element(content_document, site, self, language)
            if has_translation:
                content = html.tostring(translated_document)
        return content, has_translation

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
        # blocks = Block.objects.filter(block_in_page__webpage=self).order_by('xpath', '-time')
        blocks = Block.objects.filter(block_in_page__webpage=self).order_by('checksum', '-time')
        last_ids = []
        """
        xpath = ''
        for block in blocks:
            if not block.xpath == xpath:
                xpath = block.xpath
                last_ids.append(block.id)
        blocks = Block.objects.prefetch_related('source_block').filter(id__in=last_ids).order_by('xpath')
        """
        checksum = ''
        for block in blocks:
            if not block.checksum == checksum:
                checksum = block.checksum
                last_ids.append(block.id)
        # blocks = Block.objects.prefetch_related('source_block').filter(id__in=last_ids).order_by('xpath')
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

    def extract_blocks(self):
        site = self.site
        versions = PageVersion.objects.filter(webpage=self).order_by('-time')
        if not versions:
            return None
        last_version = versions[0]
        html_string = last_version.body
        # http://stackoverflow.com/questions/1084741/regexp-to-strip-html-comments
        html_string = re.sub("(<!--(.*?)-->)", "", html_string, flags=re.MULTILINE)
        doc = html.document_fromstring(html_string)
        tree = doc.getroottree()
        top_els = doc.getchildren()
        el_block_dict = {}
        n_1 = n_2 = n_3 = 0
        for top_el in top_els:
            for el in elements_from_element(top_el):
                if el.tag in BLOCK_TAGS:
                    save_failed = False
                    n_1 += 1
                    xpath = tree.getpath(el)
                    checksum = block_checksum(el)
                    # blocks = Block.objects.filter(site=site, xpath=xpath, checksum=checksum).order_by('-time')
                    blocks = Block.objects.filter(site=site, checksum=checksum).order_by('-time')
                    if blocks:
                        block = blocks[0]
                    else:
                        string = etree.tostring(el)
                        block = Block(site=site, xpath=xpath, checksum=checksum, body=string)
                        try:
                            block.save()
                            n_2 += 1
                        except:
                            print '--- save error in page ---', self.id
                            save_failed = True
                    # blocks_in_page = BlockInPage.objects.filter(block=block, webpage=self)
                    blocks_in_page = BlockInPage.objects.filter(block=block, xpath=xpath, webpage=self)
                    if not blocks_in_page and not save_failed:
                        n_3 += 1
                        # blocks_in_page = BlockInPage(block=block, webpage=self)
                        blocks_in_page = BlockInPage(block=block, xpath=xpath, webpage=self)
                        blocks_in_page.save()
        print self.path, n_1, n_2, n_3
        return n_1, n_2, n_3

    def create_blocks_dag(self):
        # BlockEdge.objects.all().delete()
        blocks_in_page = list(BlockInPage.objects.filter(webpage=self).order_by('xpath'))
        blocks = [None]
        xpaths = ['no-xpath']
        i = 0
        for bip in blocks_in_page:
            block = bip.block
            xpath = bip.xpath
            i += 1
            for j in range(i):
                if xpath.startswith(xpaths[j]):
                    parent = blocks[j]
                    if not BlockEdge.objects.filter(parent=parent, child=block):
                        parent.add_child(block)
                    break
            blocks = [block]+blocks
            xpaths = [xpath]+xpaths

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
    response_code = models.IntegerField()
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

    def page_version_get_segments(self, segmenter=None):
        if not segmenter:
            srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
            srx_rules = srx_segmenter.parse(srx_filepath)
            italian_rules = srx_rules['Italian']
            segmenter = srx_segmenter.SrxSegmenter(italian_rules)
        re_parentheses = re.compile(r'\(([^)]+)\)')

        site = self.webpage.site
        exclude_xpaths = BLOCKS_EXCLUDE_BY_XPATH.get(site.slug, [])
        language = site.language
        stripped_chars = STRIPPED[language.code]
        separators = SEPARATORS[language.code]
        strings = []
        html_string = re.sub("(<!--(.*?)-->)", "", self.body, flags=re.MULTILINE)
        for string in list(strings_from_html(html_string, fragment=False, exclude_xpaths=exclude_xpaths)):
            string = string.replace(u"\u2018", "'").replace(u"\u2019", "'").replace(' - ', ' – ')
            if string.count('window') and string.count('document'):
                continue
            if string.count('flickr'):
                continue
            string = string.strip(stripped_chars)
            if not string:
                continue
            for char in separators:
                if char in string:
                    continue
            found = get_strings(string, language, site=site)
            if found and found[0].invariant:
                continue
            matches = []
            if string.count('(') and string.count(')'):
                matches = re_parentheses.findall(string)
                if matches:
                    for match in matches:
                        string = string.replace('(%s)' % match, '')
            strings.extend(segmenter.extract(string)[0])
            for match in matches:
                strings.extend(segmenter.extract(match)[0])
        return strings

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

    def __unicode__(self):
        return self.entry_id or str(self.id)

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
    txu = models.ForeignKey(Txu, null=True, related_name='string')
    language = models.ForeignKey(Language)
    text = models.TextField()
    reliability = models.IntegerField(default=1)
    invariant = models.BooleanField(default=False)
    site = models.ForeignKey(Site, null=True)

    class Meta:
        verbose_name = _('string')
        verbose_name_plural = _('strings')
        ordering = ('-id',)

    def __unicode__(self):
        return self.text

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

    def get_navigation(self, translation_state='', translation_codes=[], order_by='text'):
        text = self.text
        id = self.id
        qs = String.objects.filter(language_id=self.language_id)
        if translation_state == TRANSLATED:
            qs = qs.filter(txu__string__language_id__in=translation_codes)
        elif translation_state == TO_BE_TRANSLATED:
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
        if order_by == 'text':
            qs_before = qs.filter(text__lt=text).order_by('-'+order_by)
            qs_after = qs.filter(text__gt=text).order_by(order_by)
        elif order_by == 'id':
            qs_before = qs.filter(id__lt=id).order_by('-id')
            qs_after = qs.filter(id__gt=id).order_by('id')
        previous = qs_before.count() and qs_before[0] or None
        next = qs_after.count() and qs_after[0] or None
        return previous, next

# class Block(models.Model):
class Block(node_factory('BlockEdge')):
    site = models.ForeignKey(Site)
    xpath = models.CharField(max_length=200, blank=True, default='')
    body = models.TextField(blank=True, null=True)
    language = models.ForeignKey(Language, null=True)
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

    def __unicode__(self):
        # return self.xpath
        return self.get_label()

    def pages_count(self):
        return self.webpages.all().count()

    def get_language(self):
        return self.language or self.site.language or Language.objects.get(code='it')

    """ substituted by integrating django_dag
    def get_children(self, webpage=None):
        if webpage:
            blocks_in_pages = BlockInPage.objects.get(block=self, webpage=webpage).order_by('-time')
            if blocks_in_pages.count():
                block_in_page = blocks_in_pages[0]
            else:
                return []
        else:
            blocks_in_pages = BlockInPage.objects.filter(block=self).order_by('-time')
            if blocks_in_pages.count():
                block_in_page = blocks_in_pages[0]
                webpage = block_in_page.webpage
            else:
                return []
        xpath = block_in_page.xpath
        step_count = xpath.count('/')
        blocks_in_pages = BlockInPage.objects.filter(webpage=webpage, xpath__startswith=xpath)
        return [bip.block for bip in blocks_in_pages if bip.xpath.count('/')==(step_count+1)]
    """

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
    def get_navigation(self, webpage=None, translation_state='', translation_codes=[], order_by='id'):
        target_code = len(translation_codes)==1 and translation_codes[0] or None
        qs = Block.objects.filter(site=self.site)
        if webpage:
            qs = qs.filter(block_in_page__webpage=webpage)
        if translation_state == INVARIANT: # block is language independent
            qs = qs.filter(no_translate=True)
        elif translation_state == ALREADY: # block is already in target language
            qs = qs.filter(language_id=target_code)
        elif translation_state == TRANSLATED:
            if translation_codes:
                qs = qs.filter(source_block__language_id__in=translation_codes)
            else:
                qs = qs.filter(source_block__isnull=False) # at least 1
        elif translation_state == TO_BE_TRANSLATED:
            if translation_codes:
                qs = qs.annotate(nt = RawSQL("SELECT COUNT(*) FROM wip_translatedblock WHERE block_id = wip_block.id and language_id IN ('%s')" % "','".join(translation_codes), ())).filter(nt=0)
            else:
                qs = qs.filter(source_block__isnull=True).exclude(no_translate=True) # none
            if target_code:
                qs = qs.exclude(language_id=target_code)
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

    def clone(self, language):
        return TranslatedBlock(block=self, language=language, body=self.body)

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
        language_translations = self.get_last_translations(language=language)
        if language_translations:
            #translations = language_translations.get(language.code, [])
            translations = dict(language_translations).get(language.code, [])
            if translations:
                return translations[0].state
        return 0

    def block_get_segments(self, segmenter):
        if not segmenter:
            srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
            srx_rules = srx_segmenter.parse(srx_filepath)
            italian_rules = srx_rules['Italian']
            segmenter = srx_segmenter.SrxSegmenter(italian_rules)
        return get_segments(self.body, self.site, segmenter)

    def apply_invariants(self, segmenter):
        segments = self.block_get_segments(segmenter)
        invariant = True
        for segment in segments:
            if segment.isnumeric() or segment.replace(',', '.').isnumeric():
                continue
            matches = String.objects.filter(site=self.site, text=segment, invariant=True)
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
            block_in_page = sorted(blocks_in_page, cmp=lambda x,y: len(x.xpath) < len(y.xpath))[0]
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
                if child_tags_dict_1[tag] > 1:
                    branch += '[%d]' % n
                child_xpath = '%s/%s' % (xpath, branch)
                print child_xpath
                blocks_in_page = BlockInPage.objects.filter(webpage=webpage, xpath=child_xpath).order_by('-block__time')
                print blocks_in_page.count(), webpage
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

class BlockEdge(edge_factory('Block', concrete = False)):
    created = CreationDateTimeField(_('created'))

    class Meta:
        verbose_name = _('block edge')
        verbose_name_plural = _('block edges')

# inspired by the algorithm of utils.elements_from_element
def translated_element(element, site, webpage, language, xpath='/html'):
    has_translation = False
    blocks_in_page = BlockInPage.objects.filter(xpath=xpath, webpage=webpage).order_by('-time')
    # print xpath
    if blocks_in_page:
        block = blocks_in_page[0].block
        # print 'page, block: ', webpage.id, block.id
        if block.no_translate:
            return element, True
        translated_blocks = TranslatedBlock.objects.filter(block=block, language=language, state__gt=0).order_by('-modified')
        # print 'translated_blocks : ', translated_blocks
        if translated_blocks:
            element = html.fromstring(translated_blocks[0].body)
            # retuen the complete translation of the block
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
            if child_tags_dict_1[tag] > 1:
                branch += '[%d]' % n
            translated_child, child_has_translation = translated_element(child, site, webpage, language, xpath='%s/%s' % (xpath, branch))
            if child_has_translation:
                element.replace(child, translated_child)
                has_translation = True
    # return the original element with translated sub-elements replaced in it
    return element, has_translation

def get_segments(body, site, segmenter, fragment=True, exclude_tx=True, exclude_xpaths=False):
    if not segmenter:
        srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
        srx_rules = srx_segmenter.parse(srx_filepath)
        italian_rules = srx_rules['Italian']
        segmenter = srx_segmenter.SrxSegmenter(italian_rules)
    re_parentheses = re.compile(r'\(([^)]+)\)')

    # exclude_xpaths = BLOCKS_EXCLUDE_BY_XPATH.get(site.slug, [])
    language = site.language
    stripped_chars = STRIPPED[language.code]
    separators = SEPARATORS[language.code]
    strings = []
    html_string = re.sub("(<!--(.*?)-->)", "", body, flags=re.MULTILINE)
    for string in list(strings_from_html(html_string, fragment=fragment, exclude_tx=exclude_tx, exclude_xpaths=exclude_xpaths)):
        string = string.replace(u"\u2018", "'").replace(u"\u2019", "'").replace(' - ', ' – ')
        if string.count('window') and string.count('document'):
            continue
        if string.count('flickr'):
            continue
        found = get_strings(string, language, site=site)
        if found and found[0].invariant:
            continue
        matches = []
        if string.count('(') and string.count(')'):
            matches = re_parentheses.findall(string)
            if matches:
                for match in matches:
                    string = string.replace('(%s)' % match, '')
        strings.extend(segmenter.extract(string)[0])
        for match in matches:
            strings.extend(segmenter.extract(match)[0])
    filtered = []
    for string in strings:
        string = string.strip(stripped_chars)
        # if not string:
        if len(string) < 2:
            continue
        for char in separators:
            if char in string:
                continue
        """
        for char in '@#':
            if char in string:
                continue
        """
        filtered.append(string)
    return filtered

    