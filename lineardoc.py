# -*- coding: utf-8 -*-

# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

"""
FROM TextChunk.js
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

"""
FROM Utils.js
/**
 * Find all matches of regex in text, calling callback with each match object
 *
 * @param {string} text The text to search
 * @param {Regex} regex The regex to search; should be created for this function call
 * @param {Function} callback Function to call with each match
 * @return {Array} The return values from the callback
 */
"""
def findAll(text, regex, callback):
    boundaries = []
    while True:
        match = regex.match(text)
        if match is None:
            break
        boundary = callback(text, match)
        if boundary is not None:
            boundaries.push(boundary)
    return boundaries
"""
/**
 * Escape text for inclusion in HTML, not inside a tag
 *
 * @private
 * @param {string} str String to escape
 * @return {string} Escaped version of the string
 */
"""
import cgi
def esc(string):
    return cgi.escape(string)

"""
/**
 * Escape text for inclusion inside an HTML attribute
 *
 * @private
 * @param {string} str String to escape
 * @return {string} Escaped version of the string
 */
"""
html_escape_table = {
     "&": "&amp;",
     '"': "&quot;",
     "'": "&apos;",
     ">": "&gt;",
     "<": "&lt;",
     }
def escAttr(string):
    return "".join(html_escape_table.get(c, c) for c in string)

"""
/**
 * Render a SAX open tag into an HTML string
 *
 * @private
 * @param {Object} tag Tag to render
 * @return {string} Html representation of open tag
 */
"""
def getOpenTagHtml(tag):
    html = [ '<' + esc(tag.name)]
    attributes = []
    for attr in tag.attributes:
        attributes.push(attr)
    attributes.sort()
    for attr in attributes:
        html.push(' ' + esc(attr) + '="' + escAttr(tag.attributes[attr]) + '"')
    if tag.isSelfClosing:
        html.push(' /')
    html.push('>')
    return ''.join(html)

"""
/**
 * Clone a SAX open tag
 *
 * @private
 * @param {Object} tag Tag to clone
 * @return {Object} Cloned tag
 */
"""
def cloneOpenTag(tag):
    newTag = {
        'name': tag.name,
        'attributes': {}
    }
    for attr in tag.attributes:
        newTag.attributes[attr] = tag.attributes[attr]
    return newTag

"""
/**
 * Render a SAX close tag into an HTML string
 *
 * @private
 * @param {Object} tag Name of tag to close
 * @return {string} Html representation of close tag
 */
"""
def getCloseTagHtml(tag):
    if tag.isSelfClosing:
        return ''
    return '</' + esc(tag.name) + '>'

"""
/**
 * Represent an inline tag as a single XML attribute, for debugging purposes
 *
 * @private
 * @param {Object[]} tagArray SAX open tags
 * @return {string[]} Tag names
 */
"""
def dumpTags(tagArray):
    tagDumps = []
    if not tagArray:
        return ''
    for tag in tagArray:
        attrDumps = []
        for attr in tag.attributes:
            attrDumps.push(attr + '=' + escAttr(tag.attributes[attr]))
        tagDumps.push(tag.name + len(attrDumps) and ':' or '' + ','.join(attrDumps))
    if not tagDumps:
        return ''
    return ' '.join(tagDumps)

"""
/**
 * Detect whether this is a mediawiki reference span
 */

/**
 * Detect whether this is a segment.
 * Every statement in the content is a segment and these segments are
 * identified using segmentation module.
 *
 * @param {Object} tag SAX open tag object
 * @return {boolean} Whether the tag is a segment or not
 */
function isSegment( tag ) {
    if ( tag.name === 'span' && tag.attributes.class === 'cx-segment' ) {
        return true;
    }
    return false;
}

/**
 * Determine whether a tag is an inline empty tag
 *
 * @private
 * @param {string} tagName The name of the tag (lowercase)
 * @return {boolean} Whether the tag is an inline empty tag
 */
function isInlineEmptyTag( tagName ) {
    // link/meta as they're allowed anywhere in HTML5+RDFa, and must be treated as void
    // flow content. See http://www.w3.org/TR/rdfa-in-html/#extensions-to-the-html5-syntax
    return tagName === 'br' || tagName === 'img' || tagName === 'link' || tagName === 'meta';
}

