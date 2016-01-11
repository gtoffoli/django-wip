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
                               weight=10,
                               separator=True))
Menu.add_item("main", MenuItem(ugettext_lazy("Sites"),
                               url='/sites/',
                               weight=20,
                               separator=True))
Menu.add_item("main", MenuItem(ugettext_lazy("Proxies"),
                               url='/proxies/',
                               weight=30,
                               separator=True))     

