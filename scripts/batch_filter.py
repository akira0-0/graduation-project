# -*- coding: utf-8 -*-
"""
批量过滤脚本 - Layer-1 规则引擎
从 Supabase posts / comments 表读取全量数据，
通过 filter_engine 的 Layer-1 规则引擎（垃圾/广告/敏感内容过滤）进行初步筛选，
将通过的数据写入 filtered_posts / filtered_comments 表，
同时在 filter_logs 中记录任务统计信息。

Layer-1 过滤逻辑（filter_engine 内置规则库）：
  Step 1: 内容长度 < min_content_len  → 丢弃（太短无意义）
  Step 2: 规则引擎命中 spam/ad/sensitive 且置信度 >= 阈值 → 丢弃

用法:
    uv run python scripts/batch_filter.py                         # 过滤全量帖子
    uv run python scripts/batch_filter.py --data-type comments    # 过滤全量评论
    uv run python scripts/batch_filter.py --data-type all         # 帖子+评论都过滤
    uv run python scripts/batch_filter.py --platform xhs          # 只过滤小红书
    uv run python scripts/batch_filter.py --dry-run               # 试运行，不写数据库
    uv run python scripts/batch_filter.py --min-content-len 20    # 调整最短内容长度
    uv run python scripts/batch_filter.py --threshold 0.7         # 调整 spam 置信度阈值
"""

import sys
import os
import argparse
import uuid
import time
from datetime import datetime, timezone
from typing import Optional, List

# 把项目根目录加入 sys.path，确保能 import filter_engine
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from supabase import create_client, Client
from filter_engine.pipeline import FilterPipeline

# =====================================================
# Supabase 连接配置（与 import_with_sdk.py 保持一致）
# =====================================================
SUPABASE_URL = "https://rynxtsbrwvexytmztcyh.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ5bnh0c2Jyd3ZleHl0bXp0Y3loIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3Njc4NTA5ODUsImV4cCI6MjA4MzQyNjk4NX0"
    ".0AGziOeTUQjv1cpaCfNCBST3xz97VxkMs_ggzaxthgo"
)

# =====================================================
# 默认参数
# =====================================================
DEFAULT_PAGE_SIZE = 200       # 每次从 Supabase 拉取的条数
DEFAULT_WRITE_BATCH = 50      # 每次 upsert 写入的条数
DEFAULT_MIN_CONTENT_LEN = 4  # 最短内容长度（字符数）
DEFAULT_SPAM_THRESHOLD = 0.6  # spam 置信度排除阈值


# =====================================================
# 参数解析
# =====================================================
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="批量 Layer-1 规则过滤，写入 filtered_posts / filtered_comments"
    )
    p.add_argument(
        "--data-type", type=str, default="posts",
        choices=["posts", "comments", "all"],
        help="过滤数据类型：posts / comments / all，默认 posts",
    )
    p.add_argument(
        "--platform", type=str, default=None,
        help="只过滤指定平台（如 xhs / weibo），不填则全平台",
    )
    p.add_argument(
        "--page-size", type=int, default=DEFAULT_PAGE_SIZE,
        help=f"每页拉取条数，默认 {DEFAULT_PAGE_SIZE}",
    )
    p.add_argument(
        "--min-content-len", type=int, default=DEFAULT_MIN_CONTENT_LEN,
        help=f"最小内容长度（字符），不足则直接丢弃，默认 {DEFAULT_MIN_CONTENT_LEN}",
    )
    p.add_argument(
        "--threshold", type=float, default=DEFAULT_SPAM_THRESHOLD,
        help=f"spam 置信度排除阈值 0~1，超过则丢弃，默认 {DEFAULT_SPAM_THRESHOLD}",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="试运行：只读取和过滤，不写入数据库",
    )
    p.add_argument(
        "--no-cache", action="store_true",
        help="禁用 filter_engine 内部缓存",
    )
    return p


# =====================================================
# Supabase 工具函数
# =====================================================
def create_supabase() -> Client:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase 客户端已连接")
    return client


