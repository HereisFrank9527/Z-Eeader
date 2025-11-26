# -*- coding: utf-8 -*-
"""
Z Reader - Web 服务器
基于 Flask 的 Web 界面
"""
import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
from pathlib import Path
import threading
import webbrowser

from core.rule_loader import RuleLoader
from core.http_client import HttpClient
from core.downloader import Downloader
from parsers.search_parser import SearchParser
from models.chapter import Chapter
from parsers.book_parser import BookParser
from parsers.toc_parser import TocParser
from parsers.chapter_parser import ChapterParser

# 创建 Flask 应用
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支持中文

# 全局变量
rule_loader = RuleLoader()
download_tasks = {}  # 下载任务字典
task_lock = threading.Lock()

# Reader cache for book info and chapter content
reader_cache = {}


# ==================== 首页 ====================
@app.route('/')
def index():
    """首页"""
    # 读取公告内容
    announcement_html = ""
    announcement_file = Path(__file__).parent / 'templates' / 'index.md'

    if announcement_file.exists():
        try:
            with open(announcement_file, 'r', encoding='utf-8') as f:
                announcement_md = f.read()

            # 简单的markdown转HTML（处理基本格式）
            announcement_html = convert_markdown_to_html(announcement_md)
        except Exception as e:
            print(f"读取公告文件失败: {e}")
            announcement_html = ""

    return render_template('index.html', announcement=announcement_html)


def convert_markdown_to_html(md_text):
    """简单的markdown转HTML转换器"""
    if not md_text:
        return ""

    html = md_text

    # 转换标题
    import re
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # 转换粗体和斜体
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # 转换链接
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)

    # 转换代码
    html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

    # 转换换行
    html = html.replace('\n\n', '</p><p>')
    html = html.replace('\n', '<br>')

    # 包装段落
    if html and not html.startswith('<h'):
        html = '<p>' + html + '</p>'

    return html



# ==================== 书源管理 ====================
@app.route('/api/sources')
def get_sources():
    """获取所有书源列表"""
    try:
        rules = rule_loader.load_rules("main-rules.json")
        sources = []

        for i, rule in enumerate(rules, 1):
            sources.append({
                'id': i,
                'name': rule.name,
                'url': rule.url,
                'comment': rule.comment or '',
                'search_enabled': bool(rule.search and not rule.search.disabled),
                'has_crawl_config': bool(rule.crawl)
            })

        return jsonify({
            'success': True,
            'data': sources,
            'total': len(sources)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取书源失败: {str(e)}'
        }), 500


