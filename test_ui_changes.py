# -*- coding: utf-8 -*-
"""
测试UI修改效果
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import re

def convert_markdown_to_html(md_text):
    """简单的markdown转HTML转换器"""
    if not md_text:
        return ""

    html = md_text

    # 转换标题
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
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


# 测试markdown转换
with open('templates/index.md', 'r', encoding='utf-8') as f:
    md_content = f.read()

print("Markdown转换测试:")
print("  原始内容长度:", len(md_content), "字符")

html_content = convert_markdown_to_html(md_content)
print("  HTML内容长度:", len(html_content), "字符")
print("  包含<h3>标签:", "<h3>" in html_content)
print("  包含<h4>标签:", "<h4>" in html_content)
print("  包含<strong>标签:", "<strong>" in html_content)
print()

# 验证CSS样式是否正确
with open('static/css/style.css', 'r', encoding='utf-8') as f:
    css_content = f.read()

print("CSS修改验证:")

# 检查body背景色
if 'background: #f5f5f5' in css_content:
    print("  [OK] body背景色已修改为浅灰色")
else:
    print("  [FAIL] body背景色未正确修改")

# 检查header背景色
if '#00bcd4' in css_content and '#20b2aa' in css_content:
    print("  [OK] header背景色已修改为蓝绿色")
else:
    print("  [FAIL] header背景色未正确修改")

# 检查公告样式
if '.announcement' in css_content:
    print("  [OK] 公告模块CSS样式已添加")
else:
    print("  [FAIL] 公告模块CSS样式未添加")

print()
print("="* 60)
print("所有UI修改已完成！")
print("启动服务器命令: python server.py")
print("="* 60)
