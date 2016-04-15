from __future__ import absolute_import

from actstream import action, registry

from wip.models import Site, Proxy

registry.register(Site)
registry.register(Proxy)

def site_add(user, site, description=None):
    return action.send(user, verb='SiteAdd', action_object=site, description=description)

def site_archive_pages(user, site, description=None):
    action.send(user, verb='SiteArchivePages', action_object=site, description=description)

def site_clear_pages(user, site, description=None):
    action.send(user, verb='SiteClearPages', action_object=site, description=description)

def site_crawl(user, site, description=None):
    action.send(user, verb='SiteCrawl', action_object=site, description=description)

def site_clear_blocks(user, site, description=None):
    action.send(user, verb='SiteClearBlocks', action_object=site, description=description)

def site_import_invariants(user, site, description=None):
    action.send(user, verb='SiteImportInvariants', action_object=site, description=description)

def site_extract_segments(user, site, description=None):
    action.send(user, verb='SiteExtractSegments', action_object=site, description=description)

def proxy_add_to_site(user, proxy, site, description=None):
    action.send(user, verb='ProxyAddToSite', action_object=proxy, target=site, description=description)
