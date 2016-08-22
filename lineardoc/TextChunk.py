# -*- coding: utf-8 -*-

# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

"""
 * A chunk of uniformly-annotated inline text
 *
 * The annotations consist of a list of inline tags (<a>, <i> etc), and an
 * optional "inline element" (br/img tag, or a sub-document e.g. for a
 * reference span). The tags and/or reference apply to the whole text;
 * therefore text with varying markup must be split into multiple chunks.
 *
 * @class
 *
 * @constructor
 * @param {string} text Plaintext in the chunk (can be '')
 * @param {Object[]} tags array of SAX open tag objects, for the applicable tags
 * @param {Doc|Object} [inlineContent] tag or sub-doc
"""
class TextChunk:
    """ A chunk of uniformly-annotated inline text """
    def __init__(self, text, tags, inlineContent):
        self.text = text
        self.tags = tags
        self.inlineContent = inlineContent

