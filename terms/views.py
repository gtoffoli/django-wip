from django.db.models.expressions import Q
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required

from wip.models import Language, Site, Proxy
from .models import String, Txu, TxuSubject
from wip.models import UNKNOWN, ANY, TRANSLATED, REVISED, INVARIANT, TO_BE_TRANSLATED
from .models import SEGMENT, STRING_TYPE_DICT
from wip.forms import TranslationServiceForm
from .forms import StringSequencerForm, StringEditForm, StringTranslationForm, StringsTranslationsForm
from wip.views import empty_page


def get_or_add_string(request, text, language, site=None, string_type=UNKNOWN, add=False, txu=None, reliability=1):
    if isinstance(language, str):
        language = Language.objects.get(code=language)
    is_model_instance = False
    if site:
        strings = String.objects.filter(text=text, language=language, site=site)
    else:
        strings = String.objects.filter(text=text, language=language)
    if strings:
        is_model_instance = True
        string = strings[0]
    else:
        if add:
            string = String(text=text, language=language, txu=txu, site=site, string_type=string_type, reliability=reliability, user=request.user)
            string.save()
            is_model_instance = True
        else:
            string = String(text=text, language=language, site=site)
    return is_model_instance, string

    
def list_strings(request, sources, state, targets=[]):
    """
    list strings in the source languages with translations in the target languages
    """
    if not request.user.is_superuser:
        return empty_page(request);
    post = request.POST
    if post and post.get('delete_strings', ''):
        string_ids = post.getlist('delete')
        if string_ids:
            strings = String.objects.filter(id__in=string_ids)
            for string in strings:
                string.delete()
    var_dict = {}
    var_dict['sources'] = sources
    var_dict['state'] = state
    var_dict['targets'] = targets
    source_languages = target_languages = []
    translated = None
    can_delete = False
    if sources:
        source_codes = sources.split('-')
        source_languages = Language.objects.filter(code__in=source_codes).order_by('code')
    if targets:
        target_codes = targets.split('-')
        target_languages = Language.objects.filter(code__in=target_codes).order_by('code')
    if state == 'translated':
        translated = True
    elif state == 'untranslated':
        translated = False
        can_delete = not targets and request.user.is_superuser
    else:
        translated = None
    var_dict['can_delete'] = can_delete
    var_dict['source_languages'] = source_languages
    var_dict['target_languages'] = target_languages
    var_dict['target_codes'] = [l.code for l in target_languages]
    qs = find_strings(source_languages=source_languages, target_languages=target_languages, translated=translated)
    var_dict['string_count'] = qs.count()
    paginator = Paginator(qs, settings.PAGE_SIZE)
    page = request.GET.get('page', 1)
    try:
        strings = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page = 1
        strings = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page = paginator.num_pages
        strings = paginator.page(paginator.num_pages)
    var_dict['page_size'] = settings.PAGE_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    var_dict['strings'] = strings
    return render(request, 'list_strings.html', var_dict)

def find_strings(source_languages=[], target_languages=[], translated=None, site=None, order_by=None):
    if isinstance(source_languages, Language):
        source_languages = [source_languages]
    if isinstance(target_languages, Language):
        target_languages = [target_languages]
    source_codes = [l.code for l in source_languages]
    target_codes = [l.code for l in target_languages]
    qs = String.objects
    if site:
        qs = qs.filter(site=site)
    if source_languages:
        source_codes = [l.code for l in source_languages]
        qs = qs.filter(language_id__in=source_codes)
    if translated is None:
        if not source_languages:
            qs = qs.all()
    elif translated: # translated = True
        if target_languages:
            qs = qs.filter(txu__string__language_id__in=target_codes).distinct()
    else: # translated = False
        if target_languages:
            qs = qs.exclude(invariant=True)
            if 'en' in target_codes:
                qs = qs.filter(Q(txu__isnull=True) | Q(txu__en=False))
            if 'es' in target_codes:
                qs = qs.filter(Q(txu__isnull=True) | Q(txu__es=False))
            if 'fr' in target_codes:
                qs = qs.filter(Q(txu__isnull=True) | Q(txu__fr=False))
            if 'it' in target_codes:
                qs = qs.filter(Q(txu__isnull=True) | Q(txu__it=False))
    # return qs.order_by('language', 'text')
    if order_by is None:
        qs = qs.order_by('language', 'text')
    elif order_by:
        qs = qs.order_by(order_by)
    return qs

