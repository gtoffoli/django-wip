# -*- coding: utf-8 -*-


import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

import StringIO
from itertools import chain
from lxml import html, etree

BLOCK_TAGS = {
   'body', 'header', 'footer', 'article', 'section', 'nav',
   'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
   'table', 'thead', 'tbody', 'tr', 'th', 'td',
   'pre', 'aside', 'form', 'input', 'select', 'option',
}
TO_DROP_TAGS = {
    'script', 'style','iframe',
}

def fix_html_structure(string):
    doc = html.fromstring(string)
    return html.tostring(doc)

def etree_from_html(string):
    parser = etree.HTMLParser()
    return etree.parse(StringIO.StringIO(string), parser)

# http://stackoverflow.com/questions/4624062/get-all-text-inside-a-tag-in-lxml
def strings_from_block(block):
    # print 'BLOCK: ', block.tag
    block_children = [child for child in block.getchildren() if child.tag in BLOCK_TAGS]
    if block_children:
        text = block.text
        if text: text = text.strip()
        if text: yield text
        for child in block_children:
            for el in strings_from_block(child):
                yield el
        tail = block.tail
        if tail: tail = tail.strip()
        if tail: yield tail
    else:
        content = block.text_content()
        if content: content = content.strip()
        if content: yield content

def strings_from_html(string):
    doc = html.fromstring(string)
    body = doc.find('body')
    for tag in TO_DROP_TAGS:
        els = body.findall(tag)
        for el in els:
            el.getparent().remove(el) 
    for s in strings_from_block(body):
        if s:
            yield s

