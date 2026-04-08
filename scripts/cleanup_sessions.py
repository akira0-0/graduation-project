#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Session 临时表数据清理脚本

功能：
1. 清理 session_l2_posts 和 session_l2_comments 表的所有数据
2. 可选：同时清理 session_l3_results 和 session_metadata

**推荐方法 1（最快）**: 直接在 Supabase Dashboard 执行 SQL
   1. 打开 https://supabase.com/dashboard/project/rynxtsbrwvexytmztcyh/sql/new
   2. 执行以下 SQL:
      TRUNCATE TABLE session_l2_posts, session_l2_comments, session_l3_results, session_metadata;

**推荐方法 2**: 使用本脚本（适合自动化）
   uv run python scripts/cleanup_sessions.py --confirm

使用示例：
  # 清理 L2 临时表（保留 metadata）
  uv run python scripts/cleanup_sessions.py

  # 清理所有 session 相关表（包括 L3 和 metadata）
  uv run python scripts/cleanup_sessions.py --include-l3 --include-metadata

  # 仅查看待清理的数据（不实际删除）
  uv run python scripts/cleanup_sessions.py --dry-run

  # 需要确认才执行
  uv run python scripts/cleanup_sessions.py --confirm
"""
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from supabase import create_client, Client

# =====================================================
# Supabase 连接配置
# =====================================================
SUPABASE_URL = "https://rynxtsbrwvexytmztcyh.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ5bnh0c2Jyd3ZleHl0bXp0Y3loIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3Njc4NTA5ODUsImV4cCI6MjA4MzQyNjk4NX0"
    ".0AGziOeTUQjv1cpaCfNCBST3xz97VxkMs_ggzaxthgo"
)


def create_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def count_table_rows(supabase: Client, table_name: str) -> int:
    """统计表中的总行数"""
    try:
        resp = supabase.table(table_name).select("*", count="exact").limit(1).execute()
        return resp.count or 0
    except Exception as e:
        print(f"⚠️  无法统计 {table_name}: {e}")
        return 0


def delete_all_from_table(supabase: Client, table_name: str, dry_run: bool = False) -> int:
    """删除表中的所有数据（使用 DELETE 语句，忽略返回值）"""
    if dry_run:
        count = count_table_rows(supabase, table_name)
        print(f"  [DRY-RUN] {table_name}: {count} 条")
        return count
    
    # 先统计总数
    initial_count = count_table_rows(supabase, table_name)
    if initial_count == 0:
        return 0
    
    print(f"  {table_name}: 开始删除 {initial_count:,} 条记录...")
    print(f"  💡 提示: 如果 Python API 删除缓慢，可在 Supabase Dashboard SQL 编辑器执行:")
    print(f"     TRUNCATE TABLE {table_name};")
    
    # 使用 PostgREST API 删除（不期待返回值以避免 JSON 错误）
    try:
        # 使用 neq 来匹配所有记录
        supabase.table(table_name).delete().neq("id", "").execute()
    except Exception as e:
        # 忽略返回值错误
        pass
    
    # 验证删除结果
    import time
    time.sleep(2)  # 等待数据库完成操作
    
    remaining = count_table_rows(supabase, table_name)
    actual_deleted = initial_count - remaining
    
    return actual_deleted


def main():
    parser = argparse.ArgumentParser(description="Session 临时表清理工具")
    parser.add_argument(
        "--include-l3", action="store_true",
        help="同时清理 session_l3_results 表",
    )
    parser.add_argument(
        "--include-metadata", action="store_true",
        help="同时清理 session_metadata 表",
    )
    parser.add_argument(
        "--confirm", action="store_true",
        help="跳过确认提示，直接执行删除",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="试运行，仅统计数据量，不实际删除",
    )
    
    args = parser.parse_args()
    
    supabase = create_supabase()
    
    print(f"\n{'=' * 80}")
    print(f"🧹 Session 临时表数据清理工具")
    print(f"{'=' * 80}")
    
    # 确定要清理的表
    tables_to_clean = ["session_l2_posts", "session_l2_comments"]
    
    if args.include_l3:
        tables_to_clean.append("session_l3_results")
    
    if args.include_metadata:
        tables_to_clean.append("session_metadata")
    
    print(f"🎯 清理目标表:")
    for table in tables_to_clean:
        print(f"   - {table}")
    
    # 统计数据量
    print(f"\n📊 统计数据量...")
    table_counts = {}
    total_count = 0
    
    for table in tables_to_clean:
        count = count_table_rows(supabase, table)
        table_counts[table] = count
        total_count += count
        print(f"   - {table}: {count:,} 条")
    
    if total_count == 0:
        print(f"\n✅ 所有表都是空的，无需清理")
        return
    
    print(f"\n   总计: {total_count:,} 条记录")
    
    # 显示 SQL 快速清理方法
    print(f"\n💡 快速清理方法（推荐）:")
    print(f"   1. 打开 Supabase Dashboard SQL 编辑器:")
    print(f"      https://supabase.com/dashboard/project/rynxtsbrwvexytmztcyh/sql/new")
    print(f"   2. 执行以下 SQL（瞬间完成）:")
    table_list = ", ".join(tables_to_clean)
    print(f"      TRUNCATE TABLE {table_list};")
    print(f"\n   或继续使用 Python API 清理（较慢但自动化）...")
    
    if args.dry_run:
        print(f"\n🧪 DRY-RUN 模式：仅统计，不实际删除")
        print(f"   如需实际删除，请移除 --dry-run 参数")
        return
    
    # 确认删除
    if not args.confirm:
        print(f"\n{'─' * 80}")
        print(f"⚠️  警告: 即将删除 {total_count:,} 条记录！")
        print(f"{'─' * 80}")
        confirm = input(f"确认继续？(yes/no): ")
        if confirm.lower() != "yes":
            print(f"❌ 已取消")
            return
    
    # 执行删除
    print(f"\n🗑️  开始清理...")
    total_deleted = 0
    
    for table in tables_to_clean:
        if table_counts[table] == 0:
            print(f"  {table}: 跳过（表为空）")
            continue
        
        print(f"\n  正在清理 {table}...")
        deleted = delete_all_from_table(supabase, table, dry_run=False)
        total_deleted += deleted
        print(f"  ✅ {table}: 删除 {deleted:,} 条")
    
    print(f"\n{'=' * 80}")
    print(f"✅ 清理完成！")
    print(f"{'=' * 80}")
    print(f"   总计删除: {total_deleted:,} 条记录")
    
    # 显示剩余数据
    print(f"\n📊 清理后剩余数据:")
    for table in tables_to_clean:
        remaining = count_table_rows(supabase, table)
        status = "✅ 清空" if remaining == 0 else f"⚠️  剩余 {remaining} 条"
        print(f"   - {table}: {status}")


if __name__ == "__main__":
    main()
