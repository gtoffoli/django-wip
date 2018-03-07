from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField

from wip.models import Language, Subject, Site

from wip.models import UNKNOWN
TERM = 1
SEGMENT = 2
FRAGMENT = 3
STRING_TYPE_CHOICES = (
    (UNKNOWN, _('unknown'),),
    (TERM, _('term'),),
    (SEGMENT, _('segment'),),
    (FRAGMENT,  _('fragment'),),
)
STRING_TYPE_DICT = dict(STRING_TYPE_CHOICES)

from wip.models import TEXT_ASC, ID_ASC, DATETIME_DESC, DATETIME_ASC, COUNT_DESC
STRING_SORT_CHOICES = (
    (TEXT_ASC, _('text'),),
    (ID_ASC, _('id'),),
    (DATETIME_DESC, _('datetime inverse'),),
    (DATETIME_ASC,  _('datetime'),),
)
STRING_SORT_DICT = dict(STRING_SORT_CHOICES)

from wip.models import ANY, TRANSLATED, REVISED, INVARIANT, TO_BE_TRANSLATED
STRING_TRANSLATION_STATE_CHOICES = (
    (ANY, _('any'),),
    (INVARIANT, _('invariant'),),
    (TO_BE_TRANSLATED, _('to be translated'),),
    (TRANSLATED,  _('translated'),),
    (REVISED,  _('revised'),),
)
STRING_TRANSLATION_STATE_DICT = dict(STRING_TRANSLATION_STATE_CHOICES)


class Txu(models.Model):
    provider = models.CharField(verbose_name='txu source', max_length=100, blank=True, null=True)
    entry_id = models.CharField(verbose_name='id by provider', max_length=100, blank=True, null=True)
    subjects = models.ManyToManyField('Subject', through='TxuSubject', related_name='txu', blank=True, verbose_name='subjects')
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    user = models.ForeignKey(User, null=True)
    comments = models.TextField(blank=True, null=True)
    en = models.BooleanField(default=False)
    es = models.BooleanField(default=False)
    fr = models.BooleanField(default=False)
    it = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('translation unit')
        verbose_name_plural = _('translation units')
        ordering = ('-created',)

    def __str__(self):
        return self.entry_id or str(self.id)

    def __unicode__(self):
        return self.__str__()

    def update_languages(self):
        strings = String.objects.filter(txu=self)
        l_dict = { 'en': False, 'es': False, 'fr': False, 'it': False, }
        for s in strings:
            l_dict[s.language_id] = True
        updated = False
        for code in l_dict.keys():
            if getattr(self, code) != l_dict[code]:
                setattr(self, code, l_dict[code])
                updated = True
        if updated:
            self.save()
        return updated

class TxuSubject(models.Model):
    txu = models.ForeignKey(Txu, related_name='txu')
    subject = models.ForeignKey(Subject, related_name='subject')

    class Meta:
        verbose_name = _('txu subject')
        verbose_name_plural = _('txu subjects')

class String(models.Model):
    string_type = models.IntegerField(choices=STRING_TYPE_CHOICES, default=UNKNOWN, null=True, verbose_name='string type')
    invariant = models.BooleanField(default=False)
    language = models.ForeignKey(Language)
    site = models.ForeignKey(Site, null=True)
    path = models.CharField(max_length=200, default='/', blank=True)
    txu = models.ForeignKey(Txu, blank=True, null=True, related_name='string')
    reliability = models.IntegerField(default=1)
    text = models.TextField()
    created = CreationDateTimeField(null=True)
    modified = ModificationDateTimeField(null=True)
    user = models.ForeignKey(User, null=True)
    is_fragment = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('string')
        verbose_name_plural = _('strings')
        ordering = ('-id',)

    def __str__(self):
        return self.text

    def __unicode__(self):
        return self.__str__()

    def language_code(self):
        return self.language.code

    def tokens(self):
        return self.text.split()

    def get_translations(self, target_languages=[]):
        if not target_languages:
            target_languages = Language.objects.exclude(code=self.language.code).distinct().order_by('code')
        translations = []
        has_translations = False
        txu = self.txu
        for language in target_languages:
            strings = String.objects.filter(txu=txu, language_id=language.code)
            if strings:
                has_translations = True
            translations.append([language, strings])
        return has_translations and translations or []

    def get_navigation(self, string_types=[], site=None, translation_state='', translation_codes=[], order_by=TEXT_ASC):
        # print ('order_by: ', order_by)
        text = self.text
        id = self.id
        modified = self.modified
        qs = String.objects.filter(language_id=self.language_id)
        # print (1, qs.count())
        if string_types:
            qs = qs.filter(string_type__in=string_types)
            # print (2, qs.count())
        if site:
            qs = qs.filter(site=site)
        if translation_state == INVARIANT:
            qs = qs.filter(invariant=True)
        elif translation_state == TRANSLATED:
            qs = qs.exclude(invariant=True)
            qs = qs.filter(txu__string__language_id__in=translation_codes)
        elif translation_state == TO_BE_TRANSLATED:
            qs = qs.exclude(invariant=True)
            """
            qs = qs.exclude(txu__string__language_id__in=translation_codes)
            """
            if 'en' in translation_codes:
                qs = qs.filter(txu__en=False)
            if 'es' in translation_codes:
                qs = qs.filter(txu__es=False)
            if 'fr' in translation_codes:
                qs = qs.filter(txu__fr=False)
            if 'it' in translation_codes:
                qs = qs.filter(txu__it=False)
            # print (3, qs.count())
            # print (4, translation_codes)
        first = last = previous = next = None
        n = qs.count()
        # print (n, order_by, TEXT_ASC, order_by == TEXT_ASC, 1 == 1)
        if n:
            if order_by == TEXT_ASC:
                qs = qs.order_by('text')
                qs_before = qs.filter(text__lt=text).order_by('-text')
                qs_after = qs.filter(text__gt=text).order_by('text')
                # print (order_by, qs_before.count())
            elif order_by == ID_ASC:
                qs = qs.order_by('id')
                qs_before = qs.filter(id__lt=id).order_by('-id')
                qs_after = qs.filter(id__gt=id).order_by('id')
                # print (order_by, qs_before.count())
            elif order_by == DATETIME_ASC:
                qs = qs.order_by('modified')
                qs_before = qs.filter(modified__lt=modified).order_by('-modified')
                qs_after = qs.filter(modified__gt=modified).order_by('modified')
                # print (order_by, qs_before.count())
            elif order_by == DATETIME_DESC:
                qs = qs.order_by('-modified')
                qs_before = qs.filter(modified__gt=modified).order_by('modified')
                qs_after = qs.filter(modified__lt=modified).order_by('-modified')
                # print (order_by, qs_before.count())
            previous = qs_before.count() and qs_before[0] or None
            next = qs_after.count() and qs_after[0] or None
            first = qs[0]
            first = not first.id==id or None
            last = qs.reverse()[0]
            last = not last.id==id or None
        # return previous, next
        return n, first, last, previous, next
