from django.conf.urls import include, url

import wip.terms.views as term_views
from wip.urls import urlpatterns

urlpatterns += (
    url(r"^string_add_by_language/(?P<language_code>[\w-]*)/$", term_views.string_edit, name="string_add_by_language"),
    url(r"^string_add_by_proxy/(?P<proxy_slug>[\w-]+)/$", term_views.string_edit, name="string_add_by_proxy"),
    url(r"^string_edit/(?P<string_id>[\d]+)/$", term_views.string_edit, name="string_edit"),
    url(r"^string_edit/$", term_views.string_edit, name="string_edit"),
    url(r"^string/(?P<string_id>[\d]+)/$", term_views.string_view, name="string_view"),
    url(r"^string_translate/(?P<string_id>[\d]+)/(?P<target_code>[\w]+)/$", term_views.string_translate, name="string_translate"),
    url(r"^strings/(?P<sources>[\w-]*)/(?P<state>[\w-]*)/(?P<targets>[\w-]*)/$", term_views.list_strings, name="list_strings"),
    url(r"^strings/(?P<sources>[\w-]*)/(?P<state>[\w-]*)/$", term_views.list_strings, name="list_strings_notarget"),
    url(r"^proxy/(?P<proxy_slug>[\w-]+)/translations/$", term_views.proxy_string_translations, name="proxy_string_translations"),
    url(r"^add_translated_string/$", term_views.add_translated_string, name="add_translated_string"),
    url(r"^delete_translated_string/$", term_views.delete_translated_string, name="delete_translated_string"),
    url(r"^strings_translations/(?P<proxy_slug>[\w-]+)/$", term_views.strings_translations, name="strings_translations"),
    url(r"^strings_translations/$", term_views.strings_translations, name="strings_translations"),
    # url(r'^navigation_autocomplete$', search_indexes.navigation_autocomplete, name='navigation_autocomplete'),
)
