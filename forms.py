'''
Created on 08/feb/2016
@author: giovanni
'''

from django import forms
from django.utils.translation import ugettext_lazy as _, string_concat
from django.contrib.auth.models import User
from models import Site, String
from models import UserRole
from models import STRING_TYPE_CHOICES, STRING_SORT_CHOICES, STRING_TRANSLATION_STATE_CHOICES, TRANSLATION_STATE_CHOICES, TRANSLATION_SERVICE_CHOICES
from models import ROLE_TYPE_CHOICES
from vocabularies import Language, Subject

class SiteManageForm(forms.Form):
    clear_pages = forms.BooleanField(required=False, label='Clear pages')
    clear_blocks = forms.BooleanField(required=False, label='Clear blocks')
    clear_invariants = forms.BooleanField(required=False, label='Clear invariant strings')
    # file = forms.FileField(required=False, label='Select a file to upload', widget=forms.FileInput(attrs={'class': 'btn btn-sm'}))
    file = forms.FileField(required=False, label='Select a file to upload')
    delete_confirmation = forms.BooleanField(required=False, label='Delete confirmation')

class ProxyManageForm(forms.Form):
    delete_pages_confirmation = forms.BooleanField(required=False, label='Delete pages confirmation')
    delete_blocks_confirmation = forms.BooleanField(required=False, label='Delete blocks confirmation')
    delete_proxy_confirmation = forms.BooleanField(required=False, label='Delete proxy confirmation')
    file = forms.FileField(required=False, label='Select a file to upload')

class PageEditForm(forms.Form):
    no_translate = forms.BooleanField(required=False, label='No translate')

