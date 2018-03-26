"""
https://en.wikipedia.org/wiki/XLIFF
https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=xliff
https://wiki.oasis-open.org/xliff/FAQ
http://docs.oasis-open.org/xliff/xliff-core/xliff-core.html
http://docs.oasis-open.org/xliff/v1.2/os/xliff-core.html
http://docs.oasis-open.org/xliff/xliff-core/v2.1/csprd01/xliff-core-v2.1-csprd01.html
https://www.k15t.com/blog/2017/06/xliff-standard-file-format-for-translations
https://pypi.python.org/pypi/itools/0.77.8 <----- see itools.xliff
https://github.com/translate/pyliff
https://pypi.python.org/pypi/slc.xliff/1.3.3
https://pypi.python.org/pypi/translate-toolkit/1.0.1
"""

### from itools.srx.segment.py
# Constants
TEXT, START_FORMAT, END_FORMAT = range(3)

### from itools.datatypes.primitive.py
class XMLContent(object):

    @staticmethod
    def encode(value):
        return value.replace('&', '&amp;').replace('<', '&lt;')

    @staticmethod
    def decode(value):
        return value.replace('&amp;', '&').replace('&lt;', '<')

### from itools.datatypes.primitive.py
class XMLAttribute(object):

    @staticmethod
    def encode(value):
        value = value.replace('&', '&amp;').replace('<', '&lt;')
        return value.replace('"', '&quot;')

    @staticmethod
    def decode(value):
        value = value.replace('&amp;', '&').replace('&lt;', '<')
        return value.replace('&quot;', '"')

### from itools.xliff.xliff.py
doctype = (
    '<!DOCTYPE xliff PUBLIC "-//XLIFF//DTD XLIFF//EN"\n'
    '  "http://www.oasis-open.org/committees/xliff/documents/xliff.dtd">\n')

### from itools.xliff.xliff.py
# FIXME TMXNote and XLFNote are the same
class XLFNote(object):

    def __init__(self, text='', attributes=None):
        if attributes is None:
            attributes = {}

        self.text = text
        self.attributes = attributes


    def to_str(self):
        # Attributes
        attributes = []
        for attr_name in self.attributes:
            attr_value = self.attributes[attr_name]
            attr_value = XMLContent.encode(attr_value)
            if attr_name == 'lang':
                attr_name = 'xml:lang'
            attributes.append(' %s="%s"' % (attr_name, attr_value))
        attributes = ''.join(attributes)
        # Ok
        return '<note%s>%s</note>\n' % (attributes, self.text)

### from itools.xliff.xliff.py
class XLFUnit(object):

    def __init__(self, attributes):
        self.source = None
        self.target = None
        self.context = None
        self.line = None
        self.attributes = attributes
        self.notes = []


    def to_str(self):
        s = []
        if self.attributes != {}:
            att = ['%s="%s"' % (k, self.attributes[k])
                  for k in self.attributes.keys() if k != 'space']
            # s.append('  <trans-unit %s ' % '\n'.join(att))
            s.append('  <trans-unit %s ' % ' '.join(att))
            if 'space' in self.attributes.keys():
                s.append('xml:space="%s"' % self.attributes['space'])
            s.append('>\n')
        else:
            s.append('  <trans-unit>\n')

        if self.source:
            s.append('    <source>')
            # s.append(encode_source(self.source))
            s.append(self.source)
            s.append('</source>\n')

        # if self.target:
        if True:
            s.append('    <target>')
            # s.append(encode_source(self.target))
            s.append(self.target)
            s.append('</target>\n')

        if self.line is not None or self.context is not None:
            s.append('    <context-group name="context info">\n')
            if self.line is not None:
                s.append('        <context context-type="linenumber">%d' %
                         self.line)
                s.append('</context>\n')
            if self.context is not None:
                s.append('        <context context-type="x-context">%s' %
                         self.context)
                s.append('</context>\n')
            s.append('    </context-group>\n')

        for note in self.notes:
            s.append(note.to_str())

        s.append('  </trans-unit>\n')
        return ''.join(s)

### from itools.xliff.xliff.py
class File(object):

    def __init__(self, original, attributes):
        self.original = original
        self.attributes = attributes
        # self.body = {}
        self.body = []
        self.header = []

    def to_str(self):
        output = []

        # Opent tag
        open_tag = '<file original="%s"%s>\n'
        attributes = [
            ' %s="%s"' % (key, XMLAttribute.encode(value))
            for key, value in self.attributes.items() if key != 'space']
        if 'space' in self.attributes:
            attributes.append(' xml:space="%s"' % self.attributes['space'])
        attributes = ''.join(attributes)
        open_tag = open_tag % (self.original, attributes)
        output.append(open_tag)
        # The header
        if self.header:
            output.append('<header>\n')
            for line in self.header:
                output.append(line.to_str())
            output.append('</header>\n')
        # The body
        output.append('<body>\n')
        if self.body:
            # output.extend([ unit.to_str() for unit in self.body.values() ])
            output.extend([ unit.to_str() for unit in self.body ])
        output.append('</body>\n')
        # Close tag
        output.append('</file>\n')

        return ''.join(output)

### from itools.xliff.xliff.py
# class XLFFile(TextFile):
class XLFFile(object):

    class_mimetypes = ['application/x-xliff']
    class_extension = 'xlf'

    # def new(self, version='1.0'):
    def __init__(self, version='1.2'):
        self.version = version
        self.lang = None
        self.files = {}

    #######################################################################
    # Load

    #######################################################################
    # Save
    #######################################################################
    def to_str(self, encoding='UTF-8'):
        output = []
        # The XML declaration
        output.append('<?xml version="1.0" encoding="%s"?>\n' % encoding)
        # The Doctype
        output.append(doctype)
        # <xliff>
        if self.lang:
            template = '<xliff version="%s">\n'
            output.append(template % self.version)
        else:
            template = '<xliff version="%s" xml:lang="%s">\n'
            output.append(template % (self.version, self.lang))
        # The files
        for file in self.files.values():
            output.append(file.to_str())
        # </xliff>
        output.append('</xliff>\n')
        # Ok
        return ''.join(output).encode(encoding)

    #######################################################################
    # API
    #######################################################################
    def build(self, version, files):
        self.version = version
        self.files = files

    def get_languages(self):
        files_id, sources, targets = [], [], []
        for file in self.files:
            file_id = file.attributes['original']
            source = file.attributes['source-language']
            target = file.attributes.get('target-language', '')

            if file_id not in files_id:
                files_id.append(file_id)
            if source not in sources:
                sources.append(source)
            if target not in targets:
                targets.append(target)

        return ((files_id, sources, targets))

    # def add_unit(self, filename, source, context, line):
    def add_unit(self, filename, source, target, context, line):
        file = self.files.setdefault(filename, File(filename, {}))
        unit = XLFUnit({})
        unit.source = source
        unit.target = target # added by GT
        unit.context = context
        unit.line = line
        # file.body[context, source] = unit
        file.body.append(unit)
        return unit

    def gettext(self, source, context=None):
        """Returns the translation of the given message id.

        If the context /msgid is not present in the message catalog, then the
        message id is returned.
        """

        key = (context, source)

        for file in self.files.values():
            if key in file.body:
                unit = file.body[key]
                if unit.target:
                    return unit.target
        return source
