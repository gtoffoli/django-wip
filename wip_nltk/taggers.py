import sys, os, inspect
import codecs
import re
from StringIO import StringIO

try:
    import cPickle as pickle
except:
    import pickle

import nltk
from nltk.tag import *
from nltk.tag.sequential import ContextTagger, NgramTagger, AffixTagger

import util, fixes
from tokenizers import NltkTokenizer
from lexicons import NltkLexicon
from corpora import simplify_wacky_tag

p_number = r"[^\s\{\}\[\]\(\)\"]*[0-9]+[^\s\{\}\[\]\(\)\"]*[^\s\.,\!\?\:\{\}\[\]\(\)\"]"
r_number = re.compile(p_number)
p_roman_number = '^[IVXLCD]{2,}$'
r_roman_number = re.compile(p_roman_number)
p_date_1 = "^19[0-9]{2}|20[0-1][0-9]$"
r_date_1 = re.compile(p_date_1)
p_date_3 = "^[0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4}$"
r_date_3 = re.compile(p_date_3)
p_endswith_vowel = "^.*[AEIOUaeiou]'$"
r_endswith_vowel = re.compile(p_endswith_vowel)
p_general_punctuation = u"^[\u2010-\u2044]$"
r_general_punctuation = re.compile(p_general_punctuation)

symbols_dict = {
    u'\u00b7': u'PON', # item bullet
}

ordered_morphit_tag_set = [
    u'NOUN',

    u'ARTPRE',
    u'ART',
    u'DET',
    u'PRO',
    u'WH',
    u'CON',

    u'PRE',
    u'ADV',

    u'AUX',
    u'VER',
    u'CAU',
    u'ADJ',

    u'SENT',
    u'PON',
]

