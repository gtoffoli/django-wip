import os
from StringIO import StringIO
import codecs
try:
    import cPickle as pickle
except:
    import pickle
import nltk

import util

MIN_SUFFIX = 4
MAX_SUFFIX = 6
"""
morphit_path = "d:/Tecnica/CL/risorse/italiano/morph-it/morph-it.48/morph-it_048.txt"
morphit_filename = "morph-it_048.txt"
"""
from wip.settings import morphit_path, morphit_filename

class NltkLexicon(object):
    """An object representing a Lexicon"""

    def __init__(self, path='morph-it', use_defaultdict=False, pickle_stream=None, pickle_string=None, lexicon_dict=None):
        # initialize the lexicon data
        self.lemma_dict = {}
        self.tag_dict = {}
        self.suffix_dict = {}
        self.word_tag_dict = {}
        # save the constructor parameters
        self.path = path
        self.use_defaultdict = use_defaultdict
        if lexicon_dict:
            pass
        elif pickle_stream:
            # load the lexicon data from a pickle stream
            lexicon_dict = pickle.load(pickle_stream)
        elif path:
            # load the lexicon from a source file
            if path == 'morph-it':
                path = morphit_path
                """
                this_dir, this_filename = os.path.split(__file__)
                path = os.path.join(this_dir, 'data', morphit_filename)
                """
                self.path = path
            self.load_morphoit(path)
        elif pickle_string:
            # load the lexicon data from a pickle string, possibly a file upload
            lexicon_dict = pickle.loads(pickle_string)
        # if pickle_stream or pickle_string:
        if lexicon_dict:
            self.lemma_dict = lexicon_dict.get('lemma_dict', {})
            self.tag_dict = lexicon_dict.get('tag_dict', {})
            self.suffix_dict = lexicon_dict.get('suffix_dict', {})
            self.word_tag_dict = lexicon_dict.get('word_tag_dict', {})
        # defaultdicts are convenient but cannot be pickled !
        if self.use_defaultdict:
            self.lemma_dict = nltk.defaultdict(list)
            self.tag_dict = nltk.defaultdict(int)
            self.suffix_dict = nltk.defaultdict(lambda: nltk.defaultdict(int))
            self.word_tag_dict = nltk.defaultdict(lambda: nltk.defaultdict(int))

    def load_morphoit(self, path=None):
        """
        return dicts from a lexicon in the morph-it format
        """
        path = path or self.path
        # f = open(path,'r')
        f = codecs.open(path, 'r', 'latin-1')
        lines = f.readlines()
        f.close()
        self.lemma_dict.clear()
        self.tag_dict.clear()
        self.suffix_dict.clear()
        self.word_tag_dict.clear()
        n_entries = 0
        for line in lines:
            line = line.strip()
            if line:
                # entry = line.split()
                entry = line.split(u'\u0009') # entry has TAB delimited items
                n = len(entry)
                word = entry[0]
                if n > 1:
                    lemma = entry[1]
                else:
                    lemma = 'lemma?'
                if n > 2:
                    tags = entry[2]
                    if tags:
                        splitted_tags = tags.split(u':')
                        tag = splitted_tags[0]
                        if tag == u'SMI': # smile ?
                            continue
                    else:
                        tag = 'tag?'
                n_entries += 1
                if self.use_defaultdict:
                    self.lemma_dict[lemma].append(word)
                    self.tag_dict[tag] += 1
                    self.word_tag_dict[word][tag] += 1
                else:
                    words = self.lemma_dict.get(lemma, []); words.append(word); self.lemma_dict[lemma] = words
                    self.tag_dict[tag] = self.tag_dict.get(tag, 0) + 1
                    dict = self.word_tag_dict.get(word, {})
                    """ only occurrence in corpus will increment the counter !
                    dict[tag] = dict.get(tag, 0) + 1
                    """
                    if dict.get(tag, None) is None:
                        dict[tag] = 0
                    self.word_tag_dict[word] = dict
                length = len(word)
                reversed = util.reverse(word)
                max = min(length, MAX_SUFFIX)
                for i in range(MIN_SUFFIX, max):
                    suffix = reversed[:i]
                    if self.use_defaultdict:
                        self.suffix_dict[suffix][tag] += 1
                    else: # defaultdicts cannot be pickled !
                        dict = self.suffix_dict.get(suffix, {})
                        dict[tag] = dict.get(tag, 0) + 1
                        self.suffix_dict[suffix] = dict
        return len(lines), n_entries

    def enrich(self, lazy_corpus_loader, fileids=None):
        """ update counts in the word_tag_dict vocabulary """
        tag_dict = self.tag_dict
        word_tag_dict = self.word_tag_dict
        for word_tag in lazy_corpus_loader.tagged_words(fileids=fileids):
            word = word_tag[0]
            tag = word_tag[1]
            if not tag_dict.get(tag, None):
                raise KeyError, "Unknown pos-tag: %s" % tag
            tag_dict = word_tag_dict.get(word, {})
            tag_dict[tag] = tag_dict.get(tag, 0) + 1
            word_tag_dict[word] = tag_dict
        self.word_tag_dict = word_tag_dict

    def to_pickle(self, filter=[]):
        """ return as pickle in string  """
        if not filter:
            lexicon_dict = {
                'lemma_dict': self.lemma_dict,
                'tag_dict': self.tag_dict,
                'suffix_dict': self.suffix_dict,
                'word_tag_dict': self.word_tag_dict, }
        else:
            lexicon_dict = {}
            if 'lemma_dict' in filter:
                lexicon_dict['lemma_dict'] = self.lemma_dict
            if 'tag_dict' in filter:
                lexicon_dict['tag_dict'] = self.tag_dict
            if 'suffix_dict' in filter:
                lexicon_dict['suffix_dict'] = self.suffix_dict
            if 'word_tag_dict' in filter:
                lexicon_dict['word_tag_dict'] = self.word_tag_dict
        return pickle.dumps(lexicon_dict)

    def dump_pickle(self, path):
        """ save as a pickle in Plone file """
        plonefile = self.restrictedTraverse(path)
        if not plonefile:
            parent_folder = self.restrictedTraverse(path[:-1])
            id = path[-1]
            parent_folder.invokeFactory(portal_type='File', id=id)
            plonefile = getattr(parent_folder, id)
        out_stream = StringIO()
        pickle.dump(out_stream, self.lemma_dict)
        pickle.dump(out_stream, self.tag_dict)
        pickle.dump(out_stream, self.suffix_dict)
        pickle.dump(out_stream, self.word_tag_dict)
        plonefile.setFile(out_stream.read())

    def download_pickle(self, filename, context=None, filter=[]):
        """ save as a pickle in client file """
        request = context.REQUEST
        RESPONSE = request.RESPONSE
        RESPONSE.setHeader('Content-Type', 'text/plain; charset=utf-8')
        RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)
        return self.to_pickle(filter=filter)

    def get_tag_dict(self):
        """return the tag dict"""
        return self.tag_dict

    def get_lemma_dict(self):
        """return the lemma dict"""
        return self.lemma_dict

    def get_suffix_dict(self):
        """return the suffix dict"""
        return self.suffix_dict

    def get_word_tag_dict(self):
        """return the word-tag dict"""
        return self.word_tag_dict

    def get_ambiguous_words(self, sort_on=None):
        """return the words associated to multiple tags"""
        multis = [word for word in self.word_tag_dict.keys() if len(self.word_tag_dict[word]) > 1]
        if not sort_on:
            multis.sort()
        return multis

    def get_suffixes(self, sort_on=None):
        """list suffixes"""
        suffixes = self.suffix_dict.keys()
        if sort_on=='sum':
            suffixes.sort(lambda x, y: cmp(util.dict_sum(suffix_dict[y]), util.dict_sum(suffix_dict[x])))
        else:
            suffixes.sort()
        return suffixes

    def get_unambiguous_suffixes(self, sort_on=None):
        """return the suffixes associated with only one tag"""
        suffixes = self.suffix_dict.keys()
        monos = [suffix for suffix in suffixes if len(self.suffix_dict[suffix])==1]
        if sort_on=='sum':
            monos.sort(lambda x, y: cmp(dict_sum(suffix_dict[y]), dict_sum(suffix_dict[x])))
        else:
            monos.sort()
        return monos
