# -*- coding: utf-8 -*-
"""
书源可用性测试脚本
"""
import json
import requests
from pathlib import Path
from typing import Dict, List, Tuple
import time


def load_rules(rule_file: str) -> List[Dict]:
    """
    加载规则文件
    
    Args:
        rule_file: 规则文件名
        
    Returns:
        规则列表
    """
    rule_path = Path("rules") / rule_file
    if not rule_path.exists():
        return []
    with open(rule_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_book_source(rule: Dict) -> Tuple[bool, str]:
    """
    测试单个书源的可用性
    
    Args:
        rule: 书源规则
        
    Returns:
        (是否可用, 结果信息)
    """
    name = rule.get("name", "未知书源")
    url = rule.get("url", "")
    
    if not url:
        return False, f"{name}: 缺少基础URL"
    
    try:
        # 测试基础URL是否可访问
        response = requests.get(url, timeout=3, allow_redirects=True)
        if response.status_code == 200:
            return True, f"{name}: 基础URL可访问 ({url})"
        else:
            return False, f"{name}: 基础URL访问失败，状态码: {response.status_code} ({url})"
    except requests.exceptions.RequestException as e:
        return False, f"{name}: 请求失败 - {str(e)} ({url})"


def analyze_js_usage(rule: Dict) -> List[str]:
    """
    分析书源是否使用了JavaScript
    
    Args:
        rule: 书源规则
        
    Returns:
        使用JavaScript的地方列表
    """
    js_usage = []
    
    # 检查搜索规则
    if "search" in rule and rule["search"]:
        search = rule["search"]
        for key, value in search.items():
            if isinstance(value, str) and "@js:" in value:
                js_usage.append(f"搜索规则的{key}字段")
    
    # 检查书籍规则
    if "book" in rule and rule["book"]:
        book = rule["book"]
        for key, value in book.items():
            if isinstance(value, str) and "@js:" in value:
                js_usage.append(f"书籍规则的{key}字段")
    
    # 检查目录规则
    if "toc" in rule and rule["toc"]:
        toc = rule["toc"]
        for key, value in toc.items():
            if isinstance(value, str) and "@js:" in value:
                js_usage.append(f"目录规则的{key}字段")
    
    # 检查章节规则
    if "chapter" in rule and rule["chapter"]:
        chapter = rule["chapter"]
        for key, value in chapter.items():
            if isinstance(value, str) and "@js:" in value:
                js_usage.append(f"章节规则的{key}字段")
    
    return js_usage


def main():
    """
    主函数
    """
    print("=== 书源可用性测试 ===")
    
    # 测试的规则文件列表
    rule_files = ["main-rules.json", "non-searchable-rules.json"]
    
    for rule_file in rule_files:
        print(f"\n--- 测试文件: {rule_file} ---")
        rules = load_rules(rule_file)
        
        results = []
        js_usage = []
        
        for i, rule in enumerate(rules):
            print(f"测试第 {i+1}/{len(rules)} 个书源: {rule.get('name')}")
            
            # 测试基础URL可用性
            is_available, result = test_book_source(rule)
            results.append((is_available, result))
            
            # 分析JavaScript使用情况
            js_places = analyze_js_usage(rule)
            if js_places:
                js_usage.append((rule.get("name"), js_places))
            
            # 避免请求过快
            time.sleep(1)
        
        # 输出结果
        print(f"\n--- 测试结果: {rule_file} ---")
        print("\n1. 可用性测试:")
        available_count = 0
        for is_available, result in results:
            print(f"{'✓' if is_available else '✗'} {result}")
            if is_available:
                available_count += 1
        
        print(f"\n总书源数: {len(results)}, 可用: {available_count}, 不可用: {len(results) - available_count}")
        
        # 输出JavaScript使用情况
        print("\n2. JavaScript使用情况:")
        for name, places in js_usage:
            print(f"{name}: 使用了JavaScript ({', '.join(places)})")
        
        # 输出需要人工检查的书源
        print("\n3. 需要重点检查的书源:")
        for rule in rules:
            comment = rule.get("comment", "")
            if "人机验证" in comment or "CF" in comment or "cloudflare" in comment.lower():
                print(f"{rule.get('name')}: {comment}")


if __name__ == "__main__":
    main()
