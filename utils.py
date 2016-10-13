# -*- coding: utf-8 -*-

import os
import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

import logging
logger = logging.getLogger('wip')

import StringIO
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
# from scrapy.utils.misc import md5sum
import hashlib

from string import maketrans 
from namedentities import unicode_entities
from lxml import html, etree
from guess_language import guessLanguage
import urllib
import unirest

# from wip.settings import BLOCK_TAGS, TO_DROP_TAGS
from django.conf import settings

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

# http://stackoverflow.com/questions/4624062/get-all-text-inside-a-tag-in-lxml
# http://stackoverflow.com/questions/4770191/lxml-etree-element-text-doesnt-return-the-entire-text-from-an-element
# http://stackoverflow.com/questions/26304626/lxml-how-to-get-xpath-of-htmlelement
def strings_from_block(block, tree=None, exclude_xpaths=[]):
    children = block.getchildren()
    block_children = [child for child in children if child.tag in settings.BLOCK_TAGS]
    if block_children:
        text_list = []
        text = block.text
        if text: text = text.strip()
        if text:
            text = unicode(text)
            # print 'strings_from_block - 1: ', type(text)
            text_list.append(text)
        for child in children:
            if exclude_xpaths:
                # NO [1] element index in xpath address !!!
                # xpath = tree.getpath(child)
                xpath = tree.getpath(child).replace('[1]','')
                # print xpath
                if xpath in exclude_xpaths:
                    continue
            if child.tag in settings.BLOCK_TAGS:
                if text_list:
                    # yield ' '.join(text_list)
                    # print 'strings_from_block - 2: ', type(u' '.join(text_list))
                    yield u' '.join(text_list)
                text_list = []
                for el in strings_from_block(child, tree=tree, exclude_xpaths=exclude_xpaths):
                    if el: el = el.strip()
                    if el:
                        # print 'strings_from_block - 3: ', type(el)
                        yield el
                if child.tail:
                    text = child.tail.strip()
                    if text:
                        text = unicode(text)
                        # print 'strings_from_block - 4: ', type(text)
                        text_list.append(text)
            else:
                text = child.text_content()
                if text: text = text.strip()
                if text:
                    text = unicode(text)
                    # print 'strings_from_block - 5: ', type(text)
                    text_list.append(text)
        if text_list:
            # print 'strings_from_block - 6: ', type(u' '.join(text_list))
            yield u' '.join(text_list)
    else:
        content = block.text_content()
        if content: content = content.strip()
        if content:
            content = unicode(content)
            # print 'strings_from_block - 7: ', type(content)
            yield content
    tail = block.tail
    if tail: tail = tail.strip()
    if tail:
        tail = unicode(tail)
        yield tail

def strings_from_html(string, fragment=False, exclude_xpaths=[], exclude_tx=False):
    # print 'strings_from_html - 1: ', type(string)
    try:
        doc = html.fromstring(string)
    except:
        return
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
        # print 'strings_from_html - 2: ', type(body)
    if not body:
        return
    for tag in settings.TO_DROP_TAGS:
        els = body.findall(tag)
        for el in els:
            el.getparent().remove(el)
    if exclude_tx:
        els = body.findall('.//span[@tx]')
        # print 'exclude_tx: ', len(els)
        for el in els:
            el.getparent().remove(el) 
    for s in strings_from_block(body, tree=tree, exclude_xpaths=exclude_xpaths):
        if s:
            # print 'strings_from_html - 3: ', type(s)
            yield s

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
        attrs={'tx':'', tx:''}
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
    return string_checksum('.'.join(tags) + '_' + element.text_content())

def guess_block_language(block):
    strings = strings_from_html(block.body, fragment=True)
    if strings:
        text = ' '.join(strings)
        code = guessLanguage(text)
        if len(code) == 2:
            return code
    return '?'

translated_key = 'fbcc885cdb0971380e33'
def ask_mymemory(string, langpair):
    baseurl = "https://translated-mymemory---translation-memory.p.mashape.com/api/get?"
    querydict = { 'key': translated_key, 'langpair': langpair, 'mt': 1, 'of': 'json', 'q': string, }
    headers={"X-Mashape-Key": "vBhqkjRytAmsh3COr4xRHcX2whEcp1mm26TjsnMw7ZFZSK6XIU", "Accept": "application/json"}
    querystring = urllib.urlencode(querydict)
    r = unirest.get(baseurl+querystring, headers=headers)
    code = r.code
    body = r.body
    status = body.get('responseStatus', 'no status')
    translations = []
    if status == 200:
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
            translation['quality'] = quality.isdigit() and int(round(float(quality) / 25)) or 0
            translation['entry_id'] = 'Matecat-%s' % match.get('id', '')
            translations.append(translation)
    return status, translatedText, translations

# http://stackoverflow.com/questions/8898294/convert-utf-8-with-bom-to-utf-8-with-no-bom-in-python
def remove_bom(filepath):
    fp = open(filepath, 'rw')
    s = fp.read()
    u = s.decode('utf-8-sig')
    s = u.encode('utf-8')
    fp.write(s)
    fp.close()
    
import re, htmlentitydefs
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
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
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
        s.translate(settings.TRANS_QUOTES)
        s = s.replace(u"\u2018", u"'").replace(u"\u2019", u"'")
        s = s.replace(u"\u201C", u'\"').replace(u"\u201D", u'\"')
        s = s.replace(u"\u2026", u"..").replace(u"\u2033", u'\"')
        s = s.replace(u"\u00a0", u" ")
        s = s.replace(u"&#8216;", u"'").replace(u"&#8217;", u"'")
        s = s.replace(u"&nbsp;", u" ").replace(u"&#160;", u" ").replace(u'&#39;', u" ")
    return s

def parse_xliff(filepath):
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
            print i, source
            print i, target

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
