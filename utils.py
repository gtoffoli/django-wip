# -*- coding: utf-8 -*-

import os
import sys

import string
import urllib
if (sys.version_info > (3, 0)):
    from io import StringIO
    from html.entities import entitydefs as htmlentitydefs
    from html.entities import name2codepoint
    import urllib.parse
    from urllib.parse import urlencode 

    def unichr(n):
        return chr(n)
else:
    import StringIO
    import htmlentitydefs
    from htmlentitydefs import name2codepoint
    from urllib import urlencode 

import re, regex
# from scrapy.utils.misc import md5sum
import hashlib

# from string import maketrans 
from namedentities import unicode_entities
from lxml import html, etree
from guess_language.guess_language import guessLanguage
import requests
import json
from google.cloud import translate
from difflib import Differ, HtmlDiff
# import unirest
# import wip.srx_segmenter
import wip.srx_segmenter as srx_segmenter

# from wip.settings import BLOCK_TAGS, TO_DROP_TAGS
from django.conf import settings

def is_invariant_word(word):
    # return word.count('#') or word.count('@') or word.count('http') or word.replace(',', '.').isnumeric()
    return word.count('#') or word.count('@') or word.count('http') or re.sub('[\.\,\-\/]', '', word).isnumeric() or (len(word)==1 and string.punctuation.count(word))

def element_tostring(e):
    # return html.tostring(e, encoding='utf-8')
    return html.tostring(e)

def fix_html_structure(string):
    doc = html.fromstring(string)
    return html.tostring(doc)

def etree_from_html(string):
    parser = etree.HTMLParser()
    return etree.parse(StringIO.StringIO(string), parser)
    """
    tree = etree.parse(StringIO.StringIO(string), parser)
    comments = tree.xpath('//comment()')
    for c in comments:
        p = c.getparent()
        p.remove(c)
    return tree
    """

def text_from_html(string):
    doc = html.fromstring(string)
    comments = doc.xpath('//comment()')
    for c in comments:
        p = c.getparent()
        if p is not None:
            p.remove(c)
    return doc.text_content()

def split_strip(s):
    return " ".join(s.split())

def merge_spaces(s):
    """ replace multiple contiguous spaces with a single space """
    return re.sub('\s\s+', ' ', s)

"""
http://stackoverflow.com/questions/4624062/get-all-text-inside-a-tag-in-lxml
http://stackoverflow.com/questions/4770191/lxml-etree-element-text-doesnt-return-the-entire-text-from-an-element
http://stackoverflow.com/questions/26304626/lxml-how-to-get-xpath-of-htmlelement
"""
def strings_from_block(block, tree=None, exclude_xpaths=[]):
    children = block.getchildren()
    if children:
        yield block.text
        for child in children:
            if child.tag in settings.TO_DROP_TAGS:
                continue
            if exclude_xpaths:
                # NO [1] element index in xpath address !!!
                xpath = tree.getpath(child).replace('[1]','')
                if xpath in exclude_xpaths:
                    continue
            if child.tag in settings.TO_DROP_TAGS:
                continue
            for el in strings_from_block(child, tree=tree, exclude_xpaths=exclude_xpaths):
                yield el
    else:
        content = block.text_content()
        print ('"{}"'.format(content))
        yield content
    """
    if block.tag in settings.BLOCK_TAGS:
        yield '\n'
    """
    print ('"{}"'.format(block.tail))
    yield block.tail

def strings_from_html(string, fragment=False, exclude_xpaths=[], exclude_tx=False):
    strings = []
    try:
        doc = html.fromstring(string)
    except:
        return []
    comments = doc.xpath('//comment()')
    for c in comments:
        p = c.getparent()
        if p is not None:
            p.remove(c)
    if fragment:
        tree = None
        body = doc
    else:
        tree = doc.getroottree()
        body = doc.find('body')
    if body is None:
        return []
    for tag in settings.TO_DROP_TAGS:
        els = body.findall(tag)
        for el in els:
            el.getparent().remove(el)
    if exclude_tx:
        els = body.findall('.//span[@tx]')
        for el in els:
            el.getparent().remove(el)
    ls = []
    for s in strings_from_block(body, tree=tree, exclude_xpaths=exclude_xpaths):
        if s:
            """
            if s == '\n':
                if ls:
                    # yield ' '.join(ls)
                    yield ''.join(ls)
                ls = []
            s = split_strip(s)
            """
            if s == '\n':
                if ls:
                    strings.append(merge_spaces(''.join(ls)))
                    ls = []
                s = ' '
            if s:
                ls.append(merge_spaces(s))
    if ls:
        # yield ' '.join(ls)
        strings.append(merge_spaces(''.join(ls)))
    return strings

