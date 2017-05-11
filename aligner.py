import re
from nltk.translate import AlignedSent
from .models import Segment, Translation

def make_bitext(proxy):
    site = proxy.site
    target_language = proxy.language
    segments = Segment.objects.filter(site=site)
    bitext = []
    for segment in segments:
        translations = Translation.objects.filter(segment=segment, language=target_language)
        for translation in translations:
            source_tokens = re.split("[ |\']*", segment.text)
            target_tokens = re.split("[ |\']*", translation.text)
            bitext.append(AlignedSent(source_tokens, target_tokens))
    return bitext

def train_aligner(proxy, ibm_model=2, iterations=5):
    bitext = make_bitext(proxy)
    if ibm_model == 3:
        from nltk.translate import IBMModel3
        aligner = IBMModel3(bitext, iterations)
    else:
        from nltk.translate import IBMModel2
        aligner = IBMModel2(bitext, iterations)
    return bitext, aligner

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
