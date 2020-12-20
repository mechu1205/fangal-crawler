from bs4 import BeautifulSoup as bs
from bs4 import Comment, Tag, NavigableString
import requests
import re
import logging
import os

from format_filename import formatFilename

# Use this file to crawl fangal.org/short

def get_indent(replyItem):
    # replyItem: bs4.element.Tag object
    indents = 0
    try:
        replyIndent = replyItem.find('div', class_='replyIndent', style=True)
        if replyIndent:
            indents = 1 + int(re.findall(r'\d+', replyIndent['style'])[0])//20
    except Exception as e:
        logging.warning('Failed to retrieve correct number of indentations for comment\n'+str(e))
    return indents

def formatComments(replyBox):
    # replyBox: bs4.element.Tag object
    contents = []
    indent = '  '
    firstindent = '└ '
    
    try:
        if replyBox:
            replyItems = replyBox.select('div[class^="replyItem"]')
        else:
            replyItems = []
    
    except Exception as e:
        logging.warning('Failed to retrieve comment section\n'+str(e))
        replyItems = []
    
    for replyItem in replyItems:
        content = ''
        try:
            commenter = replyItem.find('div', class_='author').get_text().strip()
            timestamp = replyItem.find('div', class_='date').get_text().strip()
            xe_content = replyItem.select_one('div[class$="xe_content"]')
            comment_contents = []
            for content in xe_content.childGenerator():
                if isinstance(content, Comment):
                    None
                elif isinstance(content, Tag):
                    comment_contents.append(str(content.get_text()).strip())
                elif isinstance(content, NavigableString):
                    comment_contents.append(str(content).strip())
            # all contents except '이 댓글을'
            
            indentations = get_indent(replyItem)
            
            content = '{} | {}'.format(commenter, timestamp)
            if indentations:
                content = indent*(indentations-1) + firstindent + content
            
            content += '\n' + indent*indentations + ('\n' + indent*indentations).join(comment_contents)
        
        except Exception as e:
            logging.warning('Failed to correctly format comment\n'+str(e))
            
        contents.append(content)
    
    header = '\n\n---\n댓글({})\n\n'.format(len(contents))
    
    return header + '\n\n'.join(contents)

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
        
        votedCount = readHeader.find('div', class_='votedCount')
        if votedCount: votedCount = str(votedCount.get_text()).strip()
        
        # replyCount = readHeader.find('div', class_='replyCount')
        # if replyCount: comments = str(replyCount.get_text()).strip()
        # else: replyCount = ''
        
        header = '{}\n{} | {}\n조회 수 {}'.format(
            title, author, timestamp, views
        )
        
        if votedCount: header += ' 추천 수 {}'.format(votedCount)
        # if replyCount: header += ' 댓글 수 {}'.format(replyCount)
        
        header += '\n{}\n\n---\n\n'.format(uri)
        
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
        if get_comments:
            replyBox = soup.find('div', class_='replyBox')
            pageContent += formatComments(replyBox)
    
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
        category = titleClass.find('strong', class_='category')
        if category: category = category.get_text().strip()
        else: category = ''
        
        n_comments = 0
        
        author = trItem.find('td', class_='author').get_text().strip()
        date_ = trItem.find('td', class_='date').get_text().strip()
        # yyyy-mm-dd
        views = trItem.find('td', class_='reading').get_text().strip()
        if views: views = int(views)
        else: views = 0
    
    except Exception as e:
        logging.warning('Failed to parse table entry on pagelist\n'+'\n'+str(e))
        num, category, title, n_comments, author, date_, views, href = -1, '', 'ERROR', 0, 'UNKNOWN', '0000.00.00', 0, ''
        
    return num, category, title, n_comments, author, date_, views, href

def crawlBoard(dir_target, board_title, get_comments=True):
    logging.info('Crawling fangal.org/{}'.format(board_title))
    try:
        dir_target = os.path.normpath(dir_target)
        if not os.path.exists(dir_target): os.makedirs(dir_target)
        
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
                num, category, title, n_comments, author, date_, views, href = listItemHandler(trItem)
                # num==0 is notice. num<0 or href=='' means there was an error in listItemHandler.
                
                if not href:
                    logging.warning('Cannot open the following entry in pagelist:\n{} - {} - {}'.format(num, title, author))
                elif num or not crawled_notice:
                    if num: found_nonNotice = True
                    url_page = url_main + href
                    filename = formatFilename(num, title, author, category=category)
                    with open(os.path.join(dir_target, filename), 'wt', encoding='utf-8') as f:
                        f.write(pageContent(url_page, get_comments=get_comments))
            
            crawled_notice = True
            reached_blankpage = not found_nonNotice
            
        logging.info('Successfully finished crawling.')
    
    except Exception as e:
        logging.critical('An error has occured during crawling {} and the crawler has aborted.\n'.format(board_title)+str(e))

if __name__ == '__main__':
    boards = {
        # 'boardname': comments_supported (bool)
        'short': False,
        'fgnovel': True,
        'invitation': False,
        'fssf': True,
        'fsf': True,
        'fgcf': True,
        'fhf': True,
        'fgproject': True,
        'old': True,
        'proposal': True,
        'notice': False,
        'critic': True,
        'reading': True,
        'novel/gow': False,
        'novel/beasts': False,
        'novel/pog': False,
        'novel/btd': False,
        'novel/bonglim': False,
        'novel/dow': False,
        'novel/oblivion': False,
        'novel/lightning': False,
        'novel/mino': False,
    }
    for board in boards:
        log = logging.getLogger()
        for hdlr in log.handlers: log.removeHandler(hdlr)
        board_lastname = board.split('/')[-1]
        logging.basicConfig(filename = '{}.log'.format(board_lastname), level=logging.INFO)
        crawlBoard('crawled/{}'.format(board), '{}'.format(board_lastname), get_comments=boards[board])