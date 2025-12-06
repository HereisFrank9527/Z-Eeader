# -*- coding: utf-8 -*-
"""
目录解析器
"""
from typing import List
from urllib.parse import urljoin
from models.chapter import Chapter
from models.rule import Rule
from core.http_client import HttpClient
from core.selector import Selector


class TocParser:
    """章节目录解析器"""

    def __init__(self, rule: Rule, http_client: HttpClient = None):
        """
        初始化目录解析器

        Args:
            rule: 书源规则
            http_client: HTTP 客户端
        """
        self.rule = rule
        self.http_client = http_client or HttpClient()

    def parse(self, book_url: str, start_index: int = 1, end_index: int = -1) -> List[Chapter]:
        """
        解析章节目录

        Args:
            book_url: 书籍详情页 URL
            start_index: 起始章节索引（从 1 开始）
            end_index: 结束章节索引（-1 表示到最后）

        Returns:
            章节列表
        """
        if not self.rule.toc:
            print(f"书源 {self.rule.name} 没有配置目录规则")
            return []

        toc_rule = self.rule.toc

        try:
            # 确定目录页 URL
            toc_url = toc_rule.url if toc_rule.url else book_url

            # 如果 toc_url 包含 %s，需要从 book_url 中提取 ID
            if toc_rule.url and '%s' in toc_rule.url:
                # 从 book_url 中提取书籍 ID
                # 例如：http://www.yeudusk.com/book/1234916/ -> 1234916
                import re
                match = re.search(r'/(\d+)/?$', book_url)
                if match:
                    book_id = match.group(1)
                    toc_url = toc_rule.url.replace('%s', book_id)
                else:
                    # 如果无法提取 ID，使用原 URL
                    print(f"无法从 {book_url} 中提取书籍 ID")
                    toc_url = book_url

            # 处理相对路径
            if toc_rule.url and not toc_url.startswith('http'):
                toc_url = urljoin(book_url, toc_url)

            # 发送请求
            response = self.http_client.get(toc_url)
            response.encoding = response.apparent_encoding
            html = response.text

            # 解析目录
            chapters = self._parse_toc_page(html, toc_url, toc_rule)

            # 处理倒序
            if toc_rule.is_desc:
                chapters.reverse()

            # 设置章节索引
            for i, chapter in enumerate(chapters, 1):
                chapter.index = i

            # 截取指定范围
            if end_index == -1:
                end_index = len(chapters)

            chapters = chapters[start_index - 1:end_index]

            print(f"成功解析目录，共 {len(chapters)} 章")
            return chapters

        except Exception as e:
            print(f"解析目录失败: {e}")
            return []

    def _parse_toc_page(self, html: str, base_url: str, toc_rule) -> List[Chapter]:
        """
        解析单个目录页

        Args:
            html: HTML 内容
            base_url: 基础 URL
            toc_rule: 目录规则

        Returns:
            章节列表
        """
        base_uri = toc_rule.base_uri or base_url
        
        # 处理 base_uri 中的 %s 占位符
        if base_uri and '%s' in base_uri:
            # 从 book_url 中提取书籍 ID
            # 例如：http://www.xbiquzw.net/10_10229/ -> 10_10229
            import re
            match = re.search(r'/(\d+_\d+|\d+)/?$', base_url)
            if match:
                book_id = match.group(1)
                base_uri = base_uri.replace('%s', book_id)
            else:
                # 如果无法提取 ID，使用原 URL
                print(f"无法从 {base_url} 中提取书籍 ID")
                base_uri = base_url
        
        selector = Selector(html, base_uri)

        chapters = []

        # 选择所有章节链接
        soup = selector.soup
        chapter_elements = soup.select(toc_rule.item)

        for elem in chapter_elements:
            try:
                title = elem.get_text(strip=True)
                href = elem.get('href', '')

                if not title or not href:
                    continue

                # 处理相对路径
                chapter_url = urljoin(base_uri, href)

                chapter = Chapter(
                    title=title,
                    url=chapter_url
                )

                chapters.append(chapter)

            except Exception as e:
                print(f"解析单个章节链接失败: {e}")
                continue

        return chapters
