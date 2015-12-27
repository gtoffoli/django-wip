"""
Django vocabilary mpodels for wip application.
"""

from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.contrib import admin

class VocabularyEntry(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.IntegerField(default=100)
    class Meta:
        abstract = True
        ordering = ('order',)

    def option_label(self):
        return self.name

    def __unicode__(self):
        return self.name

class VocabularyEntryAdmin(admin.ModelAdmin):
    fieldset = ['name', 'order',]
    list_display = ('name', 'order', 'id',)

class CodedEntry(models.Model):
    """
    Abstract class for classification entries with control on key
    """
    code = models.CharField(max_length=5, primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        abstract = True
        ordering = ['name']

    def option_label(self):
        return '%s - %s' % (self.code, self.name)

    def only_name (self):
        return '%s' % (self.name)

    def __unicode__(self):
        return self.name

class CodedEntryAdmin(admin.ModelAdmin):
    fieldset = ['code', 'name',]
    list_display = ('code', 'name', )


class ApprovalStatus(VocabularyEntry):

    class Meta:
        verbose_name = _('approval status')
        verbose_name_plural = _('approval statuses')

class ApprovalStatusAdmin(VocabularyEntryAdmin):
    pass


class Language(CodedEntry):
    """
    Enumerate languages referred by Websites, Proxies and ...
    """

    class Meta:
        verbose_name = _('language')
        verbose_name_plural = _('languages')

class LanguageAdmin(CodedEntryAdmin):
    pass


admin.site.register(ApprovalStatus, ApprovalStatusAdmin)
admin.site.register(Language, LanguageAdmin)