@app.route('/api/sources/check', methods=['POST'])
def check_sources():
    """检查所有书源可用性"""
    try:
        rules = rule_loader.load_rules("main-rules.json")
        keyword = "斗破苍穹"  # 使用固定关键词测试

        results = []

        for i, rule in enumerate(rules, 1):
            result = {
                'id': i,
                'name': rule.name,
                'url': rule.url,
                'status': 'unknown',
                'message': '',
                'book_count': 0
            }

            # 检查是否有搜索配置
            if not rule.search:
                result['status'] = 'disabled'
                result['message'] = '无搜索配置'
                results.append(result)
                continue

            try:
                # 创建HTTP客户端
                http_client = HttpClient(
                    max_retries=1,
                    min_interval=0.5,
                    max_interval=1.0,
                    verify_ssl=not rule.ignore_ssl,
                    timeout=10
                )

                # 执行搜索测试
                search_parser = SearchParser(rule, http_client)
                books = search_parser.search(keyword, max_results=5)

                if books:
                    result['status'] = 'success'
                    result['book_count'] = len(books)
                    result['message'] = f'正常 - 找到 {len(books)} 本书'
                else:
                    result['status'] = 'warning'
                    result['message'] = '无搜索结果'

                http_client.close()

            except Exception as e:
                result['status'] = 'error'
                error_msg = str(e)
                # 截取错误消息，避免过长
                result['message'] = error_msg[:100] if len(error_msg) > 100 else error_msg

            results.append(result)

        # 统计结果
        success_count = sum(1 for r in results if r['status'] == 'success')
        error_count = sum(1 for r in results if r['status'] == 'error')
        warning_count = sum(1 for r in results if r['status'] == 'warning')
        disabled_count = sum(1 for r in results if r['status'] == 'disabled')

        return jsonify({
            'success': True,
            'data': results,
            'summary': {
                'total': len(results),
                'success': success_count,
                'error': error_count,
                'warning': warning_count,
                'disabled': disabled_count
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'检查书源失败: {str(e)}'
        }), 500


# ==================== 搜索功能 ====================
@app.route('/api/search', methods=['POST'])
def search_books():
    """搜索书籍"""
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        source_id = data.get('source_id')  # 可选，指定书源 ID

        if not keyword:
            return jsonify({
                'success': False,
                'message': '请输入搜索关键词'
            }), 400

        # 加载规则
        rules = rule_loader.load_rules("main-rules.json")

        # 选择书源
        if source_id:
            if source_id < 1 or source_id > len(rules):
                return jsonify({
                    'success': False,
                    'message': f'无效的书源 ID: {source_id}'
                }), 400
            rules = [rules[source_id - 1]]

        # 执行搜索
        all_books = []
        for rule in rules:
            if not rule.search or rule.search.disabled:
                continue

            try:
                http_client = HttpClient(verify_ssl=not rule.ignore_ssl)
                parser = SearchParser(rule, http_client)
                books = parser.search(keyword, max_results=20)

                for book in books:
                    all_books.append({
                        'source_name': rule.name,
                        'source_id': rules.index(rule) + 1 if source_id is None else source_id,
                        'book_name': book.book_name,
                        'author': book.author,
                        'url': book.url,
                        'category': book.category,
                        'latest_chapter': book.latest_chapter,
                        'word_count': book.word_count,
                        'status': book.status
                    })

                http_client.close()

            except Exception as e:
                print(f"搜索失败 ({rule.name}): {e}")
                continue

        return jsonify({
            'success': True,
            'data': all_books,
            'total': len(all_books),
            'keyword': keyword
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'搜索失败: {str(e)}'
        }), 500


@app.route('/api/search/stream', methods=['POST'])
def search_books_stream():
    """搜索书籍（SSE流式返回进度）"""
    data = request.get_json()
    keyword = data.get('keyword', '').strip()
    source_id = data.get('source_id')  # 可选，指定书源 ID

    if not keyword:
        return jsonify({
            'success': False,
            'message': '请输入搜索关键词'
        }), 400

    def generate():
        """生成SSE事件流"""
        try:
            # 加载规则
            rules = rule_loader.load_rules("main-rules.json")
            original_rules = rules

            # 选择书源
            if source_id:
                if source_id < 1 or source_id > len(rules):
                    yield f"data: {json.dumps({'type': 'error', 'message': f'无效的书源 ID: {source_id}'}, ensure_ascii=False)}\n\n"
                    return
                rules = [rules[source_id - 1]]

            # 发送开始事件
            total_sources = sum(1 for r in rules if r.search and not r.search.disabled)
            yield f"data: {json.dumps({'type': 'start', 'total': total_sources, 'keyword': keyword}, ensure_ascii=False)}\n\n"

            all_books = []
            completed = 0

            for rule in rules:
                if not rule.search or rule.search.disabled:
                    continue

                # 发送当前搜索的书源
                yield f"data: {json.dumps({'type': 'searching', 'source': rule.name}, ensure_ascii=False)}\n\n"

                try:
                    http_client = HttpClient(
                        verify_ssl=not rule.ignore_ssl,
                        timeout=10
                    )
                    parser = SearchParser(rule, http_client)
                    books = parser.search(keyword, max_results=20)

                    # 构建结果
                    source_books = []
                    for book in books:
                        book_data = {
                            'source_name': rule.name,
                            'source_id': original_rules.index(rule) + 1,
                            'book_name': book.book_name,
                            'author': book.author,
                            'url': book.url,
                            'category': book.category,
                            'latest_chapter': book.latest_chapter,
                            'word_count': book.word_count,
                            'status': book.status
                        }
                        all_books.append(book_data)
                        source_books.append(book_data)

                    completed += 1

                    # 发送搜索结果
                    yield f"data: {json.dumps({'type': 'result', 'source': rule.name, 'books': source_books, 'count': len(books), 'completed': completed, 'total': total_sources}, ensure_ascii=False)}\n\n"

                    http_client.close()

                except Exception as e:
                    completed += 1
                    # 发送错误
                    yield f"data: {json.dumps({'type': 'error_source', 'source': rule.name, 'error': str(e), 'completed': completed, 'total': total_sources}, ensure_ascii=False)}\n\n"

                # 添加小延迟避免过快
                time.sleep(0.1)

            # 发送完成事件
            yield f"data: {json.dumps({'type': 'complete', 'total_books': len(all_books), 'books': all_books}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


# ==================== 下载功能 ====================
@app.route('/api/download', methods=['POST'])
def start_download():
    """开始下载书籍"""
    try:
        data = request.get_json()
        book_url = data.get('book_url', '').strip()
        source_id = data.get('source_id')
        start_chapter = data.get('start_chapter', 1)
        end_chapter = data.get('end_chapter', -1)
        format_type = data.get('format', 'txt')  # 默认为 txt

        if not book_url:
            return jsonify({
                'success': False,
                'message': '请提供书籍 URL'
            }), 400

        if not source_id:
            return jsonify({
                'success': False,
                'message': '请指定书源 ID'
            }), 400

        # 加载规则
        rules = rule_loader.load_rules("main-rules.json")

        if source_id < 1 or source_id > len(rules):
            return jsonify({
                'success': False,
                'message': f'无效的书源 ID: {source_id}'
            }), 400

        rule = rules[source_id - 1]

        # 生成任务 ID
        task_id = f"{int(datetime.now().timestamp() * 1000)}"

        # 创建下载任务
        with task_lock:
            download_tasks[task_id] = {
                'id': task_id,
                'book_url': book_url,
                'source_name': rule.name,
                'status': 'pending',
                'progress': 0,
                'total_chapters': 0,
                'downloaded_chapters': 0,
                'book_name': '',
                'author': '',
                'error': None,
                'created_at': datetime.now().isoformat()
            }

        # 在后台线程中执行下载
        def download_task():
            try:
                with task_lock:
                    download_tasks[task_id]['status'] = 'downloading'

                # 进度回调函数
                def update_progress(stage, completed, total, book_name, author):
                    with task_lock:
                        download_tasks[task_id]['book_name'] = book_name
                        download_tasks[task_id]['author'] = author
                        download_tasks[task_id]['total_chapters'] = total
                        download_tasks[task_id]['downloaded_chapters'] = completed

                        if total > 0:
                            progress = int((completed / total) * 100)
                            download_tasks[task_id]['progress'] = progress

                # 创建下载器
                downloader = Downloader(
                    rule,
                    output_dir="downloads",
                    progress_callback=update_progress
                )

                # 下载
                success = downloader.download(
                    book_url=book_url,
                    start_chapter=start_chapter,
                    end_chapter=end_chapter,
                    format=format_type
                )

                with task_lock:
                    if success:
                        download_tasks[task_id]['status'] = 'completed'
                        download_tasks[task_id]['progress'] = 100
                    else:
                        download_tasks[task_id]['status'] = 'failed'
                        download_tasks[task_id]['error'] = '下载失败'

            except Exception as e:
                with task_lock:
                    download_tasks[task_id]['status'] = 'failed'
                    download_tasks[task_id]['error'] = str(e)

        # 启动下载线程
        thread = threading.Thread(target=download_task, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id
            },
            'message': '下载任务已创建'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'创建下载任务失败: {str(e)}'
        }), 500


