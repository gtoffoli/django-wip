"""Segment text with SRX. Modified from: https://github.com/narusemotoki/srx_segmenter/blob/master/srx_segmenter.py
"""
__version__ = '0.0.2'

import lxml.etree
# import regex
import re
from typing import (
    List,
    Set,
    Tuple,
    Dict,
    Optional
)

class SrxSegmenter:
    """Handle segmentation with SRX regex format.
    """
    """
    def __init__(self, rule: Dict[str, List[Tuple[str, Optional[str]]]], source_text: str) -> None:
        self.source_text = source_text
    """
    def __init__(self, rule: Dict[str, List[Tuple[str, Optional[str]]]]) -> None:
        self.non_breaks = rule.get('non_breaks', [])
        self.breaks = rule.get('breaks', [])

    def _get_break_points(self, regexes: List[Tuple[str, str]]) -> Set[int]:
        return set([
            match.span(1)[1]
            for before, after in regexes
            # for match in regex.finditer('({})({})'.format(before, after), self.source_text)
            for match in re.finditer('({})({})'.format(before, after), self.source_text)
        ])

    def get_non_break_points(self) -> Set[int]:
        """Return segment non break points
        """
        # return self._get_break_points(self.non_breaks)
        non_break_points = []
        for before, after in self.non_breaks:
            for match in re.finditer(u'({})({})'.format(before, after), self.source_text):
                non_break_points.extend(range(match.start(1), match.end(1)+1))
        return set(non_break_points)

    def get_break_points(self) -> Set[int]:
        """Return segment break points
        """
        return self._get_break_points(self.breaks)

    # def extract(self) -> Tuple[List[str], List[str]]:
    def extract(self, source_text: str, verbose=False) -> Tuple[List[str], List[str]]:
        """Return segments and whitespaces.
        """
        self.source_text = source_text
        non_break_points = self.get_non_break_points()
        candidate_break_points = self.get_break_points()

        break_point = sorted(candidate_break_points - non_break_points)
        if verbose:
            print ('non_break_points: ', sorted(non_break_points))
            print ('break_points: ', sorted(candidate_break_points))
            print ('break_point: ', break_point)

        segments = []  # type: List[str]
        boundaries = []  # type: List[int]
        whitespaces = []  # type: List[str]
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


# def parse(srx_filepath: str) -> Dict[str, Dict[str, List[Tuple[str, Optional[str]]]]]:
def parse(srx_filepath: str, language_code=None) -> Dict[str, Dict[str, List[Tuple[str, Optional[str]]]]]:
    """Parse SRX file and return it.
    :param srx_filepath: is soruce SRX file.
    :return: dict
    """
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

    # return rules
    if languagerulename:
        return rules.get(languagerulename, [])
    else:
        return rules
