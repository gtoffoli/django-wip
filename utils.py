# -*- coding: utf-8 -*-

import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

import StringIO
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
from scrapy.utils.misc import md5sum

from lxml import html, etree
from guess_language import guessLanguage
import urllib
import unirest

# from wip.settings import BLOCK_TAGS, TO_DROP_TAGS
from django.conf import settings

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
"""
def strings_from_block(block):
    children = block.getchildren()
    block_children = [child for child in children if child.tag in settings.BLOCK_TAGS]
    if block_children:
        text = block.text
        if text: text = text.strip()
        if text: yield text
        for child in children:
            for el in strings_from_block(child):
                if el: el = el.strip()
                if el: yield el
    else:
        content = block.text_content()
        if content: content = content.strip()
        if content: yield content
    tail = block.tail
    if tail: tail = tail.strip()
    if tail: yield tail
"""
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
            text_list.append(text)
        for child in children:
            if exclude_xpaths:
                xpath = tree.getpath(child)
                # print xpath
                if xpath in exclude_xpaths:
                    continue
            if child.tag in settings.BLOCK_TAGS:
                if text_list:
                    yield ' '.join(text_list)
                text_list = []
                for el in strings_from_block(child, tree=tree, exclude_xpaths=exclude_xpaths):
                    if el: el = el.strip()
                    if el:
                        yield el
                if child.tail:
                    text = child.tail.strip()
                    if text:
                        text_list.append(text)
            else:
                text = child.text_content()
                if text: text = text.strip()
                if text:
                    text_list.append(text)
        if text_list:
            yield ' '.join(text_list)
    else:
        content = block.text_content()
        if content: content = content.strip()
        if content:
            yield content
    tail = block.tail
    if tail: tail = tail.strip()
    if tail:
        yield tail

def strings_from_html(string, fragment=False, exclude_xpaths=[], exclude_tx=False):
    doc = html.fromstring(string)
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
    for tag in settings.TO_DROP_TAGS:
        els = body.findall(tag)
        for el in els:
            el.getparent().remove(el)
    if exclude_tx:
        els = body.findall('.//span[@tx]')
        for el in els:
            el.getparent().remove(el) 
    for s in strings_from_block(body, tree=tree, exclude_xpaths=exclude_xpaths):
        if s:
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

def block_checksum(block):
    string = etree.tostring(block)
    buf = BytesIO(string)
    return md5sum(buf)

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


    
    
    