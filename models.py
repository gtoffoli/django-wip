"""
Django models for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

import os
import re
from lxml import html
from django.db import models
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField, AutoSlugField
from vocabularies import Language, Subject, ApprovalStatus
from wip.wip_sd.sd_algorithm import SDAlgorithm

from settings import RESOURCES_ROOT, BLOCK_TAGS
from utils import strings_from_html
import srx_segmenter

def text_to_list(text):
    lines = text.split('\n')
    output = []
    for line in lines:
        line = line.replace('\r','').strip()
        if line:
            output.append(line)
    return output

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
        return Proxy.objects.filter(site=self)

    class Meta:
        verbose_name = _('original website')
        verbose_name_plural = _('original websites')

class PageRegion(models.Model):
    site = models.ForeignKey(Site)
    label = models.CharField(max_length=100)
    xpath = models.CharField(max_length=200)

    class Meta:
        verbose_name = _('page region')
        verbose_name_plural = _('page regions')

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

class String(models.Model):
    language = models.ForeignKey(Language)
    text = models.CharField(max_length=1000)

    class Meta:
        verbose_name = _('source or target string')
        verbose_name_plural = _('source or target strings')
        ordering = ('text',)

    def __unicode__(self):
        text = self.text[:32]
        if len(self.text) > 32: text += '...'
        return text

# ContentType, currently not used, could be Site, Webpage or Block
class Txu(models.Model):
    source = models.ForeignKey(String, verbose_name='source string', related_name='as_source')
    target = models.ForeignKey(String, verbose_name='target string', related_name='as_target')
    provider = models.CharField(verbose_name='txu source', max_length=100, blank=True, null=True)
    entry_id = models.CharField(verbose_name='id by provider', max_length=100, blank=True, null=True)
    reliability = models.IntegerField(default=1)
    subjects = models.ManyToManyField('Subject', through='TxuSubject', related_name='txu', blank=True, verbose_name='subjects')
    context_type = models.ForeignKey(ContentType, verbose_name=_(u"Context type"), blank=True, null=True)
    context_id = models.PositiveIntegerField(verbose_name=_(u"Context id"), blank=True, null=True) # 
    context = GenericForeignKey(ct_field="context_type", fk_field="context_id")
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    user = models.ForeignKey(User, null=True)
    comments = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('translation unit')
        verbose_name_plural = _('translation units')
        ordering = ('source__text', 'target__text',)

    def __unicode__(self):
        source = self.source
        text = source.text
        display = u'%s-%s %s' % (source.language_id.upper(), self.target.language_id.upper(), text[:32])
        if len(text) > 32: display += '...'
        return display

class TxuSubject(models.Model):
    txu = models.ForeignKey(Txu, related_name='txu')
    subject = models.ForeignKey(Subject, related_name='subject')

    class Meta:
        verbose_name = _('txu subject')
        verbose_name_plural = _('txu subjects')

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

    def get_previous_next(self, include_language=None, exclude_language=None, order_by='id', no_translate=None):
        site = self.site
        qs = Block.objects.filter(site=site)
        if not no_translate is None:
            qs = qs.filter(no_translate=no_translate)
        if include_language:
            qs = qs.filter(language=include_language)
        if exclude_language:
            qs = qs.exclude(language=exclude_language)
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
        for language in languages:
            language_translations.append([language.code, TranslatedBlock.objects.filter(block=self, language=language).order_by('-modified')])
        return language_translations

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
    block = models.ForeignKey(Block, related_name='block')
    webpage = models.ForeignKey(Webpage, related_name='webpage')

    class Meta:
        verbose_name = _('blok in page')
        verbose_name_plural = _('bloks in page')
 
class TranslatedBlock(models.Model):
    language = models.ForeignKey(Language)
    block = models.ForeignKey(Block)
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
    print xpath
    has_translation = False
    blocks = Block.objects.filter(site=site, xpath=xpath, webpages=page).order_by('-time')
    if blocks:
        print blocks[0].id
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
