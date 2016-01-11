from django.conf import settings

def context_processor(request):
    my_settings = {
        'site_name': settings.SITE_NAME,
    }

    return my_settings
