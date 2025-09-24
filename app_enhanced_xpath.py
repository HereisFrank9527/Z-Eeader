import requests
from bs4 import BeautifulSoup
import re, os
import random
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import threading
import time

# 全局配置
THREAD_COUNT = 15  # 线程数
ua = UserAgent()
headers = {'User-Agent': ua.random}

# 线程安全的计数器
class ThreadSafeCounter:
    def __init__(self):
        self.count = 0
        self.lock = threading.Lock()
        self.total = 0
        self.start_time = 0
    
    def increment(self):
        with self.lock:
            self.count += 1
            if self.count == 1:
                self.start_time = time.time()
            return self.count
    
    def set_total(self, total):
        with self.lock:
            self.total = total
    
    def get_progress(self):
        with self.lock:
            if self.total == 0:
                return 0
            elapsed = time.time() - self.start_time if self.start_time > 0 else 0
            speed = self.count / elapsed if elapsed > 0 else 0
            remaining = (self.total - self.count) / speed if speed > 0 else 0
            return {
                'count': self.count,
                'total': self.total,
                'percentage': round(self.count / self.total * 100, 2),
                'elapsed': round(elapsed, 2),
                'speed': round(speed, 2),
                'remaining': round(remaining, 2)
            }

# 进度条显示
def show_progress(counter):
    while True:
        progress = counter.get_progress()
        if progress['total'] > 0:
            print(f"进度: {progress['count']}/{progress['total']} ({progress['percentage']}%) - "
                  f"速度: {progress['speed']} 章/秒 - "
                  f"已用: {progress['elapsed']}秒 - 剩余: {progress['remaining']}秒", end='\r')
        if progress['count'] >= progress['total'] and progress['total'] > 0:
            print()
            break
        time.sleep(1)

