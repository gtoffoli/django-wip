# -*- coding: utf-8 -*-

# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

from .TextChunk import TextChunk
from .Utils import esc, getOpenTagHtml, getCloseTagHtml, dumpTags

"""
 * A block of annotated inline text
 *
 * @class
 *
 * @constructor
"""
class TextBlock:
    def __init__(self, textChunks):
        self.textChunks = textChunks
        self.offsets = []
        cursor = 0
        for textChunk in self.textChunks:                                                         
            offset = {
                'start': cursor,
                'length': len(textChunk.text),
                'tags': textChunk.tags
                }
            self.offsets.append(offset)
            cursor += offset['length']

    """
    /**
     * Get the start and length of each non-common annotation
     *
     * @return {Object[]}
     * @return {number} [i].start {number} Position of each text chunk
     * @return {number} [i].length {number} Length of each text chunk
     */
    TextBlock.prototype.getTagOffsets = function () {
        var textBlock = this,
            commonTags = this.getCommonTags();
        return this.offsets.filter( function ( offset, i ) {
            var textChunk = textBlock.textChunks[ i ];
            return textChunk.tags.length > commonTags.length && textChunk.text.length > 0;
        } );
    };
    """
    def getTagOffsets(self):
        commonTags_length = len(self.getCommonTags())
        offsets = self.offsets
        filtered = [offsets[i] for i in range(offsets) if len(self.textChunks[i].tags) > commonTags_length and len(self.textChunks[i].text) > 0]
        return filtered

    """
    /**
     * Get the (last) text chunk at a given char offset
     *
     * @method
     * @param {number} charOffset The char offset of the TextChunk
     * @return {TextChunk} The text chunk
     */
    """
    def getTextChunkAt(self, charOffset):
        i = 0
        for textChunk in self.textChunks[:-1]:
            if self.offsets[i+1].start > charOffset:
                break
            i += 1
        return textChunk

    """
    /**
     * Returns the list of SAX tags that apply to the whole text block
     * @return {Object[]} List of common SAX tags
     */
    """
    def getCommonTags(self):
        textChunks = self.textChunks
        n_textChunks = len(textChunks)
        if n_textChunks == 0:
            return []
        commonTags = textChunks[0].tags[:]
        for textChunk in textChunks:
            tags = textChunk.tags
            if len(tags) < len(commonTags):
                del commonTags[:len(tags)]
            for j in range(len(commonTags)):
                if commonTags[j].name != tags[j].name:
                    del commonTags[:j]
                    break
        return commonTags

    """
    /**
     * Create a new TextBlock, applying our annotations to a translation
     * @param {string} targetText Translated plain text
     * @param {Object[]} rangeMappings Array of source-target range index mappings
     * @return {TextBlock} Translated textblock with tags applied
     */
    """
    def translateTags(self, targetText, rangeMappings):
        # map of { offset: x, textChunks: [...] }
        emptyTextChunks = {}
        emptyTextChunkOffsets = []
        # list of { start: x, length: x, textChunk: x }
        textChunks = []

        def pushEmptyTextChunks(offset, chunks):
            for chunk in chunks:
                textChunks.append({
                    'start': offset,
                    'length': 0,
                    'textChunk': chunk
                })

        # Create map of empty text chunks, by offset
        for i in range(len(self.textChunks)):
            textChunk = self.textChunks[i]
            offset = self.offsets[i].start
            if textChunk.text:
                continue
            if not emptyTextChunks[offset]:
                emptyTextChunks[offset] = []
                emptyTextChunks[offset].append(textChunk)
        for offset in emptyTextChunks:
            emptyTextChunkOffsets.append(offset)
        emptyTextChunkOffsets.sort()

        for rangeMapping in rangeMappings:
            # Copy tags from source text start offset
            sourceRangeStart = rangeMapping.source.start
            sourceRangeEnd = sourceRangeStart + rangeMapping.source.length
            targetRangeStart = rangeMapping.target.start
            targetRangeEnd = targetRangeStart + rangeMapping.target.length
            sourceTextChunk = self.getTextChunkAt(rangeMapping.source.start)
            text = targetText[targetRangeStart : targetRangeEnd]
            textChunks.append({
                'start': targetRangeStart,
                'length': rangeMapping.target.length,
                'textChunk': TextChunk(
                    text,
                    sourceTextChunk.tags,
                    sourceTextChunk.inlineContent
                )
            })

            # Empty source text chunks will not be represented in the target plaintext
            # (because they have no plaintext representation). Therefore we must clone each
            # one manually into the target rich text.

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
                emptyTextChunks[offset] = None
                del emptyTextChunkOffsets[j]

        # Sort by start position
        textChunks.sort(key = lambda x: x.start)

        # Fill in any textChunk gaps using text with commonTags
        pos = 0
        commonTags = self.getCommonTags()
        iLen = len(textChunks)
        i = 0
        while i < iLen:
            textChunk = textChunks[i]
            if textChunk.start < pos:
                # throw new Error( 'Overlappping chunks at pos=' + pos + ', textChunks=' + i + ' start=' + textChunk.start );
                pass
            elif textChunk.start > pos:
                # Unmapped chunk: insert plaintext and adjust offset
                textChunks.insert(i, {
                    'start': pos,
                    'length': textChunk.start - pos,
                    'textChunk': TextChunk(
                        targetText[pos : textChunk.start],
                        commonTags,
                        None)
                    })
                i += 2
                iLen +=1
            pos = textChunk.start + len(textChunk)

        # Get trailing text and trailing whitespace
        tail = targetText[pos:]
        tailSpace = re.match('\s*$', tail)
        if tailSpace:
            space_length = tailSpace.end - tailSpace.start
            tail = tail[:-space_length]
        if tail:
            # Append tail as text with commonTags
            textChunks.append({
                'start': pos,
                'length': tail.length,
                'textChunk': TextChunk(tail, commonTags, None)
            })
            pos += len(tail)

        # Copy any remaining textChunks that have no text
        for offset in emptyTextChunkOffsets:
            pushEmptyTextChunks(pos, emptyTextChunks[offset])
        if tailSpace:
            # Append tailSpace as text with commonTags
            textChunks.append( {
                'start': pos,
                'length': len(tailSpace),
                'textChunk': TextChunk(tailSpace, commonTags, None)
            })
            pos += len(tail)

        return TextBlock([x.textChunk for x in textChunks])

    """
    /**
     * Return plain text representation of the text block
     * @return {string} Plain text representation
     */
    """
    def getPlainText(self):
        return ''.join([textChunk.text for textChunk in self.textChunks])

    """
    /**
     * Return HTML representation of the text block
     * @return {string} Plain text representation
     */
    """
    def getHtml(self):
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
                if textChunk.inlineContent.getHtml():
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

    """
    /**
     * Segment the text block into sentences
     * @param {Function} getBoundaries Function taking plaintext, returning offset array
     * @param {Function} getNextId Function taking 'segment'|'link', returning next ID
     * @return {TextBlock} Segmented version, with added span tags
     */
    """
    def segment(self, getBoundaries, getNextId):
        allTextChunks = []
        currentTextChunks = []
  
        def flushChunks():
            if not currentTextChunks:
                return
            modifiedTextChunks = addCommonTag(
                currentTextChunks, {
                    'name': 'span',
                    'attributes': {
                        'klass': 'cx-segment',
                        'data-segmentid': getNextId('segment')
                    }
                }
            )
            setLinkIdsInPlace(modifiedTextChunks, getNextId)
            allTextChunks.extend(modifiedTextChunks)
            currentTextChunks = []

        # for each chunk, split at any boundaries that occur inside the chunk
        groups = getChunkBoundaryGroups(
            getBoundaries(self.getPlainText()),
            self.textChunks,
            lambda x: len(x.text)
        )
        
        offset = 0
        for group in groups:
            textChunk = group.chunk
            boundaries = group.boundaries
            for boundary in boundaries:
                relOffset = boundary - offset
                if relOffset == 0:
                    flushChunks()
                else:
                    leftPart = TextChunk(
                        textChunk.text[:relOffset],
                        textChunk.tags[:],
                        None
                    )
                    rightPart = TextChunk(
                        textChunk.text[relOffset:],
                        textChunk.tags[:],
                        textChunk.inlineContent
                    )
                    currentTextChunks.append(leftPart)
                    offset += relOffset
                    flushChunks()
                    textChunk = rightPart
        flushChunks()
        return TextBlock(allTextChunks)

    """
    /**
     * Dump an XML Array version of the linear representation, for debugging
     *
     * @method
     * @param {string} pad Whitespace to indent XML elements
     * @return {string[]} Array that will concatenate to an XML string representation
     */
    """
    def dumpXmlArray(self, pad):
        dump = []
        for chunk in self.textChunks:
            tagsDump = dumpTags(chunk.tags)
            tagsAttr = tagsDump and ' tags="' + tagsDump + '"' or ''
            if chunk.text:
                dump.append(
                    pad + '<cxtextchunk' + tagsAttr + '>' +
                    esc(chunk.text).replace('\n', '&#10;') +
                    '</cxtextchunk>'
                )
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
