import requests
from bs4 import BeautifulSoup
import re,os

import random
from fake_useragent import UserAgent

ua = UserAgent()
headers = {'User-Agent': ua.random}

def find_chapter_links(url,response):
    try:
        
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        patterns = [
            r'第[零一二三四五六七八九十百千0-9]+章',  # 第一章
            r'第[0-9]+章',  # 第1章
            r'第[0-9]{1,3}章',  # 第001章
            r'第\s*[0-9]+\s*章',  # 第 1 章（带空格）
        ]
        
        chapter_links = []
        for a_tag in soup.find_all('a'):
            # 获取a标签的所有文本内容
            text = a_tag.get_text().strip()
            
            for pattern_str in patterns:
                pattern = re.compile(pattern_str)
                if pattern.search(text):
                    href = a_tag.get('href', '')
                    
                    # 处理相对链接
                    if href and not href.startswith(('http://', 'https://')):
                        if href.startswith('/'):
                            # 相对于根目录的链接
                            from urllib.parse import urljoin
                            href = urljoin(url, href)
                        else:
                            # 相对于当前页面的链接
                            from urllib.parse import urljoin
                            href = urljoin(url, href)
                    
                    chapter_links.append({
                        'text': text,
                        'href': href,
                        'matched_pattern': pattern_str
                    })
                    break  # 找到一个匹配就跳出内层循环
        
        return chapter_links
        
    except Exception as e:
        print(f"发生错误: {e}")
        return []


def extract_content_advanced(url, filename=None, element_ids=None):
    """
    高级版本：支持自定义元素ID和更多格式化选项
    
    Args:
        url (str): 要提取内容的网页URL
        filename (str, optional): 保存到的文件名
        element_ids (list, optional): 要查找的元素ID列表，默认为['chaptercontent', 'content']
    
    Returns:
        str: 格式化后的文本内容（如果filename为None）
    """
    try:
        if element_ids is None:
            element_ids = ['chaptercontent', 'content']
            
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 按照优先级查找元素
        content_element = None
        for element_id in element_ids:
            if soup.find(id=element_id):
                content_element = soup.find(id=element_id)
                print(f"找到元素: #{element_id}")
                break
        
        if not content_element:
            # 尝试通过类名查找常见的内容容器
            common_classes = ['content', 'chapter-content', 'article-content', 'text-content']
            for class_name in common_classes:
                elements = soup.find_all(class_=class_name)
                if elements:
                    content_element = elements[0]
                    print(f"通过类名找到元素: .{class_name}")
                    break
        
        if not content_element:
            print("未找到内容元素")
            return None
        
        # 提取并格式化内容
        formatted_text = format_content_advanced(content_element)
        
        # 保存或返回
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
            print(f"内容已保存到: {filename}")
            return None
        else:
            return formatted_text
            
    except Exception as e:
        print(f"发生错误: {e}")
        return None

def format_content_advanced(element):
    """
    更精确的版本：更好地处理连续文字和<br>标签
    
    Args:
        element: BeautifulSoup元素对象
    
    Returns:
        str: 格式化后的文本
    """
    # 创建副本
    element_copy = BeautifulSoup(str(element), 'html.parser').find()
    
    # 获取所有直接子节点（包括文本和标签）
    nodes = list(element_copy.children)
    
    paragraphs = []
    current_paragraph = []
    
    for node in nodes:
        # 如果是字符串（文本节点）
        if isinstance(node, str):
            text = node.strip()
            if text:  # 非空文本
                current_paragraph.append(text)
        # 如果是<br>标签
        elif node.name == 'br':
            # 如果有当前段落内容，则完成当前段落
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
        # 如果是其他标签
        else:
            # 获取标签内的文本
            tag_text = node.get_text(strip=True)
            if tag_text:
                current_paragraph.append(tag_text)
            
            # 检查标签内是否有<br>，如果有则分割段落
            if node.find('br'):
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
    
    # 处理最后一个段落
    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))
    
    # 格式化每个段落
    formatted_paragraphs = []
    for para in paragraphs:
        # 处理段落内部的多个空格
        para = re.sub(r'\s+', ' ', para)
        
        # 段首添加两个空格
        formatted_para = '  ' + para
        
        formatted_paragraphs.append(formatted_para)
    
    # 合并所有段落
    result = '\n'.join(formatted_paragraphs)
    
    return result


if __name__ == "__main__":
    target_url = "https://www.57ae58c447.cfd/book/64813/"  # 请替换为实际网址
    
    response = requests.get(target_url, headers=headers)
    response.encoding = 'utf-8'
    html_content = response.text

    soup = BeautifulSoup(html_content, 'html.parser')
    bookname = soup.find('h1').text
    print(bookname)
    os.makedirs(bookname, exist_ok=True)

    chapters = find_chapter_links(target_url,response)
    it = target_url
    
    if chapters:
        print(f"找到 {len(chapters)} 个章节链接:")
        for i, chapter in enumerate(chapters, 0):
            if chapters[i]['href'] == chapters[-1]['href'] and i == 0: #最新章节
                continue
            print(f"{i}. 文本: {chapter['text']}")
            print(f"   链接: {chapter['href']}")
            # print(f"   下一个链接 {chapters[i]['href']}")
            print(f"   匹配模式: {chapter['matched_pattern']}")
            print("-" * 50)
            extract_content_advanced(chapter['href'],bookname+'/'+chapter['text']+'.txt')