/**
 * Find the boundaries that lie in each chunk
 *
 * Boundaries lying between chunks lie in the latest chunk possible.
 * Boundaries at the start of the first chunk, or the end of the last, are not included.
 * Therefore zero-width chunks never have any boundaries
 *
 * @param {number[]} boundaries Boundary offsets
 * @param {Object[]} chunks Chunks to which the boundaries apply
 * @param {Function} getLength Function returning the length of a chunk
 * @return {Object[]} Array of {chunk: ch, boundaries: [...]}
 */
function getChunkBoundaryGroups( boundaries, chunks, getLength ) {
    var i, len, groupBoundaries, chunk, chunkLength, boundary,
        groups = [],
        offset = 0,
        boundaryPtr = 0;

    // Get boundaries in order, disregarding the start of the first chunk
    boundaries = boundaries.slice();
    boundaries.sort( function ( a, b ) {
        return a - b;
    } );
    while ( boundaries[ boundaryPtr ] === 0 ) {
        boundaryPtr++;
    }
    for ( i = 0, len = chunks.length; i < len; i++ ) {
        groupBoundaries = [];
        chunk = chunks[ i ];
        chunkLength = getLength( chunk );
        while ( true ) {
            boundary = boundaries[ boundaryPtr ];
            if ( boundary === undefined || boundary > offset + chunkLength - 1 ) {
                // beyond the interior of this chunk
                break;
            }
            // inside the interior of this chunk
            groupBoundaries.push( boundary );
            boundaryPtr++;
        }
        offset += chunkLength;
        groups.push( {
            chunk: chunk,
            boundaries: groupBoundaries
        } );
        // Continue even if past boundaries: need to add remaining chunks
    }
    return groups;
}

/**
 * Add a tag to consecutive text chunks, above common tags but below others
 *
 * @private
 * @param {TextChunk[]} textChunks Consecutive text chunks
 * @param {Object} tag Tag to add
 * @return {TextChunk[]} Copy of the text chunks with the tag inserted
 */
function addCommonTag( textChunks, tag ) {
    var i, iLen, commonTags, commonTagLength, j, jLen, textChunk, tags, newTextChunks, newTags;
    if ( textChunks.length === 0 ) {
        return [];
    }
    // Find length of common tags
    commonTags = textChunks[ 0 ].tags.slice();
    for ( i = 1, iLen = textChunks.length; i < iLen; i++ ) {
        tags = textChunks[ i ].tags;
        for ( j = 0, jLen = Math.min( commonTags.length, tags.length ); j < jLen; j++ ) {
            if ( commonTags[ j ] !== tags[ j ] ) {
                break;
            }
        }
        if ( commonTags.length > j ) {
            // truncate to matched length
            commonTags.length = j;
        }
    }
    commonTagLength = commonTags.length;
    // Build new chunks with segment span inserted
    newTextChunks = [];
    for ( i = 0, iLen = textChunks.length; i < iLen; i++ ) {
        textChunk = textChunks[ i ];
        newTags = textChunk.tags.slice();
        newTags.splice( commonTagLength, 0, tag );
        newTextChunks.push( new TextChunk(
            textChunk.text,
            newTags,
            textChunk.inlineContent
        ) );
    }
    return newTextChunks;
}

/**
 * Set link IDs in-place on text chunks
 *
 * @private
 * @param {TextChunk[]} textChunks Consecutive text chunks
 * @param {Function} getNextId function accepting 'link' and returning next ID
 */
function setLinkIdsInPlace( textChunks, getNextId ) {
    var i, iLen, j, jLen, tags, tag, href;
    for ( i = 0, iLen = textChunks.length; i < iLen; i++ ) {
        tags = textChunks[ i ].tags;
        for ( j = 0, jLen = tags.length; j < jLen; j++ ) {
            tag = tags[ j ];
            if (
                tag.name === 'a' &&
                tag.attributes.href !== undefined &&
                tag.attributes[ 'data-linkid' ] === undefined
            ) {
                // Hack: copy href, then remove it, then re-add it, so that
                // attributes appear in alphabetical order (ugh)
                href = tag.attributes.href;
                delete tag.attributes.href;
                tag.attributes.class = 'cx-link';
                tag.attributes[ 'data-linkid' ] = getNextId( 'link' );
                tag.attributes.href = href;
            }
        }
    }
}