class NltkTagger(object):
    """An object representing a tagger wizard"""

    def __init__(self, language=None, tagger_types=[], default_tag=None, train_sents=[], tagger_input_file=None):
        """ set language """
        self.language = language or u'it'
        self.default_tag = default_tag
        self.train_sents = train_sents
        tagger_types = list(tagger_types)
        if default_tag and (not tagger_types or tagger_types[-1]!='DefaultTagger'):
            tagger_types.append('DefaultTagger')
        tagger_types.reverse()
        self.tagger_types = tagger_types
        self.tagger_input_file = tagger_input_file
        self.tagger = None
        self.tagged_tokens = None

    def main_tagger(self, tokens):
        """ choose a tagger based on some parameters """
        if self.language == u'italian' and self.tagger == u'link':
            return self.lexicon_based_tagger(tokens)
        else:
            return self.default_tagger(tokens)

    def default_tag(self, token=None):
        """ return the default tag for the current language and tagset """
        first_isupper = token and not token.isupper() and token[0].isupper()
        if self.language == u'it':
            return first_isupper and u'NPR' or u'NOUN'
        else:
            return first_isupper and u'NP' or u'NN'

    """
    next 3 methods currently not used:
    possibly recover some ideas for text pre-processing
    """

    def lexicon_based_tagger(self, tokens):
        """ choose a tagger based on some parameters """
        if not self.language == u'italian':
            return self.default_tagger(tokens)
        lexicon_object = NltkLexicon(path='morph-it')
        lexicon_object.load_morphoit()
        lemma_dict = lexicon_object.lemma_dict
        tag_dict = lexicon_object.tag_dict
        suffix_dict = lexicon_object.suffix_dict
        word_tag_dict = lexicon_object.word_tag_dict
        tagged_tokens = []
        for token in tokens:
            key = token
            # basic lookup
            word_tags = word_tag_dict.get(key, None)
            # lookup of lowercase token
            if not word_tags and not token.islower():
                word_tags = word_tag_dict.get(token.lower(), None)
            # convert to latin-1 other unicode codes
            filtered = util.filter_unicode(token)
            if filtered:
                key = filtered
            # new lookup, in case of conversion
            if not word_tags and filtered:
                word_tags = word_tag_dict.get(key, None)
            # match a number
            if not word_tags and r_number.search(key):
                tagged_tokens.append([token, [u'PRO-NUM', u'DET-NUM-CARD'], u'RULE'])
                continue
            # match a roman number
            #if not word_tags and key.isupper() and r_roman_number.search(key):
            if not word_tags and r_roman_number.search(key):
                tagged_tokens.append([token, ['ADJ'], u'RULE'])
                continue
            # new lookup in lexicon, if token ends with vowel+apostrofe 
            if not word_tags and r_endswith_vowel.search(key):
                word_tags = word_tag_dict.get(util.put_accent_onlast(key.lower()), None)
            # lookup of single character in symbols dict 
            if not word_tags and len(token)==1 and symbols_dict.get(token, None):
                tagged_tokens.append([token, [symbols_dict.get(token)], u'SYMBOL'])
                continue
            # in case of multiple tags, apply simple priority euristics 
            if word_tags:
                tags = word_tags.keys()
                if len(tags)>1:
                    high = []
                    low = []
                    for t1 in ordered_morphit_tag_set:
                        for t2 in tags:
                            if t1 == t2.split(u'-')[0]:
                                high.append(t2)
                    if len(high) < len (tags):
                        low = [t for t in tags if not t in high]
                    tags = high + low
                tagged_tokens.append([token, tags, u'LEXICON'])
            else:
                # worst case: assign default tag
                tags = [self.default_tag(token)]
                tagged_tokens.append([token, tags, u'DEFAULT'])
        return tagged_tokens

    def default_tagger(self, tokens):
        """ backup tagger: tags everything as a noun """
        return [[token, self.default_tag()] for token in tokens]

    def build_tagger(self):
        """ build an NLTK tagger object if needed """
        if self.tagger_input_file:
            print self.tagger_input_file
            tagger = self.upload_trained_tagger(self.tagger_input_file)
        else:
            taggers_dict = nltk_taggers()
            module = nltk.tag
            backoff = None
            tagger = None
            for tagger_type in self.tagger_types:
                if tagger_type == 'AffixTagger':
                    cutoff = 2
                else:
                    cutoff = 0
                tagger_class = taggers_dict.get(tagger_type)
                if tagger_type == 'DefaultTagger':
                    tagger = tagger_class(self.default_tag)
                elif issubclass(tagger_class, ContextTagger):
                    tagger = tagger_class(train=self.train_sents, backoff=backoff, cutoff=cutoff)
                backoff = tagger
        self.tagger = tagger

    def tag(self, text=None, tokens=[]):
        """ tag the text using a tagger of type specified  """
        raw = u''
        if text:
            raw = text
            # tokens = nltk.word_tokenize(raw)
            tokenizer = NltkTokenizer(language_code=self.language)
            tokens = tokenizer.tokenize(raw)
        if not self.tagger:
            self.build_tagger()
        self.tagged_tokens = self.tagger.tag(tokens)
        # return self.tagged_tokens
        return fixes.fix_tags(self.tagged_tokens)

    def train(self):
        """ train the tagger with the training set specified """
        if not self.tagger:
            self.build_tagger()

    def evaluate(self, test_sents=None):
        """ evaluate the tagger on the test set specified """
        if not self.tagger:
            self.build_tagger()
        return self.tagger.evaluate(test_sents)

    """
    def upload_trained_tagger(self, data):
        return pickle.loads(data)
    """
    def upload_trained_tagger(self, path):
        f = open(path, 'r')
        return pickle.load(f)

    def download_trained_tagger(self, filename, context=None):
        data = self.tagger
        content_type = 'application/octet-stream'
        ext = '.pickle'
        if not filename.endswith(ext):
            filename += ext
        request = context.REQUEST
        RESPONSE = request.RESPONSE
        RESPONSE.setHeader('Content-Type', content_type)
        RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)
        return pickle.dumps(data)

    def download_tagged_text(self, filename, context=None):
        tagged_text = u'\n'.join([u'%s/%s' % (tagged_token[0], tagged_token[1]) for tagged_token in self.tagged_tokens])
        content_type = 'text/plain; charset=utf-8'
        ext = '.txt'
        if not filename.endswith(ext):
            filename += ext
        request = context.REQUEST
        RESPONSE = request.RESPONSE
        RESPONSE.setHeader('Content-Type', content_type)
        RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)
        return tagged_text

def nltk_tagger_types():
    """
    return a list of names of the tagger types in nltk
    """
    module = nltk.tag
    # names = module.__all__
    names = dir(module)
    abstract_tagger_names = ['SequentialBackoffTagger', 'ContextTagger', 'NgramTagger', 'ClassifierBasedTagger',]
    names = [name for name in names if name.endswith('Tagger') and not name in abstract_tagger_names]
    return names

def nltk_taggers():
    """
    return a dict of the tagger types (classes) in nltk
    """
    module = nltk.tag
    dict = {}
    for name in nltk_tagger_types():
        dict[name] = getattr(module, name)
    return dict
