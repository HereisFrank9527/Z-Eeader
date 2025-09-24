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
THREAD_COUNT = 15  # 线程数，可以根据需要调整为10-20
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

# 原有函数保持不变
def find_chapter_links(url, response):
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
                    
                    chapter_links.append({
                        'text': text,
                        'href': href,
                        'matched_pattern': pattern_str
                    })
                    break  # 找到一个匹配就跳出内层循环
        
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
                
            response = requests.get(url, headers=local_headers, timeout=10)  # 添加超时设置
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
            time.sleep(2)  # 增加等待时间避免请求过于频繁
        except Exception as e:
            print(f"提取内容发生错误: {e}")
            return False
    print(f"达到最大重试次数，放弃: {url}")
    return False

# 原有函数保持不变
def format_content_advanced(element):
    # 创建副本
    element_copy = BeautifulSoup(str(element), 'html.parser').find()
    
    # 获取所有直接子节点（包括文本和标签）
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
    
    formatted_paragraphs = []
    for para in paragraphs:
        para = re.sub(r'\s+', ' ', para)
        formatted_para = '  ' + para
        formatted_paragraphs.append(formatted_para)
    
    result = '\n'.join(formatted_paragraphs)
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
        
        # 查找所有章节链接
        chapters = find_chapter_links(target_url, response)
        
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