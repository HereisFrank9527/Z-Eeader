# -*- coding: utf-8 -*-
"""
下载器
"""
import os
import time
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from models.book import Book
from models.chapter import Chapter
from models.rule import Rule
from core.http_client import HttpClient
from parsers.book_parser import BookParser
from parsers.toc_parser import TocParser
from parsers.chapter_parser import ChapterParser
from utils.file_utils import FileUtils


class Downloader:
    """小说下载器"""

    def __init__(
        self,
        rule: Rule,
        output_dir: str = "downloads",
        max_workers: int = 5,
        progress_callback: Optional[callable] = None
    ):
        """
        初始化下载器

        Args:
            rule: 书源规则
            output_dir: 输出目录
            max_workers: 最大并发数
            progress_callback: 进度回调函数
        """
        self.rule = rule
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.progress_callback = progress_callback

        # 根据规则调整配置
        if rule.crawl:
            if rule.crawl.threads:
                self.max_workers = rule.crawl.threads

        # 创建 HTTP 客户端
        min_interval = rule.crawl.min_interval if rule.crawl and rule.crawl.min_interval else 0
        max_interval = rule.crawl.max_interval if rule.crawl and rule.crawl.max_interval else 0
        max_retries = rule.crawl.max_attempts if rule.crawl and rule.crawl.max_attempts else 3

        self.http_client = HttpClient(
            max_retries=max_retries,
            min_interval=min_interval,
            max_interval=max_interval,
            verify_ssl=not rule.ignore_ssl
        )

        # 创建解析器
        self.book_parser = BookParser(rule, self.http_client)
        self.toc_parser = TocParser(rule, self.http_client)
        self.chapter_parser = ChapterParser(rule, self.http_client)

    def download(
        self,
        book_url: str,
        start_chapter: int = 1,
        end_chapter: int = -1,
        format: str = "txt"
    ) -> bool:
        """
        下载小说

        Args:
            book_url: 书籍详情页 URL
            start_chapter: 起始章节（从 1 开始）
            end_chapter: 结束章节（-1 表示到最后）
            format: 输出格式（txt）

        Returns:
            是否成功
        """
        print(f"\n开始下载...")
        print(f"书源: {self.rule.name}")
        print(f"URL: {book_url}\n")

        start_time = time.time()

        try:
            # 1. 解析书籍详情
            print("正在获取书籍信息...")
            if self.progress_callback:
                self.progress_callback("parsing_book", 0, 0, "", "")

            book = self.book_parser.parse(book_url)
            if not book:
                print("获取书籍信息失败")
                return False

            print(f"书名: {book.book_name}")
            print(f"作者: {book.author}")
            if book.intro:
                print(f"简介: {book.intro[:100]}...")
            print()

            # 2. 解析目录
            print("正在获取章节目录...")
            if self.progress_callback:
                self.progress_callback("parsing_toc", 0, 0, book.book_name, book.author)

            chapters = self.toc_parser.parse(book_url, start_chapter, end_chapter)
            if not chapters:
                print("获取章节目录失败")
                return False

            print(f"共 {len(chapters)} 章\n")

            # 3. 下载章节内容
            print(f"开始下载章节 (并发数: {self.max_workers})...")
            if self.progress_callback:
                self.progress_callback("downloading", 0, len(chapters), book.book_name, book.author)

            chapters = self._download_chapters(chapters, book.book_name, book.author)

            # 统计成功数量
            success_count = sum(1 for c in chapters if c.content)
            print(f"\n成功下载 {success_count}/{len(chapters)} 章")

            # 4. 保存文件
            print("\n正在保存文件...")
            self._save_book(book, chapters, format)

            elapsed_time = time.time() - start_time
            print(f"\n总耗时: {elapsed_time:.2f} 秒")
            print("下载完成！\n")

            return True

        except Exception as e:
            print(f"\n下载失败: {e}")
            return False

        finally:
            self.http_client.close()

    def _download_chapters(self, chapters: List[Chapter], book_name: str = "", author: str = "") -> List[Chapter]:
        """
        并发下载章节内容

        Args:
            chapters: 章节列表
            book_name: 书名
            author: 作者

        Returns:
            填充了内容的章节列表
        """
        completed_count = 0
        total_count = len(chapters)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_chapter = {
                executor.submit(self.chapter_parser.parse, chapter): chapter
                for chapter in chapters
            }

            # 按完成顺序处理结果
            for future in as_completed(future_to_chapter):
                chapter = future_to_chapter[future]
                try:
                    result = future.result()
                    completed_count += 1

                    # 调用进度回调
                    if self.progress_callback:
                        self.progress_callback("downloading", completed_count, total_count, book_name, author)

                    # 显示进度
                    status = "[OK]" if result.content else "[FAIL]"
                    print(f"[{completed_count}/{total_count}] {status} {result.title}")

                except Exception as e:
                    completed_count += 1

                    # 调用进度回调
                    if self.progress_callback:
                        self.progress_callback("downloading", completed_count, total_count, book_name, author)

                    print(f"[{completed_count}/{total_count}] [FAIL] {chapter.title} - 错误: {e}")

        return chapters

    def _save_book(self, book: Book, chapters: List[Chapter], format: str):
        """
        保存书籍

        Args:
            book: 书籍对象
            chapters: 章节列表
            format: 输出格式
        """
        # 创建输出目录
        FileUtils.ensure_dir(self.output_dir)

        # 生成文件名
        filename = FileUtils.sanitize_filename(f"{book.book_name}-{book.author}")

        if format == "txt":
            # 保存为单个 TXT 文件
            output_path = os.path.join(self.output_dir, f"{filename}.txt")
            FileUtils.save_as_txt(chapters, output_path, book.book_name, book.author)

        elif format == "epub":
            # 保存为 EPUB 文件
            output_path = os.path.join(self.output_dir, f"{filename}.epub")
            FileUtils.save_as_epub(chapters, output_path, book.book_name, book.author)

        elif format == "chapters":
            # 保存为多个章节文件
            book_dir = FileUtils.ensure_dir(os.path.join(self.output_dir, filename))
            for chapter in chapters:
                if chapter.content:
                    chapter_filename = FileUtils.sanitize_filename(f"{chapter.index:04d}-{chapter.title}.txt")
                    chapter_path = os.path.join(book_dir, chapter_filename)
                    FileUtils.save_chapter(chapter, chapter_path)
            print(f"已保存章节文件到: {book_dir}")
