from bs4 import BeautifulSoup as bs
from bs4 import Comment, Tag, NavigableString
import requests
import re
import logging
import os

from format_filename import formatFilename

# Use this file to crawl fangal.org/short

def get_content(readBody):
    
    errorMsg = '본문을 불러오는 과정에서 오류가 발생하였습니다.'
    
    try:
        xe_content = readBody.select_one('div[class$="xe_content"]')
        
        document_contents = []
        for content in xe_content.childGenerator():
            if isinstance(content, Comment):
                None
            elif isinstance(content, Tag):
                document_contents.append(content.get_text())
            elif isinstance(content, NavigableString):
                document_contents.append(str(content))
        document_content = '\n'.join(document_contents[:-1])
        # all contents except '이 게시물을'
    
    except Exception as e:
        logging.warning('Failed to retrieve body content\n'+str(e))
        document_content = errorMsg
    
    return document_content

def formatDocumentHeader(readHeader):
    
    errorMsg = '헤더를 조합하는 과정에서 오류가 발생하였습니다.'
    
    try:
        titleAndUser = readHeader.find('div', class_='titleAndUser')
        title = titleAndUser.find('div', class_='title').get_text().strip()
        author = titleAndUser.find('div', class_='author').get_text().strip()
        
        dateAndCount = readHeader.find('div', class_='dateAndCount')
        uri = dateAndCount.find('div', class_='uri').get_text().strip()
        timestamp = dateAndCount.find('div', class_='date').get_text().strip()
        views = int(dateAndCount.find('div', class_='readedCount').get_text())
        
        header = '{}\n{} | {}\n조회 수 {}\n{}\n\n---\n\n'.format(
            title, author, timestamp, views, uri
        )
        
    except Exception as e:
        logging.warning('Failed to format document header\n'+str(e))
        header = errorMsg
    
    return header

def pageContent(url, get_comments=True):
    # fangal.org/short does not support comments
    # fangal.org/fgnovel supports comments
    
    errorMsg = '다음 페이지의 내용을 불러오는 과정에서 오류가 발생하였습니다.\n{}'.format(url)
    
    logging.info(
        'Crawling {}'.format(url, )
    )
    
    try:
        ses = requests.Session()
        req = ses.get(url)
        html = req.text
        soup = bs(html, "html.parser")
        
        boardRead = soup.find('div', class_='boardRead')
        
        readHeader = boardRead.find('div', class_='readHeader')
        header = formatDocumentHeader(readHeader)
        
        readBody = boardRead.find('div', class_='readBody')
        document_content = get_content(readBody)
        
        pageContent = header + document_content
    
    except Exception as e:
        logging.warning('Failed to retrieve page content from {}\n'.format(url)+str(e))
        pageContent = errorMsg
        
    return pageContent

def listItemHandler(trItem):
    try:
        num = trItem.find('td', class_='num')
        if num: num = int(num.get_text())
        elif trItem.find('td', class_='notice'): num = 0
        else: num = -1
        
        titleClass = trItem.find('td', class_='title')
        title = titleClass.find('a').get_text().strip()
        href = titleClass.find('a', href=True)
        if href: href = href['href']
        else: href = ''
        # /index.php?mid=freenovel&page=PAGENUM&document_srl=DOCNUM
        
        n_comments = 0
        
        author = trItem.find('td', class_='author').get_text().strip()
        date_ = trItem.find('td', class_='date').get_text().strip()
        # yyyy-mm-dd
        views = trItem.find('td', class_='reading').get_text().strip()
        if views: views = int(views)
        else: views = 0
    
    except Exception as e:
        logging.warning('Failed to parse table entry on pagelist\n'+trItem+'\n'+str(e))
        num, title, n_comments, author, date_, views, href = -1, 'ERROR', 0, 'UNKNOWN', '0000.00.00', 0, ''
        
    return num, title, n_comments, author, date_, views, href

def crawlBoard(dir_target, board_title):
    logging.info('Crawling fangal.org/{}'.format(board_title))
    try:
        dir_target = os.path.normpath(dir_target)
        if not os.path.exists(dir_target): os.mkdir(dir_target)
        
        url_main = 'http://fangal.org'
        
        pageno = 0
        reached_blankpage = False
        crawled_notice = False
        
        while(not reached_blankpage or not crawled_notice):
            pageno += 1
            
            url_list = 'http://fangal.org/index.php?mid={}&page={}'.format(board_title, int(pageno))
            
            ses = requests.Session()
            req = ses.get(url_list)
            html = req.text
            
            soup = bs(html, "html.parser").find('div', id='body')
            soup = soup.find('table')
            soup = soup.find('tbody')
            
            trItems = list(soup.find_all('tr'))
            found_nonNotice = False
            
            for trItem in trItems:
                num, title, n_comments, author, date_, views, href = listItemHandler(trItem)
                # num==0 is notice. num<0 or href=='' means there was an error in listItemHandler.
                
                if not href:
                    logging.warning('Cannot open the following entry in pagelist:\n{} - {} - {}'.format(num, title, author))
                elif num or not crawled_notice:
                    if num: found_nonNotice = True
                    url_page = url_main + href
                    filename = formatFilename(num, title, author)
                    with open(os.path.join(dir_target, filename), 'wt', encoding='utf-8') as f:
                        f.write(pageContent(url_page))
            
            crawled_notice = True
            reached_blankpage = not found_nonNotice
            
        logging.info('Successfully finished crawling.')
    
    except Exception as e:
        logging.critical('An error has occured during crawling {} and the crawler has aborted.\n'.format(board_title)+str(e))

if __name__ == '__main__':
    logging.basicConfig(filename='short.log', level=logging.INFO)
    crawlBoard('crawled/short', 'short')