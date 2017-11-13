# -*- coding: utf-8 -*-

# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

import re
from .Doc import Doc
from .TextBlock import TextBlock
from .TextChunk import TextChunk

class Builder:
    """ A document builder """

    def __init__(self, parent, wrapperTag):
        self.blockTags = []
        # Stack of annotation tags
        self.inlineAnnotationTags = []
        # The height of the annotation tags that have been used, minus one
        self.inlineAnnotationTagsUsed = 0
        self.doc = Doc(wrapperTag)
        self.textChunks = []
        self.isBlockSegmentable = True
        self.parent = parent

    def createChildBuilder(self, wrapperTag):
        return Builder(self, wrapperTag)

    def pushBlockTag(self, tag):
        self.finishTextBlock()
        self.blockTags.append(tag)
        self.doc.addItem('open', tag)

    def popBlockTag(self, tagName):
        tag = None
        try:
            tag = self.blockTags.pop()
            assert tag['name'] == tagName
        except:
            print ('Mismatched block tags: open=' + (tag and tag['name'] or '') + ', close=' + tagName)
        self.finishTextBlock()
        self.doc.addItem('close', tag)
        return tag

    def pushInlineAnnotationTag(self, tag):
        self.inlineAnnotationTags.append(tag)

    def popInlineAnnotationTag(self, tagName):
        # var tag, textChunk, chunkTag, i, replace, whitespace;
        tag = self.inlineAnnotationTags.pop()
        if self.inlineAnnotationTagsUsed == len(self.inlineAnnotationTags):
            self.inlineAnnotationTagsUsed -= 1
        if not tag or tag['name'] != tagName:
            print ('Mismatched inline tags: open=' + (tag and tag['name'] or '') + ', close=' + tagName)
            raise
    
        if not tag['attributes']: # revise ?
            """
            Skip tags which have attributes, content or both from further check to
            see if we want to keep inline content. Else we assume that, if this tag has
            whitespace or empty content, it is ok to remove it from resulting document.
            But if it has attributes, we make sure that there are inline content blocks to
            avoid them missing in resulting document.
            See T104539
            """
            return tag
        # // Check for empty/whitespace-only data span. Replace as inline content
        replace = True
        whitespace = []
        for i in range (len(self.textChunks)-1, -1, -1):
            textChunk = self.textChunks[i]
            chunkTag = textChunk.tags and textChunk.tags[-1] or None
            if not chunkTag or chunkTag != tag:
                break
            if re.match('\S', textChunk.text) or textChunk.inlineContent:
                replace = False
            whitespace.append(textChunk.text)
        if (replace and
            (tag['attributes'].get('data-mw', '') or
                tag['attributes'].get('data-parsoid', '') or
                # Allow empty <a rel='mw:ExtLink'></a> because REST API v1 can output links with
                # no link text (which then get a CSS generated content numbered reference).
                (tag['name'] == 'a' and tag['attributes'].get('rel', '') == 'mw:ExtLink')
            )
        ):
            # truncate list and add data span as new sub-Doc.
            self.textChunks = self.textChunks[:i+1]
            whitespace.reverse()
            self.addInlineContent(
                Doc()
                .addItem('open', tag)
                .addItem('textblock', TextBlock(
                    [TextChunk(''.join(whitespace), [])]
                ))
                .addItem('close', tag)
            )
        return tag

    def addTextChunk(self, text, canSegment):
        self.textChunks.append(TextChunk(text, self.inlineAnnotationTags[:], None))
        self.inlineAnnotationTagsUsed = len(self.inlineAnnotationTags)
        if not canSegment:
            self.isBlockSegmentable = False

    def addInlineContent(self, content, canSegment):
        self.textChunks.append(TextChunk('', self.inlineAnnotationTags[:], content))
        self.inlineAnnotationTagsUsed = len(self.inlineAnnotationTags)
        if not canSegment:
            self.isBlockSegmentable = False

    def finishTextBlock(self):
        whitespaceOnly = True
        whitespace = []
        if not self.textChunks:
            return
        for textChunk in self.textChunks:
            if textChunk.inlineContent or re.match('\S', textChunk.text):
                whitespaceOnly = False
                whitespace = None
                break;
            else:
                whitespace.append(textChunk.text)
        if whitespaceOnly:
            self.doc.addItem('blockspace', ''.join(whitespace))
        else:
            self.doc.addItem('textblock', TextBlock(self.textChunks, self.isBlockSegmentable))
        self.textChunks = []
