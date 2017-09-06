"""
Django vocabulary mpodels for wip application.
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

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.__str__()

class VocabularyEntryAdmin(admin.ModelAdmin):
    fieldset = ['name', 'order',]
    list_display = ('name', 'order', 'id',)

class CodedEntry(models.Model):
    """
    Abstract class for classification entries with control on key
    """
    code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def option_label(self):
        try:
            return '%s - %s' % (self.code, self.name)
        except:
            return self.code

    def label_from_instance(self):
        try:
            return '%s - %s' % (self.code, self.name)
        except:
            return self.code

    def only_name (self):
        return '%s' % (self.name)

    def __str__(self):
        try:
            return self.name
        except:
            return self.code

    def __unicode__(self):
        return self.__str__()

class CodedEntryAdmin(admin.ModelAdmin):
    fieldset = ['code', 'name',]
    list_display = ('code', 'name', )

    def safe_name(self, obj):
        try:
            return obj.name
        except:
            return obj.code

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
        
    def get_other_languages(self):
        # return [l for l in Language.objects.all().order_by('code') if not l==self]
        return Language.objects.exclude(code=self.code).order_by('code')

class LanguageAdmin(CodedEntryAdmin):
    pass

class Subject(CodedEntry):
    """
    Enumerate IATE subjects
    """
    class Meta:
        verbose_name = _('subject')
        verbose_name_plural = _('subjects')
        ordering = ['code']

    def label_from_instance(self):
        return self.__str__()

class SubjectAdmin(CodedEntryAdmin):
    pass

admin.site.register(ApprovalStatus, ApprovalStatusAdmin)
admin.site.register(Language, LanguageAdmin)
admin.site.register(Subject, SubjectAdmin)

