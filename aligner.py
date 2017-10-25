"""
see the NLTK translate package: http://www.nltk.org/api/nltk.translate.html
"""

import sys
import os
from collections import defaultdict
import re
"""
import dill # required to pickle lambda functions
import pickle
"""
from django.conf import settings
from nltk.translate import AlignedSent, Alignment, IBMModel
from nltk.translate.ibm2 import IBMModel2, Model2Counts
from nltk.translate.ibm3 import IBMModel3
from nltk.translate.gdfa import grow_diag_final_and
from wip.wip_nltk.tokenizers import NltkTokenizer
"""
from nltk.translate import IBMModel2
from django.conf import settings
from .models import Segment, Translation
"""

if (sys.version_info > (3, 0)):
    from io import StringIO
else:
    import StringIO

def tokenize(text, lowercasing=False, tokenizer=None):
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

def aer(alignment, reference):
    alignment_list = alignment.split()
    reference_list = reference.split()
    alignment_set = set(alignment_list)
    reference_set = set(reference_list)
    # return float(len(alignment_set.intersection(reference_set)))/len(alignment_list)
    return 2 * float(len(alignment_set.intersection(reference_set))) / (len(alignment_list)+len(reference_list))

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
        print (matches)

def symmetrize_alignments(srclen, trglen, e2f, f2e):
    """
    symmetrize forward and reverse alignments using the NLTK grow_diag_final_and algorithm
    """
    alignment = grow_diag_final_and(srclen, trglen, e2f, f2e)
    alignment = sorted(alignment, key=lambda x: (x[0], x[1]))
    return ' '.join(['-'.join([str(link[0]), str(link[1])]) for link in alignment])

def proxy_symmetrize_alignments(proxy, base_path=None):
    if not base_path:
        base_path = os.path.join(settings.BASE_DIR, 'sandbox') 
    proxy_code = '%s_%s' % (proxy.site.slug, proxy.language_id)
    source_filename = os.path.join(base_path, '%s_source.txt' % proxy_code)
    target_filename = os.path.join(base_path, '%s_target.txt' % proxy_code)
    links_filename_fwd = os.path.join(base_path, '%s_links_fwd.txt' % proxy_code)
    links_filename_rev = os.path.join(base_path, '%s_links_rev.txt' % proxy_code)
    links_sym_filename = os.path.join(base_path, '%s_links_sym.txt' % proxy_code)
    source_file =  open(source_filename, 'r')
    target_file =  open(target_filename, 'r')
    file_fwd = open(links_filename_fwd, 'r')
    file_rev = open(links_filename_rev, 'r')
    file_sym = open(links_sym_filename, 'w')

    n_source_sents, n_source_words = list(map(int, source_file.readline().split()))
    n_target_sents, n_target_words = list(map(int, target_file.readline().split()))
    assert (n_source_sents == n_target_sents)
    while n_source_sents:
        n_source_sents -= 1
        srclen = len(list(map(int, source_file.readline().split())))
        trglen = len(list(map(int, target_file.readline().split())))
        e2f = file_fwd.readline()
        f2e = file_rev.readline()
        alignment = symmetrize_alignments(srclen, trglen, e2f, f2e)
        file_sym.write('%s\n' % alignment)
    
    source_file.close()
    target_file.close()
    file_fwd.close()
    file_rev.close()
    file_sym.close()        

