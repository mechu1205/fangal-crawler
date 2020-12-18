from bs4 import BeautifulSoup as bs
from bs4 import Comment, Tag, NavigableString
import requests
import re
import logging
import os

from format_filename import formatFilename

# Use this file to crawl fangal.org/freenovel and fangal.org/longstory

def get_indent(item):
    # item: bs4.element.Tag object
    indents = 0
    try:
        soup_indent = item.find('div', class_='indent', style=True)
        if soup_indent:
            indents = int(re.findall(r'\d+', soup_indent['style'])[0])//15
    except Exception as e:
        logging.warning('Failed to retrieve correct number of indentations for comment\n'+str(e))
    return indents

def formatComments(replyList):
    # replyList: bs4.element.Tag object
    contents = []
    indent = '  '
    firstindent = '└ '
    
    try:
        if replyList:
            items = replyList.find_all('div', class_='item')
        else:
            items = []
    except Exception as e:
        logging.warning('Failed to retrieve comment section\n'+str(e))
        items = []
    
    for item in items:
        content = ''
        try:
            commenter = item.find('h4', class_='header').get_text().strip()
            date_, time_, ipAddress = item.find('p', class_='meta').get_text().split()
            xe_content = item.find('div', class_='itemContent').select_one('div[class$="xe_content"]')
            indentations = get_indent(item)
            
            if indentations:
                content += indent*(indentations-1) + firstindent + '{} ({}) | {} {}'.format(commenter, ipAddress, date_, time_)
            else:
                content += '{} ({}) | {} {}'.format(commenter, ipAddress, date_, time_)
            
            content += '\n' + indent*indentations + xe_content.get_text('\n' + indent*indentations)
        
        except Exception as e:
            logging.warning('Failed to correctly format comment\n'+str(e))
            
        contents.append(content)
    
    header = '\n---\n\n댓글({})\n\n'.format(len(contents))
    
    return header + '\n\n'.join(contents)

def get_content(boardReadBody):
    
    errorMsg = '본문을 불러오는 과정에서 오류가 발생하였습니다.'
    
    try:
        xe_content = boardReadBody.select_one('div[class$="xe_content"]')
        if xe_content:
            document_contents = []
            for content in xe_content.childGenerator():
                if isinstance(content, Comment):
                    None
                elif isinstance(content, Tag):
                    document_contents.append(str(content.get_text()).strip())
                elif isinstance(content, NavigableString):
                    document_contents.append(str(content).strip())
            document_content = '\n'.join(document_contents[:-1])
            # all contents except '이 게시물을'
        else:
            if boardReadBody.find('form', class_='secretMessage'):
                # Password-Locked Content
                document_content = '비밀글입니다.'
            else:
                document_content = errorMsg
        
    except Exception as e:
        logging.warning('Failed to retrieve body content\n'+str(e))
        document_content = errorMsg
    
    return document_content

def formatDocumentHeader(boardReadHeader):
    
    errorMsg = '헤더를 조합하는 과정에서 오류가 발생하였습니다.'
    
    try:
        titleArea = boardReadHeader.find('div', class_='titleArea')
        title = titleArea.find('h3', class_='title').get_text().strip()
        category = titleArea.find('a', class_='category').get_text().strip()
        
        sum_ = titleArea.find('span', class_='sum')
        # 조회 수 num\n추천 수 num\nyyyy.MM.dd hh:mm:ss 
        views = sum_.find('span', class_='read').find('span', class_='num').get_text()
        upvotes = sum_.find('span', class_='vote').find('span', class_='num').get_text()
        timestamp = sum_.find('span', class_='date').get_text()
        
        authorArea = boardReadHeader.find('div', class_='authorArea')
        permaLink = authorArea.find('a', class_='permaLink').get_text().strip()
        if authorArea.find('a', href='#popup_menu_area'):
            author = authorArea.find('a').get_text().strip()
        else:
            author = authorArea.find(text=True, recursive=False).strip()
        ipAddress = authorArea.find('span', class_='ipAddress').get_text().strip()
        
        header = title
        if category:
            header += ' | {}'.format(category)
        header += '\n{} ({}) | {}\n조회 수 {} 추천 수 {}\n{}\n\n---\n\n'.format(
            author, ipAddress, timestamp, views, upvotes, permaLink
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
        
        boardRead = soup.find('div', class_='boardRead')
        commentAuthor = ""
        if (len(boardRead.find_all('center')) > 1):
            commentAuthor = boardRead.find_all('center')[-1].get_text()
        
        boardReadHeader = boardRead.find('div', class_='boardReadHeader')
        header = formatDocumentHeader(boardReadHeader)
        
        boardReadBody = boardRead.find('div', class_='boardReadBody')
        document_content = get_content(boardReadBody)
        
        pageContent = header + document_content
        
        if commentAuthor:
            pageContent += '\n\n---\n\n{}'.format(commentAuthor)
        
        if get_comments:
            replyList = soup.find('div', class_='replyList')
            pageContent += formatComments(replyList)
    
    except Exception as e:
        logging.warning('Failed to retrieve page content from {}\n'.format(url)+str(e))
        pageContent = errorMsg
        
    return pageContent

def listItemHandler(trItem):
    try:
        num = trItem.find('td', class_='num')
        if num: num = int(num.get_text())
        else: num = 0 # Notice
        
        titleClass = trItem.find('td', class_='title')
        category = titleClass.find('strong', class_='category')
        if category: category = category.get_text().strip()
        title = titleClass.find('a').get_text().strip()
        href = titleClass.find('a', href=True)
        if href: href = href['href']
        else: href = ''
        # /index.php?mid=freenovel&page=PAGENUM&document_srl=DOCNUM
        
        n_comments = 0
        if len(titleClass.find_all('a'))>1:
            n_comments = int(titleClass.find_all('a')[-1].find('span', class_='replyNum').get_text().strip()[1:-1])
            # [num]
        
        author = trItem.find('td', class_='author').get_text().strip()
        date_ = trItem.find('td', class_='date').get_text().strip()
        # yyyy-mm-dd
        views = trItem.find('td', class_='reading').get_text().strip()
        if views: views = int(views)
        else: views = 0
    
    except Exception as e:
        logging.warning('Failed to parse table entry on pagelist\n'+'\n'+str(e))
        num, category, title, n_comments, author, date_, views, href = -1, None, 'ERROR', 0, 'UNKNOWN', '0000-00-00', 0, ''
        
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
            
            soup = bs(html, "html.parser").find('div', {'id':'xe_container'})
            soup = soup.find('table', {'summary':'List of Articles', 'class': 'boardList'})
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
                    filename = formatFilename(num, title, author)
                    with open(os.path.join(dir_target, filename), 'wt', encoding='utf-8') as f:
                        f.write(pageContent(url_page, get_comments=True))
            
            crawled_notice = True
            reached_blankpage = not found_nonNotice
        
        logging.info('Successfully finished crawling.')
    
    except Exception as e:
        logging.critical('An error has occured during crawling {} and the crawler has aborted.\n'.format(board_title)+str(e))

if __name__ == '__main__':
    # logging.basicConfig(filename='freenovel.log', level=logging.INFO)
    # crawlBoard('crawled/freenovel', 'freenovel')
    # logging.basicConfig(filename='longstory.log', level=logging.INFO)
    # crawlBoard('crawled/longstory', 'longstory')
    print(pageContent('http://fangal.org/freenovel/620097'))