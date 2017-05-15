"""
see the NLTK translate package: http://www.nltk.org/api/nltk.translate.html
"""

import os
import re
import dill # required to pickle lambda functions
import pickle
from nltk.translate import AlignedSent, Alignment
from nltk.translate import IBMModel2
from django.conf import settings
from .models import Segment, Translation

def tokenize(text, lowercasing=False, tokenizer=None):
    # return re.split("[ |\']*", text)
    if tokenizer:
        return tokenizer.tokenize(text)
    if lowercasing:
        text = text.lower()
    tokens = re.split("[ |\.\,\;\:\'\"]*", text)
    return tokens

def make_bitext(proxy, lowercasing=False, use_invariant=False, tokenizer=None):
    site = proxy.site
    target_language = proxy.language
    segments = Segment.objects.filter(site=site)
    bitext = []
    for segment in segments:
        segment_text = segment.text
        source_tokens = tokenize(segment_text, tokenizer=tokenizer, lowercasing=lowercasing)
        if segment.is_invariant:
            if use_invariant:
                alignment = Alignment([(i, i) for i in range(len(source_tokens))])
                bitext.append(AlignedSent(source_tokens, source_tokens, alignment))
        else:
            translations = Translation.objects.filter(segment=segment, language=target_language)
            for translation in translations:
                translation_text = translation.text
                target_tokens = tokenize(translation_text, tokenizer=tokenizer, lowercasing=lowercasing)
                bitext.append(AlignedSent(source_tokens, target_tokens))
    return bitext

def get_train_aligner(proxy, ibm_model=2, train=False, iterations=5, tokenizer=None, lowercasing=False, use_invariant=False):
    bitext = make_bitext(proxy, lowercasing=lowercasing, tokenizer=tokenizer, use_invariant=use_invariant)
    site = proxy.site
    aligner_name = 'align_%s_%s%s.pickle' % (site.slug, site.language_id, proxy.language_id)
    aligner_path = os.path.join(settings.CACHE_ROOT, aligner_name)
    if not train:
        if os.path.isfile(aligner_path):
            f = open(aligner_path, 'rb')
            aligner = pickle.load(f)
            f.close()
            return aligner
    if ibm_model == 3:
        from nltk.translate import IBMModel3
        aligner = IBMModel3(bitext, iterations)
    else:
        aligner = IBMModel2(bitext, iterations)
        f = open(aligner_path, 'wb')
        pickle.dump(aligner, f, pickle.HIGHEST_PROTOCOL)
        f.close()
    return aligner

def best_alignment(aligner, source_text, target_text, tokenizer=None, lowercasing=False, tokens=False):
    source_tokens = tokenize(source_text, tokenizer=tokenizer, lowercasing=lowercasing)
    target_tokens = tokenize(target_text, tokenizer=tokenizer, lowercasing=lowercasing)
    sentence_pair = AlignedSent(source_tokens, target_tokens)
    alignment_info = aligner.best_model2_alignment(sentence_pair)
    alignment = alignment_info.zero_indexed_alignment()
    if not tokens:
        return alignment
    bisentence = []
    for i, j in alignment:
        biword = [source_tokens[i]]
        if j:
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
