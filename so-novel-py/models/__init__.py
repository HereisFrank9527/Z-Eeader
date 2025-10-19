# -*- coding: utf-8 -*-
"""
数据模型模块
"""
from .book import Book
from .chapter import Chapter
from .rule import Rule, SearchRule, BookRule, TocRule, ChapterRule, CrawlConfig

__all__ = [
    'Book',
    'Chapter',
    'Rule',
    'SearchRule',
    'BookRule',
    'TocRule',
    'ChapterRule',
    'CrawlConfig'
]
