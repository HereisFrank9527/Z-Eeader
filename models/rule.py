# -*- coding: utf-8 -*-
"""
规则模型类
"""
from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class SearchRule:
    """搜索规则"""
    disabled: bool = False
    url: str = ""
    method: str = "GET"
    data: str = "{}"
    cookies: str = "{}"
    result: str = ""
    book_name: str = ""
    author: str = ""
    category: Optional[str] = None
    word_count: Optional[str] = None
    status: Optional[str] = None
    latest_chapter: Optional[str] = None
    last_update_time: Optional[str] = None
    pagination: bool = False
    next_page: Optional[str] = None


@dataclass
class BookRule:
    """书籍详情规则"""
    url: Optional[str] = None
    book_name: str = ""
    author: str = ""
    intro: Optional[str] = None
    category: Optional[str] = None
    cover_url: Optional[str] = None
    latest_chapter: Optional[str] = None
    last_update_time: Optional[str] = None
    status: Optional[str] = None
    word_count: Optional[str] = None
    timeout: Optional[int] = None
    base_uri: Optional[str] = None


@dataclass
class TocRule:
    """目录规则"""
    base_uri: Optional[str] = None
    url: Optional[str] = None
    item: str = ""
    is_desc: bool = False
    pagination: bool = False
    next_page: Optional[str] = None


@dataclass
class ChapterRule:
    """章节规则"""
    title: str = ""
    content: str = ""
    paragraph_tag_closed: bool = False
    paragraph_tag: Optional[str] = None
    filter_txt: Optional[str] = None
    filter_tag: Optional[str] = None
    pagination: bool = False
    next_page: Optional[str] = None


@dataclass
class CrawlConfig:
    """爬取配置"""
    threads: Optional[int] = None
    min_interval: Optional[int] = None
    max_interval: Optional[int] = None
    max_attempts: Optional[int] = None
    retry_min_interval: Optional[int] = None
    retry_max_interval: Optional[int] = None


@dataclass
class Rule:
    """完整规则"""
    url: str = ""
    name: str = ""
    comment: Optional[str] = None
    disabled: bool = False
    search: Optional[SearchRule] = None
    book: Optional[BookRule] = None
    toc: Optional[TocRule] = None
    chapter: Optional[ChapterRule] = None
    crawl: Optional[CrawlConfig] = None
    language: Optional[str] = None
    ignore_ssl: bool = False

    def __str__(self):
        return f"{self.name} ({self.url})"