def elements_from_element(element):
    """ returns the in block and, recursively, the child blocks, when
    - a block with block children has also additional text inside itself
    - a block without block children has some text content
    """
    children = element.getchildren()
    child_blocks = []
    text = element.text
    text = text and text.strip() and True
    for child in children:
        tag = child.tag
        if not text:
            tail = child.tail
            tail = tail and tail.strip()
            if tail:
                text = True
        if tag in settings.BLOCK_TAGS:
            child_blocks.append(child)
            for el in elements_from_element(child):
                yield el
        elif not text:
            # if not tag in settings.TO_DROP_TAGS:
            # see http://lxml.de/FAQ.html#how-can-i-find-out-if-an-element-is-a-comment-or-pi
            if not tag in settings.TO_DROP_TAGS and not tag is etree.Comment:
                content = child.text_content()
                content = content and content.strip()
                if content:
                    text = True
    if child_blocks:
        if text:
            yield element
    else:
        content = element.text_content()
        if content: content = content.strip()
        if content: yield element

def replace_element_content(element, text, tag=None, attrs={}):
    for child in element:
        element.remove(child)
    if tag:
        element.text = ''
        if attrs:
            child = etree.Element(tag, **attrs)
        else:
            child = etree.Element(tag)
        child.text = text
        element.append(child)
    else:
        element.text = text

def replace_segment(html_text, segment, tx='auto'):
    element = html.fromstring(html_text)
    text_content = element.text_content() or ''
    n = text_content.count(segment)
    if not n:
        return False
    text = element.text or ''
    # if text and not text.replace(segment, '', 1).strip(settings.DEFAULT_STRIPPED):
    if text and not text.replace(segment, '', 1).strip():
        element.text = ''
        # attrs={'tx':'', tx:''}
        attrs={'tx': tx }
        child = etree.Element('span', **attrs)
        element.insert(0, child)
        # return etree.tostring(element)
        return element_tostring(element)
    return False
    # to be extended

"""
def non_invariant_words(words):
    non_invariant = []
    for word in words:
        if word.isnumeric() or word.replace(',', '.').isnumeric():
            continue
        if word.count('@')==1:
            continue
        if word in ['Roma', 'roma',]:
            continue
        non_invariant.append(word)
    return non_invariant
"""

def md5sum(file):
    """Calculate the md5 checksum of a file-like object without reading its
    whole content in memory.

    >>> from io import BytesIO
    >>> md5sum(BytesIO(b'file content to hash'))
    '784406af91dd5a54fbb9c84c2236595a'
    """
    m = hashlib.md5()
    while 1:
        d = file.read(8096)
        if not d:
            break
        m.update(d)
    return m.hexdigest()

def string_checksum(string):
    m = hashlib.md5()
    m.update(string)
    return m.hexdigest()

def block_checksum(block):
    # string = etree.tostring(block)
    string = element_tostring(block)
    """
    buf = BytesIO(string)
    return md5sum(buf)
    m = hashlib.md5()
    m.update(string)
    return m.hexdigest()
    """
    return string_checksum(string)

def element_signature(element):
    # tags = [el.tag for el in element.iter()]
    tags = []
    for el in element.iter():
        tag = el.tag
        if type(tag) is str:
            tags.append(tag)
    # return string_checksum('.'.join(tags) + '_' + element.text_content())
    return string_checksum(('.'.join(tags) + '_' + element.text_content()).encode())

def guess_block_language(block):
    strings = strings_from_html(block.body, fragment=True)
    if strings:
        text = ' '.join(strings)
        code = guessLanguage(text)
        if len(code) == 2:
            return code
    return '?'

