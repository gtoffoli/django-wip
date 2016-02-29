'''
Created on 08/feb/2016
@author: giovanni
'''
from django.db import models
from django import forms
from models import Site
from vocabularies import Language, Subject

class PageBlockForm(forms.Form):
    # block = forms.IntegerField(widget=forms.HiddenInput())
    language = forms.ModelChoiceField(required=False, queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    no_translate = forms.BooleanField(required=False, label='No translate')
    skip_no_translate = forms.BooleanField(required=False, label='Skip no-translate blocks', )
    skip_translated = forms.BooleanField(required=False, label='Skip translated blocks')
    exclude_language = forms.ModelChoiceField(required=False, queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    # include_language = forms.ModelChoiceField(required=False, queryset=Language.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    extract_strings = forms.BooleanField(required=False, label='Extract strings', )

class StringTranslationForm(forms.Form):
    translation = forms.CharField(required=True, widget=forms.Textarea(attrs={'style': 'width: 100%;'}))
    site = forms.ModelChoiceField(required=True, queryset=Site.objects.all(), widget=forms.Select(attrs={'style':'height: 24px;',}))
    subjects = forms.ModelMultipleChoiceField(required=False, queryset=Subject.objects.exclude(name='').exclude(name__isnull=True).order_by('code'), widget=forms.SelectMultiple(attrs={'size': 8,}))
