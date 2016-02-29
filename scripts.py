# -*- coding: utf-8 -*-

import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

import os
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

def no_empty(sublists):
    for sublist in sublists:
        if not sublist:
            return False
    return True

def all_equal(terms):
    first_text = terms[0][0]
    for term in terms[1:]:
        if not term[0] == first_text:
            return False
    return True

migration = '2811'
health = '2841'
education = '3206'

IATE_path = os.path.join(DATA_ROOT, 'IATE')
"""
allow_subjects = (education,)
allow_subjects = (migration,)
allow_subjects = (health,)
"""
LANGUAGES = ['it', 'en', 'es', 'fr',]
SOURCE_LANGUAGE = 'it'
TARGET_LANGUAGES = ['en', 'es', 'fr',]
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
    n_tigs = n_terms = 0 
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
        entry_dict = {}
        for langset in entry.findall('langSet'):
            language_code = langset.items()[0][1]
            # print entry_id, language_code
            entry_dict[language_code] = []
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
                if len(words) > 3:
                    continue
                # entry_dict[language_code].append(text)
                entry_dict[language_code].append([text, reliability])
        dict_values = entry_dict.values()
        # print dict_values
        terms = [term for sublist in dict_values for term in sublist]
        # terms = [term for term in sublist for sublist in dict_values]
        # if no_empty(dict_values) and len(terms) == N_LANGUAGES and not all_equal(terms):
        # if len(terms) == N_LANGUAGES:
        if no_empty(dict_values) and len(terms) == N_LANGUAGES:
            # print N_LANGUAGES, terms
            n_terms += 1
            if dry:
                # print entry_id, ', '.join([entry_dict[language_code][0][0] for language_code in LANGUAGES])
                sys.stdout.write('.')
            else:
                # print entry_id
                sys.stdout.write('.')
                source_term = entry_dict['it'][0]
                text = source_term[0]
                reliability = source_term[1]
                try:
                    source_string = String.objects.get(text=text, language_id='it')
                except:
                    source_string = String(text=text, language_id='it')
                    source_string.save()
                for language_code in TARGET_LANGUAGES:
                    target_term = entry_dict[language_code][0]
                    text = target_term[0]
                    # print text
                    reliability = target_term[1]
                    try:
                        target_string = String.objects.get(text=text, language_id=language_code)
                    except:
                        # print text
                        target_string = String(text=text, language_id=language_code)
                        target_string.save()
                    txus = Txu.objects.filter(provider=provider, entry_id=entry_id, target=target_string)
                    if txus:
                        continue                        
                    # txu = Txu(source=source_string, target=target_string, provider=provider, entry_id=entry_id, reliability=reliability)
                    txu = Txu(source=source_string, target=target_string, source_code='it', target_code=language_code, provider=provider, entry_id=entry_id, reliability=reliability)
                    txu.save()
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
                        
    print n_entries, ' entries'
    print n_tigs, ' tigs'
    print n_terms, ' terms'

def fix_txus():
    txus=Txu.objects.all()
    for txu in txus:
        txu.source_code = txu.source.language_id
        txu.target_code = txu.target.language_id
        txu.save()
    print txus.count()

def test(request):
    var_dict = {}
    import_tbx(sector='32', dry=False)
    return render_to_response('homepage.html', var_dict, context_instance=RequestContext(request))