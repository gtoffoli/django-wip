tag_fixes = {'it':
{'NPR': [
'AlfaBeta',
'Castellana',
'Civita',
'Fondi',
'Ladispoli',
'Malala',
'Pomezia',
'Rieti',
'Scuolemigranti',
'Sora',
'Velletri',
'Yousafzai'
],
'NOUN':[
'analfabeti',
'consultants',
'corsi',
'interpretariato',
'language',
'numeri',
'passeggiate',
'siti',
'recapiti',
'via',
'website',
]
}
}

def fix_tags(tagged_tokens, language='it'):
    fixed = []
    for token, tag in tagged_tokens:
        low = token.lower()
        if token[0].isupper() and token in tag_fixes[language]['NPR']:
            tag = 'NPR'
        # elif tag in ['VER', 'ADJ', 'ADV',] and token.lower() in tag_fixes[language]['NOUN']:
        elif low in tag_fixes[language]['NOUN']:
            tag = 'NOUN'
        elif low in ['and', 'or']:
            tag = 'CON'
        elif low in ["l'"]:
            tag = 'ART'
        elif low in "sull'":
            tag = 'ARTPRE'
        fixed.append((token, tag))
    return fixed
