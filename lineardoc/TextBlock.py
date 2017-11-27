# -*- coding: utf-8 -*-

# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

import re
from collections import defaultdict
from .TextChunk import TextChunk
from .Utils import esc, getOpenTagHtml, getCloseTagHtml, dumpTags, getChunkBoundaryGroups, addCommonTag, setLinkIdsInPlace
from .Utils import sameTags

class TextBlock:
    """ A block of annotated inline text """
    def __init__(self, textChunks, canSegment=True):
        self.textChunks = textChunks
        self.canSegment = canSegment
        self.offsets = []
        cursor = 0
        for textChunk in self.textChunks:                                                         
            offset = {
                'start': cursor,
                'length': len(textChunk.text),
                'tags': textChunk.tags}
            self.offsets.append(offset)
            cursor += offset['length']

    def getTagOffsets(self):
        """ Get the start and length of each non-common annotation """
        commonTags_length = len(self.getCommonTags())
        offsets = self.offsets
        filtered = [offsets[i] for i in range(len(offsets)) if len(self.textChunks[i].tags) > commonTags_length and len(self.textChunks[i].text) > 0]
        return filtered

    def getTextChunkAt(self, charOffset):
        """ Get the (last) text chunk at a given char offset """
        i = 0
        while i < len(self.textChunks)-1:
            if self.offsets[i+1]['start'] > charOffset:
                break
            i += 1
        return self.textChunks[i]

    def getCommonTags(self):
        """ Returns the list of SAX tags that apply to the whole text block """
        textChunks = self.textChunks
        n_textChunks = len(textChunks)
        if n_textChunks == 0:
            return []
        commonTags = textChunks[0].tags[:]
        for textChunk in textChunks:
            tags = textChunk.tags
            if len(tags) < len(commonTags):
                commonTags = commonTags[:len(tags)]
            for j in range(len(commonTags)):
                if commonTags[j]['name'] != tags[j]['name']:
                    commonTags = commonTags[:j]
                    break
        return commonTags

    def translateTags(self, targetText, rangeMappings):
        """ Create a new TextBlock, applying our annotations to a translation """
        # map of { offset: x, textChunks: [...] }
        emptyTextChunks = defaultdict(list)
        emptyTextChunkOffsets = [] # list of { start: x, length: x, textChunk: x }       
        textChunks = []

        def pushEmptyTextChunks(offset, chunks):
            for chunk in chunks:
                textChunks.append({ 'start': offset, 'length': 0, 'textChunk': chunk })

        # Create map of empty text chunks, by offset
        for i in range(len(self.textChunks)):
            textChunk = self.textChunks[i]
            offset = self.offsets[i]['start']
            if textChunk.text:
                continue
            emptyTextChunks[offset].append(textChunk)
        for offset in emptyTextChunks:
            emptyTextChunkOffsets.append(offset)
        emptyTextChunkOffsets.sort()

        for rangeMapping in rangeMappings:
            # Copy tags from source text start offset
            sourceRangeStart = rangeMapping['source']['start']
            sourceRangeEnd = sourceRangeStart + rangeMapping['source']['length']
            targetRangeStart = rangeMapping['target']['start']
            targetRangeLength = rangeMapping['target']['length']
            targetRangeEnd = targetRangeStart + targetRangeLength
            sourceTextChunk = self.getTextChunkAt(rangeMapping['source']['start'])
            text = targetText[targetRangeStart : targetRangeEnd]
            textChunks.append({ 
                'start': targetRangeStart,
                'length': targetRangeLength,
                'textChunk': TextChunk(text, sourceTextChunk.tags, sourceTextChunk.inlineContent)})
            # Empty source text chunks will not be represented in the target plaintext(because they have no 
            # plaintext representation); therefore we must clone each one manually into the target rich text.
            # Iterate through all remaining emptyTextChunks
            j = 0
            while j < len(emptyTextChunkOffsets):
                offset = emptyTextChunkOffsets[j]
                # Check whether chunk is in range
                if offset < sourceRangeStart or offset > sourceRangeEnd:
                    j += 1
                    continue
                # Push chunk into target text at the current point
                pushEmptyTextChunks(targetRangeEnd, emptyTextChunks[offset])
                # Remove chunk from remaining list
                del emptyTextChunks[offset] # remove from dict
                del emptyTextChunkOffsets[j] # remove from list

        # Sort by start position
        # textChunks.sort(key = lambda x: x['start'])
        textChunks.sort(key = lambda x: (x['start'], x['textChunk'].inlineContent and 1 or 0))
        # Fill in any textChunk gaps using text with commonTags
        pos = 0
        commonTags = self.getCommonTags()
        iLen = len(textChunks)
        i = 0
        while i < iLen:
            textChunk = textChunks[i]
            if textChunk['start'] < pos:
                # throw new Error( 'Overlappping chunks at pos=' + pos + ', textChunks=' + i + ' start=' + textChunk.start );
                raise
            elif textChunk['start'] > pos:
                # Unmapped chunk: insert plaintext and adjust offset
                textChunks.insert(i, {
                    'start': pos,
                    'length': textChunk['start']-pos,
                    'textChunk': TextChunk(targetText[pos : textChunk['start']], commonTags, None) })
                i += 1
                iLen += 1
            pos = textChunk['start'] + textChunk['length']
            i += 1

        # Get trailing text and trailing whitespace
        tail = targetText[pos:]
        tailSpace = re.match('\s*$', tail)
        if tailSpace:
            tailSpace = tail[tailSpace.start():tailSpace.end()]
            space_length = len(tailSpace)
            tail = tail[:-space_length]
        if tail:
            # Append tail as text with commonTags
            textChunks.append({
                'start': pos,
                'length': len(tail),
                'textChunk': TextChunk(tail, commonTags, None)})
            pos += len(tail)

        # Copy any remaining textChunks that have no text
        for offset in emptyTextChunkOffsets:
            pushEmptyTextChunks(pos, emptyTextChunks[offset])
        if tailSpace:
            # Append tailSpace as text with commonTags
            textChunks.append( {
                'start': pos,
                'length': space_length,
                'textChunk': TextChunk(tailSpace, commonTags, None) })
            pos += len(tail) # has this any effect?

        return TextBlock([x['textChunk'] for x in textChunks])

    def getPlainText(self):
        """ Return plain text representation of the text block """
        return ''.join([textChunk.text for textChunk in self.textChunks])

    def __str__(self):
        return self.getPlainText()

    def getHtml(self):
        """ Return HTML representation of the text block """
        html = [] 
        # Start with no tags open
        oldTags = []
        for textChunk in self.textChunks:
            # Compare tag stacks; render close tags and open tags as necessary
            # Find the highest offset up to which the tags match on
            matchTop = -1
            jLen = min(len(oldTags), len(textChunk.tags))
            for j in range(jLen):
                if oldTags[j] == textChunk.tags[j]:
                    matchTop = j
                else:
                    break
            for j in range(len(oldTags)-1, matchTop, -1):
                html.append(getCloseTagHtml(oldTags[j]))
            for j in range(matchTop+1, len(textChunk.tags)):
                html.append(getOpenTagHtml(textChunk.tags[j]))
            oldTags = textChunk.tags
            # Now add text and inline content
            html.append(esc(textChunk.text))
            if textChunk.inlineContent:
                if hasattr(textChunk.inlineContent, 'getHtml'):
                    # a sub-doc
                    html.append(textChunk.inlineContent.getHtml())
                else:
                    # an empty inline tag
                    html.append(getOpenTagHtml(textChunk.inlineContent))
                    html.append(getCloseTagHtml(textChunk.inlineContent))
        # Finally, close any remaining tags
        for tag in reversed(oldTags):
            html.append(getCloseTagHtml(tag))
        return ''.join(html)

    def segment(self, getBoundaries, getNextId):
        """ Segment the text block into sentences """
        allTextChunks = []
        currentTextChunks = []
  
        def flushChunks():
            if not currentTextChunks:
                return
            modifiedTextChunks = addCommonTag(
                currentTextChunks, {
                    'name': 'span',
                    'attributes': { 'klass': 'cx-segment', 'data-segmentid': getNextId('segment')}})
            setLinkIdsInPlace(modifiedTextChunks, getNextId)
            allTextChunks.extend(modifiedTextChunks)
            del currentTextChunks[:]

        # for each chunk, split at any boundaries that occur inside the chunk
        groups = getChunkBoundaryGroups(
            getBoundaries(self.getPlainText()),
            self.textChunks,
            lambda x: len(x.text)
        )
        
        offset = 0
        for group in groups:
            textChunk = group['chunk']
            boundaries = group['boundaries']
            for boundary in boundaries:
                relOffset = boundary - offset
                if relOffset == 0:
                    flushChunks()
                else:
                    leftPart = TextChunk(textChunk.text[:relOffset], textChunk.tags[:], None)
                    rightPart = TextChunk(textChunk.text[relOffset:], textChunk.tags[:], textChunk.inlineContent)
                    currentTextChunks.append(leftPart)
                    offset += relOffset
                    flushChunks()
                    textChunk = rightPart
            # Even if the textChunk is zero-width, it may have references
            currentTextChunks.append(textChunk)
            offset += len(textChunk.text)
        flushChunks()
        return TextBlock(allTextChunks)

    def dumpXmlArray(self, pad):
        """ Dump an XML Array version of the linear representation, for debugging """
        dump = []
        for chunk in self.textChunks:
            tagsDump = dumpTags(chunk.tags)
            tagsAttr = tagsDump and ' tags="' + tagsDump + '"' or ''
            if chunk.text:
                dump.append(
                    pad + '<cxtextchunk' + tagsAttr + '>' + esc(chunk.text).replace('\n', '&#10;') + '</cxtextchunk>')
            if chunk.inlineContent:
                dump.append(pad + '<cxinlineelement' + tagsAttr + '>')
                if chunk.inlineContent.dumpXmlArray:
                    # sub-doc: concatenate
                    # dump.push.apply( dump, chunk.inlineContent.dumpXmlArray( pad + '  ' ) );
                    dump.extend(chunk.inlineContent.dumpXmlArray(pad + '  '))
                else:
                    dump.append(pad + '  ' + '<' + chunk.inlineContent.name + '/>')
                dump.append(pad + '</cxinlineelement>')
        return dump

    def dump(self):
        """ added by Giovanni Toffoli to get a printable Lineardoc representation like in
            https://www.mediawiki.org/wiki/Content_translation/Product_Definition/LinearDoc """
        chunks = self.textChunks
        lines = []
        line = "{textblock: %d textChunks, canSegment=%s}" % (len(chunks), str(self.canSegment))
        lines.append(line)
        for chunk in chunks:
            tags = []
            for tag_dict in chunk.tags:
                tag = "'<%s" % tag_dict['name']
                for attr_key, attr_value in tag_dict['attributes'].items():
                    tag += ' %s="%s"' % (attr_key, attr_value)
                tag += ">'"
                tags.append(tag)
            tags = ', '.join(tags)
            inlineContent = chunk.inlineContent
            if inlineContent:
                line = "{tags:[%s], inlineContent: '%s'}" % (tags, chunk.inlineContent)
            else:
                line = "{text: %d '%s', tags:[%s]}" % (len(chunk.text), chunk.text, tags)
            lines.append(line)
        return '\n'.join(lines)

    def hasCommonTag(self, name):
        for tag in self.getCommonTags():
            if tag['name'] == name:
                return True
        return False

    def getSentences(self, getBoundaries):
        """ added by Giovanni Toffoli
            Segment the text block into sub-blocks delimited by sentence boundaries
            (see the segment method and the function Utils.getChunkBoundaryGroups) """
        boundaries = getBoundaries(self.getPlainText())
        if not boundaries:
            return self.textChunks
        boundaries = boundaries[:]
        boundaries.sort()
        # add an extra boundary to avoid a test when incrementing boundaryPtr
        boundaries.append(self.offsets[-1]['start']+self.offsets[-1]['length'])
        boundaryPtr = 0
        boundary = boundaries[boundaryPtr]

        sentences = []
        currentTextChunks = []

        def flushChunks():
            if not currentTextChunks:
                return
            sentences.append(TextBlock(currentTextChunks[:], canSegment=False))
            del currentTextChunks[:]

        offset = 0
        textChunks = self.textChunks
        iLen = len(textChunks)
        i = 0
        while i < iLen:
            textChunk = textChunks[i]
            if not textChunk.text and not textChunk.inlineContent:
                i += 1
                continue
            while offset <= boundary:
                text = textChunk.text
                chunkLength = len(text)
                relOffset = boundary - offset
                if textChunk.inlineContent:
                    flushChunks()
                    currentTextChunks.append(textChunk)
                    flushChunks()
                    break
                elif relOffset >= chunkLength:
                    if text == '\n':
                        if i>0 and textChunks[i-1].inlineContent:
                            offset += 1
                            if offset == boundary:
                                flushChunks()
                            break
                        else:
                            space = TextChunk(' ', textChunk.tags[:], None)
                            currentTextChunks.append(space)
                    else:
                        if not currentTextChunks and len(text) > 1 and text.startswith(' '):
                            space = TextChunk(' ', textChunk.tags[:], None)
                            currentTextChunks.append(space)
                            flushChunks()
                            textChunk.text = textChunk.text[1:]
                        currentTextChunks.append(textChunk)
                    offset += chunkLength
                    if offset == boundary:
                        flushChunks()
                    break
                else:
                    leftPart = TextChunk(textChunk.text[:relOffset], textChunk.tags[:], None)
                    rightPart = TextChunk(textChunk.text[relOffset:], textChunk.tags[:], textChunk.inlineContent)
                    currentTextChunks.append(leftPart)
                    offset += relOffset
                    flushChunks()
                    textChunk = rightPart
                    boundaryPtr += 1
                    boundary = boundaries[boundaryPtr]
            if offset == boundary:
                boundaryPtr += 1
                boundary = boundaries[boundaryPtr]
            i += 1

        flushChunks()
        return sentences

    def simplify(self):
        """ added by Giovanni Toffoli
            merge contiguous text chunks with the same tags;
            spaces get tags from a couple of adjacent chunks with the same tags  """

        textChunks = self.textChunks
        nChunks = len(textChunks)
        chunks = []
        currentText = ''
        currentTags = []

        def flushChunks():
            if not currentText:
                return
            chunks.append(TextChunk(currentText, currentTags, None))

        # for chunk in self.textChunks:
        for i in range(nChunks):
            chunk = textChunks[i]
            if chunk.inlineContent:
                flushChunks()
                currentText = ''
                chunks.append(chunk)
            elif chunk.text == ' ' and i > 0 and i < (nChunks-1) and sameTags(textChunks[i+1].tags, currentTags):
                currentText += ' '
            else:
                if sameTags(chunk.tags, currentTags):
                    currentText += chunk.text
                else:
                    flushChunks()
                    currentText = chunk.text
                    currentTags = chunk.tags

        flushChunks()
        return TextBlock(chunks, canSegment=self.canSegment)


def mergeSentences(sentences):
    """ added by Giovanni Toffoli
        Merge sub-blocks to a single block """
    textChunks = []
    for sentence in sentences:
        textChunks.extend(sentence.textChunks)
    return TextBlock(textChunks, canSegment=False)
