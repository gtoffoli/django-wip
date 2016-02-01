# Natural Language Toolkit: WaCKy Corpus Reader
#
# Copyright (C) 2001-2010 NLTK Project
# Author: Giovanni Toffoli <toffoli@uni.net>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A reader for POS-tagged corpora developed inside the WaCKy project.
Look for info at http://wacky.sslmit.unibo.it/doku.php
"""       

import os

import nltk.corpus
from nltk.corpus.util import LazyCorpusLoader
from nltk.corpus.reader.api import CorpusReader
from nltk.corpus.reader.util import StreamBackedCorpusView, concat
from nltk.corpus.reader.tagged import TaggedCorpusReader, TaggedCorpusView

class NltkCorpus(object):
    """An object representing a corpus or a subset of its files"""

    def __init__(self, corpus_loader=None, language=None, fileids=[], corpus_dict={}):
        # initialize the corpus data
        self.corpus_loader = corpus_loader
        self.fileids = fileids
        self.language = language
        self.n_sents = 0
        self.n_words = 0
        self.urls = []
        self.tag_dict = {}
        self.word_tag_dict = {}
        # recover the corpus data from corpus_dict if non empty
        if corpus_dict:
            self.urls = corpus_dict.get('urls', [])
            self.tag_dict = corpus_dict.get('tag_dict', {})
            self.word_tag_dict = corpus_dict.get('word_tag_dict', {})
            if corpus_dict.get('language', None):
                self.language = corpus_dict['language']
            return

    def load_tagged_words(self, simplify_tags=None, view_from=0, view_to=-1):
        """ read the corpus files, count sentences and words
            and build some dicts concerning words and tags """
        if not self.fileids or not self.corpus_loader:
            return
        # for word_tag in self.corpus_loader.tagged_words(fileids=self.fileids):
        if self.n_words: # already done ?
            return
        n_sents = 0
        n_words = 0
        tag_dict = {}
        word_tag_dict = {}
        # self.tagged_sents = self.corpus_loader.tagged_sents(fileids=self.fileids, simplify_tags=simplify_tags, view_from=view_from, view_to=view_to)
        func = self.corpus_loader.tagged_sents
        varnames = func.func_code.co_varnames
        kwargs = {}
        if 'fileids' in varnames:
            kwargs['fileids'] = self.fileids
        if 'simplify_tags' in varnames:
            kwargs['simplify_tags'] = simplify_tags
        if 'view_from' in varnames and 'view_to' in varnames:
            kwargs['view_from'] = view_from
            kwargs['view_to'] = view_to
        self.tagged_sents = self.corpus_loader.tagged_sents(**kwargs)
        for tagged_sent in self.tagged_sents:
            n_sents += 1
            for word_tag in tagged_sent:
                n_words += 1
                word = word_tag[0]
                tag = word_tag[1]
                tag_dict[tag] = tag_dict.get(tag, 0) + 1
                word_dict = word_tag_dict.get(word, {})
                word_dict[tag] = word_dict.get(tag, 0) + 1
                word_tag_dict[word] = word_dict
        self.tag_dict = tag_dict
        self.word_tag_dict = word_tag_dict
        self.n_sents = n_sents
        self.n_words = n_words

    def get_urls(self):
        """return the urls of the texts in the corpus or file subset"""
        return self.urls

    def get_tag_dict(self):
        """return the tag dict"""
        return self.tag_dict

    def get_word_tag_dict(self):
        """return the word-tag dict"""
        return self.word_tag_dict

def read_wacky_text_block(stream):
    """
    read the lines contained in a <text> element
    including the start and end tags of the element
    """
    lines = []
    while True:
        line = stream.readline()
        # End of file:
        if not line:
            return lines
        # Start of <text> element
        if line.startswith('<text'):
            lines.append(line)
            while True:
                line = stream.readline()
                if not line:
                    return lines
                lines.append(line)
                # End of <text> element
                if line.startswith('</text>'):
                    return lines

def simplify_wacky_tag(tag):
    """ see module nltk.tag.simplify.py """
    if u':' in tag:
        tag = tag.split(u':')[0]
    return tag

class WackyCorpusReader(TaggedCorpusReader):
    """
    Reader for part-of-speech tagged and lemmatized corpora
    developed inside the WaCKy project. Corpora are encoded 
    in the 'pseudo-XML' format described in the paper,
    using only the XML tags "corpus", "text" and "s" (sentence).
    """
    def __init__(self, root, fileids, 
                 para_block_reader=read_wacky_text_block,
                 encoding=None,
                 tag_mapping_function=simplify_wacky_tag):
        """
        Construct a new Wacky Corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = WackyCorpusReader(root, '.*')
        
        @param root: The root directory for this corpus.
        @param fileids: A list or regexp specifying the fileids in this corpus.
        """
        CorpusReader.__init__(self, root, fileids, encoding=encoding)
        self._para_block_reader = para_block_reader
        self._tag_mapping_function = tag_mapping_function

    def words(self, fileids=None):
        """
        @return: the given file(s) as a list of words
            and punctuation symbols.
        @rtype: C{list} of C{str}
        """
        return concat([WackyCorpusView(fileid, enc,
                                        False, False, False,
                                        self._para_block_reader,
                                        None)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def sents(self, fileids=None):
        """
        @return: the given file(s) as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        @rtype: C{list} of (C{list} of C{str})
        """
        return concat([WackyCorpusView(fileid, enc,
                                        False, True, False,
                                        self._para_block_reader,
                                        None)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def paras(self, fileids=None):
        """
        @return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        @rtype: C{list} of (C{list} of (C{list} of C{str}))
        """
        return concat([WackyCorpusView(fileid, enc,
                                        False, True, True,
                                        self._para_block_reader,
                                        None)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def tagged_words(self, fileids=None, simplify_tags=False, view_from=0, view_to=-1):
        """
        @return: the given file(s) as a list of tagged
            words and punctuation symbols, encoded as tuples
            C{(word,tag)}.
        @rtype: C{list} of C{(str,str)}
        """
        if simplify_tags:
            tag_mapping_function = self._tag_mapping_function
        else:
            tag_mapping_function = None
        return concat([WackyCorpusView(fileid, enc,
                                        True, False, False,
                                        self._para_block_reader,
                                        tag_mapping_function)
                       for (fileid, enc) in self.abspaths(fileids, True)])[view_from:view_to]

    def tagged_sents(self, fileids=None, simplify_tags=False, view_from=0, view_to=-1):
        """
        @return: the given file(s) as a list of
            sentences, each encoded as a list of C{(word,tag)} tuples.
            
        @rtype: C{list} of (C{list} of C{(str,str)})
        """
        if simplify_tags:
            tag_mapping_function = self._tag_mapping_function
        else:
            tag_mapping_function = None
        return concat([WackyCorpusView(fileid, enc,
                                        True, True, False,
                                        self._para_block_reader,
                                        tag_mapping_function)
                       for (fileid, enc) in self.abspaths(fileids, True)])[view_from:view_to]

    def tagged_paras(self, fileids=None, simplify_tags=False):
        """
        @return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of C{(word,tag)} tuples.
        @rtype: C{list} of (C{list} of (C{list} of C{(str,str)}))
        """
        if simplify_tags:
            tag_mapping_function = self._tag_mapping_function
        else:
            tag_mapping_function = None
        return concat([WackyCorpusView(fileid, enc,
                                        True, True, True,
                                        self._para_block_reader,
                                        tag_mapping_function)
                       for (fileid, enc) in self.abspaths(fileids, True)])

class WackyCorpusView(TaggedCorpusView):
    """
    A specialized corpus view for tagged documents in WaCKy format.
    It can be customized via flags to divide the tagged corpus documents up by
    sentence or text, and to include or omit part of speech tags.
    In order to reuse classes and methods from superclasses,
    "texts" are assimilated to "paras"!
    C{WackyCorpusView} objects are typically created by
    L{WackyCorpusReader} (not directly by nltk users).
    """
    # def __init__(self, corpus_file, encoding, tagged,
    def __init__(self, corpus_file, encoding, tagged,
                 group_by_sent, group_by_para,
                 para_block_reader, tag_mapping_function=None):
        # encoding = 'utf-8'
        encoding = 'latin-1'
        self._tagged = tagged
        self._group_by_sent = group_by_sent
        self._group_by_para = group_by_para
        self._para_block_reader = para_block_reader
        self._tag_mapping_function = tag_mapping_function
        StreamBackedCorpusView.__init__(self, corpus_file, encoding=encoding)
        print 'WackyCorpusView: encoding = %s' % encoding
        
    def read_block(self, stream):
        """Reads one paragraph at a time."""
        block = []
        for line in self._para_block_reader(stream):
            if not line:
                continue
            line = line.strip()
            if not line:
                continue
            if line.startswith('<text'):
                para = []
            elif line.startswith('</text>'):
                if self._group_by_para:
                    block.append(para)
                else:
                    block.extend(para)
            elif line.startswith('<s>'):
                s = []
            elif line.startswith('</s>'):
                if self._group_by_sent:
                    para.append(s)
                else:
                    para.extend(s)
            else:
                # tuple = line.split('\t')
                tuple = line.split('\t') # tuple has TAB delimited items
                n = len(tuple)
                word = tuple[0]
                if n > 1:
                    tag = tuple[1]
                else:
                    tag = 'tag?'
                if n > 2:
                    lemma = tuple[2]
                if tag and self._tag_mapping_function:
                    tag = self._tag_mapping_function(tag)
                if self._tagged:
                    s.append((word, tag))
                else:
                    s.append(word)
        return block

nltk.corpus.itwac = LazyCorpusLoader('itwac', WackyCorpusReader, r'.*\.xml')
try:
    nltk.corpus.enwac = LazyCorpusLoader('enwac', WackyCorpusReader, r'.*\.xml')
except:
    pass
try:
    nltk.corpus.dewac = LazyCorpusLoader('dewac', WackyCorpusReader, r'.*\.xml')
except:
    pass

def import_europarl_raw():
    import nltk.corpus.europarl_raw
    root = nltk.corpus
    module = nltk.corpus.europarl_raw
    for name in dir(module):
        object = getattr(module, name)
        if isinstance(object, LazyCorpusLoader):
            setattr(root, 'europarl_raw_%s' % name, object)

import_europarl_raw()

def nltk_corpora(context, module=None):
    """
    return a dict of the corpora in nltk_data
    """
    if not module:
        module = nltk.corpus
    names = dir(module)
    # print names
    dict = {}
    for name in names:
        object = getattr(module, name)
        if isinstance(object, LazyCorpusLoader) or isinstance(object, CorpusReader):
            # print name, repr(object)
            dict[name] = object
    return dict

def nltk_corpus_ids(context, module=None):
    """
    return a sorted list of the names of the corpora
    in nltk_data and in the link.nltk configuration
    """
    dict = nltk_corpora(context, module=module)
    corpus_ids = dict.keys()
    corpus_ids.sort()
    return corpus_ids
