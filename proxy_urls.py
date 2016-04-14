# -*- coding: utf-8 -*-

from django.conf.urls import url
from proxy import WipHttpProxy

urlpatterns = [
    url(r'^(?P<url>.*)$', WipHttpProxy.as_view(rewrite_links=True)),
]
