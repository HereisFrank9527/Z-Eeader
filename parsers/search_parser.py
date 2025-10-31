# -*- coding: utf-8 -*-
"""
搜索解析器
"""
import json
import re
from typing import List
from urllib.parse import urljoin
from models.book import Book
from models.rule import Rule
from core.http_client import HttpClient
from core.selector import Selector


class SearchParser:
    """搜索结果解析器"""

    def __init__(self, rule: Rule, http_client: HttpClient = None):
        """
        初始化搜索解析器

        Args:
            rule: 书源规则
            http_client: HTTP 客户端
        """
        self.rule = rule
        self.http_client = http_client or HttpClient()

    def search(self, keyword: str, max_results: int = 20) -> List[Book]:
        """
        搜索书籍

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数

        Returns:
            书籍列表
        """
        if not self.rule.search or self.rule.search.disabled:
            print(f"书源 {self.rule.name} 不支持搜索")
            return []

        search_rule = self.rule.search
        books = []

        try:
            # 构建搜索 URL
            search_url = search_rule.url.replace('%s', keyword)

            # 解析请求数据
            data_dict = self._parse_data(search_rule.data, keyword)
            cookies_dict = self._parse_cookies(search_rule.cookies)

            # 发送请求
            if search_rule.method.upper() == 'POST':
                response = self.http_client.post(
                    search_url,
                    data=data_dict,
                    cookies=cookies_dict
                )
            else:
                response = self.http_client.get(
                    search_url,
                    cookies=cookies_dict
                )

            response.encoding = response.apparent_encoding
            html = response.text

            # 解析搜索结果
            books = self._parse_results(html, search_rule)

            # 限制结果数量
            if len(books) > max_results:
                books = books[:max_results]

            print(f"从 {self.rule.name} 搜索到 {len(books)} 本书")

        except Exception as e:
            print(f"搜索失败 ({self.rule.name}): {e}")

        return books

    def _parse_data(self, data_str: str, keyword: str) -> dict:
        """
        解析请求数据

        Args:
            data_str: 数据字符串，如 "{searchkey: %s}"
            keyword: 搜索关键词

        Returns:
            数据字典
        """
        if not data_str or data_str == '{}':
            return {}

        try:
            # 替换 %s 为关键词
            data_str = data_str.replace('%s', f'"{keyword}"')
            # 转换为标准 JSON（处理没有引号的键和值）
            # 替换键名（word: -> "word":）
            data_str = re.sub(r'(\w+):', r'"\1":', data_str)
            # 替换没有引号的值（但跳过已经有引号的）
            # data_str = re.sub(r':\s*([^",\{\}\[\]]+)\s*([,\}])', r': "\1"\2', data_str)

            return json.loads(data_str)
        except Exception as e:
            # print(f"解析请求数据失败: {e}")
            # 如果 JSON 解析失败，尝试手动解析
            try:
                # 移除花括号
                data_str = data_str.strip('{}').strip()
                if not data_str:
                    return {}

                result = {}
                # 分割键值对
                pairs = data_str.split(',')
                for pair in pairs:
                    if ':' in pair:
                        key, value = pair.split(':', 1)
                        key = key.strip().strip('"\'')
                        value = value.strip().strip('"\'')
                        result[key] = value

                return result
            except:
                return {}

    def _parse_cookies(self, cookies_str: str) -> dict:
        """
        解析 Cookies

        Args:
            cookies_str: Cookies 字符串，如 "{key1: 'value1', key2: ''}"

        Returns:
            Cookies 字典
        """
        if not cookies_str or cookies_str == '{}':
            return {}

        try:
            # 尝试手动解析
            # 移除花括号
            cookies_str = cookies_str.strip('{}').strip()
            if not cookies_str:
                return {}

            result = {}
            # 分割键值对
            pairs = cookies_str.split(',')
            for pair in pairs:
                if ':' in pair:
                    key, value = pair.split(':', 1)
                    key = key.strip().strip('"\'')
                    value = value.strip().strip('"\'')
                    if value:  # 只添加非空值
                        result[key] = value

            return result
        except Exception as e:
            # print(f"解析 Cookies 失败: {e}")
            return {}

    def _parse_results(self, html: str, search_rule) -> List[Book]:
        """
        解析搜索结果

        Args:
            html: HTML 内容
            search_rule: 搜索规则

        Returns:
            书籍列表
        """
        selector = Selector(html, self.rule.url)
        books = []

        # 选择所有结果项 - 使用Selector的select方法而不是直接用soup.select
        # 这样可以利用Selector类中的tbody处理逻辑
        result_elements_html = selector.select(search_rule.result)
        
        # 需要将HTML文本转换回元素对象以提取链接
        from bs4 import BeautifulSoup
        soup = selector.soup
        
        # 重新用soup.select获取元素对象（用于提取href）
        # 但先检查是否包含tbody，如果包含则移除后再选择
        result_selector = search_rule.result
        if 'tbody' in result_selector:
            import re
            result_selector = re.sub(r'>\s*tbody\s*>', '>', result_selector)
            result_selector = re.sub(r'\s+tbody\s+', ' ', result_selector)
            result_selector = re.sub(r'>\s*tbody\s+', '> ', result_selector)
            result_selector = re.sub(r'\s+tbody\s*>', ' >', result_selector)
        
        result_elements = soup.select(result_selector)

        for elem in result_elements:
            try:
                # 为每个结果项创建选择器
                elem_html = str(elem)
                elem_selector = Selector(elem_html, self.rule.url)

                # 提取书籍信息
                book_name = elem_selector.select_one(search_rule.book_name)
                author = elem_selector.select_one(search_rule.author)

                if not book_name or not author:
                    continue

                # 提取详情页 URL
                book_url = ""
                link_elem = elem.select_one(search_rule.book_name)
                if link_elem and link_elem.get('href'):
                    book_url = urljoin(self.rule.url, link_elem.get('href'))

                # 创建书籍对象
                book = Book(
                    url=book_url,
                    book_name=book_name.strip(),
                    author=author.strip()
                )

                # 提取可选字段
                if search_rule.category:
                    book.category = elem_selector.select_one(search_rule.category)

                if search_rule.latest_chapter:
                    book.latest_chapter = elem_selector.select_one(search_rule.latest_chapter)

                if search_rule.last_update_time:
                    book.last_update_time = elem_selector.select_one(search_rule.last_update_time)

                if search_rule.word_count:
                    book.word_count = elem_selector.select_one(search_rule.word_count)

                if search_rule.status:
                    book.status = elem_selector.select_one(search_rule.status)

                books.append(book)

            except Exception as e:
                print(f"解析单个搜索结果失败: {e}")
                continue

        return books