# 使用XPath增强的章节链接提取函数 - 优化版
def find_chapter_links_enhanced(url, response):
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        chapter_links = []
        
        # 1. 尝试使用XPath定位章节列表（需要lxml解析器支持）
        try:
            # 导入lxml相关库
            from lxml import etree
            
            # 创建lxml的HTML解析对象
            html_tree = etree.HTML(response.text)
            
            # XPath表达式列表，针对不同网站结构
            xpath_expressions = [
                # 常见的章节列表容器
                '//div[contains(@class, "chapter-list")]//a',
                '//ul[contains(@class, "chapter-list")]//a',
                '//div[contains(@id, "chapter-list")]//a',
                
                # 章节列表可能的其他位置
                '//div[contains(@class, "list") and contains(@class, "chapter")]//a',
                '//div[contains(@class, "chapter") and contains(@class, "content")]//a',
                '//div[contains(@class, "chapter") and contains(@class, "list")]//a',
                
                # 按层级结构查找
                '//div[@id="content"]//a',
                '//div[@class="content"]//a',
                '//div[contains(@class, "main")]//a',
                '//div[contains(@class, "article")]//a',
                '//body//div//a',  # 兜底方案
            ]
            
            # 尝试每个XPath表达式
            found_chapters = False
            for xpath_expr in xpath_expressions:
                try:
                    elements = html_tree.xpath(xpath_expr)
                    # 过滤出看起来像章节链接的元素
                    for element in elements:
                        if element.text and len(element.text.strip()) > 0 and element.get('href'):
                            text = element.text.strip()
                            href = element.get('href', '')
                            
                            # 处理相对链接
                            if href and not href.startswith(('http://', 'https://')):
                                if href.startswith('/'):
                                    from urllib.parse import urljoin
                                    href = urljoin(url, href)
                                else:
                                    from urllib.parse import urljoin
                                    href = urljoin(url, href)
                            
                            # 添加到章节链接列表
                            chapter_links.append({
                                'text': text,
                                'href': href,
                                'matched_pattern': 'xpath: ' + xpath_expr
                            })
                    
                    # 如果通过当前XPath找到了足够多的链接，就认为找到了章节列表
                    if len(elements) > 10:
                        found_chapters = True
                        print(f"通过XPath找到章节列表: {xpath_expr} (找到 {len(elements)} 个链接)")
                        break
                except Exception as e:
                    # 当前XPath表达式失败，继续尝试下一个
                    continue
        except ImportError:
            print("警告: lxml库未安装，无法使用XPath功能")
        except Exception as e:
            print(f"XPath解析出错: {e}")
        
        # 2. 如果XPath没有找到足够的链接，回退到原有的正则表达式方法
        if not found_chapters or len(chapter_links) < 10:
            print("回退到正则表达式方法查找章节链接")
            patterns = [
                r'第[零一二三四五六七八九十百千0-9]+章',  # 第一章
                r'第[0-9]+章',  # 第1章
                r'第[0-9]{1,3}章',  # 第001章
                r'第\s*[0-9]+\s*章',  # 第 1 章（带空格）
                r'[Pp][Rr][Oo][Ll][Oo][Gg][Uu][Ee]|序章',  # 序章
                r'[Ee][Pp][Ii][Ll][Oo][Gg][Uu][Ee]|尾声|终章',  # 尾声/终章
                r'[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s*[0-9]+',  # Chapter 1
                r'[Ss][Ee][Cc][Tt][Ii][Oo][Nn]\s*[0-9]+',  # Section 1
                r'[0-9]+\s*\.',  # 1. 章节格式
                r'[0-9]+\s*、',  # 1、章节格式
            ]
            
            regex_chapters = []
            parent_paths = {}  # 统计父元素路径出现的次数
            
            for a_tag in soup.find_all('a'):
                text = a_tag.get_text().strip()
                
                for pattern_str in patterns:
                    pattern = re.compile(pattern_str)
                    if pattern.search(text):
                        href = a_tag.get('href', '')
                        
                        if href and not href.startswith(('http://', 'https://')):
                            if href.startswith('/'):
                                from urllib.parse import urljoin
                                href = urljoin(url, href)
                            else:
                                from urllib.parse import urljoin
                                href = urljoin(url, href)
                        
                        regex_chapters.append({
                            'text': text,
                            'href': href,
                            'matched_pattern': 'regex: ' + pattern_str
                        })
                        
                        # 分析父元素路径，用于后续的XPath推断
                        try:
                            parent_path = []
                            parent = a_tag.parent
                            while parent and parent.name != 'body' and parent.name != 'html':
                                # 构建父元素的简单路径表示
                                elem_repr = parent.name
                                if 'id' in parent.attrs:
                                    elem_repr += f'[id="{parent["id"]}"]'
                                elif 'class' in parent.attrs:
                                    elem_repr += f'[class*="{parent["class"][0]}"]' if parent["class"] else ''
                                parent_path.append(elem_repr)
                                parent = parent.parent
                            
                            # 反转路径并构建XPath-like表示
                            parent_path.reverse()
                            path_str = '/'.join(parent_path)
                            if path_str:
                                parent_paths[path_str] = parent_paths.get(path_str, 0) + 1
                        except Exception as e:
                            # 分析父元素路径失败，继续处理下一个链接
                            pass
                        
                        break  # 找到一个匹配就跳出内层循环
            
            # 3. 在正则表达式找到链接的同时，分析最常见的父元素路径并进行额外的XPath搜索
            additional_chapters = []
            
            if regex_chapters and parent_paths:
                # 找到出现次数最多的父元素路径
                most_common_path = max(parent_paths.items(), key=lambda x: x[1])
                
                # 只在出现次数占绝对优势时才使用这个路径进行额外搜索
                total_count = sum(parent_paths.values())
                if most_common_path[1] / total_count > 0.5:  # 如果占比超过50%
                    try:
                        from lxml import etree
                        
                        # 构建XPath表达式
                        xpath_expr = f'//{most_common_path[0]}//a'
                        print(f"发现最常见的XPath路径: {xpath_expr} (出现频率: {most_common_path[1]}/{total_count})")
                        
                        html_tree = etree.HTML(response.text)
                        elements = html_tree.xpath(xpath_expr)
                        
                        for element in elements:
                            if element.text and len(element.text.strip()) > 0 and element.get('href'):
                                text = element.text.strip()
                                href = element.get('href', '')
                                
                                # 处理相对链接
                                if href and not href.startswith(('http://', 'https://')):
                                    if href.startswith('/'):
                                        from urllib.parse import urljoin
                                        href = urljoin(url, href)
                                    else:
                                        from urllib.parse import urljoin
                                        href = urljoin(url, href)
                                
                                # 添加到额外的章节链接列表
                                additional_chapters.append({
                                    'text': text,
                                    'href': href,
                                    'matched_pattern': 'xpath_inferred: ' + xpath_expr
                                })
                        
                        if len(additional_chapters) > 0:
                            print(f"通过推断的XPath额外找到 {len(additional_chapters)} 个链接")
                    except Exception as e:
                        print(f"通过推断的XPath进行额外搜索时出错: {e}")
            
            # 4. 合并正则表达式和额外XPath搜索的结果
            all_regex_chapters = regex_chapters + additional_chapters
            
            # 如果正则表达式方法（包括额外搜索）找到了更多链接，就使用正则表达式的结果
            if len(all_regex_chapters) > len(chapter_links):
                chapter_links = all_regex_chapters
        
        # 5. 去重并排序（尝试按章节顺序）
        if chapter_links:
            # 去重
            seen = set()
            unique_chapters = []
            for chapter in chapter_links:
                key = (chapter['text'], chapter['href'])
                if key not in seen:
                    seen.add(key)
                    unique_chapters.append(chapter)
            chapter_links = unique_chapters
            
            # 尝试按章节标题中的数字排序
            try:
                def extract_number(chapter):
                    match = re.search(r'[0-9]+', chapter['text'])
                    if match:
                        return int(match.group())
                    # 中文数字转换
                    chinese_nums = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
                    for num_char, num_value in chinese_nums.items():
                        if num_char in chapter['text']:
                            return num_value
                    return float('inf')  # 无法提取数字的放在最后
                
                # 排序，但保持原始顺序的相关性
                chapter_links.sort(key=lambda x: (extract_number(x), chapter_links.index(x)))
            except Exception as e:
                print(f"排序章节链接时出错: {e}")
        
        return chapter_links
        
    except Exception as e:
        print(f"查找章节链接发生错误: {e}")
        return []

