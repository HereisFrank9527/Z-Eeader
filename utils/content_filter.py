# -*- coding: utf-8 -*-
"""
通用内容过滤器
用于清理小说章节中的广告、无效内容等
"""
import re
from typing import List, Set


class ContentFilter:
    """通用内容过滤器"""

    # 常见广告关键词模式
    AD_PATTERNS = [
        # 网站推广
        r'.*?www\.[a-z0-9\-]+\.(com|cn|net|org).*',
        r'.*?https?://[^\s]+.*',
        r'.*?【.*?(笔趣阁|书.*?阁|.*?中文网|.*?文学网).*?】.*',
        r'.*?访问.*?(m\.|wap\.|手机).*?阅读.*',

        # 章节相关广告
        r'.*?(本章|章节)(未完|没有结束|还有).*?(点击|请|下一页).*',
        r'.*?(喜欢|推荐).*?(请|记得).*?(收藏|书签|投票|打赏).*',
        r'.*?(天才)?一秒记住.*?(地址|网址|本站).*',
        r'.*?最快更新.*?(无弹窗|无广告).*',

        # 常见版权声明
        r'.*?\(本章完\).*',
        r'.*?\\(www\..*?\\).*',
        r'.*?手机(用户|版|端).*?(请|浏览|访问).*?阅读.*',

        # 空白和无意义内容
        r'^[\s\u3000]*$',  # 全是空白
        r'^(&nbsp;|　)+$',  # 全是空格符号
    ]

    # URL模式
    URL_PATTERN = re.compile(r'https?://[^\s]+|www\.[a-z0-9\-]+\.[a-z]+')

    # 常见广告关键词
    AD_KEYWORDS = {
        '笔趣阁', '书海阁', '新笔趣阁', '顶点', '飘天', '梦书',
        '本站地址', '请收藏', '请记住', '最新网址', '永久地址',
        '手机版阅读', '手机用户请', 'wap.', 'm.',
        '无弹窗', '无广告', '全文免费',
        '一秒记住', '天才一秒',
        '更新最快', '最快更新',
        '请点击下一页', '本章未完', '章节后面还有',
    }

    @classmethod
    def filter_paragraph(cls, paragraph: str) -> bool:
        """
        判断段落是否应该被过滤

        Args:
            paragraph: 段落文本

        Returns:
            True表示应该过滤（删除），False表示保留
        """
        if not paragraph or not paragraph.strip():
            return True

        para = paragraph.strip()

        # 过滤过短的段落（可能是广告或无意义内容）
        if len(para) < 5:
            return True

        # 过滤过长的单行（可能是错误提取）
        if len(para) > 1000 and '\n' not in para:
            return True

        # 匹配广告正则模式
        for pattern in cls.AD_PATTERNS:
            if re.match(pattern, para, re.IGNORECASE):
                return True

        # 检查是否包含URL
        if cls.URL_PATTERN.search(para):
            return True

        # 检查广告关键词（需要包含2个或以上才判定为广告）
        keyword_count = sum(1 for keyword in cls.AD_KEYWORDS if keyword in para)
        if keyword_count >= 2:
            return True

        # 检查是否全是特殊符号
        if re.match(r'^[^\w\u4e00-\u9fff]+$', para):
            return True

        return False

    @classmethod
    def clean_paragraph(cls, paragraph: str) -> str:
        """
        清理段落内容

        Args:
            paragraph: 原始段落

        Returns:
            清理后的段落
        """
        para = paragraph.strip()

        # 去除多余的空白字符
        para = re.sub(r'\s+', ' ', para)
        para = re.sub(r'[\u3000\xa0]+', '', para)  # 去除全角空格和不间断空格

        # 去除HTML实体
        para = re.sub(r'&nbsp;', '', para)
        para = re.sub(r'&[a-z]+;', '', para)

        # 去除常见的版权标记
        para = re.sub(r'\(本章完\)', '', para)
        para = re.sub(r'\\(.+?\\)', '', para)

        return para.strip()

    @classmethod
    def filter_content(cls, paragraphs: List[str]) -> List[str]:
        """
        过滤内容段落列表

        Args:
            paragraphs: 段落列表

        Returns:
            过滤并清理后的段落列表
        """
        filtered = []

        for para in paragraphs:
            # 清理段落
            cleaned = cls.clean_paragraph(para)

            # 判断是否应该保留
            if cleaned and not cls.filter_paragraph(cleaned):
                filtered.append(cleaned)

        return filtered

    @classmethod
    def smart_split_paragraphs(cls, content: str) -> List[str]:
        """
        智能分割段落

        Args:
            content: 原始内容

        Returns:
            段落列表
        """
        # 先按换行符分割
        parts = content.split('\n')

        paragraphs = []
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 如果段落太长且没有标点，可能需要进一步分割
            # 但为了保险，暂时保留原样
            paragraphs.append(part)

        return paragraphs

    @classmethod
    def detect_encoding(cls, response) -> str:
        """
        智能检测响应的编码

        Args:
            response: requests.Response对象

        Returns:
            编码名称
        """
        # 优先使用Content-Type中声明的编码
        if response.encoding and response.encoding.lower() != 'iso-8859-1':
            return response.encoding

        # 尝试使用chardet检测
        try:
            import chardet
            detected = chardet.detect(response.content)
            if detected and detected['encoding'] and detected['confidence'] > 0.7:
                return detected['encoding']
        except ImportError:
            pass

        # 使用apparent_encoding作为后备
        return response.apparent_encoding or 'utf-8'
