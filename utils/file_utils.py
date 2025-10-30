# -*- coding: utf-8 -*-
"""
文件工具类
"""
import os
import re
from pathlib import Path
from typing import List
from models.chapter import Chapter


class FileUtils:
    """文件操作工具类"""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清理文件名，移除非法字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        # 移除 Windows 文件名非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        cleaned = re.sub(illegal_chars, '_', filename)

        # 移除首尾空格和点
        cleaned = cleaned.strip('. ')

        # 限制长度
        if len(cleaned) > 200:
            cleaned = cleaned[:200]

        return cleaned

    @staticmethod
    def ensure_dir(directory: str) -> Path:
        """
        确保目录存在

        Args:
            directory: 目录路径

        Returns:
            目录 Path 对象
        """
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def save_chapter(chapter: Chapter, file_path: str):
        """
        保存章节到文件

        Args:
            chapter: 章节对象
            file_path: 文件路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"{chapter.title}\n\n")
            if chapter.content:
                f.write(chapter.content)

    @staticmethod
    def save_as_txt(chapters: List[Chapter], output_path: str, book_name: str, author: str):
        """
        保存为 TXT 文件

        Args:
            chapters: 章节列表
            output_path: 输出路径
            book_name: 书名
            author: 作者
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入书籍信息
            f.write(f"{book_name}\n")
            f.write(f"作者:{author}\n")
            f.write("=" * 50 + "\n\n")

            # 写入章节
            for chapter in chapters:
                f.write(f"\n\n{chapter.title}\n")
                f.write("-" * 50 + "\n\n")
                if chapter.content:
                    f.write(chapter.content)
                    f.write("\n")

        print(f"已保存为 TXT: {output_path}")

    @staticmethod
    def save_as_epub(chapters: List[Chapter], output_path: str, book_name: str, author: str):
        """
        保存为 EPUB 文件

        Args:
            chapters: 章节列表
            output_path: 输出路径
            book_name: 书名
            author: 作者
        """
        try:
            from ebooklib import epub
        except ImportError:
            print("错误: 需要安装 ebooklib 库才能生成 EPUB 文件")
            print("请运行: pip install ebooklib")
            # 降级为 TXT 格式
            txt_path = output_path.replace('.epub', '.txt')
            print(f"将改为保存为 TXT 格式: {txt_path}")
            FileUtils.save_as_txt(chapters, txt_path, book_name, author)
            return

        # 创建 EPUB 书籍
        book = epub.EpubBook()

        # 设置元数据
        book.set_identifier(f"{book_name}-{author}")
        book.set_title(book_name)
        book.set_language('zh-CN')
        book.add_author(author)

        # 添加章节
        epub_chapters = []
        spine = ['nav']

        for chapter in chapters:
            if not chapter.content:
                continue

            # 创建 EPUB 章节
            epub_chapter = epub.EpubHtml(
                title=chapter.title,
                file_name=f'chapter_{chapter.index:04d}.xhtml',
                lang='zh-CN'
            )

            # 设置章节内容 (HTML 格式)
            # 将内容转换为段落
            paragraphs = ''.join(f'<p>{line}</p>' for line in chapter.content.split('\n') if line.strip())

            content_html = f"""
            <html>
            <head>
                <title>{chapter.title}</title>
            </head>
            <body>
                <h1>{chapter.title}</h1>
                {paragraphs}
            </body>
            </html>
            """
            epub_chapter.set_content(content_html.encode('utf-8'))

            # 添加到书籍
            book.add_item(epub_chapter)
            epub_chapters.append(epub_chapter)
            spine.append(epub_chapter)

        # 添加目录
        book.toc = tuple(epub_chapters)

        # 添加导航文件
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # 设置书脊
        book.spine = spine

        # 写入文件
        epub.write_epub(output_path, book, {})
        print(f"已保存为 EPUB: {output_path}")