def string_view(request, string_id):
    if not request.user.is_superuser:
        return empty_page(request);
    var_dict = {}
    var_dict['string'] = string = get_object_or_404(String, pk=string_id)
    var_dict['string_type'] = STRING_TYPE_DICT[string.string_type]
    var_dict['source_language'] = source_language = string.language
    var_dict['other_languages'] = other_languages = Language.objects.exclude(code=source_language.code).order_by('code')

    StringSequencerForm.base_fields['translation_languages'].queryset = other_languages
    string_context = request.session.get('string_context', {})
    if string_context:
        string_types = string_context.get('string_types', [])
        translation_state = string_context.get('translation_state', TO_BE_TRANSLATED)
        translation_codes = string_context.get('translation_codes', [l.code for l in other_languages])
        translation_subjects = string_context.get('translation_subjects', [])
        order_by = string_context.get('order_by', TEXT_ASC)
        show_similar = string_context.get('show_similar', False)
    else:
        string_types = []
        translation_state = TO_BE_TRANSLATED
        translation_codes = [l.code for l in other_languages]
        translation_subjects = []
        order_by = TEXT_ASC
        show_similar = False
    translation_languages = Language.objects.filter(code__in=translation_codes)

    apply_filter = goto = '' 
    post = request.POST
    if post:
        apply_filter = post.get('apply_filter', '')
        if not (apply_filter):
            for key in post.keys():
                if key.startswith('goto-'):
                    goto = int(key.split('-')[1])
                    string = get_object_or_404(String, pk=goto)
        form = StringSequencerForm(post)
        if form.is_valid():
            data = form.cleaned_data
            # print ('data: ', data)
            string_types = data['string_types']
            """
            project_site = data['project_site']
            project_site_id = project_site and project_site.id or ''
            """
            translation_state = int(data['translation_state'])
            translation_languages = data['translation_languages']
            translation_codes = [l.code for l in translation_languages]
            order_by = int(data['order_by'])
            show_similar = data['show_similar']
        else:
            pass
            # print ('error', form.errors)
    string_context['string_types'] = string_types
    string_context['translation_state'] = translation_state
    string_context['translation_codes'] = translation_codes
    string_context['order_by'] = order_by
    string_context['show_similar'] = show_similar
    request.session['string_context'] = string_context
    if goto:
        return HttpResponseRedirect('/string/%d/' % string.id)        
    n, first, last, previous, next = string.get_navigation(string_types=string_types, translation_state=translation_state, translation_codes=translation_codes, order_by=order_by)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['last'] = last
    var_dict['translations'] = string.get_translations()
    var_dict['similar_strings'] = show_similar and find_like_strings(string, max_strings=10) or []
    var_dict['sequencer_form'] = StringSequencerForm(initial={'string_types': string_types, 'translation_state': translation_state, 'translation_languages': translation_languages, 'order_by': order_by, 'show_similar': show_similar})
    return render(request, 'string_view.html', var_dict)

