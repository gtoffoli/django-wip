import django
from django.conf import settings

def context_processor(request):
    django_minor_version = django.VERSION[1]
    my_settings = {
        'site_name': settings.SITE_NAME,
        'DJANGO_MINOR_VERSION': django_minor_version,
    }
    return my_settings
