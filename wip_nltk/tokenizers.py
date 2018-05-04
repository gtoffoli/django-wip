import sys, os
import codecs
import re
import nltk
from nltk.tokenize import TreebankWordTokenizer
from nltk.tokenize import word_tokenize, wordpunct_tokenize

from django.conf import settings

if (sys.version_info > (3, 0)):
    basestring = str

class NltkTokenizer(object):
    """An object representing a tokenizer wizard"""

    # def __init__(self, language_code='it', tokenizer_type='baroni', regexps=[], custom_regexps=[], lowercasing=False, replacements='', return_matches=False):
    def __init__(self, language_code='', tokenizer=None, tokenizer_type='', regexps=[], custom_regexps=[], lowercasing=False, replacements='', return_matches=False):
        self.language_code = language_code
        self.tokenizer_type = tokenizer_type
        self.regexps = regexps
        self.custom_regexps = custom_regexps
        self.lowercasing = lowercasing
        self.replacements = replacements
        self.return_matches = return_matches
        # added 180427
        self.tokenizer = tokenizer
        if not self.tokenizer and not self.tokenizer_type:
            if self.language_code == 'ar':
                self.tokenizer_type = 'wordpunct' # 'wordpunct' 'treebank' 'word'
            elif self.language_code:
                self.tokenizer_type = 'baroni'
        if self.tokenizer_type == 'punkt':
            self.tokenizer = nltk.data.load('tokenizers/punkt/%s.pickle' % self.language_code)
        elif self.tokenizer_type == 'treebank':
            self.tokenizer = TreebankWordTokenizer()

    def tokenize(self, text):
        """ changed 180427
        if self.tokenizer_type == u'punkt':
            tokenizer = nltk.data.load('tokenizers/punkt/%s.pickle' % self.language_code)
            return tokenizer.tokenize(text)
        elif self.tokenizer_type == u'baroni':
            return self.baroni_regexp_tokenize(text)
        else: # word
            if self.lowercasing:
                text = text.lower()
            tokenizer = TreebankWordTokenizer()
            return tokenizer.tokenize(text)
        """
        if self.lowercasing:
            text = text.lower()
        if self.tokenizer:
            return self.tokenizer.tokenize(text)
        elif self.tokenizer_type == 'word':
            return word_tokenize(text)
        elif self.tokenizer_type == 'wordpunct':
            return wordpunct_tokenize(text)
        elif self.tokenizer_type == 'baroni':
            return self.baroni_regexp_tokenize(text)
        else:
            return re.split("[ |\.\,\;\:\'\"]*", text)

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
            regexp_path = os.path.join(settings.RESOURCES_ROOT, self.language_code, 'tokenize.txt')
            if not os.path.isfile(regexp_path):
                regexp_path = os.path.join(settings.RESOURCES_ROOT, 'tokenize.txt')
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