@staff_member_required
def string_edit(request, string_id=None, language_code='', proxy_slug=''):
    user = request.user
    if not user.is_superuser:
        return empty_page(request)
    var_dict = {}
    string = string_id and get_object_or_404(String, pk=string_id) or None
    proxy = proxy_slug and get_object_or_404(Proxy, slug=proxy_slug) or None
    post = request.POST
    # print 'post: ', post
    if post:
        if post.get('cancel', ''):
            if string_id:
                return HttpResponseRedirect('/string/%s/' % string_id)
            elif proxy_slug:
                return HttpResponseRedirect('/proxy/%s/translations/' % proxy_slug)
        elif post.get('save', '') or post.get('continue', ''):
            if string:
                string_edit_form = StringEditForm(post, instance=string)
            else:
                string_edit_form = StringEditForm(post)
            if string_edit_form.is_valid():
                string = string_edit_form.save()
                if not string.user == user:
                    string.user = user
                    string.save()
                if post.get('save', ''):
                    return HttpResponseRedirect('/string/%d/' % string.id)
    else:
        if string:
            string_edit_form = StringEditForm(instance=string)
        else:
            string_type = SEGMENT
            if proxy_slug:
                proxy = get_object_or_404(Proxy, slug=proxy_slug)
                site = proxy.site
                language = site.language
            elif language_code:
                site = None
                language = get_object_or_404(Language, code=language_code)
            else:
                site = None
                language = None
            reliability = 5
            text = ''
            path = ''
            user = request.user           
            string_edit_form = StringEditForm(initial={'string_type': string_type, 'site': site, 'language': language, 'reliability': reliability, 'text': text, 'path': path, 'user': user })
    var_dict['string'] = string
    var_dict['proxy'] = proxy
    var_dict['translations'] = string and string.get_translations() or []
    var_dict['string_edit_form'] = string_edit_form
    return render(request, 'string_edit.html', var_dict)

def string_translate(request, string_id, target_code):
    if not request.user.is_superuser:
        return empty_page(request);
    var_dict = {}
    var_dict['string'] = string = get_object_or_404(String, pk=string_id)
    var_dict['string_type'] = STRING_TYPE_DICT[string.string_type]
    var_dict['source_language'] = source_language = string.language
    var_dict['target_code'] = target_code
    var_dict['target_language'] = target_language = Language.objects.get(code=target_code)
    translation_codes = [target_code]
    translation_languages = Language.objects.filter(code=target_code)

    StringSequencerForm.base_fields['translation_languages'].queryset = translation_languages

    string_context = request.session.get('string_context', {})
    if string_context:
        string_types = string_context.get('string_types', [])
        project_site_id = string_context.get('project_site', None)
        translation_state = string_context.get('translation_state', TO_BE_TRANSLATED)
        translation_codes = string_context.get('translation_codes', [target_code])
        translation_services = string_context.get('translation_services', [])
        translation_subjects = string_context.get('translation_subjects', [])
        order_by = string_context.get('order_by', TEXT_ASC)
        show_similar = string_context.get('show_similar', False)
    else:
        string_types = []
        project_site_id = string.site.id
        translation_state = TO_BE_TRANSLATED
        translation_codes = [target_code]
        translation_services = []
        translation_subjects = []
        order_by = TEXT_ASC
        show_similar = False
    project_site = project_site_id and Site.objects.get(pk=project_site_id) or None

    translation_form = StringTranslationForm()
    translation_service_form = TranslationServiceForm()
    apply_filter = goto = save_translation = '' 
    post = request.POST
    if post:
        apply_filter = post.get('apply_filter', '')
        ask_service = post.get('ask_service', '')
        if not (apply_filter or ask_service):
            for key in post.keys():
                if key.startswith('goto-'):
                    goto = int(key.split('-')[1])
                    string = get_object_or_404(String, pk=goto)
                elif key.startswith('save-'):
                    save_translation = key.split('-')[1]
        if ask_service:
            translation_service_form = TranslationServiceForm(request.POST)
            if translation_service_form.is_valid():
                data = translation_service_form.cleaned_data
                translation_services = data['translation_services']
                if str(MYMEMORY) in translation_services:
                    langpair = '%s|%s' % (source_language.code, target_code)
                    status, translatedText, external_translations = ask_mymemory(string.text, langpair)
                    var_dict['external_translations'] = external_translations
                    var_dict['translation_service'] = TRANSLATION_SERVICE_DICT[MYMEMORY]
            else:
                pass
                # print ('error', translation_service_form.errors)
            translation_form = StringTranslationForm()
        elif save_translation:
            translation_form = StringTranslationForm(request.POST)
            if translation_form.is_valid():
                data = translation_form.cleaned_data
                translation = data['translation']
                site = data['translation_site']
                translation_subjects = data['translation_subjects']
                same_txu = data['same_txu']
                txu = string.txu
                if txu and same_txu:
                    target_txu = string.txu
                else:
                    provider = site and site.name or ''
                    target_txu = Txu(provider=provider, user=request.user)
                    target_txu.save()
                is_model_instance, target = get_or_add_string(request, translation, target_language, site=project_site, string_type=string.string_type, add=True, txu=target_txu, reliability=5)
                if not txu or not same_txu:
                    string.txu = target_txu
                    string.reliability = 5
                    string.save()
                for subject in translation_subjects:
                    try:
                        txu_subject = TxuSubject.objects.get(txu=txu, subject=subject)
                    except:
                        txu_subject = TxuSubject(txu=target_txu, subject=subject)
                        txu_subject.save()
            else:
                # print ('error', translation_form.errors)
                return render(request, 'string_translate.html', {'translation_form': translation_form,})
            translation_service_form = TranslationServiceForm()
        else: # apply_filter
            form = StringSequencerForm(post)
            if form.is_valid():
                data = form.cleaned_data
                string_types = data['string_types']
                project_site = data['project_site']
                project_site_id = project_site and project_site.id or ''
                translation_state = int(data['translation_state'])
                translation_languages = data['translation_languages']
                translation_codes = [l.code for l in translation_languages]
                order_by = int(data['order_by'])
                show_similar = data['show_similar']
    string_context['project_site'] = project_site_id
    string_context['translation_state'] = translation_state
    string_context['translation_codes'] = translation_codes
    string_context['translation_subjects'] = translation_subjects
    string_context['order_by'] = order_by
    string_context['show_similar'] = show_similar
    request.session['string_context'] = string_context
    if goto:
        return HttpResponseRedirect('/string_translate/%d/%s/' % (string.id, target_code))
    n, first, last, previous, next = string.get_navigation(string_types=string_types, site=project_site, translation_state=translation_state, translation_codes=translation_codes, order_by=order_by)
    var_dict['n'] = n
    var_dict['first'] = first
    var_dict['previous'] = previous
    var_dict['next'] = next
    var_dict['last'] = last
    var_dict['similar_strings'] = show_similar and find_like_strings(string, translation_languages=[target_language], with_translations=True, max_strings=10) or []
    var_dict['translations'] = string.get_translations()
    var_dict['sequencer_form'] = StringSequencerForm(initial={'string_types': string_types, 'project_site': project_site, 'translation_state': translation_state, 'translation_languages': translation_languages, 'order_by': order_by, 'show_similar': show_similar})
    var_dict['translation_form'] = StringTranslationForm(initial={'translation_site': project_site, 'translation_subjects': translation_subjects,})
    var_dict['translation_service_form'] = translation_service_form
    return render(request, 'string_translate.html', var_dict)

