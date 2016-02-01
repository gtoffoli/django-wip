# This Python file uses the following encoding: utf-8

accented_vowel_map = {
    u"a'": u"à",
    u"e'": u"é",
    u"i'": u"ì",
    u"o'": u"ò",
    u"u'": u"ù",
}

def reverse(s):
    """return a string/array with its characters/elements in reverse order"""
    revchars = list(s)
    revchars.reverse()
    return ''.join(revchars)  

def put_accent_onlast(s):
    """put the accent on the last letter of a token ending with vowel"""
    accented = accented_vowel_map.get(s[-2:], s[-2:])
    return s[:-2] + accented

def dict_sum(int_dict):
    """return the sum of the values of an int dictionary"""
    return sum(int_dict.values(), 0)

"""
map unicode characters from general punctuation range
to quasi-equivalents characters in basic latin range
"""
unicode_to_latin1_dict = {
    u'\u2010': u'-',
    u'\u2011': u'-',
    u'\u2012': u'-',
    u'\u2013': u'-',
    u'\u2014': u'-',
    u'\u2015': u'-',
    u'\u2018': u"'",
    u'\u2019': u"'",
    u'\u201C': u'"',
    u'\u201D': u'"',
    u'\u2025': u'..',
    u'\u2026': u'...',
}

def filter_unicode(text):
    """
    replace in unicode text punctuation and other special characters,
    including those inserted by Word and other Windows applications;
    return None if no replacement has been performed
    """
    if not text:
        return None
    if not isinstance(text, unicode):
        return None
    out = text
    fixed = []
    for c in text:
        if ord(c) > 0x00FF:
            if c in fixed:
                continue
            s = unicode_to_latin1_dict.get(c, None)
            if s:
                out = out.replace(c, s)
                fixed.append(c)
    return fixed and out or None

"""
The following was adapted from Python26/Lib/idlelib/IOBinding.py
"""
import sys
import codecs
import re

try:
    from codecs import BOM_UTF8
except ImportError:
    # only available since Python 2.3
    BOM_UTF8 = '\xef\xbb\xbf'


# Try setting the locale, so that we can find out
# what encoding to use
try:
    import locale
    locale.setlocale(locale.LC_CTYPE, "")
except (ImportError, locale.Error):
    pass

# Encoding for file names
filesystemencoding = sys.getfilesystemencoding()

encoding = "ascii"
if sys.platform == 'win32':
    # On Windows, we could use "mbcs". However, to give the user
    # a portable encoding name, we need to find the code page
    try:
        encoding = locale.getdefaultlocale()[1]
        codecs.lookup(encoding)
    except LookupError:
        pass
else:
    try:
        # Different things can fail here: the locale module may not be
        # loaded, it may not offer nl_langinfo, or CODESET, or the
        # resulting codeset may be unknown to Python. We ignore all
        # these problems, falling back to ASCII
        encoding = locale.nl_langinfo(locale.CODESET)
        if encoding is None or encoding is '':
            # situation occurs on Mac OS X
            encoding = 'ascii'
        codecs.lookup(encoding)
    except (NameError, AttributeError, LookupError):
        # Try getdefaultlocale well: it parses environment variables,
        # which may give a clue. Unfortunately, getdefaultlocale has
        # bugs that can cause ValueError.
        try:
            encoding = locale.getdefaultlocale()[1]
            if encoding is None or encoding is '':
                # situation occurs on Mac OS X
                encoding = 'ascii'
            codecs.lookup(encoding)
        except (ValueError, LookupError):
            pass

encoding = encoding.lower()

coding_re = re.compile("coding[:=]\s*([-\w_.]+)")

def coding_spec(str):
    """Return the encoding declaration according to PEP 263.

    Raise LookupError if the encoding is declared but unknown.
    """
    # Only consider the first two lines
    str = str.split("\n")[:2]
    str = "\n".join(str)

    match = coding_re.search(str)
    if not match:
        return None
    name = match.group(1)
    # Check whether the encoding is known
    import codecs
    try:
        codecs.lookup(name)
    except LookupError:
        # The standard encoding error does not indicate the encoding
        raise LookupError, "Unknown encoding "+name
    return name

# def decode(self, chars):
def decode(chars):
    """Create a Unicode string

    If that fails, let Tcl try its best
    """
    fileencoding = None

    # Check presence of a UTF-8 signature first
    if chars.startswith(BOM_UTF8):
        try:
            chars = chars[3:].decode("utf-8")
        except UnicodeError:
            # has UTF-8 signature, but fails to decode...
            return chars
        else:
            # Indicates that this file originally had a BOM
            fileencoding = BOM_UTF8
            return chars
    # Next look for coding specification
    """
    try:
        enc = coding_spec(chars)
    except LookupError, name:
        tkMessageBox.showerror(
            title="Error loading the file",
            message="The encoding '%s' is not known to this Python "\
            "installation. The file may not display correctly" % name,
            master = self.text)
        enc = None
    """
    enc = coding_spec(chars)
    if enc:
        try:
            return unicode(chars, enc)
        except UnicodeError:
            pass
    # If it is ASCII, we need not to record anything
    try:
        return unicode(chars, 'ascii')
    except UnicodeError:
        pass
    # Finally, try the locale's encoding. This is deprecated;
    # the user should declare a non-ASCII encoding
    try:
        chars = unicode(chars, encoding)
        fileencoding = encoding
    except UnicodeError:
        pass
    return chars

import nltk
from nltk.probability import FreqDist

def collocations(tokens, min_score=0):
    from operator import itemgetter
    text = filter(lambda w: len(w) > 2, tokens)
    fd = FreqDist(tuple(text[i:i+2]) for i in range(len(text)-1))
    vocab = FreqDist(text)
    scored = [((w1,w2), fd[(w1,w2)] ** 3 / float(vocab[w1] * vocab[w2])) for w1, w2 in fd]
    if min_score:
        scored = [item for item in scored if item[1]>min_score]
    scored.sort(key=itemgetter(1), reverse=True)
    """
    collocations = map(itemgetter(0), scored)
    return collocations
    """
    return scored
