"""
Django admin for wip application of wip project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/db/models/
"""

from django.contrib import admin

from models import Site, Proxy, Webpage, Fetched, Translated

class SiteAdmin(admin.ModelAdmin):
    pass

class ProxyAdmin(admin.ModelAdmin):
    pass

class WebpageAdmin(admin.ModelAdmin):
    pass

class FetchedAdmin(admin.ModelAdmin):
    pass

class TranslatedAdmin(admin.ModelAdmin):
    pass

admin.site.register(Site, SiteAdmin)
admin.site.register(Proxy, ProxyAdmin)
admin.site.register(Webpage, WebpageAdmin)
admin.site.register(Fetched, FetchedAdmin)
admin.site.register(Translated, TranslatedAdmin)
