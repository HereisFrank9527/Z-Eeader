# -*- coding: utf-8 -*-
"""
书籍模型类
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Book:
    """书籍信息模型"""
    url: str = ""
    book_name: str = ""
    author: str = ""
    intro: Optional[str] = None
    cover_url: Optional[str] = None
    category: Optional[str] = None
    latest_chapter: Optional[str] = None
    last_update_time: Optional[str] = None
    status: Optional[str] = None
    word_count: Optional[str] = None

    def __str__(self):
        return f"《{self.book_name}》 - {self.author}"

    def to_dict(self):
        """转换为字典"""
        return {
            'url': self.url,
            'book_name': self.book_name,
            'author': self.author,
            'intro': self.intro,
            'cover_url': self.cover_url,
            'category': self.category,
            'latest_chapter': self.latest_chapter,
            'last_update_time': self.last_update_time,
            'status': self.status,
            'word_count': self.word_count
        }
