"""
Django admin for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

from django.db import models
from django import forms
from django.contrib import admin
from tinymce.widgets import TinyMCE

from models import Site, Proxy, Webpage, PageVersion, String, Txu, TxuSubject, TranslatedVersion, Block, BlockInPage, TranslatedBlock

class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'language', 'slug', 'path_prefix', 'url', 'allowed_domains', 'start_urls', 'deny',]

class ProxyAdmin(admin.ModelAdmin):
    list_display = ['name', 'language', 'slug', 'site_name', 'host', 'base_path',]

    def site_name(self, obj):
        return obj.site.name

class WebpageAdmin(admin.ModelAdmin):
    list_filter = ('site', 'blocks')
    list_display = ['id', 'site', 'path', 'encoding', 'blocks_count', 'last_checked', 'last_checked_response_code',]
    list_display_links = ('path',)

    def get_queryset(self, request):
        self.request = request
        qs = super(WebpageAdmin, self).get_queryset(request)
        qs = qs.annotate(blockscount=models.Count('blocks'))
        # qs = qs.order_by('-blockscount')
        return qs

    def blocks_count(self, obj):
        site_id = int(self.request.GET.get('site__id__exact',0))
        url = '/admin/wip/block/?webpages__id__exact=%d' % obj.id
        if site_id:
            url += '&site__id__exact=%d' % site_id
        label = '%d' % (obj.blocks.all().count())
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    blocks_count.admin_order_field = 'blockscount'
    blocks_count.short_description = 'Blocks'
    blocks_count.allow_tags = True

class PageVersionAdmin(admin.ModelAdmin):
    list_filter = ['webpage__site__name',]
    list_display = ['id', 'site', 'webpage', 'time', 'response_code', 'size', 'checksum',]
    list_display_links = ('id', 'webpage',)

    def site(self, obj):
        return obj.webpage.site.name

class StringAdmin(admin.ModelAdmin):
    list_filter = ['language']
    list_display = ['id', 'language', 'text', 'site', 'invariant', 'reliability', 'txu',]

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

class TranslatedVersionAdmin(admin.ModelAdmin):
    pass

class BlockForm(forms.ModelForm):
    class Meta:
        model = Block
        exclude = ('created',)
        widgets = {
            'body' : TinyMCE(attrs={'style': 'width:500px;'}),
            'xpath' : forms.TextInput(attrs={'style': 'width:500px;'}),
        }

class BlockAdmin(admin.ModelAdmin):
    list_filter = ('site', 'webpages',)
    list_display = ['id', 'site', 'block_link', 'translations_list', 'pages_count', 'time',] # , 'checksum'
    list_display_links = ('block_link',)
    search_fields = ['site', 'path',]
    form = BlockForm

    def block_link(self, obj):
        url = '/admin/wip/block/%d/' % obj.id
        label = '%s' % (obj.xpath)
        link = '<a href="%s" style="font-size:smaller;">%s</a>' % (url, label)
        return link
    block_link.short_description = 'Block'
    block_link.allow_tags = True

    def get_queryset(self, request):
        self.request = request
        qs = super(BlockAdmin, self).get_queryset(request)
        qs = qs.annotate(pagescount=models.Count('webpages'))
        # qs = qs.order_by('-pagescount')
        return qs

    def pages_count(self, obj):
        site_id = int(self.request.GET.get('site__id__exact',0))
        url = '/admin/wip/webpage/?blocks__id__exact=%d' % obj.id
        if site_id:
            url += '&site__id__exact=%d' % site_id
        label = '%d' % (obj.webpages.all().count())
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    pages_count.admin_order_field = 'pagescount'
    pages_count.short_description = 'Pages'
    pages_count.allow_tags = True

    def translations_list(self, obj):
        tranlations = TranslatedBlock.objects.filter(block=obj)
        links = []
        for translation in tranlations:
            code = translation.language.code
            label = code.upper()
            url = '/admin/wip/translatedblock/%s/' % code
            link = '<a href="%s">%s</a>' % (url, label)
            links.append(link)
        return ' '.join(links)
    translations_list.short_description = 'Trans.'

class BlockInPageAdmin(admin.ModelAdmin):
    list_filter = ['block__site',]
    list_display = ['id', 'page_link', 'block_link',]

    def block_link(self, obj):
        block = obj.block
        url = '/admin/wip/block/%d/' % block.id
        label = '%s' % (block.xpath)
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    block_link.short_description = 'Block'
    block_link.allow_tags = True

    def page_link(self, obj):
        page = obj.webpage
        url = '/admin/wip/webpage/%d/' % page.id
        label = '%s %s' % (page.site.name, page.path)
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    page_link.short_description = 'Page'
    page_link.allow_tags = True

class TranslatedBlockForm(forms.ModelForm):
    class Meta:
        model = Block
        exclude = ('language', 'block', 'created', 'modified',)
        widgets = {
            'body' : TinyMCE(),
        }

class TranslatedBlockAdmin(admin.ModelAdmin):
    list_filter = ['block__site__name', 'language',]
    list_display = ['id', 'site_name', 'block_link', 'language', 'xpath', 'state', 'modified', 'editor',]

    def site_name(self, obj):
        return obj.block.site.name

    def xpath(self, obj):
        return obj.block.xpath

    def block_link(self, obj):
        block = obj.block
        url = '/admin/wip/block/%d/' % block.id
        label = block.id
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    block_link.short_description = 'Block'
    block_link.allow_tags = True

admin.site.register(Site, SiteAdmin)
admin.site.register(Proxy, ProxyAdmin)
admin.site.register(Webpage, WebpageAdmin)
admin.site.register(PageVersion, PageVersionAdmin)
admin.site.register(String, StringAdmin)
admin.site.register(Txu, TxuAdmin)
admin.site.register(TxuSubject, TxuSubjectAdmin)
admin.site.register(TranslatedVersion, TranslatedVersionAdmin)
admin.site.register(Block, BlockAdmin)
admin.site.register(BlockInPage, BlockInPageAdmin)
admin.site.register(TranslatedBlock, TranslatedBlockAdmin)

