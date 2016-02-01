import os
import codecs
import re
import nltk
from nltk.tree import Tree
import util

from wip.settings import RESOURCES_ROOT

class NltkChunker(object):
    """An object representing a chunker wizard"""

    def __init__(self, language=None, chunker=None, grammar=None):
        """ set language """
        self.language = language or u'it'
        self.chunker = chunker or u'link'
        self.grammar = grammar

    def main_chunker(self, tagged_tokens, simplify=True, chunk_tag=None):
        """ choose a chunker based on some parameters """
        tagged_tokens = self.disambiguate_tokens(tagged_tokens, simplify=simplify)
        if self.language == u'it' and self.chunker == u'link':
            chunked_tokens = self.link_chunker(tagged_tokens)
        else:
            chunked_tokens = []
        if chunk_tag:
            chunks = self.filter_chunks(chunked_tokens, chunk_tag)
            return chunks
        else:
            return chunked_tokens

    def link_chunker(self, tagged_tokens):
        """ compile and execute the chunk parser specified """
        if self.grammar:
            grammar = self.grammar
        else:
            """
            this_dir, this_filename = os.path.split(__file__)
            grammar_path = os.path.join(this_dir, 'data', '%s_chunk_grammar.txt' % self.language)
            """
            grammar_path = os.path.join(RESOURCES_ROOT, '%s_chunk_grammar.txt' % self.language)
            f = codecs.open(grammar_path, 'r', 'unicode_escape')
            grammar = f.read()
            f.close()
        cp = nltk.RegexpParser(grammar)
        return cp.parse(tagged_tokens)

    def disambiguate_tokens(self, tagged_tokens, simplify=False):
        """ return a list of couples (token, tag) """
        out = []
        for item in tagged_tokens:
            token = item[0]
            tag = item[1]
            if tag and isinstance(tag, (tuple, list)):
                tag = tag[0]
            if simplify:
                tag = tag.split(u'-')[0]
            out.append((token, tag))
        return out         

    def filter_chunks(self, chunked_tokens, chunk_tag=None):
        """ return a list of couples (token, tag) """
        chunks = []
        for item in chunked_tokens:
            # if isinstance(item, (tuple, list)) and item[0]==chunk_tag:
            if isinstance(item, Tree):
                # chunks.append(item[1:])
                chunks.append(item)
        return chunks
