import sys, os, inspect
import codecs
import re
import nltk

if (sys.version_info > (3, 0)):
    basestring = str

from wip.settings import RESOURCES_ROOT

class NltkTokenizer(object):
    """An object representing a tokenizer wizard"""

    def __init__(self, language=None, tokenizer=None, regexps=[], lowercasing=False, replacements=''):
        """ set language """
        language = language==u'it' and u'italian' or language
        self.language = language or u'italian'
        self.tokenizer = tokenizer or u'baroni'
        self.regexps = regexps
        self.lowercasing = lowercasing
        self.replacements = replacements

    def tokenize(self, text):
        """ tokenize """
        if self.tokenizer == u'punkt':
            tokenizer = nltk.data.load('tokenizers/punkt/%s.pickle' % self.language)
            return tokenizer.tokenize(text)
        elif self.tokenizer == u'baroni' or language==u'italian':
            return self.baroni_regexp_tokenize(text)
        else:
            # return []
            return nltk.word_tokenize(text)

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
            regexp_list = ["[a-zA-Z\xc0-\xff]+"]
            """
            this_dir, this_filename = os.path.split(__file__)
            regexp_path = os.path.join(this_dir, 'data', '%s_regexps.txt' % self.language)
            """
            regexp_path = os.path.join(RESOURCES_ROOT, 'it', '%s_regexps.txt' % self.language)
            f = codecs.open(regexp_path, 'r', 'unicode_escape')
            regexp_list = []
            for line in f.readlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    regexp_list.append(line)
            f.close()
        pattern = '|'.join(regexp_list)
        tokenizer = nltk.tokenize.regexp.RegexpTokenizer(pattern)
        if isinstance(text, basestring):
            tokens = tokenizer.tokenize(text)
            # tokens = [token.replace(u'\u2019', u"'") for token in tokens if isinstance(token, basestring)]
        else:
            tokens = tokenizer.batch_tokenize(text)
        return tokens
        """
        flags = re.UNICODE | re.MULTILINE | re.DOTALL
        self._regexp = re.compile(pattern, flags)
        return self._regexp.findall(text)
        """

    def apply_replacements(self, s, replacements):
        """ apply the replacements specified to text """
        return s
