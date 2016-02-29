'''
Created on 18/Feb/2016
@author: giovanni
'''

from haystack import indexes
from haystack.query import SearchQuerySet

from wip.models import String

class StringIndex(indexes.SearchIndex, indexes.Indexable):

    text = indexes.EdgeNgramField(document=True, use_template=True)
    # id = indexes.IntegerField(model_attr='id', indexed=False)
    label = indexes.CharField(model_attr='text', indexed=False)
    language_code = indexes.CharField(model_attr='language_code', indexed=True)

    def get_model(self):
        return String

    def index_queryset(self, using=None):
        return self.get_model().objects.all()

from collections import defaultdict
from django.shortcuts import render

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
