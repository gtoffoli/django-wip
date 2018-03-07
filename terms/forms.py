from django import forms

from wip.models import Language, Subject, Site
from .models import String
from .models import STRING_TYPE_CHOICES, STRING_SORT_CHOICES, STRING_TRANSLATION_STATE_CHOICES


class StringSequencerForm(forms.Form):
    string_types = forms.MultipleChoiceField(required=False, choices=STRING_TYPE_CHOICES, label="String types", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 4, 'onchange': 'javascript: this.form.submit()', }))
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

class StringsTranslationsForm(forms.Form):
    project_site = forms.ModelChoiceField(required=False, label="Project site", queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    translation_state = forms.ChoiceField(required=False, label="Translation state", choices=STRING_TRANSLATION_STATE_CHOICES, widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;', 'onchange': 'javascript: this.form.submit()',}))
    source_language = forms.ModelChoiceField(required=True, label="Source language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    source_text_filter = forms.CharField(required=False, label="Text in source string", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    target_language = forms.ModelChoiceField(required=True, label="Target language", queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;', 'onchange': 'javascript: this.form.submit()',}))
    target_text_filter = forms.CharField(required=False, label="Text in target string", widget=forms.TextInput(attrs={'style': 'width: 500px;', 'onchange': 'javascript: this.form.submit()',}))
    show_other_targets = forms.BooleanField(required=False, label='Show other targets', widget=forms.CheckboxInput(attrs={'onchange': 'javascript: this.form.submit()',}))
