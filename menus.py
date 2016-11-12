from menu import Menu, MenuItem
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _, ugettext_lazy
# from settings import SITE_NAME
from vocabularies import Language
from models import Site, Proxy
from session import get_language, get_site

# print SITE_NAME

Menu.items = {}
Menu.sorted = {}

def sites_children(request):
    children = []
    for site in Site.objects.all().order_by('name'):
        if site.can_view(request.user):
            slug = site.slug
            children.append (MenuItem(
                 site.name,
                 url='/site/%s/' % slug,
                 # selected=lambda site: get_site(request)==slug,
                ))
    return children        

def discovery_children(request):
    children = []
    children.append (MenuItem(
         'My scans',
         url='/my_scans/'
        ))
    children.append (MenuItem(
         'New scan',
         url='/discover/'
        ))
    return children        

def languages_children(request):
    children = []
    languages = Language.objects.all().order_by('code')
    for language in languages:
        code = language.code
        children.append (MenuItem(
             language.name,
             url='/language/%s/set/' % code,
             # selected=lambda code: get_language(request)==code,
            ))
    children.append (MenuItem(
         'none',
         url='/language//set/',
        ))
    return children        

def proxies_children(request):
    children = []
    # for site in Site.objects.filter(slug=get_site(request)):
    for site in Site.objects.all().order_by('name'):
        # for proxy in Proxy.objects.filter(site=site, language_id=get_language(request)).order_by('name'):
        for proxy in Proxy.objects.filter(site=site).order_by('name'):
            if proxy.can_view(request.user):
                children.append (MenuItem(
                     proxy.name,
                     url='/proxy/%s/' % proxy.slug,
                    ))
    return children        

def strings_children(request):
    children = []
    languages = Language.objects.all().order_by('code')
    for language in languages:
        children.append (MenuItem(
             '%s strings' % language.name,
             url='/strings/%s/any/' % language.code,
            ))
    if request.user.is_authenticated():
        children.append (MenuItem(
             'Italian strings with translations',
             url='/strings/it/translated/en-es-fr/',
            ))
    return children        

def italian_strings_children(request):
    children = []
    targets = Language.objects.exclude(code='it').order_by('code')
    for target in targets:
        children.append (MenuItem(
             'to be translated to %s' % target.name,
             url='/strings/it/untranslated/%s/' % target.code,
            ))
    for target in targets:
        children.append (MenuItem(
             'translated to %s' % target.name,
             url='/strings/it/translated/%s/' % target.code,
            ))
    return children        

def check_proxies(request):
    if not request.user.is_authenticated():
        return False
    code = get_language(request)
    slug = get_site(request)
    return code and slug and Proxy.objects.filter(site__slug=slug, language_id=code).count() or False

# Add a few items to our main menu
"""
Menu.add_item("main", MenuItem(ugettext_lazy("Home"),
                               url='/',
                               icon='',
                               weight=10,
                               separator=True))
"""
Menu.add_item("main", MenuItem(ugettext_lazy("Discovery"),
                               url='/',
                               icon='',
                               weight=20,
                               children=discovery_children,
                               check=lambda request: request.user.is_authenticated(),
                               separator=True))
Menu.add_item("main", MenuItem(ugettext_lazy("Sites"),
                               url='/',
                               icon='',
                               weight=20,
                               children=sites_children,
                               check=lambda request: request.user.is_authenticated(),
                               separator=True))
"""
Menu.add_item("main", MenuItem(ugettext_lazy("Languages"),
                               url='/',
                               icon='',
                               weight=30,
                               children=languages_children,
                               separator=True))     
"""
Menu.add_item("main", MenuItem(ugettext_lazy("Proxies"),
                               url='/',
                               icon='',
                               weight=30,
                               children=proxies_children,
                               # check=check_proxies,
                               check=lambda request: request.user.is_authenticated(),
                               separator=True))     

Menu.add_item("main", MenuItem(ugettext_lazy("Strings"),
                               url='/',
                               icon='',
                               weight=30,
                               children=strings_children,
                               separator=True))     
Menu.add_item("main", MenuItem(ugettext_lazy("Italian strings"),
                               url='/',
                               icon='',
                               weight=30,
                               children=italian_strings_children,
                               check=lambda request: request.user.is_authenticated(),
                               separator=True))     