def find_like_strings(source_string, translation_languages=[], with_translations=False, min_chars=3, max_strings=10, min_score=0.4):
    """
    source_string is an object of type String
    we look for similar strings of the same language
    first we use fuzzy search (more_like_this)
    then we find strings containing some of the same tokens
    """
    min_chars_times_10 = min_chars*10
    language = source_string.language
    language_code = language.code
    hits = list(SearchQuerySet().more_like_this(source_string))
    if not hits:
        return []
    source_tokens = filtered_tokens(source_string.text, language_code, truncate=True, min_chars=min_chars)
    source_set = set(source_tokens)
    like_strings = []
    for hit in hits:
        if not hit.language_code == language_code:
            continue
        try: # the index could be not in sync
            string = String.objects.get(language=language, text=hit.text)
        except:
            continue
        if with_translations:
            translations = string.get_translations(target_languages=translation_languages)
            if not translations:
                continue
        text = string.text
        tokens = raw_tokens(text, language_code)
        l = len(tokens)
        tokens = filtered_tokens(text, language_code, tokens=tokens, truncate=True, min_chars=min_chars)
        l = float(len(source_tokens) + l + len(tokens))/3
        like_set = set(tokens)
        i = len(like_set.intersection(source_set))
        if not i:
            continue
        # core  formula
        similarity_score = float(i * sqrt(i)) / sqrt(l)
        # print similarity_score, text
        # add a small pseudo-random element to compensate for the bias in the results of more_like_this
        correction = float(len(text) % min_chars) / min_chars_times_10
        similarity_score += correction
        if similarity_score < min_score:
            continue
        if with_translations:
            like_strings.append([similarity_score, string, translations])
        else:
            like_strings.append([similarity_score, string])
    like_strings.sort(key=lambda x: x[0], reverse=True)
    return like_strings[:max_strings]

