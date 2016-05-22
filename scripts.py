# -*- coding: utf-8 -*-

import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

import os
import urllib2
from datetime import datetime
from collections import defaultdict
from django.shortcuts import get_object_or_404
from settings import DATA_ROOT, RESOURCES_ROOT
from models import Site, Webpage, PageVersion, Block, String, Txu, TxuSubject
from vocabularies import Language, Subject
from utils import string_checksum, normalize_string

def set_blocks_language(slug, dry=False):
    from wip.utils import guess_block_language
    site = Site.objects.get(slug=slug)
    blocks = Block.objects.filter(site=site, language__isnull=True)
    for block in blocks:
        code = guess_block_language(block)
        print block.id, code
        if code in ['en',] and not dry:
            block.language_id = code
            block.save()

migration = '2811'
health = '2841'
education = '3206'

IATE_path = os.path.join(DATA_ROOT, 'IATE')
LANGUAGES = ['it', 'en', 'es', 'fr',]
N_LANGUAGES = len(LANGUAGES)
filename_template = 'export_EN_ES_FR_IT_2016-02-16_All_Langs_Domain_%s.tbx'

# /Tecnica/OpenData/language/export_EN_IT_2016-02-16_All_Langs_Domain_32.tbx
def import_tbx(path='', base_path=IATE_path, filename=filename_template, sector='', dry=True, allow_subjects=[], provider='IATE'):
    if not path and not sector:
        return 'Please, specify a sector code'
    from xml.etree import ElementTree
    if not path and sector:
        filename = filename % sector
        path = os.path.join(base_path, filename)
    tree = ElementTree.parse(path)
    root = tree.getroot()
    print root.tag
    print root.find('martifHeader').find('fileDesc').find('sourceDesc').find('p').text
    entries = root.find('text').find('body').findall('termEntry')
    n_entries = len(entries)
    n_tigs = n_terms = n_strings = 0 
    for entry in entries:
        entry_id = entry.attrib['id']
        # print entry_id
        subjectfield = entry.find("descripGrp/descrip[@type='subjectField']").text
        subject_codes = subjectfield.split(',')
        subject_codes = [subject.strip() for subject in subject_codes]
        if allow_subjects:
            in_subjects = False
            for subject_code in subject_codes:
                if subject_code[:4] in allow_subjects:
                    in_subjects = True
                    break
            if not in_subjects:
                continue
        entry_dict = defaultdict(list)
        for langset in entry.findall('langSet'):
            language_code = langset.items()[0][1]
            tigs = langset.findall('tig')
            for tig in tigs:
                n_tigs += 1
                reliability = int(tig.find("descrip[@type='reliabilityCode']").text)
                if reliability < 3:
                    continue
                termtype = tig.find("termNote[@type='termType']").text
                if not termtype == 'fullForm':
                    continue
                term = tig.find('term')
                text = term.text
                if not text.lower() == text:
                    continue
                words = text.split()
                # if len(words) > 3:
                if len(words) > 10:
                    continue
                entry_dict[language_code].append([text, reliability])
        txus = Txu.objects.filter(provider=provider, entry_id=entry_id)
        if len(entry_dict) == N_LANGUAGES:
            if dry:
                sys.stdout.write('.')
            else:
                sys.stdout.write('.')
                txus = Txu.objects.filter(provider=provider, entry_id=entry_id)
                if txus:
                    txu = txus[0]
                else:                       
                    txu = Txu(provider=provider, entry_id=entry_id)
                    txu.save()
                    n_terms += 1
                for subject_code in subject_codes:
                    try:
                        subject = Subject.objects.get(code=subject_code)
                    except:
                        subject = Subject(code=subject_code)
                        subject.save()
                    try:
                        txu_subject = TxuSubject.objects.get(txu=txu, subject=subject)
                    except:
                        txu_subject = TxuSubject(txu=txu, subject=subject)
                        txu_subject.save()
                for language_code in LANGUAGES:
                    for text, reliability in entry_dict[language_code]:
                        strings = String.objects.filter(txu=txu, language_id=language_code, text=text)
                        if not strings:
                            string = String(txu=txu, language_id=language_code, text=text, reliability=reliability)
                            string.save()
                            n_strings += 1

    print n_entries, ' entries'
    print n_tigs, ' tigs'
    print n_terms, ' terms'
    print n_strings, ' strings'