def create_batch_id() -> str:
    """生成唯一批次 ID，格式: batch_20260407_123456_abc123"""
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = str(uuid.uuid4())[:6]
    return f"batch_{date_str}_{short_id}"


def fetch_posts_page(
    supabase: Client,
    page: int,
    page_size: int,
    platform: Optional[str],
) -> list:
    """分页拉取 posts 表全量数据"""
    q = supabase.table("posts").select(
        "id, platform, type, url, title, content, publish_time, "
        "author_id, author_nickname, author_ip_location, author_is_verified, "
        "metrics_likes, metrics_collects, metrics_comments, metrics_shares, "
        "tags, source_keyword"
    )
    if platform:
        q = q.eq("platform", platform)
    start = page * page_size
    resp = q.range(start, start + page_size - 1).execute()
    return resp.data or []


def fetch_comments_page(
    supabase: Client,
    page: int,
    page_size: int,
    platform: Optional[str],
) -> list:
    """分页拉取 comments 表全量数据"""
    q = supabase.table("comments").select(
        "id, content_id, platform, content, publish_time, "
        "author_id, author_nickname, author_ip_location, "
        "metrics_likes, metrics_sub_comments, "
        "parent_comment_id, root_comment_id, "
        "reply_to_user_id, reply_to_user_nickname, comment_level"
    )
    if platform:
        q = q.eq("platform", platform)
    start = page * page_size
    resp = q.range(start, start + page_size - 1).execute()
    return resp.data or []


def write_batch(
    supabase: Client,
    rows: list,
    table: str,
    dry_run: bool,
) -> None:
    """批量 upsert 到目标表"""
    if dry_run or not rows:
        return
    supabase.table(table).upsert(rows, on_conflict="id").execute()


# =====================================================
# 构建写入行
# =====================================================
def build_post_row(post: dict, batch_id: str, matched_rules: List[str]) -> dict:
    """
    组合帖子原始字段 + 过滤元数据，写入 filtered_posts。
    matched_rules: FilterResult.matched_rules，是 List[str]（规则名称列表）。
    Layer-1 通过说明内容未被 spam 规则高置信度命中，
    低于阈值命中的规则记录在 filter_rejected_rules 供审计。
    """
    return {
        "id": post["id"],
        "original_id": post["id"],
        "platform": post.get("platform", ""),
        "type": post.get("type"),
        "url": post.get("url"),
        "title": post.get("title"),
        "content": post.get("content"),
        "publish_time": post.get("publish_time"),
        "author_id": post.get("author_id"),
        "author_nickname": post.get("author_nickname"),
        "author_ip_location": post.get("author_ip_location"),
        "author_is_verified": post.get("author_is_verified", False),
        "metrics_likes": post.get("metrics_likes", 0),
        "metrics_collects": post.get("metrics_collects", 0),
        "metrics_comments": post.get("metrics_comments", 0),
        "metrics_shares": post.get("metrics_shares", 0),
        "tags": post.get("tags"),
        "source_keyword": post.get("source_keyword"),
        # 过滤元数据
        "filter_batch_id": batch_id,
        "filter_passed_rules": [],
        "filter_rejected_rules": matched_rules,  # List[str]，审计用
        "quality_score": None,                   # 留给 Layer-2 填充
        "relevance_score": None,                 # 留给 Layer-3 填充
        "filter_layer": 1,
    }