def strings_translations(request, proxy_slug=None, state=None):
    """
    list translations from source language (code) to target language (code)
    NOW REPLACED BY function list_segments
    """
    if not request.user.is_superuser:
        return empty_page(request);
    # PAGE_SIZE = 100
    tm_edit_context = request.session.get('tm_edit_context', {})
    translation_state = state or tm_edit_context.get('translation_state', 0)
    proxy = proxy_slug and Proxy.objects.get(slug=proxy_slug) or None
    if proxy:
        project_site = proxy.site
        project_site_id = project_site.id
        source_language = project_site.language
        source_language_code = source_language.code
        target_language = proxy.language
        target_language_code = target_language.code
    else:
        project_site_id = tm_edit_context.get('project_site', None)
        project_site = project_site_id and Site.objects.get(pk=project_site_id) or None
        source_language_code = project_site and project_site.language_id or tm_edit_context.get('source_language', None)
        source_language = source_language_code and Language.objects.get(code=source_language_code) or None
        target_language_code = tm_edit_context.get('target_language', None)
        target_language = target_language_code and Language.objects.get(code=target_language_code) or None
        if project_site and target_language:
            proxies = Proxy.objects.filter(site=project_site, language=target_language)
            if proxies:
                proxy = proxies[0]
    source_text_filter = tm_edit_context.get('source_text_filter', '')
    target_text_filter = tm_edit_context.get('target_text_filter', '')
    show_other_targets = tm_edit_context.get('show_other_targets', False)
    tm_edit_context['project_site'] = project_site_id
    tm_edit_context['source_language'] = source_language_code
    tm_edit_context['target_language'] = target_language_code
    request.session['tm_edit_context'] = tm_edit_context
    if request.method == 'POST':
        post = request.POST
        form = StringsTranslationsForm(post)
        if post.get('delete-segment', ''):
            selection = post.getlist('selection')
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                if txu:
                    for string in String.objects.filter(txu=txu):
                        string.delete()
                    txu.delete()
                else:
                    string.delete()
        elif post.get('delete-translation', ''):
            selection = post.getlist('selection')
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                if txu:
                    translations = String.objects.filter(txu=txu, language=target_language)
                    for string in translations:
                        string.delete()
        elif post.get('make-invariant', ''):
            selection = post.getlist('selection')
            # print ('make-invariant', selection)
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                string.txu = None
                string.invariant = True
                string.save()
                if txu:
                    for string in String.objects.filter(txu=txu):
                        string.delete()
                    txu.delete()
        elif post.get('toggle-invariant', ''):
            selection = post.getlist('selection')
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                if string.invariant:
                    string.invariant = False
                    string.save()
                elif not string.txu:
                    string.invariant = True
                    string.save()
        elif form.is_valid():
            data = form.cleaned_data
            tm_edit_context['translation_state'] = translation_state = int(data['translation_state'])
            project_site = data['project_site']
            tm_edit_context['project_site'] = project_site and project_site.id or None
            source_language = data['source_language']
            tm_edit_context['source_language'] = source_language and source_language.code or None
            target_language = data['target_language']
            tm_edit_context['target_language'] = target_language and target_language.code or None
            tm_edit_context['source_text_filter'] = source_text_filter = data['source_text_filter']
            tm_edit_context['target_text_filter'] = target_text_filter = data['target_text_filter']
            tm_edit_context['show_other_targets'] = show_other_targets = data['show_other_targets']
            request.session['tm_edit_context'] = tm_edit_context
            if project_site and target_language:
                proxies = Proxy.objects.filter(site=project_site, language=target_language)
                proxy = proxies and proxies[0] or None
    else:
        form = StringsTranslationsForm(initial={'project_site': project_site, 'translation_state': translation_state, 'source_language': source_language, 'target_language': target_language, 'source_text_filter': source_text_filter, 'target_text_filter': target_text_filter, 'show_other_targets': show_other_targets, })

    if translation_state == TRANSLATED:
        translated = True
    elif translation_state == TO_BE_TRANSLATED:
        translated = False
    else:
        translated = None

    var_dict = {}
    var_dict['proxy'] = proxy
    var_dict['site'] = project_site_id and Site.objects.get(pk=project_site_id) or None
    var_dict['state'] = translation_state
    var_dict['source_language'] = source_language
    var_dict['target_language'] = target_language
    var_dict['show_other_targets'] = show_other_targets

    if project_site and translation_state == INVARIANT:
        qs = String.objects.filter(site=project_site, invariant=True)
    else:
        qs = find_strings(source_languages=[source_language], target_languages=[target_language], site=project_site, translated=translated, order_by='')
    if source_text_filter:
        qs = qs.filter(text__icontains=source_text_filter)
    if target_text_filter:
        qs = qs.filter(txu__string__text__icontains=target_text_filter)
    qs = qs.order_by('text')
    string_count = qs.count()
    var_dict['string_count'] = string_count
    paginator = Paginator(qs, settings.PAGE_SIZE)
    page = request.GET.get('page', 1)
    try:
        strings = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page = 1
        strings = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page = paginator.num_pages
        strings = paginator.page(paginator.num_pages)
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    var_dict['strings'] = strings
    var_dict['strings_translations_form'] = form
    return render(request, 'strings_translations.html', var_dict)

