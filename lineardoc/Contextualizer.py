# -*- coding: utf-8 -*-

# converted from the LinearDoc javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/tree/master/lineardoc

class Contextualizer:
    """ Contextualizer for HTML - tracks the segmentation context of the currently open node """

    def __init__(self):
        self.contexts = []

    def getChildContext(self, openTag):
        # Change to 'media' context inside figure
        if openTag['name'] == 'figure':
            return 'media'
        # Exception: return to undefined context inside figure//figcaption
        if openTag['name'] == 'figcaption':
            return None
        # No change: same as parent context
        return self.getContext()

    def getContext(self):
        """ Get the current context """
        return self.contexts and self.contexts[-1] or None

    def onOpenTag(self, openTag):
        """ Call when a tag opens """
        self.contexts.append(self.getChildContext(openTag))

    def onCloseTag(self):
        """ Call when a tag closes (or just after an empty tag opens) """
        self.contexts.pop()

    def canSegment(self):
        """ Determine whether sentences can be segmented into spans in this context """
        return self.getContext() is None
