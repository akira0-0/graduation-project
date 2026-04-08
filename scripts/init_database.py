#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
自动执行所有必要的 SQL schema 文件，初始化过滤流程所需的表

用法:
    python scripts/init_database.py
    python scripts/init_database.py --reset  # 重置所有表（谨慎使用）
"""

import sys
import os
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from supabase import create_client

# Supabase 配置
SUPABASE_URL = "https://rynxtsbrwvexytmztcyh.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ5bnh0c2Jyd3ZleHl0bXp0Y3loIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3Njc4NTA5ODUsImV4cCI6MjA4MzQyNjk4NX0"
    ".0AGziOeTUQjv1cpaCfNCBST3xz97VxkMs_ggzaxthgo"
)

SQL_FILES = [
    ("database/schema_filtered.sql", "过滤结果表 (filtered_posts/comments/logs)"),
    ("database/migrate_add_data_type.sql", "filter_logs.data_type 字段迁移"),
    ("database/schema_session.sql", "Session 临时表 (session_l2/l3/metadata)"),
]


def read_sql_file(filepath: Path) -> str:
    """读取 SQL 文件内容"""
    if not filepath.exists():
        raise FileNotFoundError(f"SQL 文件不存在: {filepath}")
    return filepath.read_text(encoding="utf-8")


def execute_sql(supabase, sql: str, description: str):
    """执行 SQL（通过 Supabase RPC）"""
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"{'='*60}")
    
    try:
        # Supabase Python SDK 不支持直接执行 DDL
        # 需要用户手动在 Supabase SQL Editor 中执行
        print("⚠️  Supabase Python SDK 不支持 DDL 执行")
        print("请手动复制以下 SQL 到 Supabase Dashboard > SQL Editor 中执行:\n")
        print(sql[:500] + "..." if len(sql) > 500 else sql)
        print("\n或者直接在 SQL Editor 中运行对应文件:")
        return False
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False


def check_table_exists(supabase, table_name: str) -> bool:
    """检查表是否存在"""
    try:
        # 尝试查询表（limit 0 不会返回数据）
        supabase.table(table_name).select("*").limit(0).execute()
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="初始化数据库表")
    parser.add_argument(
        "--reset", action="store_true",
        help="重置所有表（会删除现有数据，谨慎使用）"
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="只检查表是否存在，不执行创建"
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("  数据库初始化脚本")
    print(f"  模式: {'重置模式' if args.reset else '检查模式' if args.check_only else '初始化模式'}")
    print(f"{'='*60}\n")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 检查必要的表
    tables_to_check = [
        "filtered_posts",
        "filtered_comments", 
        "filter_logs",
        "session_l2_posts",
        "session_l2_comments",
        "session_l3_results",
        "session_metadata",
    ]

    print("检查表是否存在...")
    existing_tables = []
    missing_tables = []
    
    for table in tables_to_check:
        exists = check_table_exists(supabase, table)
        if exists:
            existing_tables.append(table)
            print(f"  ✓ {table}")
        else:
            missing_tables.append(table)
            print(f"  ✗ {table} (不存在)")

    if args.check_only:
        print(f"\n总结: {len(existing_tables)}/{len(tables_to_check)} 个表已存在")
        if missing_tables:
            print(f"缺失的表: {', '.join(missing_tables)}")
        return

    if not missing_tables and not args.reset:
        print("\n✅ 所有必要的表都已存在，无需初始化")
        print("   如需重置，请使用 --reset 参数（会删除现有数据）")
        return

    if args.reset:
        print("\n⚠️  重置模式：将删除以下表的数据")
        for table in existing_tables:
            print(f"   - {table}")
        confirm = input("\n确认继续？(yes/no): ")
        if confirm.lower() != "yes":
            print("已取消")
            return

    # 由于 Supabase Python SDK 限制，提供手动执行指引
    print("\n" + "="*60)
    print("  ⚠️  重要提示")
    print("="*60)
    print("\nSupabase Python SDK 不支持直接执行 DDL 语句。")
    print("请按以下步骤手动初始化数据库:\n")
    
    print("1. 登录 Supabase Dashboard")
    print("   https://app.supabase.com/project/rynxtsbrwvexytmztcyh\n")
    
    print("2. 进入 'SQL Editor'")
    print("   左侧菜单 > SQL Editor > New Query\n")
    
    print("3. 依次执行以下 SQL 文件:\n")
    
    for filepath, description in SQL_FILES:
        full_path = PROJECT_ROOT / filepath
        if full_path.exists():
            print(f"   • {filepath}")
            print(f"     说明: {description}")
            print(f"     路径: {full_path}\n")
        else:
            print(f"   ⚠️  文件不存在: {filepath}\n")
    
    print("\n4. 执行完成后，再次运行本脚本检查:")
    print("   python scripts/init_database.py --check-only\n")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
