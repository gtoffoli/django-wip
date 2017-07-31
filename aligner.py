"""
see the NLTK translate package: http://www.nltk.org/api/nltk.translate.html
"""

from collections import defaultdict
import re
"""
import dill # required to pickle lambda functions
import pickle
"""
from nltk.translate import AlignedSent, Alignment, IBMModel
from nltk.translate.ibm2 import IBMModel2, Model2Counts
from nltk.translate.ibm3 import IBMModel3
from wip.wip_nltk.tokenizers import NltkTokenizer
"""
from nltk.translate import IBMModel2
from django.conf import settings
from .models import Segment, Translation
"""

def tokenize(text, lowercasing=False, tokenizer=None):
    # return re.split("[ |\']*", text)
    if tokenizer:
        return tokenizer.tokenize(text)
    if lowercasing:
        text = text.lower()
    tokens = re.split("[ |\.\,\;\:\'\"]*", text)
    return tokens

class BitextBuilder(object):

    def __init__(self, lowercasing=False, tokenizer=None, build_tables=False):
        self.bitext = []
        if not tokenizer:
            tokenizer = NltkTokenizer(lowercasing=lowercasing)
        self.tokenizer = tokenizer
        self.build_tables = build_tables
        if build_tables:
            self.translation_table = defaultdict(
                                       lambda: defaultdict(int))
            self.alignment_table = defaultdict(
                                       lambda: defaultdict(lambda: defaultdict(
                                       lambda: defaultdict(int))))

    def append(self, source, target, alignment=None):
        mots = type(source) is list and source or tokenize(source, tokenizer=self.tokenizer)
        words = type(target) is list and target or tokenize(target, tokenizer=self.tokenizer)
        self.total = 0
        if self.build_tables and alignment:
            alignment = Alignment.fromstring(alignment)
            self.bitext.append(AlignedSent(mots, words, alignment=alignment))
            l = len(mots)
            m = len(words)
            for i, j in alignment:
                mot = mots[i]
                word = words[j]
                self.translation_table[word][mot] += 1
                # self.alignment_table[i][j][l][m] += 1
                self.alignment_table[i+1][j+1][l][m] += 1
                self.total += 1
        else:
            self.bitext.append(AlignedSent(mots, words))

    def get_bitext(self):
        return self.bitext

    def get_translation_table(self):
        translation_table = defaultdict(
            lambda: defaultdict(lambda: IBMModel.MIN_PROB))
        for word in self.translation_table.keys():
            mots = self.translation_table[word].keys()
            total = 0
            for mot in mots:
                total += self.translation_table[word][mot]
            for mot in mots:
                translation_table[word][mot] = float(self.translation_table[word][mot])/total
        return translation_table

    def get_alignment_table(self):
        alignment_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(
            lambda: defaultdict(lambda: IBMModel.MIN_PROB))))
        # return alignment_table
        total = self.total
        i_s = self.alignment_table.keys()
        for i in i_s:
            j_s = self.alignment_table[i].keys()
            for j in j_s:
                l_s = self.alignment_table[i][j].keys()
                for l in l_s:
                    m_s = self.alignment_table[i][j][l].keys()
                    for m in m_s:
                        alignment_table[i][j][l][m] = float(self.alignment_table[i][j][l][m])/total
        return alignment_table
 
def best_alignment(aligner, source_tokens=[], target_tokens=[], tokens=False, aligned_sent=None):
    if aligned_sent:
        source_tokens = aligned_sent.words
        target_tokens = aligned_sent.mots
    elif source_tokens and target_tokens:
        aligned_sent = AlignedSent(source_tokens, target_tokens)
    else:
        return None
    if type(aligner) is IBMModel3:
        sampled_alignments, alignment_info = aligner.sample(aligned_sent)
    else:
        alignment_info = aligner.best_model2_alignment(aligned_sent)
    alignment = alignment_info.zero_indexed_alignment()
    if not tokens:
        return alignment
    bisentence = []
    for i, j in alignment:
        biword = [source_tokens[i]]
        if j is not None:
            biword.append(target_tokens[j])
        bisentence.append(biword)
    return bisentence

def print_aligned(bitext, start=0, n=10):
    for aligned_sent in bitext[start:n]:
        words = aligned_sent.words
        mots = aligned_sent.mots
        matches = []
        for i, j in aligned_sent.alignment:
            match = [words[i]]
            if j:
                match.append(mots[j])
            matches.append(match)
        print matches
