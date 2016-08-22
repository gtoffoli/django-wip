# -*- coding: utf-8 -*-

# converted from Parser.js in the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/lineardoc/Parser.js

from xml.sax import parseString, ContentHandler
from .Utils import esc, getOpenTagHtml, getCloseTagHtml

class NormalizerSAXHandler(ContentHandler):

    def __init__(self, doc):
        ContentHandler.__init__(self)
        self.doc = doc

    # def init(self):
    def startDocument(self):
        self.tags = []

    # def onopentag(self, tag):
    def startElement(self, tagName, attributes):
        tag = { 'name': tagName,
                'attributes': attributes }
        self.tags.push(tag)
        self.doc.push(getOpenTagHtml(tag))
 
    # def onclosetag(self, tagName):
    def endElement(self, tagName):
        tag = self.tags.pop()
        if not tag.name == tagName:
            print ( 'Unmatched tags: ' + tag.name + ' !== ' + tagName )
            raise
        self.doc.push(getCloseTagHtml(tag))

    # def ontext(self, text):
    def characters(self, text):
        self.doc.push(esc(text))

def Normalize(html):
    doc = []
    handler = NormalizerSAXHandler(doc)
    parseString(html, handler)
    return ''.join(doc)
