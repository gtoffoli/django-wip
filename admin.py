"""
Django admin for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

from django import forms
from django.contrib import admin
from tinymce.widgets import TinyMCE

from models import Site, Proxy, PageRegion, Webpage, PageVersion, String, StringTranslation, TranslatedVersion, Block, BlockInPage, StringInBlock, TranslatedBlock

class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'path_prefix', 'url', 'allowed_domains', 'start_urls', 'deny',]

class ProxyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'site_name', 'language', 'host', 'base_path',]

    def site_name(self, obj):
        return obj.site.name

class WebpageAdmin(admin.ModelAdmin):
    list_filter = ('site__name',)
    list_display = ['id', 'path', 'site', 'encoding', 'blocks', 'last_checked', 'last_checked_response_code',]
    list_display_links = ('id', 'site',)
    search_fields = ['site_name', 'path',]

    def site_name(self, obj):
        return obj.site.name

    def blocks(self, obj):
        return BlockInPage.objects.filter(webpage=obj).count()

class PageRegionAdmin(admin.ModelAdmin):
    list_filter = ('site__name',)
    list_display = ['id', 'site', 'label', 'xpath',]
    list_display_links = ('id', 'site',)
    search_fields = ['site_name', 'xpath',]

    def site_name(self, obj):
        return obj.site.name

class PageVersionAdmin(admin.ModelAdmin):
    list_filter = ['webpage__site__name',]
    list_display = ['id', 'site', 'webpage', 'time', 'response_code', 'size', 'checksum',]
    list_display_links = ('id', 'webpage',)

    def site(self, obj):
        return obj.webpage.site.name

class StringAdmin(admin.ModelAdmin):
    list_filter = ['language']
    list_display = ['id', 'language', 'created', 'text',]

class StringTranslationAdmin(admin.ModelAdmin):
    list_filter = ['language', 'user',]
    list_display = ['id', 'language', 'user', 'created', 'modified', 'text',]

class TranslatedVersionAdmin(admin.ModelAdmin):
    pass

class BlockForm(forms.ModelForm):
    class Meta:
        model = Block
        exclude = ('created',)
        widgets = {
            'body' : TinyMCE(),
        }

class BlockAdmin(admin.ModelAdmin):
    list_filter = ('site',)
    list_display = ['id', 'site', 'xpath', 'pages', 'checksum', 'time',]
    list_display_links = ('id', 'site',)
    search_fields = ['site', 'path',]
    form = BlockForm

    def pages(self, obj):
        return BlockInPage.objects.filter(block=obj).count()

class StringInBlockAdmin(admin.ModelAdmin):
    list_filter = ['site',]
    list_display = ['id', 'site', 'xpath', 'created',]

    def xpath(self, obj):
        return obj.block.xpath

class TranslatedBlockForm(forms.ModelForm):
    class Meta:
        model = Block
        exclude = ('language', 'block', 'created', 'modified',)
        widgets = {
            'body' : TinyMCE(),
        }

class TranslatedBlockAdmin(admin.ModelAdmin):
    list_filter = ['block__site__name', 'language',]
    list_display = ['id', 'site_name', 'language', 'xpath', 'state', 'modified', 'editor',]

    def site_name(self, obj):
        return obj.block.site.name

    def xpath(self, obj):
        return obj.block.xpath

admin.site.register(Site, SiteAdmin)
admin.site.register(Proxy, ProxyAdmin)
admin.site.register(Webpage, WebpageAdmin)
admin.site.register(PageRegion, PageRegionAdmin)
admin.site.register(PageVersion, PageVersionAdmin)
admin.site.register(String, StringAdmin)
admin.site.register(StringTranslation,StringTranslationAdmin)
admin.site.register(TranslatedVersion, TranslatedVersionAdmin)
admin.site.register(Block, BlockAdmin)
admin.site.register(StringInBlock, StringInBlockAdmin)
admin.site.register(TranslatedBlock, TranslatedBlockAdmin)

