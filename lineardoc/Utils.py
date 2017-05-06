# -*- coding: utf-8 -*-

# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

"""
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
            boundaries.append(boundary)
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
    html = ['<' + esc(tag['name'])]
    attributes = []
    for attr in tag['attributes']:
        attributes.append(attr)
    attributes.sort()
    for attr in attributes:
        html.append(' ' + esc(attr) + '="' + escAttr(tag['attributes'][attr]) + '"')
    if tag.get('isSelfClosing', None):
        html.append(' /')
    html.append('>')
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
        'name': tag['name'],
        'attributes': {}
    }
    for attr in tag['attributes']:
        newTag['attributes'][attr] = tag['attributes'][attr]
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
    if tag.get('isSelfClosing', None):
        return ''
    return '</' + esc(tag['name']) + '>'

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
        for attr in tag['attributes']:
            attrDumps.append(attr + '=' + escAttr(tag['attributes'][attr]))
        tagDumps.append(tag['name'] + (len(attrDumps) and ':' or '') + ','.join(attrDumps))
    if not tagDumps:
        return ''
    return ' '.join(tagDumps)

"""
/**
 * Detect whether this is a mediawiki reference span
 * @param {Object} tag SAX open tag object
 * @return {boolean} Whether the tag is a mediawiki reference span
 */
"""
def isReference(tag):
    if tag['name']=='span' and tag['attributes'].get('typeof', '')=='mw:Extension/ref':
        # See https://www.mediawiki.org/wiki/Parsoid/MediaWiki_DOM_spec#Ref_and_References
        return True
    elif tag['name']=='sup' and tag['attributes'].get('klass', '')=='reference':
        # See "cite_reference_link" message of Cite extension
        # https://www.mediawiki.org/wiki/Extension:Cite
        return True
    return False

"""
/**
 * Detect whether this is a segment.
 * Every statement in the content is a segment and these segments are
 * identified using segmentation module.
 * @param {Object} tag SAX open tag object
 * @return {boolean} Whether the tag is a segment or not
 */
"""
def isSegment(tag):
    return tag['name']=='span' and tag['attributes'].get('klass', '')=='cx-segment'

"""
/**
 * Determine whether a tag is an inline empty tag
 * @param {string} tagName The name of the tag (lowercase)
 * @return {boolean} Whether the tag is an inline empty tag
 */
"""
def isInlineEmptyTag(tagName):
    return tagName in ('br', 'img', 'link', 'meta',)

"""
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
