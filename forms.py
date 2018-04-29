'''
Created on 08/feb/2016
@author: giovanni
'''

from django import forms
from django.utils.translation import ugettext_lazy as _, string_concat
from django.contrib.auth.models import User
from .models import Site, Segment
from .models import UserRole
from .models import SEGMENT_SORT_CHOICES, TRANSLATION_STATE_CHOICES, TRANSLATION_EXPORT_CHOICES, BLOCK_TRANSLATION_STATE_CHOICES, TRANSLATION_SERVICE_CHOICES, SOURCE_CACHE_TYPE_CHOICES, SCAN_MODE_CHOICES
from .models import ROLE_TYPE_CHOICES
from .vocabularies import Language, Subject

YES_NO_CHOICES = (('', '',), ('Y', 'Y',), ('N', 'N',),)

PARALLEL_SENTENCES_FORMAT_CHOICES = (
    (1, _("xliff")),
    (2, _("text"))
)

ALIGNMENT_CHOICES = (
    (0, _("any")),
    (2, _("mt")),
    (3, _("manual"))
)

TRANSLATION_CHOICES = ALIGNMENT_CHOICES

ALIGNER_CHOICES = (
    (1, _("eflomal")),
    (2, _("nltk"))
)

ALIGNMENT_TEST_SET_CHOICES = (
    (0, _("all")),
    (2, _("1 out of 2")),
    (4, _("1 out of 4"))
)

DISCRETE_VALUES = (0, 10, 20, 50, 100, 200, 500)
DISCRETE_CHOICES = [(value, str(value)) for value in DISCRETE_VALUES]

class SiteManageForm(forms.Form):
    clear_pages = forms.BooleanField(required=False, label='Clear pages')
    clear_blocks = forms.BooleanField(required=False, label='Clear blocks')
    clear_invariants = forms.BooleanField(required=False, label='Clear invariant strings')
    # file = forms.FileField(required=False, label='Select a file to upload', widget=forms.FileInput(attrs={'class': 'btn btn-sm'}))
    file = forms.FileField(required=False, label='Select a file to upload')
    delete_confirmation = forms.BooleanField(required=False, label='Delete confirmation')
    verbose = forms.BooleanField(required=False, label='Verbose')

