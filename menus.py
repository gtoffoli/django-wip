from menu import Menu, MenuItem
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _, ugettext_lazy
# from settings import SITE_NAME
from vocabularies import Language
from models import Site

# print SITE_NAME

Menu.items = {}
Menu.sorted = {}

def sites_children(request):
    children = []
    for site in Site.objects.all().order_by('name'):
        children.append (MenuItem(
             site.name,
             url='/site/%s/' % site.slug,
            ))
    return children        


def strings_children(request):
    children = []
    languages = Language.objects.all().order_by('code')
    for language in languages:
        children.append (MenuItem(
             '%s strings' % language.name,
             url='/strings/%s/' % language.code,
            ))
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

# Add a few items to our main menu
Menu.add_item("main", MenuItem(ugettext_lazy("Home"),
                               url='/',
                               icon='',
                               weight=10,
                               separator=True))
Menu.add_item("main", MenuItem(ugettext_lazy("Sites"),
                               url='/sites/',
                               icon='',
                               weight=20,
                               children=sites_children,
                               separator=True))
"""
Menu.add_item("main", MenuItem(ugettext_lazy("Proxies"),
                               url='/proxies/',
                               icon='',
                               weight=30,
                               separator=True))     
"""
Menu.add_item("main", MenuItem(ugettext_lazy("Strings"),
                               url='/strings/',
                               icon='',
                               weight=30,
                               children=strings_children,
                               separator=True))     
Menu.add_item("main", MenuItem(ugettext_lazy("Italian strings"),
                               url='/strings/',
                               icon='',
                               weight=30,
                               children=italian_strings_children,
                               separator=True))     

