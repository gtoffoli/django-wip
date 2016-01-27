import os
import unittest

import srx_segmenter

# class SegmenterTest(unittest.TestCase):
class SegmenterTest(object):
    def setUp(self):
        srx_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'segment.srx')
        print(srx_filepath)
        self.rules = srx_segmenter.parse(srx_filepath)

    def test_ja(self):
        table = [
            {
                'expect': (
                    ["Hello.", "This is an example."],
                    ["", " ", ""]
                ),
                'source': ("Hello. This is an example."),
                'language': 'English',
            },
        ]

        for test in table:
            # segmenter = srx_segmenter.SrxSegmenter(self.rules[test['language']], test['source'])
            segmenter = srx_segmenter.SrxSegmenter(self.rules[test['language']])
            # self.assertEqual(test['expect'], segmenter.extract())
            # assert test['expect'] == segmenter.extract()
            # print segmenter.extract()
            print segmenter.extract(test['source'])
