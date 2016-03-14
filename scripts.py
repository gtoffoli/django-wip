# -*- coding: utf-8 -*-

import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

import os
from collections import defaultdict
from settings import DATA_ROOT
from models import Site, Block, String, Txu, TxuSubject
from vocabularies import Language, Subject

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


def test(request):
    var_dict = {}
    import_tbx(sector='32', dry=False)
    return render_to_response('homepage.html', var_dict, context_instance=RequestContext(request))
