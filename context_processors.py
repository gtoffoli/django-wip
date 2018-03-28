import django
from django.conf import settings

def context_processor(request):
    django_minor_version = django.VERSION[1]
    path = request.path
    for language in settings.LANGUAGES:
        # path = path.replace('/%s' % language[0], '')
        path = path.replace('/%s/' % language[0], '/')
    my_settings = {
        'site_name': settings.SITE_NAME,
        'DJANGO_MINOR_VERSION': django_minor_version,
        'path_no_language': path,
    }
    return my_settings
