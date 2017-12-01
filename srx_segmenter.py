# -*- coding: utf-8 -*-

""" Segment text with SRX: cannot remember where this code comes from! """

import lxml.etree
import re

class SrxSegmenter:
    """ Handle segmentation with SRX regex format """
    def __init__(self, rule):
        self.non_breaks = rule.get('non_breaks', [])
        self.breaks = rule.get('breaks', [])

    def _get_break_points(self, regexes):
        return set([
            match.span(1)[1]
            for before, after in regexes
            for match in re.finditer(u'({})({})'.format(before, after), self.source_text)
        ])

    def get_non_break_points(self):
        """ Return segment non break points """
        return self._get_break_points(self.non_breaks)

    def get_break_points(self):
        """ Return segment break points """
        return self._get_break_points(self.breaks)

    def extract(self, source_text, verbose=False):
        """ Return segments and whitespaces. """
        self.source_text = source_text
        non_break_points = self.get_non_break_points()
        candidate_break_points = self.get_break_points()

        break_point = sorted(candidate_break_points - non_break_points)
        source_text = self.source_text
        if verbose:
            print ('non_break_points: ', non_break_points)
            print ('break_points: ', candidate_break_points)
            print ('break_point: ', break_point)

        segments = []
        boundaries = []
        whitespaces = []
        previous_foot = ""
        for start, end in zip([0] + break_point, break_point + [len(source_text)]):
            segment_with_space = source_text[start:end]
            candidate_segment = segment_with_space.strip()
            if not candidate_segment:
                previous_foot += segment_with_space
                continue

            head, segment, foot = segment_with_space.partition(candidate_segment)

            segments.append(segment)
            boundaries.append(end)
            whitespaces.append('{}{}'.format(previous_foot, head))
            previous_foot = foot
        whitespaces.append(previous_foot)

        # return segments, whitespaces
        return segments, boundaries, whitespaces

# def parse(srx_filepath):
def parse(srx_filepath, language_code=None):
    """ Parse SRX file and return it as a dict if no language_code is provided; 
        extract and return only the related rule list if a known language_code is provided """

    tree = lxml.etree.parse(srx_filepath)
    namespaces = {
        'ns': 'http://www.lisa.org/srx20'
    }

    languagerulename = None
    if language_code:
        for languagemap in tree.xpath('//ns:languagemap', namespaces=namespaces):
            languagepattern = languagemap.attrib.get('languagepattern')
            if re.search(languagepattern, language_code):
                languagerulename = languagemap.attrib.get('languagerulename')

    rules = {}

    for languagerule in tree.xpath('//ns:languagerule', namespaces=namespaces):
        rule_name = languagerule.attrib.get('languagerulename')
        if rule_name is None:
            continue

        current_rule = {
            'breaks': [],
            'non_breaks': [],
        }

        for rule in languagerule.xpath('ns:rule', namespaces=namespaces):
            is_break = rule.attrib.get('break', 'yes') == 'yes'
            rule_holder = current_rule['breaks'] if is_break else current_rule['non_breaks']

            beforebreak = rule.find('ns:beforebreak', namespaces=namespaces)
            beforebreak_text = '' if beforebreak.text is None else beforebreak.text

            afterbreak = rule.find('ns:afterbreak', namespaces=namespaces)
            afterbreak_text = '' if afterbreak.text is None else afterbreak.text

            rule_holder.append((beforebreak_text, afterbreak_text))

        rules[rule_name] = current_rule

    if languagerulename:
        return rules.get(languagerulename, [])
    else:
        return rules