@app.route('/api/tasks')
def get_tasks():
    """获取所有下载任务"""
    with task_lock:
        tasks = list(download_tasks.values())

    return jsonify({
        'success': True,
        'data': tasks,
        'total': len(tasks)
    })


@app.route('/api/tasks/<task_id>')
def get_task(task_id):
    """获取指定下载任务的状态"""
    with task_lock:
        task = download_tasks.get(task_id)

    if not task:
        return jsonify({
            'success': False,
            'message': '任务不存在'
        }), 404

    return jsonify({
        'success': True,
        'data': task
    })


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除下载任务"""
    with task_lock:
        if task_id in download_tasks:
            del download_tasks[task_id]
            return jsonify({
                'success': True,
                'message': '任务已删除'
            })
        else:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404


# ==================== 文件下载 ====================
@app.route('/api/files')
def list_files():
    """列出下载目录中的文件"""
    try:
        download_dir = Path("downloads")
        if not download_dir.exists():
            return jsonify({
                'success': True,
                'data': [],
                'total': 0
            })

        files = []
        # 支持多种文件格式：txt和epub
        for pattern in ["*.txt", "*.epub"]:
            for file_path in download_dir.glob(pattern):
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        # 按修改时间降序排序
        files.sort(key=lambda x: x['modified_at'], reverse=True)

        return jsonify({
            'success': True,
            'data': files,
            'total': len(files)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取文件列表失败: {str(e)}'
        }), 500


@app.route('/api/files/<filename>')
def download_file(filename):
    """下载文件"""
    try:
        file_path = Path("downloads") / filename

        if not file_path.exists():
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'下载文件失败: {str(e)}'
        }), 500


# ==================== 阅读器功能 ====================
@app.route('/api/reader/book', methods=['POST'])
def get_reader_book_info():
    """获取阅读器书籍信息和章节列表"""
    try:
        data = request.get_json()
        book_url = data.get('book_url', '').strip()
        source_id = data.get('source_id')

        if not book_url or not source_id:
            return jsonify({
                'success': False,
                'message': '请提供书籍 URL 和书源 ID'
            }), 400

        # 检查缓存
        cache_key = f"book_{source_id}_{book_url}"
        if cache_key in reader_cache:
            return jsonify({
                'success': True,
                'data': reader_cache[cache_key],
                'cached': True
            })

        # 加载规则
        rules = rule_loader.load_rules("main-rules.json")
        if source_id < 1 or source_id > len(rules):
            return jsonify({
                'success': False,
                'message': f'无效的书源 ID: {source_id}'
            }), 400

        rule = rules[source_id - 1]

        try:
            # 创建HTTP客户端和解析器
            http_client = HttpClient(verify_ssl=not rule.ignore_ssl, timeout=10)
            
            # 获取书籍信息
            book_parser = BookParser(rule, http_client)
            book = book_parser.parse(book_url)
            
            if not book:
                http_client.close()
                return jsonify({
                    'success': False,
                    'message': '获取书籍信息失败'
                }), 404

            # 获取章节列表
            toc_parser = TocParser(rule, http_client)
            chapters = toc_parser.parse(book_url, 1, -1)  # 获取所有章节
            
            http_client.close()

            # 构建返回数据
            book_data = {
                'book_name': book.book_name,
                'author': book.author,
                'intro': book.intro,
                'category': book.category,
                'cover_url': book.cover_url,
                'latest_chapter': book.latest_chapter,
                'status': book.status,
                'chapters': [
                    {
                        'index': chapter.index,
                        'title': chapter.title,
                        'url': chapter.url
                    } for chapter in chapters
                ]
            }

            # 缓存结果
            reader_cache[cache_key] = book_data

            return jsonify({
                'success': True,
                'data': book_data,
                'cached': False
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取书籍信息失败: {str(e)}'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'请求处理失败: {str(e)}'
        }), 500


@app.route('/api/reader/chapter', methods=['POST'])
def get_reader_chapter():
    """获取阅读器章节内容"""
    try:
        data = request.get_json()
        chapter_url = data.get('chapter_url', '').strip()
        source_id = data.get('source_id')

        if not chapter_url or not source_id:
            return jsonify({
                'success': False,
                'message': '请提供章节 URL 和书源 ID'
            }), 400

        # 检查缓存
        cache_key = f"chapter_{source_id}_{chapter_url}"
        if cache_key in reader_cache:
            return jsonify({
                'success': True,
                'data': reader_cache[cache_key],
                'cached': True
            })

        # 加载规则
        rules = rule_loader.load_rules("main-rules.json")
        if source_id < 1 or source_id > len(rules):
            return jsonify({
                'success': False,
                'message': f'无效的书源 ID: {source_id}'
            }), 400

        rule = rules[source_id - 1]

        try:
            # 创建HTTP客户端和解析器
            http_client = HttpClient(verify_ssl=not rule.ignore_ssl, timeout=10)
            chapter_parser = ChapterParser(rule, http_client)
            
            # 创建章节对象并传递URL
            chapter_obj = Chapter(url=chapter_url)
            
            # 获取章节内容
            chapter = chapter_parser.parse(chapter_obj)
            http_client.close()

            if not chapter:
                return jsonify({
                    'success': False,
                    'message': '获取章节内容失败'
                }), 404

            # 构建返回数据
            chapter_data = {
                'title': chapter.title,
                'content': chapter.content,
                'url': chapter.url,
                'index': chapter.index
            }

            # 缓存结果
            reader_cache[cache_key] = chapter_data

            return jsonify({
                'success': True,
                'data': chapter_data,
                'cached': False
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取章节内容失败: {str(e)}'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'请求处理失败: {str(e)}'
        }), 500


@app.route('/reader/<int:source_id>/<path:book_url>')
def reader_page(source_id, book_url):
    """阅读器页面"""
    # 加载规则验证书源ID
    try:
        rules = rule_loader.load_rules("main-rules.json")
        if source_id < 1 or source_id > len(rules):
            return "无效的书源 ID", 404
        
        rule = rules[source_id - 1]
        
        return render_template('reader.html', 
                          source_id=source_id, 
                          book_url=book_url,
                          source_name=rule.name)
    except Exception as e:
        return f"加载阅读器失败: {str(e)}", 500


# ==================== 启动服务器 ====================
if __name__ == '__main__':
    # 创建下载目录
    Path("downloads").mkdir(exist_ok=True)

    # 启动服务器
    print("\n" + "=" * 60)
    print("Z Reader - Web 服务器")
    print("=" * 60)
    print("\n访问地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务器\n")
    webbrowser.open("http://localhost:5000")
    app.run(
        host='::',
        port=5000,
        debug=True,
        threaded=True
    )
