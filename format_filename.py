from sanitize_filename import sanitize
from unicodedata import normalize

def formatFilename(num, title, author, char_limit=255, category=''):
    header = '({0:04d}) '.format(num)
    
    body = '{}'.format(normalize('NFC', sanitize(title)))
    if category: body = '[{}]'.format(normalize('NFC', sanitize(category))) + body
    
    footer = ' - {}.txt'.format(normalize('NFC', sanitize(author)))
    
    body = body[:char_limit - len(header) - len(footer)]
    
    return header + body + footer