def proxy_string_translations(request, proxy_slug=None, state=None):
    """
    list translations from source language (code) to target language (code)
    """
    if not request.user.is_superuser:
        return empty_page(request);
    # PAGE_SIZE = 100
    proxy = proxy_slug and Proxy.objects.get(slug=proxy_slug) or None

    tm_edit_context = request.session.get('tm_edit_context', {})
    translation_state = state or tm_edit_context.get('translation_state', 0)
    project_site_id = proxy and proxy.site.id or tm_edit_context.get('project_site', None)
    project_site = project_site_id and Site.objects.get(pk=project_site_id) or None
    source_language_code = project_site and project_site.language_id or tm_edit_context.get('source_language', None)
    source_language = source_language_code and Language.objects.get(code=source_language_code) or None
    target_language_code = proxy and proxy.language_id or tm_edit_context.get('target_language', None)
    target_language = target_language_code and Language.objects.get(code=target_language_code) or None
    source_text_filter = tm_edit_context.get('source_text_filter', '')
    target_text_filter = tm_edit_context.get('target_text_filter', '')
    show_other_targets = tm_edit_context.get('show_other_targets', False)
    if proxy:
        tm_edit_context['project_site'] = project_site_id
        tm_edit_context['source_language'] = source_language_code
        tm_edit_context['target_language'] = target_language_code
        request.session['tm_edit_context'] = tm_edit_context
    if request.method == 'POST':
        post = request.POST
        form = StringsTranslationsForm(post)
        if post.get('delete-segment', ''):
            selection = post.getlist('selection')
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                if txu:
                    for string in String.objects.filter(txu=txu):
                        string.delete()
                    txu.delete()
                else:
                    string.delete()
        elif post.get('delete-translation', ''):
            selection = post.getlist('selection')
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                if txu:
                    translations = String.objects.filter(txu=txu, language=target_language)
                    for string in translations:
                        string.delete()
        elif post.get('make-invariant', ''):
            selection = post.getlist('selection')
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                txu = string.txu
                string.txu = None
                string.invariant = True
                string.save()
                if txu:
                    for string in String.objects.filter(txu=txu):
                        string.delete()
                    txu.delete()
        elif post.get('toggle-invariant', ''):
            selection = post.getlist('selection')
            for string_id in selection:
                string = String.objects.get(pk=int(string_id))
                if string.invariant:
                    string.invariant = False
                    string.save()
                elif not string.txu:
                    string.invariant = True
                    string.save()
        elif form.is_valid():
            data = form.cleaned_data
            tm_edit_context['translation_state'] = translation_state = int(data['translation_state'])
            project_site = data['project_site']
            tm_edit_context['project_site'] = project_site and project_site.id or None
            source_language = data['source_language']
            tm_edit_context['source_language'] = source_language and source_language.code or None
            target_language = data['target_language']
            tm_edit_context['target_language'] = target_language and target_language.code or None
            tm_edit_context['source_text_filter'] = source_text_filter = data['source_text_filter']
            tm_edit_context['target_text_filter'] = target_text_filter = data['target_text_filter']
            tm_edit_context['show_other_targets'] = show_other_targets = data['show_other_targets']
            request.session['tm_edit_context'] = tm_edit_context
    else:
        form = StringsTranslationsForm(initial={'project_site': project_site, 'translation_state': translation_state, 'source_language': source_language, 'target_language': target_language, 'source_text_filter': source_text_filter, 'target_text_filter': target_text_filter, 'show_other_targets': show_other_targets, })

    if translation_state == TRANSLATED:
        translated = True
    elif translation_state == TO_BE_TRANSLATED:
        translated = False
    else:
        translated = None

    var_dict = {}
    var_dict['proxy'] = proxy
    var_dict['site'] = project_site_id and Site.objects.get(pk=project_site_id) or None
    var_dict['state'] = translation_state
    var_dict['source_language'] = source_language
    var_dict['target_language'] = target_language
    var_dict['show_other_targets'] = show_other_targets

    if project_site and translation_state == INVARIANT:
        qs = String.objects.filter(site=project_site, invariant=True)
    else:
        qs = find_strings(source_languages=[source_language], target_languages=[target_language], site=project_site, translated=translated, order_by='')
    if source_text_filter:
        qs = qs.filter(text__icontains=source_text_filter)
    if target_text_filter:
        qs = qs.filter(txu__string__text__icontains=target_text_filter)
    qs = qs.order_by('text')
    string_count = qs.count()
    var_dict['string_count'] = string_count
    paginator = Paginator(qs, settings.PAGE_SIZE)
    page = request.GET.get('page', 1)
    try:
        strings = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page = 1
        strings = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page = paginator.num_pages
        strings = paginator.page(paginator.num_pages)
    var_dict['page_size'] = settings.PAGE_SIZE
    var_dict['page'] = page = int(page)
    var_dict['offset'] = (page-1) * settings.PAGE_SIZE
    var_dict['before'] = steps_before(page)
    var_dict['after'] = steps_after(page, paginator.num_pages)
    var_dict['strings'] = strings
    var_dict['strings_translations_form'] = form
    return render(request, 'proxy_string_translations.html', var_dict)

