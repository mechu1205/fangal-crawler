from pathvalidate import sanitize_filename
from unicodedata import normalize

def formatFilename(num, title, author, char_limit=255, category='', zero_as_notice=True):
    header = '({0:04d}) '.format(num) if (num or not zero_as_notice) else '(공지) '
    
    body = '{}'.format(title)
    if category: body = '[{}]'.format(category) + body
    
    footer = ' - {}'.format(author)
    extension = '.txt'
    
    body = body[:char_limit - len(header) - len(footer) - len(extension)]
    
    return sanitize_filename(header + body + footer + extension)