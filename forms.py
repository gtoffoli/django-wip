'''
Created on 08/feb/2016
@author: giovanni
'''

from django import forms
from models import Site
from models import TRANSLATION_STATE_CHOICES
from vocabularies import Language, Subject

class PageBlockForm(forms.Form):
    language = forms.ModelChoiceField(required=False, queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    no_translate = forms.BooleanField(required=False, label='No translate')
    skip_no_translate = forms.BooleanField(required=False, label='Skip no-translate blocks', )
    skip_translated = forms.BooleanField(required=False, label='Skip translated blocks')
    exclude_language = forms.ModelChoiceField(required=False, queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    # include_language = forms.ModelChoiceField(required=False, queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    extract_strings = forms.BooleanField(required=False, label='Extract strings', )

class BlockEditForm(forms.Form):
    language = forms.ModelChoiceField(required=False, queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    no_translate = forms.BooleanField(required=False, label='No translate')

class BlockSequencerForm(forms.Form):
    webpage = forms.IntegerField(required=False, widget=forms.HiddenInput())
    block_age = forms.CharField(required=False, label="Block age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))
    translation_state = forms.ChoiceField(required=False, choices=TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;',}))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Translation languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3,}))
    translation_age = forms.CharField(required=False, label="Translation age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))

class StringTranslationForm(forms.Form):
    translation = forms.CharField(required=True, widget=forms.Textarea(attrs={'style': 'width: 100%;'}))
    site = forms.ModelChoiceField(required=True, queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    subjects = forms.ModelMultipleChoiceField(required=False, queryset=Subject.objects.exclude(name='').exclude(name__isnull=True).order_by('code'), widget=forms.SelectMultiple(attrs={'size': 8,}))
