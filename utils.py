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

from itertools import chain
from lxml import html, etree

# from wip.settings import BLOCK_TAGS, TO_DROP_TAGS
from django.conf import settings

def fix_html_structure(string):
    doc = html.fromstring(string)
    return html.tostring(doc)

def etree_from_html(string):
    parser = etree.HTMLParser()
    return etree.parse(StringIO.StringIO(string), parser)

# http://stackoverflow.com/questions/4624062/get-all-text-inside-a-tag-in-lxml
def strings_from_block(block):
    # print 'BLOCK: ', block.tag
    block_children = [child for child in block.getchildren() if child.tag in settings.BLOCK_TAGS]
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
    for tag in settings.TO_DROP_TAGS:
        els = body.findall(tag)
        for el in els:
            el.getparent().remove(el) 
    for s in strings_from_block(body):
        if s:
            yield s

"""
def blocks_from_block(block):
    block_children = [child for child in block.getchildren() if child.tag in settings.BLOCK_TAGS]
    if block_children:
        lead = block.text
        if lead: lead = lead.strip()
        print 'lead', lead
        children = []
        for child in block_children:
            for el in blocks_from_block(child):
                if el:
                    children.append(el)
                    yield el
        tail = block.tail
        if tail: tail = tail.strip()
        print 'tail', tail
        # if lead or children or tail:
        if lead or tail:
            yield block
    else:
        content = block.text_content()
        if content: content = content.strip()
        if content: yield block
"""

def blocks_from_block(block):
    # block_children = [child for child in block.getchildren() if child.tag in settings.BLOCK_TAGS]
    children = block.getchildren()
    child_blocks = []
    text = block.text
    text = text and text.strip() and True
    for child in children:
        tag = child.tag
        if not text:
            tail = child.tail
            # text = tail and tail.strip() and True
            tail = tail and tail.strip()
            if tail:
                text = True
                print tail
        if tag in settings.BLOCK_TAGS:
            child_blocks.append(child)
            for el in blocks_from_block(child):
                yield el
        elif not text:
            if not tag in settings.TO_DROP_TAGS:
                content = child.text_content()
                # text = content and content.strip() and True
                content = content and content.strip()
                if content:
                    text = True
                    print content
    if child_blocks:
        if text:
            yield block
    else:
        content = block.text_content()
        if content: content = content.strip()
        if content: yield block

def block_checksum(block):
    string = etree.tostring(block)
    buf = BytesIO(string)
    return md5sum(buf)
    