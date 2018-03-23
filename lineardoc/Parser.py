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
    'address', # added by Giovanni Toffoli
    # other
    'hr', 'button', 'canvas', 'center', 'col', 'colgroup', 'embed',
    'map', 'object', 'pre', 'progress', 'video',
    # non-annotation inline tags
    'img', 'br', 'figure-inline',
    # form controls
    'input', 'select', 'textarea',
]
blockTags_dict = dict([(tagName, True,) for tagName in blockTags])

# from xml.sax import parseString, ContentHandler
from lxml import html
from .Contextualizer import Contextualizer
from .Builder import Builder
from .Utils import isSegment, isReference, isInlineEmptyTag

class LineardocParser():
    """ Parses an html text with a DOM parser
        and generates a Lineardoc by emulating a SAX parser """

    def __init__(self, contextualizer, options, html_text):
        parent = None
        wrapperTag = None
        self.builder = Builder(parent, wrapperTag)
        self.contextualizer = contextualizer
        self.options = options
        self.doc = html.fromstring(html_text)
        # remove XML comments
        comments = self.doc.xpath('//comment()')
        for c in comments:
            p = c.getparent()
            if p is not None:
                p.remove(c)
        self.process(self.doc)

    def onopentag(self, tagName, attributes):
        """ see funcion onopentag in Javascript version """
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

    def onclosetag(self, tagName):
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
        """ see function ontext in Javascript version """
        self.builder.addTextChunk(text, self.contextualizer.canSegment())

    def isInlineAnnotationTag(self, tagName):
        """ Determine whether a tag is an inline annotation """
        return not blockTags_dict.get(tagName, False)

    def process(self, el):
        """ Visit DOM tree recursively and generate SAX events """
        tagName = el.tag
        attrs = el.attrib
        self.onopentag(tagName, attrs)
        if el.text:
            self.characters(el.text)
        for child in el.iterchildren():
            self.process(child)
        self.onclosetag(tagName)
        if el.tail:
            self.characters(el.tail)

def LineardocParse(html):
    """ Parses an html text with a DOM parser
        and generates a Lineardoc by emulating a SAX parser """
    contextualizer = Contextualizer()
    options = {}
    handler = LineardocParser(contextualizer, options, html)
    return handler.builder.doc
