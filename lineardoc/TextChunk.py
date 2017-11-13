# -*- coding: utf-8 -*-

# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

""" A chunk of uniformly-annotated inline text
 The annotations consist of a list of inline tags (<a>, <i> etc), and an
 optional "inline element" (br/img tag, or a sub-document e.g. for a
 reference span). The tags and/or reference apply to the whole text;
 therefore text with varying markup must be split into multiple chunks. """
class TextChunk:
    def __init__(self, text, tags, inlineContent):
        self.text = text
        self.tags = tags
        self.inlineContent = inlineContent
