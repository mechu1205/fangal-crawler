from bs4 import BeautifulSoup as bs
import requests
import re
import logging
import os

from format_filename import formatFilename

# Use this file to crawl fangal.org/free_review

def formatComments(cmtPosition):
    # replyList: bs4.element.Tag object
    contents = []
    
    try:
        if cmtPosition:
            header = cmtPosition.select_one('a[class^="nametag"]').get_text()
            items = list(cmtPosition.select('li[id^="comment_"]'))
        else:
            header = "Comment '0'"
            items = []
    
    except Exception as e:
        logging.warning('Failed to retrieve comment section\n'+str(e))
        items = []
    
    for item in items:
        content = ''
        try:
            commenter = item.find('div', class_='meta').find('a').get_text().strip()
            timestamp = item.find('span', class_='date').get_text().strip()
            content = '{} | {}'.format(commenter, timestamp)
            
            content += '\n' + item.select_one('div[class$="xe_content"]').get_text('\n')
            
        except Exception as e:
            logging.warning('Failed to correctly format comment\n'+str(e))
            
        contents.append(content)
    
    header = '\n---\n\n댓글({})\n\n'.format(len(contents))
    
    return header + '\n\n'.join(contents)

def get_content(rd_body):
    
    errorMsg = '본문을 불러오는 과정에서 오류가 발생하였습니다.'
    
    try:
        xe_content = rd_body.select_one('div[class$="xe_content"]')
        
        document_contents = []
        for content in xe_content.childGenerator():
            if 'get_text' in dir(content):
                document_contents.append(content.get_text())
            else:
                document_contents.append(str(content))
        document_content = '\n'.join(document_contents)
    
    except Exception as e:
        logging.warning('Failed to retrieve body content\n'+str(e))
        document_content = errorMsg
    
    return document_content

def formatDocumentHeader(rd_hd):
    
    errorMsg = '헤더를 조합하는 과정에서 오류가 발생하였습니다.'
    
    try:
        top_area = rd_hd.select_one('div[class^="top_area"]')
        timestamp = top_area.find('span', class_='date m_no').get_text().strip()
        # yyyy.MM.dd hh:mm
        ahref = top_area.find('a', href=True)
        link = ahref['href']
        title = ahref.get_text()
        
        btm_area = rd_hd.select_one('div[class^="btm_area"]')
        author = btm_area.find('div').get_text().strip()
        
        spans = list(btm_area.find_all('span'))
        views = spans[0].find('b').get_text().strip()
        # views = int(views) if views else 0
        upvotes = spans[1].find('b').get_text().strip()
        # upvotes = int(upvotes) if upvotes else 0
        n_comments = spans[2].find('b').get_text().strip()
        # n_comments = int(n_comments) if n_comments else 0
        
        header = '{}\n{} | {}\n조회 수 {} 추천 수 {} 댓글 {}\n{}\n\n---\n\n'.format(
            title, author, timestamp, views, upvotes, n_comments, link
        )
        
    except Exception as e:
        logging.warning('Failed to format document header\n'+str(e))
        header = errorMsg
    
    return header

def pageContent(url, get_comments=True):
    
    errorMsg = '다음 페이지의 내용을 불러오는 과정에서 오류가 발생하였습니다.\n{}'.format(url)
    
    logging.info(
        'Crawling {} with{} comments'.format(url, ('' if get_comments else 'out'))
    )
    
    try:
        ses = requests.Session()
        req = ses.get(url)
        html = req.text
        soup = bs(html, "html.parser")
        
        rd = soup.find('div', class_='rd clear')
        
        rd_hd = rd.find('div', class_='rd_hd clear')
        header = formatDocumentHeader(rd_hd)
        
        rd_body = rd.find('div', class_='rd_body clear')
        document_content = get_content(rd_body)
        
        pageContent = header + document_content
        
        if get_comments:
            cmtPosition = soup.find('div', id='cmtPosition')
            pageContent += formatComments(cmtPosition)
    
    except Exception as e:
        logging.warning('Failed to retrieve page content from {}\n'.format(url)+str(e))
        pageContent = errorMsg
        
    return pageContent

def listItemHandler(trItem):
    try:
        num = trItem.find('td', class_='no')
        if num: num = int(num.get_text())
        else: num = -1
        
        titleClass = trItem.find('td', class_='title')
        title = titleClass.find('a').get_text().strip()
        href = titleClass.find('a', href=True)
        if href: href = href['href']
        else: href = ''
        # /index.php?mid=freenovel&page=PAGENUM&document_srl=DOCNUM
        
        n_comments = 0
        if titleClass.find('a', class_='replyNum'):
            n_comments = int(titleClass.find('a', class_='replyNum').get_text())
        
        author = trItem.find('td', class_='author').get_text().strip()
        date_ = trItem.find('td', class_='time').get_text().strip()
        # yyyy.mm.dd
        views = trItem.find('td', class_='m_no').get_text().strip()
        if views: views = int(views)
        else: views = 0
    
    except Exception as e:
        logging.warning('Failed to parse table entry on pagelist\n'+trItem+'\n'+str(e))
        num, title, n_comments, author, date_, views, href = -1, 'ERROR', 0, 'UNKNOWN', '0000.00.00', 0, ''
        
    return num, title, n_comments, author, date_, views, href

def crawlBoard(dir_target, board_title):
    logging.info('Crawling fangal.org/{}'.format(board_title))
    try:
        if not os.path.exists(dir_target): os.mkdir(dir_target)
        
        url_main = 'http://fangal.org'
        
        pageno = 0
        reached_blankpage = False
        
        while(not reached_blankpage):
            pageno += 1
            
            url_list = 'http://fangal.org/index.php?mid={}&page={}'.format(board_title, int(pageno))
            
            ses = requests.Session()
            req = ses.get(url_list)
            html = req.text
            
            soup = bs(html, "html.parser").find('div', class_='bd_lst_wrp')
            soup = soup.find('table')
            soup = soup.find('tbody')
            
            trItems = list(soup.find_all('tr'))
            
            reached_blankpage = (len(trItems) == 0)
            
            for trItem in trItems:
                num, title, n_comments, author, date_, views, href = listItemHandler(trItem)
                # num==0 is notice. num<0 or href=='' means there was an error in listItemHandler.
                
                if not href:
                    logging.warning('Cannot open the following entry in pagelist:\n{} - {} - {}'.format(num, title, author))
                elif num or reached_blankpage:
                    url_page = url_main + href
                    filename = formatFilename(num, title, author)
                    
                    with open(os.path.join(dir_target, filename), 'wt', encoding='utf-8') as f:
                        f.write(pageContent(url_page))
        
        logging.info('Successfully finished crawling.')
    
    except Exception as e:
        logging.critical('An error has occured during crawling {} and the crawler has aborted.\n'.format(board_title)+str(e))

if __name__ == '__main__':
    logging.basicConfig(filename='free_review.log', level=logging.INFO)
    crawlBoard('free_review', 'free_review')