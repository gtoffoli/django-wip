"""
Django admin for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

from django.db import models
from django import forms
from django.contrib import admin
from tinymce.widgets import TinyMCE

from .models import Site, SiteTheme, Proxy, Webpage, PageVersion, TranslatedVersion # , SiteTheme
from .models import Block, BlockEdge, BlockInPage, TranslatedBlock
from .models import Scan, Link, SegmentCount, WordCount
from .models import UserRole, Segment, Translation
from .models import TRANSLATION_TYPE_DICT, MANUAL
from wip.terms.admin import *


class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'language', 'slug', 'path_prefix', 'url', 'http_server', 'allowed_domains', 'start_urls', 'deny',]

class SiteThemeAdmin(admin.ModelAdmin):
    list_display = ['id', 'site_link', 'theme_link',]

    def site_link(self, obj):
        site = obj.site
        label = site.name
        url = '/admin/wip/site/%d/' % site.id
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    site_link.short_description = 'site'
    site_link.allow_tags = True

    def theme_link(self, obj):
        theme = obj.theme
        label = theme.name
        url = '/admin/django_diazo/theme/%d/' % theme.id
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    theme_link.short_description = 'theme'
    theme_link.allow_tags = True

class ProxyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'site_name', 'language', 'url', 'host', 'base_path', 'live',]

    def site_name(self, obj):
        return obj.site.name
    site_name.short_description = 'site'

    def live(self, obj):
        return obj.enable_live_translation

class WebpageAdmin(admin.ModelAdmin):
    list_filter = ('site',)
    list_display = ['id', 'site', 'path', 'no_translate', 'blocks_count', 'versions_count', 'last_checked', 'last_checked_response_code',]
    list_display_links = ('path',)

    def get_queryset(self, request):
        self.request = request
        qs = super(WebpageAdmin, self).get_queryset(request)
        qs = qs.annotate(blockscount=models.Count('blocks'))
        return qs

    def versions_count(self, obj):
        url = '/admin/wip/pageversion/?webpage__id__exact=%d' % obj.id
        label = '%d' % (obj.blocks.all().count())
        label = '%d' % PageVersion.objects.filter(webpage=obj).count()
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    versions_count.short_description = 'Versions'
    versions_count.allow_tags = True

    def blocks_count(self, obj):
        label = obj.get_blocks_in_use().count()
        # return label
        url = '/admin/wip/blockinpage/?webpage__id__exact=%d' % obj.id
        link = '<a href="%s">%s</a>' % (url, label)
        return link
        """
        """
    blocks_count.admin_order_field = 'blockscount'
    blocks_count.short_description = 'Blocks'
    blocks_count.allow_tags = True

class PageVersionAdmin(admin.ModelAdmin):
    list_filter = ['webpage__site__name',]
    list_display = ['id', 'site', 'scan_link', 'webpage_link', 'time', 'response_code', 'size', 'checksum',]
    list_display_links = ('id',)
    search_fields = ['webpage__id', 'webpage__path', 'body',]

    def site(self, obj):
        return obj.webpage.site.name

    def webpage_link(self, obj):
        webpage = obj.webpage
        label = '%d %s' % (webpage.id, webpage.path)
        url = '/admin/wip/webpage/%d/' % webpage.id
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    webpage_link.short_description = 'webpage'
    webpage_link.allow_tags = True

    def scan_link(self, obj):
        scan = obj.scan
        link = ''
        if scan:
            label = '%s' % scan.id
            url = '/admin/wip/scan/%d/' % scan.id
            link = '<a href="%s">%s</a>' % (url, label)
        return link
    scan_link.short_description = 'scan'
    scan_link.allow_tags = True

class TranslatedVersionAdmin(admin.ModelAdmin):
    pass

class BlockForm(forms.ModelForm):
    class Meta:
        model = Block
        exclude = ('xpath', 'created',)
        """
        widgets = {
            'body' : TinyMCE(attrs={'style': 'width:500px;'}),
            'xpath' : forms.TextInput(attrs={'style': 'width:500px;'}),
        }
        """

class BlockAdmin(admin.ModelAdmin):
    list_filter = ('site',)
    list_display = ['id', 'site', 'block_link', 'translations_list', 'state', 'pages_count', 'time',] # , 'checksum'
    list_display_links = ('block_link',)
    # search_fields = ['site', 'path',]
    search_fields = ['body',]
    form = BlockForm

    def block_link(self, obj):
        url = '/admin/wip/block/%d/' % obj.id
        # label = '%s' % (obj.xpath)
        label = '%s' % obj.get_label()
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
    translations_list.allow_tags = True

class BlockEdgeAdmin(admin.ModelAdmin):
    list_display = ['id', 'parent_link', 'child_link']
    
    def parent_link(self, obj):
        parent = obj.parent
        url = '/admin/wip/block/%d/' % parent.id
        label = parent
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    parent_link.short_description = 'Parent'
    parent_link.allow_tags = True
    def child_link(self, obj):
        child = obj.child
        url = '/admin/wip/block/%d/' % child.id
        label = child
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    child_link.short_description = 'Child'
    child_link.allow_tags = True

class BlockInPageAdmin(admin.ModelAdmin):
    list_filter = ['block__site',]
    list_display = ['id', 'page_link', 'block_link', 'xpath', 'time']
    list_per_page = 500
    search_fields = ['xpath',]

    def block_link(self, obj):
        block = obj.block
        url = '/admin/wip/block/%d/' % block.id
        label = '%s' % block.get_label()
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
    search_fields = ['body',]
    list_filter = ['block__site__name', 'language',]
    list_display = ['id', 'site_name', 'block_link', 'block_label', 'language', 'state', 'modified', 'editor',]

    def site_name(self, obj):
        return obj.block.site.name
    site_name.short_description = 'site'

    def block_label(self, obj):
        url = '/admin/wip/translatedblock/%d/' % obj.id
        # label = '%s' % (obj.xpath)
        label = '%s' % obj.get_label()
        link = '<a href="%s" style="font-size:smaller;">%s</a>' % (url, label)
        return link
    block_label.short_description = 'Body'
    block_label.allow_tags = True

    def block_link(self, obj):
        block = obj.block
        url = '/admin/wip/block/%d/' % block.id
        label = block.id
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    block_link.short_description = 'Block'
    block_link.allow_tags = True

class ScanAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'scan_type', 'scan_mode', 'task_id', 'user', 'created', 'terminated',]

class LinkAdmin(admin.ModelAdmin):
    list_display = ['id', 'scan_link', 'url', 'status', 'size', 'title',]
    list_filter = ['scan__name',]
    search_fields = ['scan__name',]

    def scan_link(self, obj):
        scan = obj.scan
        url = '/admin/wip/scan/%d/' % scan.pk
        label = '%d - %s' % (scan.pk, scan.get_label())
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    scan_link.short_description = 'Scan'
    scan_link.allow_tags = True

class SegmentCountAdmin(admin.ModelAdmin):
    list_display = ['id', 'scan_link', 'segment', 'count',]

    def scan_link(self, obj):
        scan = obj.scan
        url = '/admin/wip/scan/%d/' % scan.pk
        label = '%d - %s' % (scan.pk, scan.get_label())
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    scan_link.short_description = 'Scan'
    scan_link.allow_tags = True

class WordCountAdmin(admin.ModelAdmin):
    list_display = ['id', 'scan_link', 'word', 'count',]

    def scan_link(self, obj):
        scan = obj.scan
        url = '/admin/wip/scan/%d/' % scan.pk
        label = '%d - %s' % (scan.pk, scan.get_label())
        link = '<a href="%s">%s</a>' % (url, label)
        return link
    scan_link.short_description = 'Scan'
    scan_link.allow_tags = True

class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'role_type', 'level', 'site', 'source_language', 'target_language', 'creator',]
    list_filter = ('site', 'role_type', 'source_language', 'target_language')

class SegmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'site', 'language', 'text', 'in_use', 'is_fragment',]
    list_filter = ['site', 'language', 'in_use',]
    search_fields = ['text',]

class TranslationAdmin(admin.ModelAdmin):
    list_display = ['id', 'segment_link', 'site_name', 'language', 'text', 'translationtype', 'has_alignment', 'alignmenttype', 'time', 'user_role']
    list_filter = ['language', 'alignment_type',  'user_role',]
    search_fields = ['text', 'alignment',]

    def segment_link(self, obj):
        segment = obj.segment
        url = '/admin/wip/segment/%d/' % segment.pk
        link = '<a href="%s">%d</a>' % (url, segment.pk)
        return link
    segment_link.short_description = 'segment'
    segment_link.allow_tags = True

    def site_name(self, obj):
        return obj.segment.site.name
    site_name.short_description = 'site'

    def languages(self, obj):
        return '%s -> %s' % (obj.segment.language_id, obj.language_id)

    def translationtype(self, obj):
        return TRANSLATION_TYPE_DICT[obj.translation_type]
    translationtype.short_description = 'Tr.type'
    
    def has_alignment(self, obj):
        return obj.alignment and 'X' or ''
    has_alignment.short_description = 'Al.'

    def alignmenttype(self, obj):
        if obj.alignment:
            return obj.alignment_type == MANUAL and 'Manual' or 'Auto'
        else:
            return ''
    alignmenttype.short_description = 'Al.type'

    def time(self, obj):
        return obj.timestamp.strftime("%y%m%d-%H%M")
    time.short_description = 'Time'

admin.site.register(Site, SiteAdmin)
admin.site.register(SiteTheme, SiteThemeAdmin)
admin.site.register(Proxy, ProxyAdmin)
admin.site.register(Webpage, WebpageAdmin)
admin.site.register(PageVersion, PageVersionAdmin)
admin.site.register(TranslatedVersion, TranslatedVersionAdmin)
admin.site.register(Block, BlockAdmin)
admin.site.register(BlockEdge, BlockEdgeAdmin)
admin.site.register(BlockInPage, BlockInPageAdmin)
admin.site.register(TranslatedBlock, TranslatedBlockAdmin)

admin.site.register(Scan, ScanAdmin)
admin.site.register(Link, LinkAdmin)
admin.site.register(SegmentCount, SegmentCountAdmin)
admin.site.register(WordCount, WordCountAdmin)

admin.site.register(UserRole, UserRoleAdmin)
admin.site.register(Segment, SegmentAdmin)
admin.site.register(Translation, TranslationAdmin)