class PageSequencerForm(forms.Form):
    page_age = forms.CharField(required=False, label="Page age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))
    translation_state = forms.ChoiceField(required=False, choices=TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;',}))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Translation languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3,}))
    translation_age = forms.CharField(required=False, label="Translation age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))
    list_blocks = forms.BooleanField(required=False, label='List contained blocks')

class BlockEditForm(forms.Form):
    language = forms.ModelChoiceField(required=False, queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    no_translate = forms.BooleanField(required=False, label='No translate')

class BlockSequencerForm(forms.Form):
    webpage = forms.IntegerField(required=False, widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;', 'onchange': 'javascript: this.form.submit()',}))
    # block_age = forms.CharField(required=False, label="Block age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;', 'onchange': 'javascript: this.form.submit()',}))
    translation_state = forms.ChoiceField(required=False, choices=TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()',}))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Translation languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3, 'onchange': 'javascript: this.form.submit()',}))
    # translation_age = forms.CharField(required=False, label="Translation age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;', 'onchange': 'javascript: this.form.submit()',}))
    source_text_filter = forms.CharField(required=False, label="Text in block", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    # list_pages = forms.BooleanField(required=False, label='List containing pages')

class StringSequencerForm(forms.Form):
    string_types = forms.MultipleChoiceField(required=False, choices=STRING_TYPE_CHOICES, label="String types", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 4, 'onchange': 'javascript: this.form.submit()', }))
    project_site = forms.ModelChoiceField(required=False, label="Project site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    translation_state = forms.ChoiceField(required=False, choices=STRING_TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()', }))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Target languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3, 'onchange': 'javascript: this.form.submit()', }))
    order_by = forms.ChoiceField(required=False, choices=STRING_SORT_CHOICES, label="Sort order", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', }))
    show_similar = forms.BooleanField(required=False, label='Show similar', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class SegmentSequencerForm(forms.Form):
    # string_types = forms.MultipleChoiceField(required=False, choices=STRING_TYPE_CHOICES, label="String types", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 4, 'onchange': 'javascript: this.form.submit()', }))
    project_site = forms.ModelChoiceField(required=False, label="Project site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    translation_state = forms.ChoiceField(required=False, choices=STRING_TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()', }))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Target languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3, 'onchange': 'javascript: this.form.submit()', }))
    order_by = forms.ChoiceField(required=False, choices=STRING_SORT_CHOICES, label="Sort order", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', }))
    show_similar = forms.BooleanField(required=False, label='Show similar', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class StringEditForm(forms.ModelForm):
    class Meta:
        model = String
        exclude = ('txu', 'is_fragment', 'user',)

    id = forms.CharField(required = False, widget=forms.HiddenInput())
    string_type = forms.ChoiceField(required=True, choices=STRING_TYPE_CHOICES, label="Type", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', }))
    site = forms.ModelChoiceField(required=False, label="Site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    path = forms.CharField(required=False, label="Path", widget=forms.TextInput(attrs={'style': 'width: 500px;'}))
    language = forms.ModelChoiceField(required=True, label="Language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    invariant = forms.BooleanField(required=False, label='Invariant')
    reliability = forms.IntegerField(required=False, label="Score", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))
    text = forms.CharField(required=True, widget=forms.Textarea(attrs={'style': 'width: 100%; height: 60px;'}))

class StringTranslationForm(forms.Form):
    translation = forms.CharField(required=True, widget=forms.Textarea(attrs={'style': 'width: 100%; height: 60px;'}))
    translation_site = forms.ModelChoiceField(required=True, queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    translation_subjects = forms.ModelMultipleChoiceField(required=False, queryset=Subject.objects.exclude(name='').exclude(name__isnull=True).order_by('code'), widget=forms.SelectMultiple(attrs={'size': 3,}))
    same_txu = forms.BooleanField(required=False, label='Add to same TU')
    show_similar = forms.BooleanField(required=False, label='Show similar', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class SegmentTranslationForm(forms.Form):
    translation = forms.CharField(required=True, widget=forms.Textarea(attrs={'style': 'width: 100%; height: 60px;'}))
    show_similar = forms.BooleanField(required=False, label='Show similar', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class StringsTranslationsForm(forms.Form):
    project_site = forms.ModelChoiceField(required=False, label="Project site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    translation_state = forms.ChoiceField(required=False, label="Translation state", choices=STRING_TRANSLATION_STATE_CHOICES, widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()',}))
    source_language = forms.ModelChoiceField(required=True, label="Source language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    source_text_filter = forms.CharField(required=False, label="Text in source string", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    target_language = forms.ModelChoiceField(required=True, label="Target language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    target_text_filter = forms.CharField(required=False, label="Text in target string", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    show_other_targets = forms.BooleanField(required=False, label='Show other targets', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class ListSegmentsForm(forms.Form):
    project_site = forms.ModelChoiceField(required=False, label="Project site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    translation_state = forms.ChoiceField(required=False, label="Translation state", choices=STRING_TRANSLATION_STATE_CHOICES, widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()',}))
    source_language = forms.ModelChoiceField(required=True, label="Source language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    source_text_filter = forms.CharField(required=False, label="Text in source string", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    target_language = forms.ModelChoiceField(required=True, label="Target language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    target_text_filter = forms.CharField(required=False, label="Text in target string", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    show_other_targets = forms.BooleanField(required=False, label='Show other targets', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class TranslationViewForm(forms.Form):
    compute_alignment = forms.BooleanField(required=False, label='Show alignment', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))

class TranslationServiceForm(forms.Form):
    translation_services = forms.MultipleChoiceField(required=True, choices=TRANSLATION_SERVICE_CHOICES, label="Translation service", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3,}))

class FilterPagesForm(forms.Form):
    path_filter = forms.CharField(required=False, label="Pattern in page path", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    from_start = forms.BooleanField(required=False, label='Only paths starting with pattern')

class DiscoverForm(forms.Form):
    site = forms.ModelChoiceField(required=False, label="Site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    name = forms.CharField(required=False, label="Name", widget=forms.TextInput(attrs={'style': 'width: 200px;'}))
    max_pages = forms.IntegerField(required=False, label="Max pages", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))
    allowed_domains = forms.CharField(required=False, label="Allowed domains", widget=forms.Textarea(attrs={'style': 'width: 100%; height: 24px;'}))
    start_urls = forms.CharField(required=False, label="Start urls", widget=forms.Textarea(attrs={'style': 'width: 100%; height: 24px;'}))
    allow = forms.CharField(required=False, label="Allow", widget=forms.Textarea(attrs={'style': 'width: 100%; height: 40px;'}))
    deny = forms.CharField(required=False, label="Deny", widget=forms.Textarea(attrs={'style': 'width: 100%; height: 40px;'}))
    count_words = forms.BooleanField(required=False, label='Extract word count')
    count_segments = forms.BooleanField(required=False, label='Extract segment count')

class UserRoleEditForm(forms.ModelForm):
    class Meta:
        model = UserRole
        exclude = ()

    id = forms.CharField(required = False, widget=forms.HiddenInput())
    user = forms.ModelChoiceField(queryset=User.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    site = forms.ModelChoiceField(required=False, label="Site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    role_type = forms.ChoiceField(required=False, choices=ROLE_TYPE_CHOICES, label="Tole type", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;',}))
    level = forms.IntegerField(required=False, label="Level", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))
    source_language = forms.ModelChoiceField(required=False, label="Source language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    target_language = forms.ModelChoiceField(required=False, label="Target language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))

class ImportXliffForm(forms.Form):
    file = forms.FileField(label='Select a file to upload', widget=forms.FileInput(attrs={'accept': '.xlf'}), help_text=_('Usually XLIFF files have the .xlf extension'))
    user_role = forms.ModelChoiceField(label="User role", queryset=UserRole.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;'}), help_text=_('Choose a user role of the author of the translations in the XLIFF file.'))
