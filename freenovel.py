from bs4 import BeautifulSoup as bs
import requests
from functools import reduce
import re
import logging
#import json

#url = "http://fangal.org/freenovel/620097"
url = "http://fangal.org/freenovel/620060"
target = 'sample.txt'

def get_indent(item):
    # item: bs4.element.Tag object
    try:
        soup_indent = item.find('div', class_='indent', style=True)
        if soup_indent:
            return int(re.findall(r'\d+', soup_indent['style'])[0])//15
        else:
            return 0
    except Exception as e:
        logging.warning('Failed to retrieve correct number of indentations for comment')
        return 0

def formatComments(replyList):
    # replyList: bs4.element.Tag object
    contents = []
    indent = '   '
    firstindent = ' └ '
    
    items = replyList.find_all('div', class_='item')
    for item in items:
        commenter = item.find('h4', class_='header').get_text().strip()
        date_, time_, ipAddress = item.find('p', class_='meta').get_text().split()
        comment = item.find('div', class_='itemContent').find('div', recursive=False).get_text()
        indentations = get_indent(item)
        
        content = ''
        if indentations:
            content += indent*(indentations-1) + firstindent + '{} ({}) | {} {}'.format(commenter, ipAddress, date_, time_)
            content += '\n' + indent*indentations + comment
        else:
            content += '{} ({}) | {} {}\n{}'.format(commenter, ipAddress, date_, time_, comment)
        
        contents.append(content)
    
    header = '\n---\n\n댓글({})\n\n'.format(len(contents))
    
    return header + '\n\n'.join(contents)

def pageContent(url, get_comments=True):
    ses = requests.Session()
    req = ses.get(url)
    html = req.text
    soup = bs(html, "html.parser")
    
    boardRead = soup.find('div', class_='boardRead')
    commentAuthor = ""
    if (len(boardRead.find_all('center')) > 1):
        commentAuthor = boardRead.find_all('center')[-1].get_text()
    
    boardReadHeader = boardRead.find('div', class_='boardReadHeader')
    
    permaLink = boardReadHeader.find('a', class_='permaLink').get_text()
    title = boardReadHeader.find('h3', class_='title').get_text()
    category = boardReadHeader.find('a', class_='category').get_text()
    author = boardReadHeader.find('div', class_='authorArea').find_all('a')[0].get_text()
    ipAddress = boardReadHeader.find('span', class_='ipAddress').get_text()
    
    sum_ = boardReadHeader.find('div', class_='titleArea').find('span', class_='sum')
    # 조회 수 num\n추천 수 num\nyyyy.MM.dd hh:mm:ss 
    
    views = sum_.find('span', class_='read').find('span', class_='num').get_text()
    upvotes = sum_.find('span', class_='vote').find('span', class_='num').get_text()
    timestamp = sum_.find('span', class_='date').get_text()
    
    boardReadBody = boardRead.find('div', class_='boardReadBody')
    document_content = '\n'.join(
        [div.get_text() for div in boardReadBody.find('td', class_='novelbox').find('div').find_all('div')[:-1]]
    ) # all text in content except '이 게시물을..'
    
    header = '{} | {}\n{} ({}) | {}\n조회 수 {} 추천 수 {}\n{}\n\n---\n\n'.format(
        category, title, author, ipAddress, timestamp, views, upvotes, permaLink
    )
    
    pageContent = header + document_content
    
    if commentAuthor:
        pageContent += '\n---\n\n{}'.format(commentAuthor)
    
    if get_comments:
        replyList = soup.find('div', class_='replyList')
        pageContent += formatComments(replyList)
    
    return pageContent

with open(target, 'wt') as f:
    f.write(pageContent(url))