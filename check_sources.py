# -*- coding: utf-8 -*-
"""
快速检查所有书源状态
"""
from core.rule_loader import RuleLoader
from core.http_client import HttpClient
from parsers.search_parser import SearchParser

def check_sources():
    """检查所有书源"""
    rule_loader = RuleLoader()
    rules = rule_loader.load_rules("main-rules.json")

    keyword = "斗破苍穹"

    working = []
    failed = []

    print(f"检查 {len(rules)} 个书源...\n")

    for i, rule in enumerate(rules, 1):
        if not rule.search:
            failed.append((rule.name, "无搜索配置"))
            continue

        try:
            http_client = HttpClient(
                max_retries=1,
                min_interval=0.5,
                max_interval=1.0,
                verify_ssl=not rule.ignore_ssl,
                timeout=10
            )

            search_parser = SearchParser(rule, http_client)
            books = search_parser.search(keyword)

            if books:
                working.append(rule.name)
                print(f"[OK] {i}. {rule.name} - {len(books)}本")
            else:
                failed.append((rule.name, "无搜索结果"))
                print(f"[--] {i}. {rule.name} - 无结果")

            http_client.close()

        except Exception as e:
            error_msg = str(e)[:50]
            failed.append((rule.name, error_msg))
            print(f"[XX] {i}. {rule.name} - {error_msg}")

    print(f"\n{'='*60}")
    print(f"可用书源: {len(working)}/{len(rules)}")
    print(f"不可用: {len(failed)}")

    if failed:
        print(f"\n失败的书源:")
        for name, reason in failed:
            print(f"  - {name}: {reason}")

if __name__ == "__main__":
    check_sources()
