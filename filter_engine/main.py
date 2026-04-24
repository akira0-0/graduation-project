# -*- coding: utf-8 -*-
# ⚠️  [REDUNDANT - 待审查是否删除]
# 原因：这是 FilterPipeline 的 CLI 命令行入口，随 pipeline.py 一起被废弃。
#       当前系统通过 uvicorn 启动 FastAPI，不再需要 CLI 入口。
#       删除条件：确认无人通过命令行调用 `python -m filter_engine` 后可安全删除。
"""过滤引擎CLI入口"""
import json
import argparse
from pathlib import Path

from .pipeline import FilterPipeline
from .rules import RuleManager, RuleCreate
from .config import settings


def cmd_filter(args):
    """过滤命令"""
    pipeline = FilterPipeline(use_llm=args.llm)
    
    if args.text:
        # 过滤单条文本
        result = pipeline.filter_text(args.text)
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    
    elif args.file:
        # 过滤JSON文件
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            results = pipeline.filter_and_split(data, content_field=args.field)
            output_path = pipeline.save_results(results, args.output)
            
            print(f"✅ 过滤完成!")
            print(f"   总数: {results['stats']['total']}")
            print(f"   正常: {results['stats']['clean_count']}")
            print(f"   垃圾: {results['stats']['spam_count']} ({results['stats']['spam_rate']}%)")
            print(f"   输出: {output_path}")


def cmd_rules(args):
    """规则管理命令"""
    manager = RuleManager(settings.DATABASE_PATH)
    
    if args.action == "list":
        rules = manager.list()
        for r in rules:
            status = "✅" if r.enabled else "❌"
            print(f"{status} [{r.id}] {r.name} ({r.type}) - {r.category}")
    
    elif args.action == "add":
        content = json.dumps(args.content.split(",")) if args.content else "[]"
        rule = RuleCreate(
            name=args.name,
            type=args.type,
            content=content,
            category=args.category,
        )
        created = manager.create(rule)
        print(f"✅ 创建成功: {created.name} (ID: {created.id})")
    
    elif args.action == "delete":
        if manager.delete(args.id):
            print(f"✅ 删除成功")
        else:
            print(f"❌ 规则不存在")
    
    elif args.action == "toggle":
        rule = manager.toggle(args.id)
        if rule:
            print(f"✅ {rule.name} 已{'启用' if rule.enabled else '禁用'}")
        else:
            print(f"❌ 规则不存在")
    
    elif args.action == "export":
        rules = manager.export_rules()
        output = args.output or "rules_export.json"
        with open(output, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2, default=str)
        print(f"✅ 导出 {len(rules)} 条规则到 {output}")
    
    elif args.action == "import":
        with open(args.file, "r", encoding="utf-8") as f:
            rules = json.load(f)
        count = manager.import_rules(rules)
        print(f"✅ 导入 {count} 条规则")


def cmd_serve(args):
    """启动API服务"""
    import uvicorn
    uvicorn.run(
        "filter_engine.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def main():
    parser = argparse.ArgumentParser(description="过滤引擎CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    # 过滤命令
    filter_parser = subparsers.add_parser("filter", help="过滤数据")
    filter_parser.add_argument("-t", "--text", help="过滤单条文本")
    filter_parser.add_argument("-f", "--file", help="过滤JSON文件")
    filter_parser.add_argument("--field", default="content", help="内容字段名")
    filter_parser.add_argument("-o", "--output", help="输出文件路径")
    filter_parser.add_argument("--llm", action="store_true", help="启用LLM")
    filter_parser.set_defaults(func=cmd_filter)
    
    # 规则命令
    rules_parser = subparsers.add_parser("rules", help="规则管理")
    rules_parser.add_argument("action", choices=["list", "add", "delete", "toggle", "export", "import"])
    rules_parser.add_argument("--id", type=int, help="规则ID")
    rules_parser.add_argument("--name", help="规则名称")
    rules_parser.add_argument("--type", choices=["keyword", "regex"], help="规则类型")
    rules_parser.add_argument("--content", help="规则内容(逗号分隔)")
    rules_parser.add_argument("--category", help="分类")
    rules_parser.add_argument("--file", help="导入文件")
    rules_parser.add_argument("-o", "--output", help="导出文件")
    rules_parser.set_defaults(func=cmd_rules)
    
    # 服务命令
    serve_parser = subparsers.add_parser("serve", help="启动API服务")
    serve_parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    serve_parser.add_argument("--port", type=int, default=8081, help="端口")
    serve_parser.add_argument("--reload", action="store_true", help="热重载")
    serve_parser.set_defaults(func=cmd_serve)
    
    args = parser.parse_args()
    
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
