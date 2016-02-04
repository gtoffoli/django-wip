"""
Django models for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField, AutoSlugField
from vocabularies import Language, ApprovalStatus
from wip.wip_sd.sd_algorithm import SDAlgorithm

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
