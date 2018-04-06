import requests

URL = 'https://api.deepl.com/v1/translate'

LANGUAGES = {
    'auto': 'Auto',
    'DE': 'German',
    'EN': 'English',
    'FR': 'French',
    'ES': 'Spanish',
    'IT': 'Italian',
    'NL': 'Dutch',
    'PL': 'Polish'
}

class TranslationError(Exception):
    def __init__(self, message):
        super(TranslationError, self).__init__(message)

def translate(text, target_code, subscription, source_code=None):
    target_code = target_code.upper()
    if text is None:
        raise TranslationError('Text can\'t be None.')
    if len(text) > 5000:
        raise TranslationError('Text too long (limited to 5000 characters).')
    if target_code not in LANGUAGES.keys():
        raise TranslationError('Language {} not available.'.format(target_code))
    if source_code is not None and source_code not in LANGUAGES.keys():
        raise TranslationError('Language {} not available.'.format(source_code))

    parameters = {
        'text': text,
        'target_lang': target_code.upper(),
        'split_sentences': 0,
        'auth_key': subscription.secret_1
    }
    if source_code:
        parameters['source_lang'] = source_code.upper()

    response = requests.post(URL, data=parameters)
    response = response.json()
    translations = response.get('translations', [])
    return translations