# 包装提取内容函数，添加线程安全的重试逻辑
def extract_content_advanced_with_retry(url, filename=None, element_ids=None, max_retries=3):
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 创建新的User-Agent以避免被识别为爬虫
            local_headers = {'User-Agent': UserAgent().random}
            if element_ids is None:
                element_ids = ['chaptercontent', 'content']
                
            response = requests.get(url, headers=local_headers, timeout=10)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 按照优先级查找元素
            content_element = None
            for element_id in element_ids:
                if soup.find(id=element_id):
                    content_element = soup.find(id=element_id)
                    break
            
            if not content_element:
                common_classes = ['content', 'chapter-content', 'article-content', 'text-content']
                for class_name in common_classes:
                    elements = soup.find_all(class_=class_name)
                    if elements:
                        content_element = elements[0]
                        break
            
            if not content_element:
                print(f"未找到内容元素: {url}")
                return False
            
            # 提取并格式化内容
            formatted_text = format_content_advanced(content_element)
            
            # 保存
            if filename:
                # 确保目录存在
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(formatted_text)
                return True
            else:
                return formatted_text
        except requests.exceptions.RequestException as e:
            retry_count += 1
            print(f"请求错误，正在重试 ({retry_count}/{max_retries}): {e}")
            time.sleep(2)
        except Exception as e:
            print(f"提取内容发生错误: {e}")
            return False
    print(f"达到最大重试次数，放弃: {url}")
    return False

