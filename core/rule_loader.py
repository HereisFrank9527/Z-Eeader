# -*- coding: utf-8 -*-
"""
规则加载器
"""
import json
import os
from pathlib import Path
from typing import List, Optional
from models.rule import (
    Rule, SearchRule, BookRule, TocRule, ChapterRule, CrawlConfig
)


class RuleLoader:
    """规则文件加载器"""

    def __init__(self, rules_dir: str = None):
        """
        初始化规则加载器

        Args:
            rules_dir: 规则文件目录路径，默认为项目下的 rules 目录
        """
        if rules_dir is None:
            # 获取项目根目录
            current_dir = Path(__file__).parent.parent
            rules_dir = current_dir / "rules"

        self.rules_dir = Path(rules_dir)
        self._rules_cache = {}

    def load_rules(self, rule_file: str = "main-rules.json") -> List[Rule]:
        """
        加载规则文件

        Args:
            rule_file: 规则文件名

        Returns:
            规则对象列表
        """
        rule_path = self.rules_dir / rule_file

        if not rule_path.exists():
            raise FileNotFoundError(f"规则文件不存在: {rule_path}")

        with open(rule_path, 'r', encoding='utf-8') as f:
            rules_data = json.load(f)

        rules = []
        for rule_dict in rules_data:
            rule = self._parse_rule(rule_dict)
            if rule and not rule.disabled:
                rules.append(rule)

        return rules

    def _parse_rule(self, rule_dict: dict) -> Optional[Rule]:
        """
        解析单个规则字典

        Args:
            rule_dict: 规则字典

        Returns:
            规则对象
        """
        try:
            # 解析搜索规则
            search_rule = None
            if 'search' in rule_dict and rule_dict['search']:
                search_dict = rule_dict['search']
                search_rule = SearchRule(
                    disabled=search_dict.get('disabled', False),
                    url=search_dict.get('url', ''),
                    method=search_dict.get('method', 'GET'),
                    data=search_dict.get('data', '{}'),
                    cookies=search_dict.get('cookies', '{}'),
                    result=search_dict.get('result', ''),
                    book_name=search_dict.get('bookName', ''),
                    author=search_dict.get('author', ''),
                    category=search_dict.get('category'),
                    word_count=search_dict.get('wordCount'),
                    status=search_dict.get('status'),
                    latest_chapter=search_dict.get('latestChapter'),
                    last_update_time=search_dict.get('lastUpdateTime'),
                    pagination=search_dict.get('pagination', False),
                    next_page=search_dict.get('nextPage')
                )

            # 解析书籍规则
            book_rule = None
            if 'book' in rule_dict and rule_dict['book']:
                book_dict = rule_dict['book']
                book_rule = BookRule(
                    url=book_dict.get('url'),
                    book_name=book_dict.get('bookName', ''),
                    author=book_dict.get('author', ''),
                    intro=book_dict.get('intro'),
                    category=book_dict.get('category'),
                    cover_url=book_dict.get('coverUrl'),
                    latest_chapter=book_dict.get('latestChapter'),
                    last_update_time=book_dict.get('lastUpdateTime'),
                    status=book_dict.get('status'),
                    word_count=book_dict.get('wordCount'),
                    timeout=book_dict.get('timeout'),
                    base_uri=book_dict.get('baseUri')
                )

            # 解析目录规则
            toc_rule = None
            if 'toc' in rule_dict and rule_dict['toc']:
                toc_dict = rule_dict['toc']
                toc_rule = TocRule(
                    base_uri=toc_dict.get('baseUri'),
                    url=toc_dict.get('url'),
                    item=toc_dict.get('item', ''),
                    is_desc=toc_dict.get('isDesc', False),
                    pagination=toc_dict.get('pagination', False),
                    next_page=toc_dict.get('nextPage')
                )

            # 解析章节规则
            chapter_rule = None
            if 'chapter' in rule_dict and rule_dict['chapter']:
                chapter_dict = rule_dict['chapter']
                chapter_rule = ChapterRule(
                    title=chapter_dict.get('title', ''),
                    content=chapter_dict.get('content', ''),
                    paragraph_tag_closed=chapter_dict.get('paragraphTagClosed', False),
                    paragraph_tag=chapter_dict.get('paragraphTag'),
                    filter_txt=chapter_dict.get('filterTxt'),
                    filter_tag=chapter_dict.get('filterTag'),
                    pagination=chapter_dict.get('pagination', False),
                    next_page=chapter_dict.get('nextPage')
                )

            # 解析爬取配置
            crawl_config = None
            if 'crawl' in rule_dict and rule_dict['crawl']:
                crawl_dict = rule_dict['crawl']
                crawl_config = CrawlConfig(
                    threads=crawl_dict.get('threads'),
                    min_interval=crawl_dict.get('minInterval'),
                    max_interval=crawl_dict.get('maxInterval'),
                    max_attempts=crawl_dict.get('maxAttempts'),
                    retry_min_interval=crawl_dict.get('retryMinInterval'),
                    retry_max_interval=crawl_dict.get('retryMaxInterval')
                )

            # 创建规则对象
            rule = Rule(
                url=rule_dict.get('url', ''),
                name=rule_dict.get('name', ''),
                comment=rule_dict.get('comment'),
                disabled=rule_dict.get('disabled', False),
                search=search_rule,
                book=book_rule,
                toc=toc_rule,
                chapter=chapter_rule,
                crawl=crawl_config,
                language=rule_dict.get('language'),
                ignore_ssl=rule_dict.get('ignoreSsl', False)
            )

            return rule

        except Exception as e:
            print(f"解析规则失败: {rule_dict.get('name', 'Unknown')} - {e}")
            return None

    def get_rule_by_name(self, name: str, rule_file: str = "main-rules.json") -> Optional[Rule]:
        """
        根据名称获取规则

        Args:
            name: 规则名称
            rule_file: 规则文件名

        Returns:
            规则对象
        """
        rules = self.load_rules(rule_file)
        for rule in rules:
            if rule.name == name:
                return rule
        return None

    def get_all_rule_names(self, rule_file: str = "main-rules.json") -> List[str]:
        """
        获取所有规则名称

        Args:
            rule_file: 规则文件名

        Returns:
            规则名称列表
        """
        rules = self.load_rules(rule_file)
        return [rule.name for rule in rules]
