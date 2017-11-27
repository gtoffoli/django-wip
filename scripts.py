# -*- coding: utf-8 -*-

import os
import sys
"""
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)
"""

# import urllib2
from datetime import datetime
from collections import defaultdict
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
# from settings import DATA_ROOT, RESOURCES_ROOT, SITES_ROOT
from .models import Site, Proxy, Webpage, PageVersion, Block, TranslatedBlock
from .models import String, Txu, TxuSubject
from .models import UserRole, Segment, Translation, SEGMENT, FRAGMENT
from .models import OWNER, MANAGER, LINGUIST, REVISOR, TRANSLATOR, GUEST
from .models import MANUAL
from .vocabularies import Language, Subject
from .utils import string_checksum, normalize_string
from wip import srx_segmenter

def set_blocks_language(slug, dry=False):
    from wip.utils import guess_block_language
    site = Site.objects.get(slug=slug)
    blocks = Block.objects.filter(site=site, language__isnull=True)
    for block in blocks:
        code = guess_block_language(block)
        print (block.id, code)
        if code in ['en',] and not dry:
            block.language_id = code
            block.save()

migration = '2811'
health = '2841'
education = '3206'

IATE_path = os.path.join(settings.DATA_ROOT, 'IATE')
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
    print (root.tag)
    print (root.find('martifHeader').find('fileDesc').find('sourceDesc').find('p').text)
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

    print (n_entries, ' entries')
    print (n_tigs, ' tigs')
    print (n_terms, ' terms')
    print (n_strings, ' strings')

def feed_txu_index():
    print (datetime.now())
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
    print (n_entries, n_strings)
    print (datetime.now())

def test(request):
    var_dict = {}
    import_tbx(sector='32', dry=False)
    return render_to_response('homepage.html', var_dict, context_instance=RequestContext(request))

def import_invariants(filename, language, site):
    path = os.path.join(settings.DATA_ROOT, filename)
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
    print (strings.count())
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

srx_filepath = os.path.join(settings.RESOURCES_ROOT, 'it', 'segment.srx')
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
        print (s.id, t, t2)
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
                print (version.checksum, '->', checksum, version.webpage.path)
            version.checksum = site.page_checksum(version.body)
            version.save()
            n_updates += 1
    return '%d updates on %d' % (n_updates, versions.count())

def test_segmenter(site, s, verbose=False):
    segmenter = site.make_segmenter()
    segments = segmenter.extract(s, verbose=verbose)
    return segments

# from http://www.jeffsidea.com/2016/06/using-scrapy-from-a-script-or-celery-task/
from scrapy.spiders import Spider
from scrapy.settings import Settings
# from scrapyscript import Job, Processor

class PythonSpider(Spider):
    name = 'myspider'
    start_urls = ['http://www.python.org']

    def parse(self, response):
        title = response.xpath('//title/text()').extract()
        if self.payload:
            mantra = self.payload.get('mantra', None)
        else:
            mantra = None
        return {'title': title,
                'mantra': mantra}
"""
def jeffs_run():
    spider = PythonSpider()
    
    settings = Settings()
    settings.set('USER_AGENT',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.86 Safari/537.36')
    
    basicjob = Job(spider)
    jobwithdata = Job(spider,
                      payload={'mantra': 'Simple is better than complex.'})  # availabe in spider as self.payload
    
    Processor(settings=settings).run([basicjob, jobwithdata])
"""
def migrate_segments():
    admin = User.objects.get(username='admin')
    # for s in String.objects.filter(language_id='it', string_type__in=[SEGMENT, FRAGMENT]).exclude(site=None):
    for s in String.objects.filter(language_id='it', string_type__in=[SEGMENT, FRAGMENT]):
        site = None
        if s.site:
            site = s.site
        elif s.txu and s.txu.provider:
            txu = s.txu
            provider = txu.provider
            try:
                site = Site.objects.get(name=provider)
            except:
                pass
        if not site:
            continue
        segment = Segment(site=site, language_id='it', text=s.text, is_fragment=s.string_type==FRAGMENT, is_invariant=s.invariant)
        segment.save()
        if s.created:
            segment.created = s.created
            segment.save()
        txu = s.txu
        if not txu:
            s.delete()
            continue
        for t in String.objects.filter(site=site, txu=txu, string_type__in=[SEGMENT, FRAGMENT]).exclude(language_id='it'):
            user_role, created = UserRole.objects.get_or_create(user=admin, source_language=s.language, target_language=t.language, level=3, site=site, role_type=OWNER)
            translation = Translation(segment=segment, language=t.language, text=t.text, translation_type=MANUAL, user_role=user_role)
            translation.save()
            if t.created:
                translation.created = t.created
                translation.save()
            t.delete()
        s.delete()
        txu.delete()

