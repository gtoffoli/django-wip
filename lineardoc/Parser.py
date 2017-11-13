# -*- coding: utf-8 -*-

# converted from Parser.js in the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/lineardoc/Parser.js

blockTags = [
    'html', 'head', 'body', 'script',
    # head tags
    # In HTML5+RDFa, link/meta are actually allowed anywhere in the body, and are to be
    # treated as void flow content (like <br> and <img>).
    'title', 'style', 'meta', 'link', 'noscript', 'base',
    # non-visual content
    'audio', 'data', 'datagrid', 'datalist', 'dialog', 'eventsource', 'form',
    'iframe', 'main', 'menu', 'menuitem', 'optgroup', 'option',
    # paragraph
    'div', 'p',
    # tables
    'table', 'tbody', 'thead', 'tfoot', 'caption', 'th', 'tr', 'td',
    # lists
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    # HTML5 heading content
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hgroup',
    # HTML5 sectioning content
    'article', 'aside', 'body', 'nav', 'section', 'footer', 'header', 'figure',
    'figcaption', 'fieldset', 'details', 'blockquote',
    # other
    'hr', 'button', 'canvas', 'center', 'col', 'colgroup', 'embed',
    'map', 'object', 'pre', 'progress', 'video',
    # non-annotation inline tags
    'img', 'br', 'figure-inline'
]
blockTags_dict = dict([(tagName, True,) for tagName in blockTags])

from xml.sax import parseString, ContentHandler
from .Contextualizer import Contextualizer
from .Builder import Builder
from .Utils import isSegment, isReference, isInlineEmptyTag

class LineardocSAXHandler(ContentHandler):

    def __init__(self, builder, options, contextualizer):
        ContentHandler.__init__(self)
        self.builder = builder
        self.options = options
        self.contextualizer = contextualizer

    def startDocument(self):
        pass

    def startElement(self, tagName, attrs):
        """ see funcion onopentag in Javascript version """
        attributes = {}
        for name in attrs.getNames():
            attributes[name] = attrs.getValue(name)
        tag = { 'name': tagName,
                'attributes': attributes }
        if self.options.get('isolateSegments', None) and isSegment(tag):
            self.builder.pushBlockTag({
                'name': 'div',
                'attributes': {
                    'class': 'cx-segment-block'
                }
            })
        if isReference(tag):
            # Start a reference: create a child builder, and move into it
            self.builder = self.builder.createChildBuilder(tag)
        elif isInlineEmptyTag(tagName):
            self.builder.addInlineContent(tag, self.contextualizer.canSegment())
        elif self.isInlineAnnotationTag(tagName):
            self.builder.pushInlineAnnotationTag(tag)
        else:
            self.builder.pushBlockTag(tag)
        self.contextualizer.onOpenTag(tag)
 
    # def onclosetag(self, tagName):
    def endElement(self, tagName):
        """ see funcion onclosetag in Javascript version """
        self.contextualizer.onCloseTag()
        isAnn = self.isInlineAnnotationTag(tagName)
        if isInlineEmptyTag(tagName):
            return
        elif isAnn and self.builder.inlineAnnotationTags:
            tag = self.builder.popInlineAnnotationTag(tagName)
            if self.options.get('isolateSegments', None) and isSegment(tag):
                self.builder.popBlockTag('div')
        elif isAnn and self.builder.parent:
            # In a sub document: should be a span or sup that closes a reference
            if not tagName in ('span', 'sup',):
                # throw new Error( 'Expected close reference - span or sup tags, got "' + tagName + '"' );
                raise
            self.builder.finishTextBlock()
            self.builder.parent.addInlineContent(self.builder.doc)
            # Finished with child now. Move back to the parent builder
            self.builder = self.builder.parent
        elif not isAnn:
            self.builder.popBlockTag(tagName)
        else:
            # throw new Error( 'Unexpected close tag: ' + tagName );
            raise

    def characters(self, text):
        """ see funcion ontext in Javascript version """
        self.builder.addTextChunk(text, self.contextualizer.canSegment())

    def isInlineAnnotationTag(self, tagName):
        """ Determine whether a tag is an inline annotation """
        return not blockTags_dict.get(tagName, False)

def Parse(html):
    """ Parse an html text and generate a Lineardoc """
    parent = None
    wrapperTag = None
    builder = Builder(parent, wrapperTag)
    options = {}
    contextualizer = Contextualizer()
    handler = LineardocSAXHandler(builder, options, contextualizer)
    parseString(html, handler)
    return builder.doc
