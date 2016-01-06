"""
Django admin for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

from django.contrib import admin

from models import Site, Proxy, Webpage, Fetched, Translated

class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'path_prefix', 'url', 'allowed_domains', 'start_urls', 'deny',]

class ProxyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'site_name', 'language', 'host', 'base_path',]

    def site_name(self, obj):
        return obj.site.name

class WebpageAdmin(admin.ModelAdmin):
    list_display = ['path', 'site_name', 'last_checked', 'last_checked_response_code',]

    def site_name(self, obj):
        return obj.site.name

class FetchedAdmin(admin.ModelAdmin):
    pass

class TranslatedAdmin(admin.ModelAdmin):
    pass

admin.site.register(Site, SiteAdmin)
admin.site.register(Proxy, ProxyAdmin)
admin.site.register(Webpage, WebpageAdmin)
admin.site.register(Fetched, FetchedAdmin)
admin.site.register(Translated, TranslatedAdmin)
