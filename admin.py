"""
Django admin for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

from django.contrib import admin

from models import Site, Proxy, PageRegion, Webpage, PageVersion, String, StringTranslation, TranslatedVersion

class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'path_prefix', 'url', 'allowed_domains', 'start_urls', 'deny',]

class ProxyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'site_name', 'language', 'host', 'base_path',]

    def site_name(self, obj):
        return obj.site.name

class WebpageAdmin(admin.ModelAdmin):
    list_filter = ('site__name',)
    list_display = ['id', 'path', 'site', 'encoding', 'last_checked', 'last_checked_response_code',]
    list_display_links = ('id', 'site',)
    search_fields = ['site_name', 'path',]

    def site_name(self, obj):
        return obj.site.name

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

admin.site.register(Site, SiteAdmin)
admin.site.register(Proxy, ProxyAdmin)
admin.site.register(Webpage, WebpageAdmin)
admin.site.register(PageRegion, PageRegionAdmin)
admin.site.register(PageVersion, PageVersionAdmin)
admin.site.register(String, StringAdmin)
admin.site.register(StringTranslation,StringTranslationAdmin)
admin.site.register(TranslatedVersion, TranslatedVersionAdmin)
