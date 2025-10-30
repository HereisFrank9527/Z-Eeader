# -*- coding: utf-8 -*-
"""
章节模型类
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Chapter:
    """章节信息模型"""
    title: str = ""
    url: str = ""
    content: Optional[str] = None
    index: int = 0

    def __str__(self):
        return f"第{self.index}章 {self.title}"

    def to_dict(self):
        """转换为字典"""
        return {
            'title': self.title,
            'url': self.url,
            'content': self.content,
            'index': self.index
        }