def build_comment_row(comment: dict, batch_id: str, matched_rules: List[str]) -> dict:
    """组合评论原始字段 + 过滤元数据，写入 filtered_comments。"""
    return {
        "id": comment["id"],
        "original_id": comment["id"],
        "content_id": comment.get("content_id", ""),
        "platform": comment.get("platform", ""),
        "content": comment.get("content"),
        "publish_time": comment.get("publish_time"),
        "author_id": comment.get("author_id"),
        "author_nickname": comment.get("author_nickname"),
        "author_ip_location": comment.get("author_ip_location"),
        "metrics_likes": comment.get("metrics_likes", 0),
        "metrics_sub_comments": comment.get("metrics_sub_comments", 0),
        "parent_comment_id": comment.get("parent_comment_id"),
        "root_comment_id": comment.get("root_comment_id"),
        "reply_to_user_id": comment.get("reply_to_user_id"),
        "reply_to_user_nickname": comment.get("reply_to_user_nickname"),
        "comment_level": comment.get("comment_level", 1),
        # 过滤元数据
        "filter_batch_id": batch_id,
        "filter_passed_rules": [],
        "filter_rejected_rules": matched_rules,
        "quality_score": None,
        "relevance_score": None,
        "filter_layer": 1,
    }


# =====================================================
# 核心过滤函数
# =====================================================
def run_filter(
    supabase: Client,
    pipeline: FilterPipeline,
    data_type: str,   # "posts" or "comments"
    args,
) -> dict:
    """执行单类型批量 Layer-1 过滤任务。"""
    start_time = time.time()
    batch_id = create_batch_id()
    target_table = "filtered_posts" if data_type == "posts" else "filtered_comments"

    filter_criteria = {
        "data_type": data_type,
        "min_content_len": args.min_content_len,
        "spam_threshold": args.threshold,
        "use_llm": False,
        "filter_layer": 1,
    }
    if args.platform:
        filter_criteria["platform"] = args.platform

    print(f"\n{'='*55}")
    print(f"  批量 Layer-1 过滤  [{data_type}]")
    print(f"  batch_id   : {batch_id}")
    print(f"  platform   : {args.platform or '(全平台)'}")
    print(f"  min_len    : {args.min_content_len} 字符")
    print(f"  threshold  : {args.threshold}")
    print(f"  dry_run    : {args.dry_run}")
    print(f"{'='*55}")

    # 创建 filter_logs 记录
    if not args.dry_run:
        supabase.table("filter_logs").insert({
            "batch_id": batch_id,
            "filter_criteria": filter_criteria,
            "data_type": data_type,
            "platform": args.platform,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        print(f"📋 filter_logs 已创建，batch_id={batch_id}\n")

    total_input = 0
    total_passed = 0
    rejected_short = 0    # Step1 被丢弃：内容过短
    rejected_spam = 0     # Step2 被丢弃：规则引擎判定 spam
    page = 0
    write_buffer = []

    try:
        while True:
            # ---- 分页拉取（全量，不按关键词筛选） ----
            if data_type == "posts":
                rows = fetch_posts_page(supabase, page, args.page_size, args.platform)
            else:
                rows = fetch_comments_page(supabase, page, args.page_size, args.platform)

            if not rows:
                break  # 已读完全部数据

            total_input += len(rows)
            print(f"📄 第 {page+1:>3} 页 | 读取 {len(rows):>4} 条", end="  ")

            page_passed = 0
            for row in rows:
                content = (row.get("content") or "").strip()

                # ---- Step 1: 长度过滤 ----
                if len(content) < args.min_content_len:
                    rejected_short += 1
                    continue

                # ---- Step 2: Layer-1 规则引擎过滤 ----
                # pipeline.filter_text 返回 FilterResult(Pydantic model)：
                #   .is_spam: bool         —— 是否被判定为垃圾
                #   .confidence: float     —— 综合置信度 0~1
                #   .matched_rules: List[str]  —— 命中的规则名称（字符串列表）
                result = pipeline.filter_text(content)

                if result.is_spam and result.confidence >= args.threshold:
                    # 高置信度 spam，排除
                    rejected_spam += 1
                    continue

                # ---- 通过：构建写入行 ----
                if data_type == "posts":
                    out_row = build_post_row(row, batch_id, result.matched_rules)
                else:
                    out_row = build_comment_row(row, batch_id, result.matched_rules)

                write_buffer.append(out_row)
                page_passed += 1
                total_passed += 1

                if len(write_buffer) >= DEFAULT_WRITE_BATCH:
                    write_batch(supabase, write_buffer, target_table, args.dry_run)
                    write_buffer = []

            print(f"→ 通过 {page_passed:>4} 条 | 累计 {total_passed} / {total_input}")
            page += 1

        # flush 最后一批
        if write_buffer:
            write_batch(supabase, write_buffer, target_table, args.dry_run)

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ 过滤出错 [{data_type}]: {e}")
        if not args.dry_run:
            supabase.table("filter_logs").update({
                "status": "failed",
                "error_message": str(e),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round(duration, 2),
            }).eq("batch_id", batch_id).execute()
        raise

    duration = time.time() - start_time
    pass_rate = round(total_passed / total_input, 4) if total_input > 0 else 0.0

    step_stats = [
        {
            "step": "min_length",
            "input": total_input,
            "output": total_input - rejected_short,
            "removed": rejected_short,
        },
        {
            "step": "layer1_rule_engine",
            "input": total_input - rejected_short,
            "output": total_passed,
            "removed": rejected_spam,
            "threshold": args.threshold,
        },
    ]

    # 更新 filter_logs
    if not args.dry_run:
        supabase.table("filter_logs").update({
            "total_input": total_input,
            "total_passed": total_passed,
            "total_rejected": total_input - total_passed,
            "pass_rate": pass_rate,
            "step_stats": step_stats,
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(duration, 2),
        }).eq("batch_id", batch_id).execute()

    print(f"\n{'='*55}")
    print(f"  ✅ [{data_type}] Layer-1 过滤完成")
    print(f"  总输入        : {total_input} 条")
    print(f"  ├─ 内容过短   : -{rejected_short} 条  (< {args.min_content_len} 字符)")
    print(f"  ├─ spam 排除  : -{rejected_spam} 条  (confidence >= {args.threshold})")
    print(f"  └─ 最终通过   : {total_passed} 条  ({round(pass_rate*100, 1)}%)")
    print(f"  耗时          : {duration:.1f} 秒")
    if not args.dry_run:
        print(f"  写入表        : {target_table}")
        print(f"  批次 ID       : {batch_id}")
    else:
        print(f"  [dry-run] 未写入任何数据")
    print(f"{'='*55}\n")

    return {
        "batch_id": batch_id,
        "total_input": total_input,
        "total_passed": total_passed,
        "rejected_short": rejected_short,
        "rejected_spam": rejected_spam,
    }


# =====================================================
# 入口
# =====================================================
def run(args) -> None:
    supabase = create_supabase()
    # use_llm=False：只使用规则引擎（Layer-1），不调用 LLM
    pipeline = FilterPipeline(use_llm=False, use_cache=not args.no_cache)

    # Layer-1 只加载"通用-"前缀的规则（垃圾/敏感/涉黄/涉政/广告等基础过滤）
    # 避免加载场景规则（电商/新闻/旅游等），防止误杀正常内容
    general_rules = pipeline.rule_manager.list(enabled_only=True, name_prefix="通用-")
    if general_rules:
        # 临时替换引擎只加载通用规则
        from filter_engine.rules import RuleManager
        from filter_engine.core import RuleEngine

        class _GeneralOnlyRuleManager(RuleManager):
            """只返回通用规则的临时 RuleManager"""
            def list(self, enabled_only=False, **kwargs):
                return super().list(enabled_only=enabled_only, name_prefix="通用-")

        from filter_engine.config import settings as fe_settings
        general_manager = _GeneralOnlyRuleManager(fe_settings.DATABASE_PATH)
        pipeline.rule_engine = RuleEngine(general_manager)
        print(f"ℹ️  Layer-1 规则已限定为通用规则，共 {len(general_rules)} 条\n")
    else:
        print("⚠️  未找到通用规则，将使用全部规则\n")

    data_types = ["posts", "comments"] if args.data_type == "all" else [args.data_type]
    for dt in data_types:
        run_filter(supabase, pipeline, dt, args)


if __name__ == "__main__":
    parser = build_arg_parser()
    run(parser.parse_args())