class ProxyManageForm(forms.Form):
    delete_pages_confirmation = forms.BooleanField(required=False, label='Delete pages confirmation')
    delete_blocks_confirmation = forms.BooleanField(required=False, label='Delete blocks confirmation')
    delete_proxy_confirmation = forms.BooleanField(required=False, label='Delete proxy confirmation')
    file = forms.FileField(required=False, label='Select a file to upload')
    translation_state = forms.ChoiceField(choices=TRANSLATION_EXPORT_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;'}))
    parallel_format = forms.ChoiceField(choices=PARALLEL_SENTENCES_FORMAT_CHOICES, label="Format", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;',}))
    aligner = forms.ChoiceField(choices=ALIGNER_CHOICES, label="Aligner", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;',}))
    use_known_links = forms.BooleanField(required=False, label='Use known links')
    test_set_module = forms.ChoiceField(choices=ALIGNMENT_TEST_SET_CHOICES, label="Test set generation module", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;',}))
    verbose = forms.BooleanField(required=False, label='Verbose')
    debug = forms.BooleanField(required=False, label='Debug')

class PageManageForm(forms.Form):
    no_translate = forms.BooleanField(required=False, label='No translate')

class PageSequencerForm(forms.Form):
    page_age = forms.CharField(required=False, label="Page age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;', 'onchange': 'javascript: this.form.submit()',}))
    translation_state = forms.ChoiceField(required=False, choices=TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()',}))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Tr. languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3, 'onchange': 'javascript: this.form.submit()',}))
    translation_age = forms.CharField(required=False, label="Translation age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;', 'onchange': 'javascript: this.form.submit()',}))
    list_blocks = forms.BooleanField(required=False, label='List contained blocks')

class BlockEditForm(forms.Form):
    language = forms.ModelChoiceField(required=False, queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    no_translate = forms.BooleanField(required=False, label='No translate')

class BlockSequencerForm(forms.Form):
    project_site = forms.ModelChoiceField(required=False, label="Project", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    webpage = forms.IntegerField(required=False, widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;', 'onchange': 'javascript: this.form.submit()',}))
    # block_age = forms.CharField(required=False, label="Block age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;', 'onchange': 'javascript: this.form.submit()',}))
    translation_state = forms.ChoiceField(required=False, choices=BLOCK_TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()',}))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Tr. languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3, 'onchange': 'javascript: this.form.submit()',}))
    # translation_age = forms.CharField(required=False, label="Translation age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;', 'onchange': 'javascript: this.form.submit()',}))
    source_text_filter = forms.CharField(required=False, label="Text in block", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    # list_pages = forms.BooleanField(required=False, label='List containing pages')

class SegmentSequencerForm(forms.Form):
    # string_types = forms.MultipleChoiceField(required=False, choices=STRING_TYPE_CHOICES, label="String types", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 4, 'onchange': 'javascript: this.form.submit()', }))
    project_site = forms.ModelChoiceField(required=False, label="Project site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    in_use = forms.ChoiceField(required=False, choices=YES_NO_CHOICES, label="In use", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()', }))
    translation_state = forms.ChoiceField(required=False, choices=TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()', }))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Target languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3, 'onchange': 'javascript: this.form.submit()', }))
    translation_sources = forms.MultipleChoiceField(required=False, choices=TRANSLATION_SERVICE_CHOICES, label="Translation source", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3, 'onchange': 'javascript: this.form.submit()', }))
    order_by = forms.ChoiceField(required=False, choices=SEGMENT_SORT_CHOICES, label="Sort order", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()', }))
    show_similar = forms.BooleanField(required=False, label='Show similar', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class SegmentEditForm(forms.ModelForm):
    class Meta:
        model = Segment
        exclude = ('comment', 'is_comment_settled',)

    id = forms.CharField(required = False, widget=forms.HiddenInput())
    site = forms.ModelChoiceField(required=False, label="Site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    language = forms.ModelChoiceField(label="Language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    is_fragment = forms.BooleanField(required=False, label='Fragment')
    is_invariant = forms.BooleanField(required=False, label='Invariant')
    text = forms.CharField(required=True, widget=forms.Textarea(attrs={'style': 'width: 100%; height: 60px;'}))

class SegmentTranslationForm(forms.Form):
    translation_source = forms.ChoiceField(required=False, choices=TRANSLATION_SERVICE_CHOICES, label="Translation source", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;'}))
    translation = forms.CharField(required=True, widget=forms.Textarea(attrs={'style': 'width: 100%; height: 60px;', 'placeholder': _('Put translation here')}))
    show_similar = forms.BooleanField(required=False, label='Show similar', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class ListSegmentsForm(forms.Form):
    project_site = forms.ModelChoiceField(required=False, label="Project site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    translation_state = forms.ChoiceField(required=False, label="Translation state", choices=TRANSLATION_STATE_CHOICES, widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()',}))
    translation_source = forms.ChoiceField(required=False, choices=TRANSLATION_SERVICE_CHOICES, label="Translation source", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()', }))
    in_use = forms.ChoiceField(required=False, choices=YES_NO_CHOICES, label="In use", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()', }))
    source_language = forms.ModelChoiceField(required=True, label="Source language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    source_text_filter = forms.CharField(required=False, label="Text in source string", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    target_language = forms.ModelChoiceField(required=True, label="Target language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    target_text_filter = forms.CharField(required=False, label="Text in target string", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    order_by = forms.ChoiceField(required=False, choices=SEGMENT_SORT_CHOICES, label="Sort order", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()',}))
    show_other_targets = forms.BooleanField(required=False, label='Show other targets', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))
    show_alignments = forms.BooleanField(required=False, label='Show alignments', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class TranslationSequencerForm(forms.Form):
    order_by = forms.ChoiceField(required=False, choices=SEGMENT_SORT_CHOICES, label="Sort order", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', }))
    translation_type = forms.ChoiceField(required=False, choices=TRANSLATION_CHOICES, label="Translation type", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()', }))
    alignment_type = forms.ChoiceField(required=False, choices=ALIGNMENT_CHOICES, label="Alignment type", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()', }))

class TranslationViewForm(forms.Form):
    alignment = forms.CharField(required = False, widget=forms.HiddenInput())
    compute_alignment = forms.BooleanField(required=False, label='Show alignment', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class TranslationServiceForm(forms.Form):
    translation_services = forms.MultipleChoiceField(required=True, choices=TRANSLATION_SERVICE_CHOICES, label="Translation service", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3,}))
    # max_segments = forms.IntegerField(required=False, label="Max segments", widget=forms.TextInput(attrs={'class':'form-control'}))
    max_segments = forms.ChoiceField(required=False, choices=DISCRETE_CHOICES, label="Max segments", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', }))

class FilterPagesForm(forms.Form):
    path_filter = forms.CharField(required=False, label="Pattern in page path", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    from_start = forms.BooleanField(required=False, label='Only paths starting with pattern')

class DiscoverForm(forms.Form):
    site = forms.ModelChoiceField(required=False, label="Site", queryset=Site.objects.all(), widget=forms.Select(attrs={'class':'form-control'}))
    name = forms.CharField(required=False, label="Name", widget=forms.TextInput(attrs={'class':'form-control'}))
    scan_mode = forms.ChoiceField(required=False, choices=SCAN_MODE_CHOICES, label="Scan mode", widget=forms.Select(attrs={'class':'form-control'}))
    max_pages = forms.IntegerField(required=False, label="Max pages", widget=forms.TextInput(attrs={'class':'form-control'}))
    allowed_domains = forms.CharField(required=False, label="Allowed domains", widget=forms.Textarea(attrs={'class':'form-control', 'rows': 1}))
    start_urls = forms.CharField(required=False, label="Start urls", widget=forms.Textarea(attrs={'class':'form-control', 'rows': 1}))
    allow = forms.CharField(required=False, label="Allowed paths", widget=forms.Textarea(attrs={'class':'form-control', 'rows': 1}))
    deny = forms.CharField(required=False, label="Denied paths", widget=forms.Textarea(attrs={'class':'form-control', 'rows': 6}))
    count_words = forms.BooleanField(required=False, label='Extract word count', widget=forms.CheckboxInput(attrs={'class':'form-control'}))
    count_segments = forms.BooleanField(required=False, label='Extract segment count', widget=forms.CheckboxInput(attrs={'class':'form-control'}))

class CrawlForm(forms.Form):
    cache_type = forms.ChoiceField(required=False, choices=SOURCE_CACHE_TYPE_CHOICES, label="Cache type", widget=forms.Select(attrs={'class':'form-control'}))
    scan_mode = forms.ChoiceField(required=False, choices=SCAN_MODE_CHOICES, label="Scan mode", widget=forms.Select(attrs={'class':'form-control'}))
    extract_blocks = forms.BooleanField(required=False, label='Extract blocks', widget=forms.CheckboxInput(attrs={'class':'form-control'}))
    max_pages = forms.IntegerField(required=False, label="Max pages", widget=forms.TextInput(attrs={'class':'form-control'}))
    allowed_domains = forms.CharField(required=False, label="Allowed domains", widget=forms.Textarea(attrs={'class':'form-control', 'rows': 1}))
    start_urls = forms.CharField(required=False, label="Start urls", widget=forms.Textarea(attrs={'class':'form-control', 'rows': 1}))
    allow = forms.CharField(required=False, label="Allowed paths", widget=forms.Textarea(attrs={'class':'form-control', 'rows': 1}))
    deny = forms.CharField(required=False, label="Denied paths", widget=forms.Textarea(attrs={'class':'form-control', 'rows': 6}))

class UserRoleEditForm(forms.ModelForm):
    class Meta:
        model = UserRole
        exclude = ('creator',)

    id = forms.CharField(required = False, widget=forms.HiddenInput())
    user = forms.ModelChoiceField(queryset=User.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    site = forms.ModelChoiceField(required=False, label="Site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    role_type = forms.ChoiceField(required=False, choices=ROLE_TYPE_CHOICES, label="Role type", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;',}), help_text=_('level of experience/reliability: let try to use the range 1 to 5 (top level)'))
    level = forms.IntegerField(required=False, label="Level", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))
    source_language = forms.ModelChoiceField(required=False, label="Source language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    target_language = forms.ModelChoiceField(required=False, label="Target language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))

class ImportXliffForm(forms.Form):
    file = forms.FileField(label='Select a file to upload', widget=forms.FileInput(attrs={'accept': '.xlf'}), help_text=_('Usually XLIFF files have the .xlf extension'))
    user_role = forms.ModelChoiceField(label="User role", queryset=UserRole.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;'}), help_text=_('Choose a user role of the author of the translations in the XLIFF file.'))