if (sys.version_info > (3, 0)):
    import eflomal
    
    # def proxy_eflomal_align(proxy, base_path=None, lowercasing=False, max_tokens=1000, max_fertility=100, translation_ids=None, use_know_links=False):
    def proxy_eflomal_align(proxy, base_path=None, lowercasing=False, max_tokens=1000, max_fertility=100, translation_ids=None, use_know_links=False, evaluate=False, test_set_module=2, verbose=False, debug=False):
        if not base_path:
            base_path = os.path.join(settings.BASE_DIR, 'sandbox') 
        proxy_code = '%s_%s' % (proxy.site.slug, proxy.language_id)
        tokenizer_1 = NltkTokenizer(language=proxy.site.language_id, lowercasing=lowercasing)
        tokenizer_2 = NltkTokenizer(language=proxy.language_id, lowercasing=lowercasing)
        tokenized_1 = StringIO()
        tokenized_2 = StringIO()
        known_links_filename_fwd = os.path.join(base_path, '%s_known_links_fwd.txt' % proxy_code)
        known_links_filename_rev = os.path.join(base_path, '%s_known_links_rev.txt' % proxy_code)
        known_links_fwd = known_links_rev = None
        if use_know_links:
            known_links_fwd = open(known_links_filename_fwd, 'w')
            known_links_rev = open(known_links_filename_rev, 'w')
            # proxy.export_translations(tokenized_1, outfile_2=tokenized_2, outfile_3=translation_ids, tokenizer_1=tokenizer_1, tokenizer_2=tokenizer_2, lowercasing=lowercasing, max_tokens=max_tokens, max_fertility=max_fertility, known_links_fwd=known_links_fwd, known_links_rev=known_links_rev)
            proxy.export_translations(tokenized_1, outfile_2=tokenized_2, outfile_3=translation_ids, tokenizer_1=tokenizer_1, tokenizer_2=tokenizer_2, lowercasing=lowercasing, max_tokens=max_tokens, max_fertility=max_fertility, known_links_fwd=known_links_fwd, known_links_rev=known_links_rev, evaluate=evaluate, test_set_module=test_set_module, verbose=verbose)
            known_links_fwd.close()
            known_links_rev.close()
        else:
            proxy.export_translations(tokenized_1, outfile_2=tokenized_2, outfile_3=translation_ids, tokenizer_1=tokenizer_1, tokenizer_2=tokenizer_2, lowercasing=lowercasing, max_tokens=max_tokens, max_fertility=max_fertility, verbose=verbose)
        tokenized_1.seek(0)
        tokenized_2.seek(0)
        sents_1, index_1 = eflomal.read_text(tokenized_1, lowercasing, 0, 0)
        sents_2, index_2 = eflomal.read_text(tokenized_2, lowercasing, 0, 0)
        rev_index_1 = dict((v,k) for k,v in index_1.items())
        rev_index_2 = dict((v,k) for k,v in index_2.items())
        source_filename = os.path.join(base_path, '%s_source.txt' % proxy_code)
        target_filename = os.path.join(base_path, '%s_target.txt' % proxy_code)
        scores_filename = os.path.join(base_path, '%s_scores.txt' % proxy_code)
        links_filename_fwd = os.path.join(base_path, '%s_links_fwd.txt' % proxy_code)
        links_filename_rev = os.path.join(base_path, '%s_links_rev.txt' % proxy_code)
        statistics_filename = os.path.join(base_path, '%s_stats.txt' % proxy_code)
        all_filename = os.path.join(base_path, '%s_all.txt' % proxy_code)

        source_file = open(source_filename, 'w')
        target_file = open(target_filename, 'w')
        eflomal.write_text(source_file, tuple(sents_1), len(index_1))
        source_file.close()
        eflomal.write_text(target_file, tuple(sents_2), len(index_2))
        target_file.close()
        if verbose:
            print (known_links_filename_fwd, known_links_filename_rev)
        if use_know_links:
            status = eflomal.align(source_filename, target_filename, scores_filename=scores_filename, links_filename_fwd=links_filename_fwd, links_filename_rev=links_filename_rev, statistics_filename=statistics_filename, quiet=not verbose, use_gdb=debug, fixed_links_filename_fwd=known_links_filename_fwd, fixed_links_filename_rev=known_links_filename_rev)
        else:
            status = eflomal.align(source_filename, target_filename, scores_filename=scores_filename, links_filename_fwd=links_filename_fwd, links_filename_rev=links_filename_rev, statistics_filename=statistics_filename, quiet=not verbose, use_gdb=debug)
        if verbose:
            print ('eflomal terminated with status', status)
        all_file =  open(all_filename, 'w', encoding="utf-8")
        score_file = open(scores_filename, 'r')
        file_fwd = open(links_filename_fwd, 'r')
        file_rev = open(links_filename_rev, 'r')
        n_sents = len(sents_1)
        i = 0
        while i<n_sents:
            score = score_file.readline()[:-1]
            source = ' '.join([rev_index_1[token] for token in sents_1[i]])
            target = ' '.join([rev_index_2[token] for token in sents_2[i]])
            links_fwd = file_fwd.readline()[:-1]
            links_rev = file_rev.readline()[:-1]
            all_file.write('(%s) (%s) [%s] [%s] %s\n' % (links_fwd, links_rev, source, target, score))
            i += 1
        all_file.close()
        score_file.close()
        file_fwd.close()
        file_rev.close()
        if verbose:
            print ('proxy_eflomal_align returns')

def split_alignment(alignment):
    """
    alignment: a symmetric alignment, in pharaoh text format
    fwd: an asymmetric alignment keeping only links whose right element is unique
    rev: an asymmetric alignment keeping only links whose left  element is unique
    """
    links = []
    lefts = []
    rights = []
    for link in alignment.split():
        left, right = link.split('-')
        if not left or not right:
            continue
        left = int(left)
        right = int(right)
        links.append([left, right])
        links.sort(key=lambda x: (x[0], x[1]))
        lefts.append(left)
        rights.append(right)
    fwd = []
    for link in links:
        if rights.count(link[1]) > 1:
            continue
        fwd.append(link)
    fwd = ' '.join(['-'.join([str(link[0]), str(link[1])]) for link in fwd])
    rev = []
    for link in links:
        if lefts.count(link[0]) > 1:
            continue
        rev.append(link)
    rev = ' '.join(['-'.join([str(link[0]), str(link[1])]) for link in rev])
    return fwd, rev

def merge_alignments(fwd, rev):        
    """
    very rough symmetrization alorithm
    fwd: an asymmetric forward alignment, in pharaoh text format
    rev: an asymmetric reverse alignment, in pharaoh text format
    alignment: a symmetrized alignment including all links without duplicates, in pharaoh text format
    """
    fwd = fwd.split()
    rev = rev.split()
    links = fwd
    for link in rev:
        if not link in links:
            links.append(link)
    alignment = []
    for link in links:
        left, right = link.split('-')
        left = int(left)
        right = int(right)
        alignment.append([left, right])
        alignment.sort(key=lambda x: (x[0], x[1]))
    return ' '.join(['-'.join([str(link[0]), str(link[1])]) for link in alignment])

def proxy_null_aligner_eval(proxy, translations, lowercasing=False):
    """
    compute the quality of a null evaluator applying in cascade
    unsymmetrizzation and symmetrizzation of a known alignment
    """
    tokenizer_1 = NltkTokenizer(language=proxy.site.language_id, lowercasing=lowercasing)
    tokenizer_2 = NltkTokenizer(language=proxy.language_id, lowercasing=lowercasing)
    aer_total = 0.0
    n_evaluated = 0
    for translation in translations:
        alignment = translation.alignment
        if not alignment:
            continue
        source_text = translation.segment.text
        target_text = translation.text
        srclen = len(tokenize(source_text, tokenizer=tokenizer_1))
        trglen = len(tokenize(target_text, tokenizer=tokenizer_2))
        fwd, rev = split_alignment(alignment)
        alignment = symmetrize_alignments(srclen, trglen, fwd, rev)
        aer_total += aer(alignment, translation.alignment)
        n_evaluated += 1
    return aer_total/n_evaluated
