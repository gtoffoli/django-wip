"""
Django models for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

import os
import re
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField, AutoSlugField
from vocabularies import Language, ApprovalStatus
from wip.wip_sd.sd_algorithm import SDAlgorithm

from settings import DATA_ROOT, RESOURCES_ROOT, tagger_filename, BLOCK_TAGS
from utils import strings_from_html, blocks_from_block, block_checksum
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
    blocks = models.ManyToManyField('Block', through='BlockInPage', related_name='page_blocks', blank=True, verbose_name='blocks')

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

class PageVersion(models.Model):
    webpage = models.ForeignKey(Webpage)
    time = CreationDateTimeField()
    delay = models.IntegerField(default=0)
    response_code = models.IntegerField()
    size = models.IntegerField()
    checksum = models.CharField(max_length=32, blank=True, null=True)
    body = models.TextField(null=True)

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
    body = models.TextField(null=True)
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    approval_status = models.ForeignKey(ApprovalStatus)
    user = models.ForeignKey(User, null=True)
    comments = models.TextField()

    class Meta:
        verbose_name = _('translated version')
        verbose_name_plural = _('translated version')

class String(models.Model):
    language = models.ForeignKey(Language)
    text = models.CharField(max_length=1000)
    created = CreationDateTimeField()
    user = models.ForeignKey(User, null=True)

    class Meta:
        verbose_name = _('source string')
        verbose_name_plural = _('source strings')
        ordering = ('text',)

class StringInPage(models.Model):
    site = models.ForeignKey(Site, null=True)
    string = models.ForeignKey(String)
    webpage = models.ForeignKey(Webpage, null=True)
    xpath = models.CharField(max_length=200, null=True, blank=True)
    pos = models.CharField(max_length=10, null=True, blank=True)
    created = CreationDateTimeField()

    class Meta:
        verbose_name = _('string in page')
        verbose_name_plural = _('strings in page')
        ordering = ('-created',)

class StringTranslation(models.Model):
    string = models.ForeignKey(String, null=True)
    string_in_page = models.ForeignKey(StringInPage, null=True)
    language = models.ForeignKey(Language)
    text = models.CharField(max_length=1000)
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    user = models.ForeignKey(User, null=True)

    class Meta:
        verbose_name = _('string translation')
        verbose_name_plural = _('string translations')
        ordering = ('text',)

class Block(models.Model):
    site = models.ForeignKey(Site)
    xpath = models.CharField(max_length=200, blank=True)
    body = models.TextField(null=True)
    language = models.ForeignKey(Language, null=True)
    no_translate = models.BooleanField(default=False)
    checksum = models.CharField(max_length=32)
    time = CreationDateTimeField()
    webpages = models.ManyToManyField(Webpage, through='BlockInPage', related_name='block_pages', blank=True, verbose_name='pages')

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

    def get_previous_next(self, exclude_language=None, order_by='id', no_translate=None):
        site = self.site
        qs = Block.objects.filter(site=site)
        if not no_translate is None:
            qs = qs.filter(no_translate=no_translate)
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
    body = models.TextField(null=True)
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    editor = models.ForeignKey(User, null=True, related_name='editor')
    state = models.IntegerField(default=0)
    revisor = models.ForeignKey(User, null=True, related_name='revisor')
    comments = models.TextField()

    class Meta:
        verbose_name = _('translated block')
        verbose_name_plural = _('translated blocks')

class StringInBlock(models.Model):
    site = models.ForeignKey(Site, null=True)
    string = models.ForeignKey(String)
    block = models.ForeignKey(Block, null=True)
    created = CreationDateTimeField()

    class Meta:
        verbose_name = _('string in block')
        verbose_name_plural = _('strings in block')
        ordering = ('-created',)