def create_filepaths():
    if not os.path.isdir(settings.SITES_ROOT):
        os.mkdir(settings.SITES_ROOT)
    sites = Site.objects.all()
    for site in sites:
        if not os.path.isdir(site.get_filepath()):
            os.mkdir(site.get_filepath())
        for proxy in Proxy.objects.filter(site=site):
            if not os.path.isdir(proxy.get_filepath()):
                os.mkdir(proxy.get_filepath())

from .aligner import split_alignment, merge_alignments
def proxy_unsymmetrize_alignment(proxy, alignment_type=MANUAL):
    base_path = os.path.join(settings.BASE_DIR, 'sandbox') 
    proxy_code = '%s_%s' % (proxy.site.slug, proxy.language_id)
    filename = os.path.join(base_path, '%s_unsymmetrize.txt' % proxy_code)
    out_file =  open(filename, 'w')
    segments = Segment.objects.filter(site=proxy.site)
    for segment in segments:
        segment_text = segment.text
        translations = Translation.objects.filter(segment=segment, language=proxy.language)
        if alignment_type:
            translations = translations.filter(alignment_type=alignment_type)
        for translation in translations:
            translation_text = translation.text
            alignment = translation.alignment
            if alignment:
                print (alignment)
                fwd, rev = split_alignment(alignment)
                both = merge_alignments(fwd, rev)
                out_file.write('%s\n' % segment_text)
                out_file.write('%s\n' % translation_text)
                out_file.write('%s\n' % alignment)
                out_file.write('%s\n' % fwd)
                out_file.write('%s\n' % rev)
                out_file.write('%s\n' % both)
    out_file.close()

def fix_segment_translations(site, target):
    """ add to segments translations derived by those of similar segments
        ending by '.' or ';' or ':', possibly preceded by a space """
    segments = Segment.objects.filter(site=site, language=site.language, is_invariant=False).exclude(segment_translation__language=target).distinct()
    i = j = 0
    for segment in segments:
        text = segment.text
        l1 = len(segment.text)
        if l1 > 10:
            pk = segment.pk
            likes = Segment.objects.filter(site=site, language=site.language, is_invariant=False, segment_translation__language=target, text__istartswith=text[:-3]).exclude(id=pk).distinct()
            if not likes:
                continue
            i += 1
            for like in likes:
                l2 = len(like.text)
                if (l1>l2) and (l1-l2 <= 2):
                    diff = text[l2:].strip()
                    if len(diff)==1 and diff in ['.',';',':']:
                        translation = Translation.objects.filter(segment=like, language=target).order_by('-timestamp')[0]
                        translation.id = None
                        translation.segment = segment
                        translation.text = translation.text+diff
                        translation.save()
                        j += 1
    return (j, 'translations added')

def fix_translated_blocks():
    translated_blocks = TranslatedBlock.objects.all()
    n_auto = n_man = 0
    for tb in translated_blocks:
        body = tb.body
        c_auto = body.count('tx auto')
        if c_auto:
            body = body.replace('tx auto', 'tx="auto"')
            n_auto += c_auto
        c_man = body.count('tx man')
        if c_man:
            body = body.replace('tx man', 'tx="man"')
            n_man += c_man
        if c_auto or c_man:
            tb.body = body
            tb.save()
    return n_auto, n_man

