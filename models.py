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

class Site(models.Model):
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=100)
    allowed_domains = models.TextField()
    start_urls = models.TextField()
    deny = models.TextField()

    class Meta:
        verbose_name = _('original website')
        verbose_name_plural = _('original websites')

class Proxy(models.Model):
    name = models.CharField(max_length=100)
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
    path = models.TextField()
    created = CreationDateTimeField()
    referer = models.ForeignKey('self', related_name='page_referer', blank=True, null=True)
    last_modified = ModificationDateTimeField()
    last_checked = models.DateTimeField()
    last_checked_response_code = models.IntegerField()

    class Meta:
        verbose_name = _('original page')
        verbose_name_plural = _('original pages')

class Fetched(models.Model):
    webpage = models.ForeignKey(Webpage)
    time = models.DateTimeField()
    delay = models.IntegerField()
    response_code = models.IntegerField()
    size = models.IntegerField()

    class Meta:
        verbose_name = _('fetched page')
        verbose_name_plural = _('fetched pages')

class Translated(models.Model):
    webpage = models.ForeignKey(Webpage)
    language = models.ForeignKey(Language)
    approval_status = models.ForeignKey(ApprovalStatus)
    comments = models.TextField()

    class Meta:
        verbose_name = _('translated page')
        verbose_name_plural = _('translated page')

