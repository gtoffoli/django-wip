'''
Created on 18/Feb/2016
@author: giovanni
'''

from django.shortcuts import render
from django.db.models.signals import post_save, post_delete
from haystack import indexes
from haystack.query import SearchQuerySet

from models import String

class StringIndex(indexes.SearchIndex, indexes.Indexable):

    text = indexes.EdgeNgramField(document=True, use_template=True)
    # id = indexes.IntegerField(model_attr='id', indexed=False)
    label = indexes.CharField(model_attr='text', indexed=False)
    language_code = indexes.CharField(model_attr='language_code', indexed=True)

    def get_model(self):
        return String

    def index_queryset(self, using=None):
        return self.get_model().objects.all()

def string_post_save_handler(sender, **kwargs):
    string = kwargs['instance']
    StringIndex().update_object(string)
    txu = string.txu
    if txu:
        txu.update_languages()

def string_post_delete_handler(sender, **kwargs):
    string = kwargs['instance']
    try:
        txu = string.txu
    except:
        txu = None
    StringIndex().remove_object(string)
    if txu:
        txu.update_languages()

post_save.connect(string_post_save_handler, sender=String)
post_delete.connect(string_post_delete_handler, sender=String)

q_extra = ['(', ')', '[', ']', '"']
def clean_q(q):
    for c in q_extra:
        q = q.replace(c, '')
    return q

def navigation_autocomplete(request, template_name='autocomplete.html'):
    q = request.GET.get('q', '')
    q = clean_q(q)
    context = {'q': q}

    MAX = 8
    results = SearchQuerySet().filter(text=q)
    queries = { 'it': [], 'en': [], 'es': [], 'fr': [], }
    for result in results:
        # klass = result.model.__name__
        additional_fields = result.get_additional_fields()
        language_code = additional_fields['language_code']
        label = additional_fields['label']
        values_list = [result.pk, label]
        if len(queries[language_code]) <= MAX:
            queries[language_code].append(values_list)
    context['language_strings'] = sorted(queries.items())
    context.update(queries)
    return render(request, template_name, context)
