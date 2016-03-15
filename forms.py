'''
Created on 08/feb/2016
@author: giovanni
'''

from django import forms
from models import Site
from models import STRING_TRANSLATION_STATE_CHOICES, TRANSLATION_STATE_CHOICES, TRANSLATION_SERVICE_CHOICES
from vocabularies import Language, Subject

class PageEditForm(forms.Form):
    no_translate = forms.BooleanField(required=False, label='No translate')

class PageSequencerForm(forms.Form):
    page_age = forms.CharField(required=False, label="Page age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))
    translation_state = forms.ChoiceField(required=False, choices=TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;',}))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Translation languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3,}))
    translation_age = forms.CharField(required=False, label="Translation age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))

class BlockEditForm(forms.Form):
    language = forms.ModelChoiceField(required=False, queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    no_translate = forms.BooleanField(required=False, label='No translate')

class BlockSequencerForm(forms.Form):
    webpage = forms.IntegerField(required=False, widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))
    block_age = forms.CharField(required=False, label="Block age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))
    translation_state = forms.ChoiceField(required=False, choices=TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;',}))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Translation languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3,}))
    translation_age = forms.CharField(required=False, label="Translation age range", widget=forms.TextInput(attrs={'size': 8, 'style': 'width: 50px;',}))

class StringSequencerForm(forms.Form):
    translation_state = forms.ChoiceField(required=False, choices=STRING_TRANSLATION_STATE_CHOICES, label="Translation state", widget=forms.Select(attrs={ 'style': 'width: auto; height: 2em;',}))
    translation_languages = forms.ModelMultipleChoiceField(required=False, queryset=Language.objects.all(), label="Translation languages", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3,}))

class StringTranslationForm(forms.Form):
    translation = forms.CharField(required=True, widget=forms.Textarea(attrs={'style': 'width: 100%;'}))
    translation_site = forms.ModelChoiceField(required=False, queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    translation_subjects = forms.ModelMultipleChoiceField(required=False, queryset=Subject.objects.exclude(name='').exclude(name__isnull=True).order_by('code'), widget=forms.SelectMultiple(attrs={'size': 8,}))
    same_txu = forms.BooleanField(required=False, label='Add to same TU')

class TranslationServiceForm(forms.Form):
    translation_services = forms.MultipleChoiceField(required=True, choices=TRANSLATION_SERVICE_CHOICES, label="Translation service", widget=forms.SelectMultiple(attrs={ 'style': 'width: auto;', 'size': 3,}))