# 优化版函数：删除a标签和包含网址的段落
def format_content_advanced(element):
    # 创建副本
    element_copy = BeautifulSoup(str(element), 'html.parser').find()
    
    # 1. 移除所有<a>标签及其内容
    for a_tag in element_copy.find_all('a'):
        a_tag.decompose()  # 完全删除标签及其内容
    
    # 2. 获取所有直接子节点（包括文本和标签）
    nodes = list(element_copy.children)
    
    paragraphs = []
    current_paragraph = []
    
    for node in nodes:
        if isinstance(node, str):
            text = node.strip()
            if text:  # 非空文本
                current_paragraph.append(text)
        elif node.name == 'br':
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
        else:
            tag_text = node.get_text(strip=True)
            if tag_text:
                current_paragraph.append(tag_text)
            
            if node.find('br'):
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
    
    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))
    
    # 3. 过滤掉包含网址的段落
    # 网址正则表达式模式
    url_pattern = re.compile(r'https?://\S+|www\.\S+|\.com|\.cn|\.net|\.org|\.info')
    
    filtered_paragraphs = []
    for para in paragraphs:
        para = re.sub(r'\s+', ' ', para)
        # 检查段落是否包含网址
        if not url_pattern.search(para):
            formatted_para = '  ' + para
            filtered_paragraphs.append(formatted_para)
    
    result = '\n'.join(filtered_paragraphs)
    return result

# 多线程处理函数
def process_chapter(chapter, bookname, counter):
    try:
        if extract_content_advanced_with_retry(chapter['href'], f"{bookname}/{chapter['text']}.txt"):
            done_count = counter.increment()
            return True, chapter
        return False, chapter
    except Exception as e:
        print(f"处理章节时出错 {chapter['text']}: {e}")
        return False, chapter

# 主函数
if __name__ == "__main__":
    start_total_time = time.time()
    target_url = "https://www.57ae58c447.cfd/book/64813/"  # 请替换为实际网址
    
    print(f"开始抓取网站: {target_url}")
    
    # 获取网站首页内容
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        bookname = soup.find('h1').text
        print(f"找到书籍: {bookname}")
        os.makedirs(bookname, exist_ok=True)
        
        # 使用增强版的章节链接提取函数
        chapters = find_chapter_links_enhanced(target_url, response)
        
        # 过滤掉最新章节（如果需要）
        if chapters and len(chapters) > 1:
            filtered_chapters = [ch for i, ch in enumerate(chapters) if not (i == 0 and ch['href'] == chapters[-1]['href'])]
        else:
            filtered_chapters = chapters
        
        print(f"找到 {len(chapters)} 个章节链接，过滤后剩余 {len(filtered_chapters)} 个章节")
        
        if filtered_chapters:
            # 初始化计数器
            counter = ThreadSafeCounter()
            counter.set_total(len(filtered_chapters))
            
            # 启动进度条线程
            progress_thread = threading.Thread(target=show_progress, args=(counter,))
            progress_thread.daemon = True
            progress_thread.start()
            
            # 使用线程池处理章节
            success_count = 0
            failed_chapters = []
            
            with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
                # 提交所有任务
                futures = {executor.submit(process_chapter, chapter, bookname, counter): chapter for chapter in filtered_chapters}
                
                # 处理完成的任务
                for future in as_completed(futures):
                    success, chapter = future.result()
                    if success:
                        success_count += 1
                    else:
                        failed_chapters.append(chapter)
            
            # 等待进度条线程结束
            progress_thread.join(timeout=2)
            
            total_time = time.time() - start_total_time
            print(f"\n任务完成！")
            print(f"成功下载: {success_count} 章")
            print(f"下载失败: {len(failed_chapters)} 章")
            print(f"总耗时: {round(total_time, 2)} 秒")
            print(f"平均速度: {round(success_count / total_time, 2)} 章/秒")
            
            # 如果有失败的章节，保存到文件
            if failed_chapters:
                with open(f"{bookname}_failed_chapters.txt", 'w', encoding='utf-8') as f:
                    for chapter in failed_chapters:
                        f.write(f"{chapter['text']}: {chapter['href']}\n")
                print(f"失败的章节列表已保存到: {bookname}_failed_chapters.txt")
        
    except Exception as e:
        print(f"程序运行出错: {e}")