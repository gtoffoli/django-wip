# -*- coding: utf-8 -*-

# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

voidTags = ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']
voidTags_dict = dict([(tagName, True,) for tagName in voidTags])

from .TextChunk import TextChunk

def findAll(text, regex, callback):
    """ Find all matches of regex in text, calling callback with each match object
    text: The text to search
    regex: The regex to search; should be created for this function call
    callback: Function to call with each match
    return: The return values from the callback
    """
    boundaries = []
    while True:
        match = regex.match(text)
        if match is None:
            break
        boundary = callback(text, match)
        if boundary is not None:
            boundaries.append(boundary)
    return boundaries

import cgi
def esc(string):
    """ Escape text for inclusion in HTML, not inside a tag """
    return cgi.escape(string)

html_escape_table = {
     "&": "&amp;",
     '"': "&quot;",
     "'": "&apos;",
     ">": "&gt;",
     "<": "&lt;",
     }
def escAttr(string):
    """ Escape text for inclusion inside an HTML attribute """
    return "".join(html_escape_table.get(c, c) for c in string)

def getOpenTagHtml(tag):
    """ Render a SAX open tag into an HTML string """
    html = ['<' + esc(tag['name'])]
    attributes = []
    for attr in tag['attributes']:
        attributes.append(attr)
    attributes.sort()
    for attr in attributes:
        html.append(' ' + esc(attr) + '="' + escAttr(tag['attributes'][attr]) + '"')
    # if tag.get('isSelfClosing', None):
    if voidTags_dict.get(tag['name'], None):
        html.append(' /')
    html.append('>')
    return ''.join(html)

def cloneOpenTag(tag):
    """ Clone a SAX open tag """
    newTag = {
        'name': tag['name'],
        'attributes': {}
    }
    for attr in tag['attributes']:
        newTag['attributes'][attr] = tag['attributes'][attr]
    return newTag

def getCloseTagHtml(tag):
    """ Render a SAX close tag into an HTML string """
    # if tag.get('isSelfClosing', None):
    if voidTags_dict.get(tag['name'], None):
        return ''
    return '</' + esc(tag['name']) + '>'

def dumpTags(tagArray):
    """ Represent an inline tag as a single XML attribute, for debugging purposes """
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

def isReference(tag):
    """ Detect whether this is a mediawiki reference span """
    if tag['name']=='span' and tag['attributes'].get('typeof', '')=='mw:Extension/ref':
        # See https://www.mediawiki.org/wiki/Parsoid/MediaWiki_DOM_spec#Ref_and_References
        return True
    elif tag['name']=='sup' and tag['attributes'].get('klass', '')=='reference':
        # See "cite_reference_link" message of Cite extension
        # https://www.mediawiki.org/wiki/Extension:Cite
        return True
    return False

def isSegment(tag):
    """ Detect whether this is a segment. """
    return tag['name']=='span' and tag['attributes'].get('klass', '')=='cx-segment'

def isInlineEmptyTag(tagName):
    """ Determine whether a tag is an inline empty tag """
    return tagName in ('br', 'img', 'link', 'meta',)

def getChunkBoundaryGroups (boundaries, chunks, getLength):
    """ Find the boundaries that lie in each chunk """
    groups = []
    offset = 0
    boundaryPtr = 0
    #  Get boundaries in order, disregarding the start of the first chunk
    boundaries = boundaries[:]
    boundaries.sort()
    while boundaries[boundaryPtr] == 0:
        boundaryPtr += 1
    for chunk in chunks:
        groupBoundaries = []
        chunkLength = getLength(chunk)
        while True:
            boundary = boundaries[boundaryPtr]
            if not boundary or boundary > offset+chunkLength-1:
                # beyond the interior of this chunk
                break
            # inside the interior of this chunk
            groupBoundaries.append(boundary)
            boundaryPtr += 1
        offset += chunkLength
        groups.append( { 'chunk': chunk, 'boundaries': groupBoundaries })
        # Continue even if past boundaries: need to add remaining chunks
    return groups

def addCommonTag (textChunks, tag):
    """ Add a tag to consecutive text chunks, above common tags but below others """
    if not len(textChunks):
        return []
    # Find length of common tags
    commonTags = textChunks[0].tags[:]
    for textChunk in textChunks:
        tags = textChunk.tags
        jLen = min(len(commonTags), len(tags))
        for j in range(jLen):
            if commonTags[j] != tags[j]:
                break;
        if len(commonTags) > jLen:
            # truncate to matched length
            commonTags = commonTags[:jLen]
    commonTagLength = len(commonTags)
    # Build new chunks with segment span inserted
    newTextChunks = []
    for textChunk in textChunks:
        tags = textChunk.tags
        newTags = tags[:commonTagLength]+[tag]+tags[commonTagLength:]
        newTextChunks.append(TextChunk(textChunk.text, newTags, textChunk.inlineContent))
    return newTextChunks

def setLinkIdsInPlace(textChunks, getNextId):
    """ Set link IDs in-place on text chunks (???) """
    for textChunk in textChunks:
        for tag in textChunk.tags:
            if tag['name']=='a' and tag['attributes'].get('href', '') and not tag['attributes'].get('data-linkid', ''):
                tag['attributes']['class'] = 'cx-link'
                tag['attributes']['data-linkid'] = getNextId('link')

def sameTags(tags1, tags2):
    """ added by Giovanni Toffoli
        return True if lists tags1 and tags2 include the same tags in the same order """
    nTags1 = len(tags1)
    nTags2 = len(tags2)
    if not nTags2 == nTags1:
        return False
    if not nTags1:
        return True
    for i in range(nTags1):
        tag1 = tags1[i]
        tag2 = tags2[i]
        if not tag1['name'] == tag2['name']:
            return False
        attrs1 = tag1.get('attributes', {})
        attrs2 = tag2.get('attributes', {})
        if len(attrs1) != len(attrs2):
            return False        
        for key in attrs1.keys():
            if attrs1[key] != attrs2.get(key, None):
                return False

    return True
