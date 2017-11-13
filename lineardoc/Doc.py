# -*- coding: utf-8 -*-

# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

from .Utils import cloneOpenTag, getOpenTagHtml, getCloseTagHtml

"""
 * An HTML document in linear representation.
 *
 * The document is a list of items, where each items is
 * - a block open tag (e.g. <p>); or
 * - a block close tag (e.g. </p>); or
 * - a TextBlock of annotated inline text; or
 * - "block whitespace" (a run of whitespace separating two block boundaries)
 *
 * Some types of HTML structure get normalized away. In particular:
 *
 * 1. Identical adjacent annotation tags are merged
 * 2. Inline annotations across block boundaries are split
 * 3. Annotations on block whitespace are stripped (except spans with 'data-mw')
 *
 * N.B. 2 can change semantics, e.g. identical adjacent links != single link
"""
class Doc:

    def __init__(self, wrapperTag):
        self.items = []
        self.wrapperTag = wrapperTag

    """
     * Clone the Doc, modifying as we go
     * @param {Function} callback The function to modify a node
     * @return {Doc} clone with modifications
    """
    def clone(self, callback):
        newDoc = Doc(self.wrapperTag)
        for item in self.items:
            newItem = callback(item)
            newDoc.addItem(newItem.type, newItem.item)
        return newDoc

    """
     * Add an item to the document
     * @param {string} type Type of item: open|close|blockspace|textblock
     * @param {Object|string|TextBlock} item Open/close tag, space or text block
    """
    def addItem(self, item_type, item):
        self.items.append({
            'type': item_type,
            'item': item
        })
        return self

    """
     * Segment the document into sentences
     * @param {Function} getBoundaries Function taking plaintext, returning offset array
     * @return {Doc} Segmented version of document TODO: warning: *shallow copied*.
    """
    def segment(self, getBoundaries):
        newDoc = Doc()
        nextId = 0

        def getNextId(item_type):
            if item_type in ('segment', 'link', 'block',):
                nextId += 1
                return nextId
            else:
                print ('Unknown ID type: ' + item_type)
                raise

            for item in self.items:
                if item['type'] == 'open':
                    tag = cloneOpenTag(item['item'])
                    if tag.attributes.id:
                        #Kept for restoring the old articles.
                        tag.attributes['data-seqid'] = getNextId('block')
                    else:
                        tag.attributes.id = getNextId('block')
                    newDoc.addItem(item['type'], tag)
                elif item['type'] == 'textblock':
                    newDoc.addItem(item['type'], item['item'])
                else:
                    textBlock = item['item']
                    newDoc.addItem(
                        'textblock',
                        textBlock.segment(getBoundaries, getNextId)
                    )
        return newDoc

    """
     * Dump an XML version of the linear representation, for debugging
     * @return {string} XML version of the linear representation
    """
    def dumpXml(self):
        return '\n'.join(self.dumpXmlArray(''))

    """
     * Dump the document in HTML format
     * @return {string} HTML document
    """
    def getHtml(self):
        html = []

        if self.wrapperTag:
            html.append(getOpenTagHtml(self.wrapperTag))

        for i in self.items:
            item_type = i['type']
            item = i['item']

            if isinstance(item, dict) and item['attributes'] and item['attributes']['class'] == 'cx-segment-block':
                continue

            if item_type == 'open':
                tag = item
                html.append(getOpenTagHtml(tag))
            elif item_type == 'close':
                tag = item
                html.append(getCloseTagHtml(tag))
            elif item_type == 'blockspace':
                space = item
                html.append(space)
            elif item_type == 'textblock':
                textblock = item
                # textblock html list may be quite long, so concatenate now
                html.append(textblock.getHtml())
            else:
                print ('Unknown item type at ' + item_type )
                raise
                
        if self.wrapperTag:
            html.append(getCloseTagHtml(self.wrapperTag))

        return ''.join(html)

    """
     * Dump an XML Array version of the linear representation, for debugging
     * @return {string[]} Array that will concatenate to an XML string representation
    """
    def dumpXmlArray(self, pad):
        dump = []

        if self.wrapperTag:
            dump.append(pad + '<cxwrapper>')

        for i in self.items:
            item_type = i['type']
            item = i['item']

            if item_type == 'open':
                # open block tag
                tag = item
                dump.append(pad + '<' + tag['name'] + '>' )
                if tag['name'] == 'head':
                    # Add a few things for easy display
                    dump.append(pad + '<meta charset="UTF-8" />')
                    dump.append(pad + '<style>cxtextblock { border: solid #88f 1px }')
                    dump.append(pad + 'cxtextchunk { border-right: solid #f88 1px }</style>')
            elif item_type == 'close':
                # close block tag
                tag = item
                dump.append(pad + '</' + tag['name'] + '>')
            elif item_type == 'blockspace':
                # Non-inline whitespace
                dump.append(pad + '<cxblockspace/>')
            elif item_type == 'textblock':
                # Block of inline text
                textBlock = item
                dump.append(pad + '<cxtextblock>')
                dump.extend(textBlock.dumpXmlArray(pad + '  '))
                dump.append(pad + '</cxtextblock>')
            else:
                print ('Unknown item type at ' + item_type )
                raise

        if self.wrapperTag:
            dump.append(pad + '</cxwrapper>')

        return dump

    """
     * Extract the text segments from the document
     * @return {string[]} balanced html fragments, one per segment
    """
    def getSegments(self):
        segments = []

        for item in self.items:
            if not item['type'] == 'textblock':
                continue
            textblock = item['item']
            segments.append(textblock.getHtml())
        return segments

    """ added by Giovanni Toffoli to get a printable LinearDoc representation like in
        https://www.mediawiki.org/wiki/Content_translation/Product_Definition/LinearDoc """
    def dump(self):
        lines = []
        for item in self.items:
            item_type = item['type']
            if item_type == 'textblock':
                for chunk in item['item'].textChunks:
                    tags = []
                    for tag_dict in chunk.tags:
                        tag = "'<%s" % tag_dict['name']
                        for attr_key, attr_value in tag_dict['attributes'].items():
                            tag += ' %s="%s"' % (attr_key, attr_value)
                        tag += ">'"
                        tags.append(tag)
                    tags = ', '.join(tags)
                    line = "{text:'%s', tags:[%s]}" % (chunk.text, tags)
                    if chunk.inlineContent:
                        pass
                    lines.append(line)
            else:
                line = '%s, %s' % (item_type, str(item['item']))
                lines.append(line)
        return '\n'.join(lines)

    """ added by Giovanni Toffoli """
    def getText(self):
        text_chunks = []
        for item in self.items:
            item_type = item['type']
            if item_type == 'textblock':
                for chunk in item['item'].textChunks:
                    text_chunks.append(chunk.text)
        return ''.join(text_chunks)
