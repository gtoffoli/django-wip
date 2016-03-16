"""
Django models for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

import sys
reload(sys)  
sys.setdefaultencoding('utf8')

import os
import re
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
from vocabularies import Language, Subject, ApprovalStatus
from wip.wip_sd.sd_algorithm import SDAlgorithm

from settings import RESOURCES_ROOT, BLOCK_TAGS
from utils import strings_from_html, elements_from_element, block_checksum
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

TO_BE_TRANSLATED = 1
TRANSLATED = 2
INVARIANT = 3
ALREADY = 4
TRANSLATION_STATE_CHOICES = (
    (0, _('any'),),
    (TO_BE_TRANSLATED, _('to be translated'),),
    (TRANSLATED,  _('translated'),),
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
    deny = models.TextField(blank=True, null=True)

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
        blocks = Block.objects.filter(block_in_page__webpage__site=self).order_by('xpath', 'checksum', '-time')
        last_ids = []
        xpath = ''
        checksum = '' 
        for block in blocks:
            if not (block.xpath==xpath and block.checksum==checksum):
                xpath = block.xpath
                checksum = block.checksum
                last_ids.append(block.id)
        blocks = Block.objects.prefetch_related('source_block').filter(id__in=last_ids).order_by('xpath')
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

    class Meta:
        verbose_name = _('proxy site')
        verbose_name_plural = _('proxy sites')

class Webpage(models.Model):
    site = models.ForeignKey(Site)
    path = models.CharField(max_length=200)
    no_translate = models.BooleanField(default=False)
    created = CreationDateTimeField()
    # referer = models.ForeignKey('self', related_name='page_referer', blank=True, null=True)
    encoding = models.CharField(max_length=200, blank=True, null=True)
    last_modified = ModificationDateTimeField()
    last_checked = models.DateTimeField()
    last_checked_response_code = models.IntegerField('Response code')
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
        blocks = Block.objects.filter(block_in_page__webpage=self).order_by('xpath', '-time')
        last_ids = []
        xpath = ''
        for block in blocks:
            if not block.xpath == xpath:
                xpath = block.xpath
                last_ids.append(block.id)
        blocks = Block.objects.prefetch_related('source_block').filter(id__in=last_ids).order_by('xpath')
        # blocks = Block.objects.filter(id__in=last_ids).order_by('xpath')
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
        # page = Webpage.objects.get(pk=page_id)
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
        n_1 = n_2 = n_3 = 0
        for top_el in top_els:
            for el in elements_from_element(top_el):
                if el.tag in BLOCK_TAGS:
                    save_failed = False
                    n_1 += 1
                    xpath = tree.getpath(el)
                    checksum = block_checksum(el)
                    blocks = Block.objects.filter(site=site, xpath=xpath, checksum=checksum).order_by('-time')
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
                    blocks_in_page = BlockInPage.objects.filter(block=block, webpage=self)
                    if not blocks_in_page and not save_failed:
                        n_3 += 1
                        blocks_in_page = BlockInPage(block=block, webpage=self)
                        blocks_in_page.save()
        return n_1, n_2, n_3

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

class TranslatedVersion(models.Model):
    webpage = models.ForeignKey(Webpage)
    language = models.ForeignKey(Language)
    body = models.TextField(blank=True, null=True)
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    approval_status = models.ForeignKey(ApprovalStatus)
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
        return self.entry_id or self.id

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

    class Meta:
        verbose_name = _('string')
        verbose_name_plural = _('strings')
        ordering = ('text',)

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

class Block(models.Model):
    site = models.ForeignKey(Site)
    xpath = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True, null=True)
    language = models.ForeignKey(Language, null=True)
    no_translate = models.BooleanField(default=False)
    checksum = models.CharField(max_length=32)
    time = CreationDateTimeField()
    webpages = models.ManyToManyField(Webpage, through='BlockInPage', related_name='block', blank=True, verbose_name='pages')

    class Meta:
        verbose_name = _('page block')
        verbose_name_plural = _('page blocks')
        ordering = ('-time',)

    def __unicode__(self):
        return self.xpath

    def pages_count(self):
        return self.webpages.all().count()

    def get_language(self):
        return self.language or self.site.language or Language.objects.get(code='it')

    def get_previous_next(self, include_language=None, exclude_language=None, order_by='id', skip_no_translate=None):
        site = self.site
        qs = Block.objects.filter(site=site)
        if skip_no_translate:
            qs = qs.exclude(no_translate=True)
        if order_by == 'id':
            id = self.id
            qs_before = qs.filter(id__lt=id)
            qs_after = qs.filter(id__gt=id)
        elif order_by == 'xpath':
            xpath = self.xpath
            qs_before = qs.filter(xpath__lt=xpath)
            qs_after = qs.filter(xpath__gt=xpath)
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
        elif order_by == 'xpath':
            xpath = self.xpath
            qs_before = qs.filter(xpath__lt=xpath)
            qs_after = qs.filter(xpath__gt=xpath)
        qs_before = qs_before.order_by('-'+order_by)
        qs_after = qs_after.order_by(order_by)
        previous = qs_before.count() and qs_before[0] or None
        next = qs_after.count() and qs_after[0] or None
        return previous, next

    def get_last_translations(self):
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
                    if translation.state == 2:
                        state = 'V'
                    elif translation.state == 1:
                        state = 'T'
                    else:
                        state = 'P'
            states.append(state)
        return states

    def get_strings(self):
        srx_filepath = os.path.join(RESOURCES_ROOT, 'segment.srx')
        srx_rules = srx_segmenter.parse(srx_filepath)
        italian_rules = srx_rules['Italian']
        segmenter = srx_segmenter.SrxSegmenter(italian_rules)
        re_parentheses = re.compile(r'\(([^)]+)\)')

        strings = []
        for string in list(strings_from_html(self.body, fragment=True)):
            string = string.replace(u"\u2018", "'").replace(u"\u2019", "'")
            if string.count('window') and string.count('document'):
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

class BlockInPage(models.Model):
    block = models.ForeignKey(Block, related_name='block_in_page')
    webpage = models.ForeignKey(Webpage, related_name='webpage')

    class Meta:
        verbose_name = _('blok in page')
        verbose_name_plural = _('bloks in page')
 
class TranslatedBlock(models.Model):
    language = models.ForeignKey(Language)
    block = models.ForeignKey(Block, related_name='source_block')
    body = models.TextField(blank=True, null=True)
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    editor = models.ForeignKey(User, null=True, related_name='editor')
    state = models.IntegerField(default=0)
    revisor = models.ForeignKey(User, null=True, related_name='revisor')
    comments = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('translated block')
        verbose_name_plural = _('translated blocks')

# inspired by the algorithm of utils.elements_from_element
def translated_element(element, site, page, language, xpath='/html'):
    has_translation = False
    blocks = Block.objects.filter(site=site, xpath=xpath, webpages=page).order_by('-time')
    if blocks:
        translated_blocks = TranslatedBlock.objects.filter(block=blocks[0], language=language).order_by('-modified')
        if translated_blocks:
            element = html.fromstring(translated_blocks[0].body)
            has_translation = True
        else:
            element = html.fromstring(blocks[0].body)
    child_tags_dict_1 = {}
    child_tags_dict_2 = {}
    text = element.text
    text = text and text.strip() and True
    for child in element.getchildren():
        tag = child.tag
        if tag in BLOCK_TAGS:
            child_tags_dict_1[tag] = child_tags_dict_1.setdefault(tag, 0)+1
    for child in element.getchildren():
        tag = child.tag
        if tag in BLOCK_TAGS:
            child_tags_dict_2[tag] = n = child_tags_dict_2.setdefault(tag, 0)+1
            branch = tag
            if child_tags_dict_1[tag] > 1:
                branch += '[%d]' % n
            translated_child, child_has_translation = translated_element(child, site, page, language, xpath='%s/%s' % (xpath, branch))
            if child_has_translation:
                element.replace(child, translated_child)
                has_translation = True
    return element, has_translation