module.exports = {
    esc: esc,
    findAll: findAll,
    dumpTags: dumpTags,
    setLinkIdsInPlace: setLinkIdsInPlace,
    addCommonTag: addCommonTag,
    getChunkBoundaryGroups: getChunkBoundaryGroups,
    isReference: isReference,
    isSegment: isSegment,
    getOpenTagHtml: getOpenTagHtml,
    isInlineEmptyTag: isInlineEmptyTag,
    getCloseTagHtml: getCloseTagHtml,
    cloneOpenTag: cloneOpenTag
};
"""


"""
FROM TextBlock.js
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
            cursor += offset.length

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
    TextBlock.prototype.getTextChunkAt = function ( charOffset ) {
        // TODO: bisecting instead of linear search
        var i, len;
        for ( i = 0, len = this.textChunks.length - 1; i < len; i++ ) {
            if ( this.offsets[ i + 1 ].start > charOffset ) {
                break;
            }
        }
        return this.textChunks[ i ];
    };
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
     *
     * @return {Object[]} List of common SAX tags
     */
    TextBlock.prototype.getCommonTags = function () {
        var i, iLen, j, jLen, commonTags, tags;
        if ( this.textChunks.length === 0 ) {
            return [];
        }
        commonTags = this.textChunks[ 0 ].tags.slice();
        for ( i = 0, iLen = this.textChunks.length; i < iLen; i++ ) {
            tags = this.textChunks[ i ].tags;
            if ( tags.length < commonTags.length ) {
                commonTags.splice( tags.length );
            }
            for ( j = 0, jLen = commonTags.length; j < jLen; j++ ) {
                if ( commonTags[ j ].name !== tags[ j ].name ) {
                    // truncate
                    commonTags.splice( j );
                    break;
                }
            }
        }
        return commonTags;
    };
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
     *
     * @method
     * @param {string} targetText Translated plain text
     * @param {Object[]} rangeMappings Array of source-target range index mappings
     * @return {TextBlock} Translated textblock with tags applied
     */
    TextBlock.prototype.translateTags = function ( targetText, rangeMappings ) {
        var i, iLen, j, rangeMapping, sourceTextChunk, text, pos, textChunk, offset,
            sourceRangeEnd, targetRangeEnd, tail, tailSpace, commonTags,
            // map of { offset: x, textChunks: [...] }
            emptyTextChunks = {},
            emptyTextChunkOffsets = [],
            // list of { start: x, length: x, textChunk: x }
            textChunks = [];
    
        function pushEmptyTextChunks( offset, chunks ) {
            var c, cLen;
            for ( c = 0, cLen = chunks.length; c < cLen; c++ ) {
                textChunks.push( {
                    start: offset,
                    length: 0,
                    textChunk: chunks[ c ]
                } );
            }
        }
    
        // Create map of empty text chunks, by offset
        for ( i = 0, iLen = this.textChunks.length; i < iLen; i++ ) {
            textChunk = this.textChunks[ i ];
            offset = this.offsets[ i ].start;
            if ( textChunk.text.length > 0 ) {
                continue;
            }
            if ( !emptyTextChunks[ offset ] ) {
                emptyTextChunks[ offset ] = [];
            }
            emptyTextChunks[ offset ].push( textChunk );
        }
        for ( offset in emptyTextChunks ) {
            emptyTextChunkOffsets.push( offset );
        }
        emptyTextChunkOffsets.sort( function ( a, b ) {
            return a - b;
        } );
    
        for ( i = 0, iLen = rangeMappings.length; i < iLen; i++ ) {
            // Copy tags from source text start offset
            rangeMapping = rangeMappings[ i ];
            sourceRangeEnd = rangeMapping.source.start + rangeMapping.source.length;
            targetRangeEnd = rangeMapping.target.start + rangeMapping.target.length;
            sourceTextChunk = this.getTextChunkAt( rangeMapping.source.start );
            text = targetText.substr( rangeMapping.target.start, rangeMapping.target.length );
            textChunks.push( {
                start: rangeMapping.target.start,
                length: rangeMapping.target.length,
                textChunk: new TextChunk(
                    text,
                    sourceTextChunk.tags,
                    sourceTextChunk.inlineContent
                )
            } );
    
            // Empty source text chunks will not be represented in the target plaintext
            // (because they have no plaintext representation). Therefore we must clone each
            // one manually into the target rich text.
    
            // Iterate through all remaining emptyTextChunks
            for ( j = 0; j < emptyTextChunkOffsets.length; j++ ) {
                offset = emptyTextChunkOffsets[ j ];
                // Check whether chunk is in range
                if ( offset < rangeMapping.source.start || offset > sourceRangeEnd ) {
                    continue;
                }
                // Push chunk into target text at the current point
                pushEmptyTextChunks( targetRangeEnd, emptyTextChunks[ offset ] );
                // Remove chunk from remaining list
                delete emptyTextChunks[ offset ];
                emptyTextChunkOffsets.splice( j, 1 );
                // Decrement pointer to match removal
                j--;
            }
        }
        // Sort by start position
        textChunks.sort( function ( textChunk1, textChunk2 ) {
            return textChunk1.start - textChunk2.start;
        } );
        // Fill in any textChunk gaps using text with commonTags
        pos = 0;
        commonTags = this.getCommonTags();
        for ( i = 0, iLen = textChunks.length; i < iLen; i++ ) {
            textChunk = textChunks[ i ];
            if ( textChunk.start < pos ) {
                throw new Error( 'Overlappping chunks at pos=' + pos + ', textChunks=' + i + ' start=' + textChunk.start );
            } else if ( textChunk.start > pos ) {
                // Unmapped chunk: insert plaintext and adjust offset
                textChunks.splice( i, 0, {
                    start: pos,
                    length: textChunk.start - pos,
                    textChunk: new TextChunk(
                        targetText.substr( pos, textChunk.start - pos ),
                        commonTags
                    )
                } );
                i++;
                iLen++;
            }
            pos = textChunk.start + textChunk.length;
        }
    
        // Get trailing text and trailing whitespace
        tail = targetText.substr( pos );
        tailSpace = tail.match( /\s*$/ )[ 0 ];
        if ( tailSpace ) {
            tail = tail.substr( 0, tail.length - tailSpace.length );
        }
    
        if ( tail ) {
            // Append tail as text with commonTags
            textChunks.push( {
                start: pos,
                length: tail.length,
                textChunk: new TextChunk( tail, commonTags )
            } );
            pos += tail.length;
        }
    
        // Copy any remaining textChunks that have no text
        for ( i = 0, iLen = emptyTextChunkOffsets.length; i < iLen; i++ ) {
            offset = emptyTextChunkOffsets[ i ];
            pushEmptyTextChunks( pos, emptyTextChunks[ offset ] );
        }
        if ( tailSpace ) {
            // Append tailSpace as text with commonTags
            textChunks.push( {
                start: pos,
                length: tailSpace.length,
                textChunk: new TextChunk( tailSpace, commonTags )
            } );
            pos += tail.length;
        }
        return new TextBlock( textChunks.map( function ( x ) {
            return x.textChunk;
        } ) );
    };
    """

    """
    /**
     * Return plain text representation of the text block
     *
     * @return {string} Plain text representation
     */
    TextBlock.prototype.getPlainText = function () {
        var i, len,
            text = [];
        for ( i = 0, len = this.textChunks.length; i < len; i++ ) {
            text.push( this.textChunks[ i ].text );
        }
        return text.join( '' );
    };
    """
    def getPlainText(self):
        return ''.join([textChunk.text for textChunk in self.textChunks])

    """
    /**
     * Return HTML representation of the text block
     *
     * @return {string} Plain text representation
     */
    TextBlock.prototype.getHtml = function () {
        var i, iLen, j, jLen, textChunk, matchTop, oldTags,
            html = [];
    
        // Start with no tags open
        oldTags = [];
        for ( i = 0, iLen = this.textChunks.length; i < iLen; i++ ) {
            textChunk = this.textChunks[ i ];
    
            // Compare tag stacks; render close tags and open tags as necessary
            // Find the highest offset up to which the tags match on
            matchTop = -1;
            for ( j = 0, jLen = Math.min( oldTags.length, textChunk.tags.length ); j < jLen; j++ ) {
                if ( oldTags[ j ] === textChunk.tags[ j ] ) {
                    matchTop = j;
                } else {
                    break;
                }
            }
            for ( j = oldTags.length - 1; j > matchTop; j-- ) {
                html.push( Utils.getCloseTagHtml( oldTags[ j ] ) );
            }
            for ( j = matchTop + 1, jLen = textChunk.tags.length; j < jLen; j++ ) {
                html.push( Utils.getOpenTagHtml( textChunk.tags[ j ] ) );
            }
            oldTags = textChunk.tags;
    
            // Now add text and inline content
            html.push( Utils.esc( textChunk.text ) );
            if ( textChunk.inlineContent ) {
                if ( textChunk.inlineContent.getHtml ) {
                    // a sub-doc
                    html.push( textChunk.inlineContent.getHtml() );
                } else {
                    // an empty inline tag
                    html.push( Utils.getOpenTagHtml( textChunk.inlineContent ) );
                    html.push( Utils.getCloseTagHtml( textChunk.inlineContent ) );
                }
            }
        }
        // Finally, close any remaining tags
        for ( j = oldTags.length - 1; j >= 0; j-- ) {
            html.push( Utils.getCloseTagHtml( oldTags[ j ] ) );
        }
        return html.join( '' );
    };
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
                # ...
        return html

    """
    /**
     * Segment the text block into sentences
     *
     * @method
     * @param {Function} getBoundaries Function taking plaintext, returning offset array
     * @param {Function} getNextId Function taking 'segment'|'link', returning next ID
     * @return {TextBlock} Segmented version, with added span tags
     */
    TextBlock.prototype.segment = function ( getBoundaries, getNextId ) {
        var allTextChunks, currentTextChunks, groups, i, iLen, group, offset, textChunk, j, jLen,
            leftPart, rightPart, boundaries, relOffset;
    
        // Setup: currentTextChunks for current segment, and allTextChunks for all segments
        allTextChunks = [];
        currentTextChunks = [];
    """
    def segment(self):
        allTextChunks = []
        currentTextChunks = []
  
        """  
        function flushChunks() {
            var modifiedTextChunks;
            if ( currentTextChunks.length === 0 ) {
                return;
            }
            modifiedTextChunks = Utils.addCommonTag(
                currentTextChunks, {
                    name: 'span',
                    attributes: {
                        class: 'cx-segment',
                        'data-segmentid': getNextId( 'segment' )
                    }
                }
            );
            Utils.setLinkIdsInPlace( modifiedTextChunks, getNextId );
            allTextChunks.push.apply( allTextChunks, modifiedTextChunks );
            currentTextChunks = [];
        }

        // for each chunk, split at any boundaries that occur inside the chunk
        groups = Utils.getChunkBoundaryGroups(
            getBoundaries( this.getPlainText() ),
            this.textChunks,
            function ( textChunk ) {
                return textChunk.text.length;
            }
        );
        """
        
    """
    
        offset = 0;
        for ( i = 0, iLen = groups.length; i < iLen; i++ ) {
            group = groups[ i ];
            textChunk = group.chunk;
            boundaries = group.boundaries;
            for ( j = 0, jLen = boundaries.length; j < jLen; j++ ) {
                relOffset = boundaries[ j ] - offset;
                if ( relOffset === 0 ) {
                    flushChunks();
                } else {
                    leftPart = new TextChunk(
                        textChunk.text.substring( 0, relOffset ),
                        textChunk.tags.slice()
                    );
                    rightPart = new TextChunk(
                        textChunk.text.substring( relOffset ),
                        textChunk.tags.slice(),
                        textChunk.inlineContent
                    );
                    currentTextChunks.push( leftPart );
                    offset += relOffset;
                    flushChunks();
                    textChunk = rightPart;
                }
            }
            // Even if the textChunk is zero-width, it may have references
            currentTextChunks.push( textChunk );
            offset += textChunk.text.length;
        }
        flushChunks();
        return new TextBlock( allTextChunks );
    };
    
    /**
     * Dump an XML Array version of the linear representation, for debugging
     *
     * @method
     * @param {string} pad Whitespace to indent XML elements
     * @return {string[]} Array that will concatenate to an XML string representation
     */
    TextBlock.prototype.dumpXmlArray = function ( pad ) {
        var i, len, chunk, tagsDump, tagsAttr,
            dump = [];
        for ( i = 0, len = this.textChunks.length; i < len; i++ ) {
            chunk = this.textChunks[ i ];
            tagsDump = Utils.dumpTags( chunk.tags );
            tagsAttr = tagsDump ? ' tags="' + tagsDump + '"' : '';
            if ( chunk.text ) {
                dump.push(
                    pad + '<cxtextchunk' + tagsAttr + '>' +
                    Utils.esc( chunk.text ).replace( /\n/g, '&#10;' ) +
                    '</cxtextchunk>'
                );
            }
            if ( chunk.inlineContent ) {
                dump.push( pad + '<cxinlineelement' + tagsAttr + '>' );
                if ( chunk.inlineContent.dumpXmlArray ) {
                    // sub-doc: concatenate
                    dump.push.apply( dump, chunk.inlineContent.dumpXmlArray( pad + '  ' ) );
                } else {
                    dump.push( pad + '  ' + '<' + chunk.inlineContent.name + '/>' );
                }
                dump.push( pad + '</cxinlineelement>' );
            }
        }
        return dump;
    };
    """
