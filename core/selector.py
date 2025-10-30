# -*- coding: utf-8 -*-
"""
选择器工具，支持 CSS Selector 和 XPath
"""
import re
from typing import List, Optional
from lxml import etree
from bs4 import BeautifulSoup


class Selector:
    """HTML 选择器，支持 CSS Selector 和 XPath"""

    def __init__(self, html: str, base_url: str = ""):
        """
        初始化选择器

        Args:
            html: HTML 内容
            base_url: 基础 URL，用于处理相对路径
        """
        self.html = html
        self.base_url = base_url
        self.soup = BeautifulSoup(html, 'lxml')
        self.tree = etree.HTML(html)

    def select(self, selector: str, attr: Optional[str] = None) -> List[str]:
        """
        使用 CSS Selector 或 XPath 选择元素

        Args:
            selector: 选择器表达式
            attr: 要提取的属性名，None 表示提取文本

        Returns:
            结果列表
        """
        if not selector:
            return []

        # 判断是 XPath 还是 CSS Selector
        if selector.startswith('//') or selector.startswith('/'):
            return self._select_xpath(selector, attr)
        else:
            return self._select_css(selector, attr)

    def select_one(self, selector: str, attr: Optional[str] = None) -> Optional[str]:
        """
        选择单个元素

        Args:
            selector: 选择器表达式
            attr: 要提取的属性名，None 表示提取文本

        Returns:
            结果字符串
        """
        results = self.select(selector, attr)
        return results[0] if results else None

    def _select_css(self, selector: str, attr: Optional[str] = None) -> List[str]:
        """
        使用 CSS Selector 选择

        Args:
            selector: CSS 选择器
            attr: 要提取的属性名

        Returns:
            结果列表
        """
        # 处理 @js: 后缀（JavaScript 表达式）
        js_expr = None
        if '@js:' in selector:
            selector, js_expr = selector.split('@js:', 1)
            selector = selector.strip()

        elements = self.soup.select(selector)
        results = []

        for elem in elements:
            value = None

            if attr:
                # 提取属性
                value = elem.get(attr, '')
            else:
                # 提取文本
                value = elem.get_text(strip=True)

            # 执行 JavaScript 表达式（简化版）
            if js_expr and value:
                value = self._eval_js(js_expr, value)

            if value:
                results.append(value)

        return results

    def _select_xpath(self, xpath: str, attr: Optional[str] = None) -> List[str]:
        """
        使用 XPath 选择

        Args:
            xpath: XPath 表达式
            attr: 要提取的属性名

        Returns:
            结果列表
        """
        try:
            elements = self.tree.xpath(xpath)
            results = []

            for elem in elements:
                if isinstance(elem, str):
                    results.append(elem)
                elif hasattr(elem, 'text'):
                    if attr:
                        value = elem.get(attr, '')
                    else:
                        value = ''.join(elem.itertext()).strip()
                    if value:
                        results.append(value)

            return results

        except Exception as e:
            print(f"XPath 选择失败: {xpath} - {e}")
            return []

    def _eval_js(self, js_expr: str, value: str) -> str:
        """
        执行简化的 JavaScript 表达式

        Args:
            js_expr: JavaScript 表达式
            value: 输入值

        Returns:
            处理后的值
        """
        try:
            result = value

            # 移除外层赋值 (r = xxx)
            expr = js_expr.strip()
            if expr.startswith('r=') or expr.startswith('r ='):
                expr = expr.split('=', 1)[1].strip()

            # 处理链式 replace 调用
            # 例如: r.replace('作者:', '').replace('abc', 'def')
            if '.replace(' in expr:
                import re
                # 提取所有 replace 调用
                replace_pattern = r"\.replace\(['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]"
                matches = re.findall(replace_pattern, expr)

                for old_str, new_str in matches:
                    result = result.replace(old_str, new_str)

                return result

            # 处理字符串拼接
            # 例如: 'http://example.com' + r
            # 或: r + '/suffix'
            expr = expr.replace('r', f'"{value}"')

            # 简单求值（仅支持字符串拼接）
            result = eval(expr)
            return str(result)

        except Exception as e:
            print(f"JavaScript 表达式执行失败: {js_expr} - {e}")
            return value

    def extract_content(self, selector: str, paragraph_tag_closed: bool = False,
                        paragraph_tag: Optional[str] = None, filter_tags: Optional[str] = None) -> str:
        """
        提取章节内容（增强版，支持智能分段和标签过滤）

        Args:
            selector: 选择器
            paragraph_tag_closed: 段落是否有闭合标签
            paragraph_tag: 段落分隔符
            filter_tags: 需要过滤的HTML标签（空格分隔，如"div p script"）

        Returns:
            内容字符串
        """
        elem = self.soup.select_one(selector)
        if not elem:
            return ""

        # 先清理需要过滤的标签（基于规则配置）
        if filter_tags:
            # 将"div p script"分割为列表
            tags_to_remove = filter_tags.split()
            for tag_name in tags_to_remove:
                for tag in elem.find_all(tag_name):
                    tag.decompose()

        # 清理通用的无用标签
        for tag in elem.find_all(['script', 'style', 'iframe', 'noscript']):
            tag.decompose()

        paragraphs = []

        if paragraph_tag_closed:
            # 有闭合标签，每个标签为一个段落
            # 尝试查找p、div等常见段落标签
            for tag_name in ['p', 'div', 'section']:
                found = elem.find_all(tag_name)
                if found:
                    paragraphs = [p.get_text(strip=True) for p in found]
                    break

            # 如果没找到，使用所有子元素
            if not paragraphs:
                paragraphs = [p.get_text(strip=True) for p in elem.find_all()]

        else:
            # 按分隔符分割
            html_content = str(elem)

            if paragraph_tag:
                # 转换规则中的段落标签为正确的正则表达式
                # 规则文件中的"<br>+"应该匹配一个或多个br标签（包括自闭合形式<br/>）
                paragraph_pattern = paragraph_tag

                # 处理<br>标签：将<br>转换为能匹配自闭合标签的模式
                if '<br>' in paragraph_tag.lower():
                    # <br> -> <br\s*/?> （匹配<br>、<br/>、<br />）
                    # <br>+ -> (<br\s*/?>)+ （匹配一个或多个br标签）
                    paragraph_pattern = paragraph_tag.replace('<br>', r'<br\s*/?>')
                    paragraph_pattern = paragraph_pattern.replace('<BR>', r'<br\s*/?>')

                # 使用正则分割
                parts = re.split(paragraph_pattern, html_content, flags=re.IGNORECASE)
                paragraphs = [BeautifulSoup(p, 'lxml').get_text(strip=True) for p in parts]
            else:
                # 没有指定分隔符，使用智能分段
                # 先获取纯文本
                text = elem.get_text()

                # 尝试按<br>标签分割
                br_parts = elem.find_all('br')
                if br_parts and len(br_parts) > 3:
                    # 有足够的<br>标签，按br分割
                    html_str = str(elem)
                    parts = re.split(r'<br\s*/?>+', html_str, flags=re.IGNORECASE)
                    paragraphs = [BeautifulSoup(p, 'lxml').get_text(strip=True) for p in parts]
                else:
                    # 按换行符分割
                    paragraphs = [line.strip() for line in text.split('\n')]

        # 过滤空段落
        content = '\n'.join(p for p in paragraphs if p and p.strip())

        return content
