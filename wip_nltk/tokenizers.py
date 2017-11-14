import sys, os, inspect
import codecs
import re
import nltk
from nltk.tokenize import TreebankWordTokenizer
from nltk.tokenize import word_tokenize

from django.conf import settings

if (sys.version_info > (3, 0)):
    basestring = str

# from wip.settings import RESOURCES_ROOT

class NltkTokenizer(object):
    """An object representing a tokenizer wizard"""

    # def __init__(self, language=None, tokenizer=None, regexps=[], lowercasing=False, replacements=''):
    def __init__(self, language=None, tokenizer=None, regexps=[], custom_regexps=[], lowercasing=False, replacements='', return_matches=False):
        self.tokenizer = tokenizer
        if not language or language==u'it':
            self.language = 'italian'
            self.tokenizer = self.tokenizer or u'baroni'
        self.tokenizer = self.tokenizer or u'word'
        self.regexps = regexps
        self.custom_regexps = custom_regexps
        self.lowercasing = lowercasing
        self.replacements = replacements
        self.return_matches = return_matches

    def tokenize(self, text):
        """ tokenize """
        if self.tokenizer == u'punkt':
            tokenizer = nltk.data.load('tokenizers/punkt/%s.pickle' % self.language)
            return tokenizer.tokenize(text)
        # elif self.tokenizer == u'baroni' or language==u'italian':
        elif self.tokenizer == u'baroni':
            return self.baroni_regexp_tokenize(text)
        else: # word
            # return nltk.word_tokenize(text)
            if self.lowercasing:
                text = text.lower()
            tokenizer = TreebankWordTokenizer()
            return tokenizer.tokenize(text)

    def baroni_regexp_tokenize(self, text):
        """ from regexp_tokenizer.pl by Marco Baroni, baroni AT sslmit.unibo.it """

        if self.lowercasing:
            if isinstance(text, basestring):
                text = text.lower()
            else:
                text = [line.lower() for line in text]
        if self.replacements:
            if isinstance(text, basestring):
                text = self.apply_replacements(text, self.replacements)
            else:
                text = [self.apply_replacements(line, self.replacements) for line in text]
        if self.regexps:
            regexp_list = self.regexps
        else:
            regexp_path = os.path.join(settings.RESOURCES_ROOT, 'it', '%s_regexps.txt' % self.language)
            f = codecs.open(regexp_path, 'r', 'unicode_escape')
            regexp_list = []
            for line in f.readlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    regexp_list.append(line)
            f.close()
            if self.custom_regexps:
                regexp_list = self.custom_regexps + regexp_list
        pattern = '|'.join(regexp_list)
        tokenizer = nltk.tokenize.regexp.RegexpTokenizer(pattern)
        if self.return_matches:
            compiled_re = re.compile(pattern)
            matches = compiled_re.finditer(text)
            return matches
        else:
            tokens = tokenizer.tokenize(text)
            return tokens

    def apply_replacements(self, s, replacements):
        """ apply the replacements specified to text """
        return s