def ask_mymemory(string, langpair, use_key=False):
    baseurl = "https://translated-mymemory---translation-memory.p.mashape.com/api/get?"
    querydict = { 'langpair': langpair, 'mt': 1, 'of': 'json', 'q': string, }
    if use_key:
        querydict['key'] = settings.TRANSLATED_KEY
    querystring = urlencode(querydict)
    url = baseurl + querystring
    headers={"X-Mashape-Key": settings.MASHAPE_KEY, "Accept": "application/json"}
    response = requests.get(url, headers=headers)
    status = response.status_code
    translatedText = ''
    translations = []
    if status == 200:
        body = json.loads(response.content.decode())
        details = body.get('responseDetails', 'no details')
        data = body.get('responseData', {})
        translatedText = data.get('translatedText', '')
        matches = []
        if data.get('match', 0):
            matches = body.get('matches', [])
        for match in matches:
            translation = {}
            translation['segment'] = match.get('segment', '')
            translation['translation'] = match.get('translation', '')
            quality = match.get('quality', '0')
            # quality = int(round(float(quality) / 25))
            quality = quality and int(round(float(quality) / 25)) or None
            """
            translation['quality'] = quality.isdigit() and int(round(float(quality) / 25)) or 0
            """
            translation['entry_id'] = 'Matecat-%s' % match.get('id', '')
            translations.append(translation)
    return status, translatedText, translations

def ask_gt(text, target_code):
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", settings.GOOGLE_APPLICATION_CREDENTIALS)
    client = translate.Client()
    return client.translate(text, target_language=target_code)    

# http://stackoverflow.com/questions/8898294/convert-utf-8-with-bom-to-utf-8-with-no-bom-in-python
def remove_bom(filepath):
    fp = open(filepath, 'rw')
    s = fp.read()
    u = s.decode('utf-8-sig')
    s = u.encode('utf-8')
    fp.write(s)
    fp.close()
    
"""
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.
"""
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                # text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                text = unichr(name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

def normalize_string(s):
    # s = unicode_entities(s)
    if s:
        # s = s.replace(u"\u2018", "'").replace(u"\u2019", "'").replace(' - ', ' – ')
        # s = s.replace("‘", "'").replace("’", "'").replace(' - ', ' – ')
        s = unescape(s)
        try:
            s.translate(settings.TRANS_QUOTES)
            s = s.replace(u"\u2018", u"'").replace(u"\u2019", u"'")
            s = s.replace(u"\u201C", u'\"').replace(u"\u201D", u'\"')
            s = s.replace(u"\u2026", u"..").replace(u"\u2033", u'\"')
            s = s.replace(u"\u00a0", u" ")
            s = s.replace(u"&#8216;", u"'").replace(u"&#8217;", u"'")
            s = s.replace(u"&nbsp;", u" ").replace(u"&#160;", u" ").replace(u'&#39;', u" ")
        except:
            pass
    return s

def parse_xliff(filepath, verbose=False):
    tree = etree.iterparse(filepath)
    i = 0
    for action, elem in tree:
        # print("--- %s: %s | %s | %s" % (action, elem.tag, elem.text, elem.tail))
        tag = elem.tag
        text = elem.text
        if tag.endswith('source') and not tag.endswith('seg-source'):
            source = text
            mrk_text = None
        elif tag.endswith('seg-source'):
            mrk_text = None
        elif tag.endswith('mrk'):
            mrk_text = text
        elif tag.endswith('target'):
            if mrk_text is None:
                target = text
            else:
                target = mrk_text
        elif tag.endswith('trans-unit'):
            i += 1
            if verbose:
                print (i, source)
                print (i, target)

def text_to_list(text):
    if not text:
        return []
    list = text.splitlines()
    list = [item.strip() for item in list]
    return [item for item in list if len(item)]

def pretty_html(in_path, out_name=''):
    if out_name:
        in_file = open(in_path)
    else:
        in_file = open(in_path, 'r+')
    parser = etree.HTMLParser(remove_blank_text=True)
    tree = etree.parse(in_file, parser)
    # html_text = etree.tostring(tree, pretty_print=True)
    html_text = html.tostring(tree, pretty_print=True)
    if out_name:
        in_file.close()
        out_path = os.path.join(os.path.dirname(in_path), out_name)
        out_file = open(out_path, 'w')
    else:
        out_file = in_file
    out_file.write(html_text)
    out_file.close

def make_segmenter(language_code):
    srx_filepath = os.path.join(settings.RESOURCES_ROOT, language_code, 'segment.srx')
    srx_rules = srx_segmenter.parse(srx_filepath)
    current_rules = srx_rules['Italian']
    return srx_segmenter.SrxSegmenter(current_rules)