def add_translated_string(request):
    user = request.user
    user_id = user.id
    if request.is_ajax() and request.method == 'POST':
        form = request.POST
        source_id = int(form.get('source_id'))
        translated_id = int(form.get('translated_id'))
        txu_id = int(form.get('txu_id'))
        translation = form.get('translation')
        target_language = form.get('t_l')
        source_language = form.get('s_l')
        site_name = form.get('site_name')
        target_language = Language.objects.get(name=target_language)
        source_language = Language.objects.get(name=source_language)
        reliability = 5
        if (txu_id == 0):
            # print ('txu non esiste')
            target_txu = Txu(provider=site_name, user=request.user)
            target_txu.save()
            target_txu_id = target_txu.id
            string = String.objects.filter(pk=source_id).update(txu=target_txu.id)
            string_new = String(text=translation, language=target_language, txu=target_txu, site=None, reliability=reliability, invariant=False)
            string_new.save()
            translated_new_id = string_new.id
            return JsonResponse({"data": "add-txt-string","txu_id": target_txu_id,"translated_id": translated_new_id,})
        else:
            string = String.objects.filter(pk=translated_id)
            if string:
                string.update(text=translation)
                return JsonResponse({"data": "modify-string",})
            else:
                string_new = String(txu_id=txu_id, language=target_language, site=None, text=translation, reliability=reliability, invariant=False)
                string_new.save()
                translated_new_id = string_new.id
                return JsonResponse({"data": "add-string","translated_id": translated_new_id,})
    return empty_page(request);

def delete_translated_string(request):
    if request.is_ajax() and request.method == 'GET':
        form = request.GET
        source_id = int(form.get('source_id'))
        translated_id = int(form.get('translated_id'))
        txu_id = int(form.get('txu_id'))
        # print (source_id)
        return JsonResponse({"data": "delete-string",})
    return empty_page(request);
