# adapted from https://github.com/1o0ko/Emotion-vectors/blob/master/babelnet/utils.py

import urllib2
import urllib
import json
import gzip
import logging

from StringIO import StringIO

import re
from collections import defaultdict
from django.conf import settings
base_url = 'https://babelnet.io/v4/'

def sendRequest(params, service_url):
    logger = logging.getLogger(__name__)

    params['key'] = settings.BABELNET_KEY
    url = service_url + '?' + urllib.urlencode(params, doseq=True)
    request = urllib2.Request(url)
    request.add_header('Accept-encoding', 'gzip')
    response = urllib2.urlopen(request)

    if response.info().get('Content-Encoding') == 'gzip':
        logger.debug('Received response for: {0}'.format(params))
        buf = StringIO( response.read())
        f = gzip.GzipFile(fileobj=buf)
        data = json.loads(f.read())
        return data
    else:
        logger.debug('Could not receive response for: {0}'.format(params))
    return []

def getSynsetIds(word, langs='IT', filterLangs=[], source=[]):
    service_url = base_url + 'getSynsetIds'

    params = {
        'word' : word,
        'langs' : langs,
    }
    if langs:
        params['langs'] = langs
    if filterLangs:
        params['filterLangs'] = filterLangs
    if source:
        params['source'] = source

    ids = []
    for result in sendRequest(params, service_url):                        
        ids.append(result.get('id'))
    return ids

def getSynset(synsetId, filterLangs=[]):
    service_url = base_url + 'getSynset'
    
    params = {
        'id' : synsetId,
    }
    if filterLangs:
        params['filterLangs'] = filterLangs
    
    return sendRequest(params, service_url)

def make_term(word, source_lang='IT', target_langs=['EN','ES','FR'], sources=['WN','WIKI','WIKIDATA','WIKITR']):
    filterLangs = target_langs
    if not source_lang in target_langs:
        filterLangs = [source_lang] + target_langs
    multi_dict = defaultdict(dict)
    for lang in filterLangs:
        multi_dict[lang] = defaultdict(int)
    synset_ids = getSynsetIds(word, langs=source_lang, filterLangs=filterLangs, source=sources)
    for synsetId in synset_ids:
        synset =  getSynset(synsetId, filterLangs=filterLangs)
        bkeyConcepts = synset['bkeyConcepts']
        categories =  synset['categories']
        domains =  synset['domains']
        if not bkeyConcepts and not categories and not domains:
            continue
        senses = synset.get('senses', [])
        for sense in senses:
            lemma = sense['lemma']
            if re.search(r'[\\/_]', lemma):
                continue
            language = sense['language']
            frequency = sense.get('frequency', 0)
            translationInfo = sense.get('translationInfo', '')
            score = 1
            if synset.get('bKeyConcept', False):
                score = 5
            elif frequency:
                score = int(round(frequency**(1/3.0)))
            elif translationInfo:
                confidence, numberOfTranslations, sampleSize = translationInfo.split('_')
                score = int(round(float(confidence) * round(int(numberOfTranslations)**(1/3.5)) * round(int(sampleSize)**(1/3.5))))
            multi_dict[language][lemma] += score
    sorted_dict = {}
    for language in target_langs:
        lemmas = multi_dict[language].items()
        lemmas = sorted(lemmas, key=lambda x: x[1], reverse=True)
        sorted_dict[language] = lemmas
    return sorted_dict

    