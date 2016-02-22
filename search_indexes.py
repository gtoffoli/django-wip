'''
Created on 18/Feb/2016
@author: giovanni
'''

from haystack import indexes

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

