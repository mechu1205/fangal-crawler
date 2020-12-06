from bs4 import BeautifulSoup as bs
import requests
from functools import reduce

url = "http://fangal.org/freenovel/620097"
target = 'sample.txt'

def pageContent(url, get_comments=True):
    ses = requests.Session()
    req = ses.get(url)
    html = req.text
    soup = bs(html, "html.parser")

    boardReadHeader = soup.find('div', class_='boardReadHeader')
    permaLink = boardReadHeader.find('a', class_='permaLink').get_text()
    title = boardReadHeader.find('h3', class_='title').get_text()
    category = boardReadHeader.find('a', class_='category').get_text()
    author = boardReadHeader.find('div', class_='authorArea').find_all('a')[0].get_text()
    ipAddress = boardReadHeader.find('span', class_='ipAddress').get_text()
    
    boardReadBody = soup.find('div', class_='boardReadBody')
    document_content = '\n'.join(
        [div.get_text() for div in boardReadBody.find('td', class_='novelbox').find('div').find_all('div')[:-1]]
    ) # all text in content except '이 게시물을..'
    
    pageContent = '{}|{}\n{} ({})\n{}\n\n---\n\n{}'.format(category, title, author, ipAddress, permaLink, document_content)
    
    if get_comments:
        replyList = soup.find('div', class_='replyList')
        
    
    return pageContent

with open(target, 'wt') as f:
    f.write(pageContent(url))