"""
test of the grow_diag_final_and in module nltk.translate.gdfa
"""

import os
from nltk.translate.gdfa import grow_diag_final_and

def symmetrize_alignment(srclen, trglen, e2f, f2e):
    """
    symmetrize forward and reverse alignments using the NLTK grow_diag_final_and algorithm
    """
    alignment = grow_diag_final_and(srclen, trglen, e2f, f2e)
    alignment = sorted(alignment, key=lambda x: (x[0], x[1]))
    return ' '.join(['-'.join([str(link[0]), str(link[1])]) for link in alignment])

def symmetrize_alignments(base_path=''):
    if not base_path:
        base_path = os.path.dirname(os.path.abspath(__file__))
    source_filename = os.path.join(base_path, 'source.txt')
    target_filename = os.path.join(base_path, 'target.txt')
    links_filename_fwd = os.path.join(base_path, 'links_fwd.txt')
    links_filename_rev = os.path.join(base_path, 'links_rev.txt')
    links_filename_sym = os.path.join(base_path, 'links_sym.txt')
    source_file =  open(source_filename, 'r')
    target_file =  open(target_filename, 'r')
    file_fwd = open(links_filename_fwd, 'r')
    file_rev = open(links_filename_rev, 'r')
    file_sym = open(links_filename_sym, 'w')

    n_source_sents, n_source_words = list(map(int, source_file.readline().split()))
    n_target_sents, n_target_words = list(map(int, target_file.readline().split()))
    assert (n_source_sents == n_target_sents)
    while n_source_sents:
        n_source_sents -= 1
        srclen = len(list(map(int, source_file.readline().split())))
        trglen = len(list(map(int, target_file.readline().split())))
        e2f = file_fwd.readline()
        f2e = file_rev.readline()
        alignment = symmetrize_alignment(srclen, trglen, e2f, f2e)
        file_sym.write('%s\n' % alignment)
    
    source_file.close()
    target_file.close()
    file_fwd.close()
    file_rev.close()
    file_sym.close()        

symmetrize_alignments()
