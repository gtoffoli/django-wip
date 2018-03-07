from django.db import models
from django.contrib import admin

from .models import String, Txu, TxuSubject


class StringAdmin(admin.ModelAdmin):
    fields = ['string_type', 'language', 'text', 'site', 'path', 'invariant', 'reliability', 'user']
    list_filter = ['string_type', 'language']
    list_display = ['id', 'string_type', 'language', 'text', 'site', 'path', 'invariant', 'reliability', 'txu_link', 'user', 'created', 'modified']
    search_fields = ['text',]

    def txu_link(self, obj):
        txu = obj.txu
        if txu:
            url = '/admin/wip/txu/%d/' % txu.id
            label = obj.txu.entry_id or obj.txu.id
            link = '<a href="%s">%s</a>' % (url, label)
        else:
            link = ''
        return link
    txu_link.short_description = 'Txu'
    txu_link.allow_tags = True

class TxuAdmin(admin.ModelAdmin):
    list_filter = ['user',]
    list_display = ['id', 'provider', 'entry_id', 'en', 'es', 'fr', 'it', 'user', 'created', 'modified',]

class TxuSubjectAdmin(admin.ModelAdmin):
    # list_filter = ['subject',]
    list_display = ['id', 'subject_link', 'txu_link',]

    def subject_link(self, obj):
        subject = obj.subject
        url = '/admin/wip/subject/%s/' % subject.code
        label = '%s' % (subject.code)
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    subject_link.short_description = 'Subject'
    subject_link.allow_tags = True

    def txu_link(self, obj):
        txu = obj.txu
        url = '/admin/wip/txu/%d/' % txu.id
        # label = '%s -> %s' % (txu.source.text, txu.target.text)
        label = obj.txu.entry_id or obj.txu.id
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    txu_link.short_description = 'Txu'
    txu_link.allow_tags = True

admin.site.register(String, StringAdmin)
admin.site.register(Txu, TxuAdmin)
admin.site.register(TxuSubject, TxuSubjectAdmin)
