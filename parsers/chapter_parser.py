# -*- coding: utf-8 -*-
"""
章节内容解析器（重构版 - 忠实于规则配置）
"""
import re
from typing import Optional
from models.chapter import Chapter
from models.rule import Rule
from core.http_client import HttpClient
from core.selector import Selector
from utils.content_filter import ContentFilter


class ChapterParser:
    """章节内容解析器"""

    def __init__(self, rule: Rule, http_client: HttpClient = None):
        """
        初始化章节解析器

        Args:
            rule: 书源规则
            http_client: HTTP 客户端
        """
        self.rule = rule
        self.http_client = http_client or HttpClient()

    def parse(self, chapter: Chapter) -> Chapter:
        """
        解析章节内容（重构版，严格遵循规则配置）

        Args:
            chapter: 章节对象（包含 URL）

        Returns:
            填充了内容的章节对象
        """
        if not self.rule.chapter:
            print(f"书源 {self.rule.name} 没有配置章节规则")
            return chapter

        chapter_rule = self.rule.chapter

        try:
            # 获取所有分页内容
            all_content = []
            current_url = chapter.url
            page_count = 0
            max_pages = 50  # 防止无限循环

            while current_url and page_count < max_pages:
                page_count += 1

                # 发送请求
                response = self.http_client.get(current_url)

                # 智能检测编码
                encoding = ContentFilter.detect_encoding(response)
                response.encoding = encoding

                html = response.text

                # 创建选择器
                selector = Selector(html, current_url)

                # 提取章节标题（仅第一页）
                if page_count == 1:
                    if not chapter.title and chapter_rule.title:
                        title = selector.select_one(chapter_rule.title)
                        if title:
                            chapter.title = title.strip()

                # 提取本页内容（使用规则中的filterTag）
                content = selector.extract_content(
                    chapter_rule.content,
                    chapter_rule.paragraph_tag_closed,
                    chapter_rule.paragraph_tag,
                    chapter_rule.filter_tag  # 使用规则配置的filterTag
                )

                if content:
                    all_content.append(content)

                # 检查是否有下一页
                if chapter_rule.pagination and chapter_rule.next_page:
                    next_url = selector.select_one(chapter_rule.next_page, 'href')
                    if next_url and next_url != current_url:
                        # 处理相对路径
                        if not next_url.startswith('http'):
                            from urllib.parse import urljoin
                            next_url = urljoin(current_url, next_url)
                        current_url = next_url
                    else:
                        break
                else:
                    break

            # 合并所有分页内容
            full_content = '\n'.join(all_content)

            # 分割段落（依赖selector.extract_content已完成的分段，不使用ContentFilter）
            # selector.extract_content已经使用了规则的paragraphTag和paragraphTagClosed参数
            paragraphs = [p.strip() for p in full_content.split('\n') if p.strip()]

            # 应用规则中的过滤器（如果有filterTxt）
            if chapter_rule.filter_txt:
                filtered_paragraphs = []
                for p in paragraphs:
                    filtered = self._filter_text(p, chapter_rule.filter_txt)
                    if filtered and filtered.strip():
                        filtered_paragraphs.append(filtered)
                paragraphs = filtered_paragraphs

            # 基础清理（仅去除明显无效的段落，不使用激进的广告过滤）
            paragraphs = self._basic_clean(paragraphs)

            # 合并段落
            chapter.content = '\n'.join(paragraphs)

            # 如果内容为空或过短，给出警告
            if not chapter.content or len(chapter.content) < 50:
                print(f"警告：章节内容过短或为空 ({chapter.title}), 长度: {len(chapter.content)}")

        except Exception as e:
            print(f"解析章节内容失败 ({chapter.title}): {e}")
            chapter.content = ""

        return chapter

    def _filter_text(self, text: str, filter_pattern: str) -> str:
        """
        清理文本中的垃圾内容（保留段落主体）

        Args:
            text: 原始文本
            filter_pattern: 过滤正则表达式（多个用 | 分隔）

        Returns:
            清理后的文本（如果清理后变空且原文主要是广告，返回空字符串）
        """
        try:
            # 使用正则表达式替换
            filtered = re.sub(filter_pattern, '', text, flags=re.MULTILINE | re.DOTALL)
            filtered = filtered.strip()

            # 关键修复：如果清理后变空，判断原文是否主要是广告
            if not filtered:
                original_len = len(text.strip())
                if original_len == 0:
                    return ''  # 原文就是空的

                # 原文全被删除，说明100%是广告
                return ''  # 丢弃广告段落

            # 如果清理后还有内容，只要有意义的内容（>=5字符）就保留
            # 不要因为广告占比高就丢弃有意义的正常内容
            filtered_len = len(filtered)
            if filtered_len >= 5:
                return filtered  # 保留有意义的内容

            # 对于非常短的内容（<5字符），检查占比
            original_len = len(text.strip())
            if original_len > 0:
                retain_ratio = filtered_len / original_len
                # 只有占比极低（<10%）且内容极短（<5字符）时才丢弃
                if retain_ratio < 0.1:
                    return ''

            return filtered
        except Exception as e:
            print(f"过滤文本失败: {e}")
            return text

    def _basic_clean(self, paragraphs: list) -> list:
        """
        基础清理（仅去除明显无效的段落，不进行激进过滤）

        Args:
            paragraphs: 段落列表

        Returns:
            清理后的段落列表
        """
        cleaned = []

        for para in paragraphs:
            if not para or not para.strip():
                continue

            para = para.strip()

            # 仅过滤明显无效的内容
            # 1. 空段落
            if len(para) == 0:
                continue

            # 2. 过短段落（小于3字符，但允许"嗯"、"啊"、"嗯嗯"、"哈哈"等1-2字对话）
            if len(para) < 3 and not re.match(r'^[\u4e00-\u9fff]{1,2}$', para):
                continue

            # 3. 清理HTML实体
            para = re.sub(r'&nbsp;', '', para)
            para = re.sub(r'&[a-z]+;', '', para)

            # 4. 去除多余空白
            para = re.sub(r'\s+', ' ', para)

            if para and para.strip():
                cleaned.append(para.strip())

        return cleaned
