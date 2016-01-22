"""
Django models for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

from django.db import models
# from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField, AutoSlugField
from vocabularies import Language, ApprovalStatus

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
    # path = models.TextField()
    path = models.CharField(max_length=200)
    created = CreationDateTimeField()
    referer = models.ForeignKey('self', related_name='page_referer', blank=True, null=True)
    encoding = models.CharField(max_length=200, blank=True, null=True)
    last_modified = ModificationDateTimeField()
    last_checked = models.DateTimeField()
    last_checked_response_code = models.IntegerField('Response code')

    class Meta:
        verbose_name = _('original page')
        verbose_name_plural = _('original pages')
        ordering = ('path',)

    def __unicode__(self):
        return self.path

class Fetched(models.Model):
    webpage = models.ForeignKey(Webpage)
    time = CreationDateTimeField()
    delay = models.IntegerField(default=0)
    response_code = models.IntegerField()
    size = models.IntegerField()
    checksum = models.CharField(max_length=32, blank=True, null=True)
    body = models.TextField(null=True)

    class Meta:
        verbose_name = _('fetched page')
        verbose_name_plural = _('fetched pages')
        ordering = ('webpage__site', 'webpage__path', '-time')

class Translated(models.Model):
    webpage = models.ForeignKey(Webpage)
    language = models.ForeignKey(Language)
    approval_status = models.ForeignKey(ApprovalStatus)
    comments = models.TextField()

    class Meta:
        verbose_name = _('translated page')
        verbose_name_plural = _('translated page')

