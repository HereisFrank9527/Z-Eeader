# -*- coding: utf-8 -*-
"""
书籍详情解析器
"""
from typing import Optional
from urllib.parse import urljoin
from models.book import Book
from models.rule import Rule
from core.http_client import HttpClient
from core.selector import Selector


class BookParser:
    """书籍详情解析器"""

    def __init__(self, rule: Rule, http_client: HttpClient = None):
        """
        初始化书籍解析器

        Args:
            rule: 书源规则
            http_client: HTTP 客户端
        """
        self.rule = rule
        self.http_client = http_client or HttpClient()

    def parse(self, book_url: str) -> Optional[Book]:
        """
        解析书籍详情

        Args:
            book_url: 书籍详情页 URL

        Returns:
            书籍对象
        """
        if not self.rule.book:
            print(f"书源 {self.rule.name} 没有配置书籍规则")
            return None

        book_rule = self.rule.book

        try:
            # 发送请求
            response = self.http_client.get(book_url)
            response.encoding = response.apparent_encoding
            html = response.text

            # 创建选择器
            base_uri = book_rule.base_uri or book_url
            selector = Selector(html, base_uri)

            # 提取书名和作者（必填）
            book_name = self._get_content(selector, book_rule.book_name)
            author = self._get_content(selector, book_rule.author)

            if not book_name or not author:
                print(f"未能提取书名或作者: {book_url}")
                return None

            # 创建书籍对象
            book = Book(
                url=book_url,
                book_name=book_name.strip(),
                author=author.strip()
            )

            # 提取可选字段
            if book_rule.intro:
                book.intro = self._get_content(selector, book_rule.intro)

            if book_rule.cover_url:
                cover = self._get_content(
                    selector,
                    book_rule.cover_url,
                    attr='content' if 'meta[' in book_rule.cover_url else 'src'
                )
                if cover:
                    book.cover_url = urljoin(base_uri, cover)

            if book_rule.category:
                book.category = self._get_content(selector, book_rule.category)

            if book_rule.latest_chapter:
                book.latest_chapter = self._get_content(selector, book_rule.latest_chapter)

            if book_rule.last_update_time:
                book.last_update_time = self._get_content(selector, book_rule.last_update_time)

            if book_rule.status:
                book.status = self._get_content(selector, book_rule.status)

            if book_rule.word_count:
                book.word_count = self._get_content(selector, book_rule.word_count)

            print(f"成功解析书籍: {book}")
            return book

        except Exception as e:
            print(f"解析书籍详情失败: {e}")
            return None

    def _get_content(self, selector: Selector, query: str, attr: Optional[str] = None) -> str:
        """
        从选择器中提取内容

        Args:
            selector: 选择器对象
            query: 查询表达式
            attr: 属性名

        Returns:
            提取的内容
        """
        if not query:
            return ""

        # 判断是否为 meta 标签（默认提取 content 属性）
        if query.startswith('meta[') and attr is None:
            attr = 'content'

        result = selector.select_one(query, attr)
        return result.strip() if result else ""