re_eu_date = re.compile(r'(0?[1-9]|[1-2][0-9]|3[0-1])(-|/|\.)(0?[1-9]|1[0-2])(-|/|\.)([0-9]{4})') # es: 10/7/1953, 21-12-2015
re_decimal_thousands_separators = re.compile(r'[0-9](\.|\,)[0-9]')
re_spaces = re.compile(r'\b[\b]+')
# see models.segments_from_string
# def segments_from_string(string, site, segmenter, exclude_TM_invariants=True):
def segments_from_string(string, segmenter):
    if string.count('window') and string.count('document'):
        return []
    if string.count('flickr'):
        return []
    segments = segmenter.extract(string)[0]
    filtered = []
    for s in segments:
        # REPLACE NON-BREAK SPACES
        s = s.replace('\xc2\xa0', ' ')
        s = re_spaces.sub(' ', s)
        s = s.strip()
        # REMOVE PSEUDO-BULLETS
        if s.startswith(u'- ') or s.startswith(u'– '): s = s[2:]
        if s.endswith(u' -') or s.endswith(u' –'): s = s[:-3]
        s = s.strip()
        if len(s) < 3:
            continue
        # KEEP SEGMENTS CONTAINING: DATES, NUMBERS INCLUDING SEPARATORS, CURRENCY SYMBOLS
        # if re_eu_date.findall(s) or re_decimal_thousands_separators.findall(s) or regex.findall(ur'\p{Sc}', s):
        if re_eu_date.findall(s) or re_decimal_thousands_separators.findall(s) or regex.findall(r'\p{Sc}', s):
            filtered.append(s)
            continue
        # REMOVE RESIDUOUS SEGMENTS NON INCLUDING ANY LETTER
        if not re.search('[a-zA-Z]', s):
            continue
        if not s: continue
        # REMOVE SEGMENTS INCLUDING ONLY WORDS BELONGING TO INVARIANT CLASSES
        words = re.split(" |\'", s)
        if len(words) > 1:
            while words and is_invariant_word(words[0]):
                words = words[1:]
            while words and is_invariant_word(words[-1]):
                words = words[:-1]
            if not words: continue
        if len(words) == 1: # 1 word at the start or as the result of stripping other words
            word = words[0]
            if is_invariant_word(word) or word.isupper():
                continue
        filtered.append(s)
    return filtered

# see: http://stackoverflow.com/questions/8506914/detect-whether-celery-is-available-running
def get_celery_worker_stats():
    ERROR_KEY = "ERROR"
    try:
        from celery.task.control import inspect
        insp = inspect()
        d = insp.stats()
        if not d:
            d = { ERROR_KEY: 'No running Celery workers were found.' }
    except IOError as e:
        from errno import errorcode
        msg = "Error connecting to the backend: " + str(e)
        if len(e.args) > 0 and errorcode.get(e.args[0]) == 'ECONNREFUSED':
            msg += ' Check that the RabbitMQ server is running.'
        d = { ERROR_KEY: msg }
    except ImportError as e:
        d = { ERROR_KEY: str(e)}
    return d

diff_style = """
    <style type="text/css">
        table.diff {all:none; font-family:Courier; font-size:x-small; border:medium;}
        .diff_header {background-color:#e0e0e0}
        td.diff_header {text-align:right}
        .diff_next {background-color:#c0c0c0}
        .diff_add {background-color:#aaffaa}
        .diff_chg {background-color:#ffff77}
        .diff_sub {background-color:#ffaaaa}
    </style>
"""

def string_diff(old, new, html=False, wrap=None):
    old_lines = old.split('\n')
    new_lines = new.split('\n')
    if html:
        differ = HtmlDiff(wrapcolumn=wrap)
        if html == 'table':
            diff = differ.make_table(old_lines, new_lines)
        else:
            diff = differ.make_file(old_lines, new_lines)
    else:
        differ = Differ()
        diff_lines = differ.compare(old_lines, new_lines)
        diff = '\n'.join(diff_lines)
    return diff

def pageversion_diff(old_version, new_version, html=False, wrap=None, diff_file=None):
    diff = string_diff(old_version.body, new_version.body, html=html, wrap=wrap)
    if diff_file:
        if html == 'table':
            diff = diff_style + diff
        diff_file.write(diff)
    else:
        return diff

