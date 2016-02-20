from menu import Menu, MenuItem
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _, ugettext_lazy
from settings import SITE_NAME

print SITE_NAME

Menu.items = {}
Menu.sorted = {}

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
                               separator=True))     