def feed_txu_index():
    print datetime.now()
    codes = ['en', 'es', 'fr', 'it']
    txus = Txu.objects.all()
    n_entries = n_strings = 0
    for txu in txus:
        n_entries +=1
        strings = String.objects.filter(txu=txu)
        for string in strings:
            n_strings +=1
            code = string.language_id
            if code == 'en':
                txu.en = True
            elif code == 'es':
                txu.es = True
            elif code == 'fr':
                txu.fr = True
            elif code == 'it':
                txu.it = True
        txu.save()
    print n_entries, n_strings
    print datetime.now()

def test(request):
    var_dict = {}
    import_tbx(sector='32', dry=False)
    return render_to_response('homepage.html', var_dict, context_instance=RequestContext(request))

def import_invariants(filename, language, site):
    path = os.path.join(DATA_ROOT, filename)
    file = open(path, 'r')
    for line in file:
        line = line.strip()
        if line:
            string = String(txu=None, language=language, site=site, text=line, reliability=0, invariant=True)
            string.save()

# def export_segments():
def export_segments(site, source_code='it', target_code='it'):
    from wip.views import find_strings
    """
    source = Language.objects.get(code='it')
    target = Language.objects.get(code='en')
    strings = find_strings(source_languages=[source], target_languages=[target], translated=False)
    """
    source = Language.objects.get(code=source_code)
    target = Language.objects.get(code=target_code)
    strings = find_strings(site=site, source_languages=[source], target_languages=[target], translated=False)
    print strings.count()
    # file = open('alfa.txt', 'w')
    file = open('%s_alfa.txt' % site.slug, 'w')
    for s in strings:
      file.write(s.text + '\n')
    file.close()
    strings = strings.order_by('id')
    # file = open('time.txt', 'w')
    file = open('%s_time.txt' % site.slug, 'w')
    for s in strings:
      file.write(s.text + '\n')
    file.close()

import srx_segmenter
srx_filepath = os.path.join(RESOURCES_ROOT, 'it', 'segment.srx')
srx_rules = srx_segmenter.parse(srx_filepath)
italian_rules = srx_rules['Italian']
segmenter = srx_segmenter.SrxSegmenter(italian_rules)

def segment(s):
    return segmenter.extract(s)

def db_fix_italian_strings():
    ss = String.objects.filter(language_id='it', site_id=1)
    for s in ss:
      t = s.text
      t2 = normalize_string(t)
      if not t2 == t:
        print s.id, t, t2
        s.text = t2
        s.save()    

"""
example: fetch_page('scuolemigranti', '/osservatorio/', dry=True)
"""
def fetch_page(site_slug, path, extract_blocks=True, extract_segments=False, diff=False, dry=False):
    sites = Site.objects.filter(slug=site_slug)
    site = sites and sites[0] or None
    if not site:
        return 0, 0, 0, path
    return site.fetch_page(path, extract_blocks=extract_blocks, extract_segments=extract_segments, diff=diff, dry=dry)

"""
example: fix_pages_checksum('scuolemigranti', verbose=True)
"""
def fix_pages_checksum(site_slug, verbose=False):
    sites = Site.objects.filter(slug=site_slug)
    site = sites and sites[0] or None
    if not site:
        return 'no site found'
    versions = PageVersion.objects.filter(webpage__site=site).order_by('-time')
    n_updates = 0
    for version in versions:
        checksum = site.page_checksum(version.body)
        if not checksum == version.checksum:
            if verbose:
                print version.checksum, '->', checksum, version.webpage.path
            version.checksum = site.page_checksum(version.body)
            version.save()
            n_updates += 1
    return '%d updates on %d' % (n_updates, versions.count())

