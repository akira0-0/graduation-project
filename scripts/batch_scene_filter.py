# -*- coding: utf-8 -*-
"""
批量场景过滤脚本 - Layer-2 动态场景规则过滤
处理流程：
  Step 1: 从 filtered_posts（Layer-1 已通过）中读取帖子
  Step 2: 根据用户 query 分析场景（电商/旅游/美食等）
  Step 3: 使用 DynamicFilterPipeline 动态选择场景规则
  Step 4: 对帖子应用场景规则，通过的写入 session_l2_posts
  Step 5: 从 filtered_comments 中读取评论（全量或仅 L2 通过帖子的）
  Step 6: 对评论应用相同场景规则，通过的写入 session_l2_comments

用法:
    uv run python scripts/batch_scene_filter.py --query "过滤电商评论中的广告和刷单内容"
    uv run python scripts/batch_scene_filter.py --query "旅游攻略帖子" --platform xhs
    uv run python scripts/batch_scene_filter.py --query "美食推荐" --severity strict --dry-run
    uv run python scripts/batch_scene_filter.py --query "新闻资讯" --no-generate-rules

说明:
    - 本脚本读取 filtered_posts / filtered_comments（Layer-1 结果）
    - 使用 DynamicFilterPipeline 的场景感知能力
    - 输出到 session_l2_posts / session_l2_comments 临时表
    - Session 数据默认 2 小时 TTL，需定期调用清理函数
    - --severity 控制过滤严格程度：relaxed / normal / strict
    - Layer-2 主要过滤场景不匹配的内容，不输出置信度分数
"""

import sys
import os
import argparse
import uuid
import time
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from supabase import create_client, Client
from filter_engine.llm.smart_matcher import SmartRuleMatcher, SmartMatchResult
from filter_engine.rules import RuleManager

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

# =====================================================
# 默认参数
# =====================================================
DEFAULT_PAGE_SIZE = 200
DEFAULT_WRITE_BATCH = 50

SEVERITY_MAP = {
    "relaxed": FilterSeverity.RELAXED,
    "normal": FilterSeverity.NORMAL,
    "strict": FilterSeverity.STRICT,
}


# =====================================================
# 参数解析
# =====================================================
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Layer-2 动态场景规则过滤：根据 query 智能选择规则"
    )
    p.add_argument(
        "--query", type=str, required=True,
        help="查询描述，如 '过滤电商广告' / '旅游攻略' / '美食推荐'，用于场景识别",
    )
    p.add_argument(
        "--platform", type=str, default=None,
        help="只处理指定平台（如 xhs / weibo），不填则全平台",
    )
    p.add_argument(
        "--severity", type=str, default="normal",
        choices=["relaxed", "normal", "strict"],
        help="过滤严格程度：relaxed(宽松) / normal(正常) / strict(严格)，默认 normal",
    )
    p.add_argument(
        "--page-size", type=int, default=DEFAULT_PAGE_SIZE,
        help=f"每页拉取条数，默认 {DEFAULT_PAGE_SIZE}",
    )
    p.add_argument(
        "--no-llm", action="store_true",
        help="禁用 LLM 辅助决策（只用规则引擎，更快但可能不准确）",
    )
    p.add_argument(
        "--no-generate-rules", action="store_true",
        help="禁止自动生成规则（不分析缺口）",
    )
    p.add_argument(
        "--filter-comments-mode", type=str, default="all",
        choices=["all", "valid-posts-only"],
        help="评论过滤模式：all(全量评论) / valid-posts-only(仅 L2 通过帖子的评论)，默认 all",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="试运行，只输出统计，不写数据库",
    )
    return p


# =====================================================
# Supabase 工具
# =====================================================
def create_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_filtered_posts_page(
    supabase: Client,
    page: int,
    page_size: int,
    platform: Optional[str],
) -> list:
    """分页拉取 filtered_posts 表（Layer-1 已通过）"""
    q = supabase.table("filtered_posts").select("*")
    if platform:
        q = q.eq("platform", platform)
    start = page * page_size
    resp = q.range(start, start + page_size - 1).execute()
    return resp.data or []


def fetch_filtered_comments_page(
    supabase: Client,
    page: int,
    page_size: int,
    platform: Optional[str],
) -> list:
    """分页拉取 filtered_comments 表（Layer-1 已通过）"""
    q = supabase.table("filtered_comments").select("*")
    if platform:
        q = q.eq("platform", platform)
    start = page * page_size
    resp = q.range(start, start + page_size - 1).execute()
    return resp.data or []


def fetch_filtered_comments_by_post_ids(
    supabase: Client,
    post_ids: List[str],
    platform: Optional[str],
) -> list:
    """拉取指定帖子 ID 集合的评论"""
    if not post_ids:
        return []
    q = supabase.table("filtered_comments").select("*").in_("content_id", post_ids)
    if platform:
        q = q.eq("platform", platform)
    resp = q.execute()
    return resp.data or []


def batch_insert_session_data(
    supabase: Client,
    table: str,
    rows: List[Dict],
    dry_run: bool,
) -> None:
    """批量插入 session 表（insert，不是 upsert，避免覆盖）"""
    if dry_run or not rows:
        return
    for i in range(0, len(rows), DEFAULT_WRITE_BATCH):
        chunk = rows[i: i + DEFAULT_WRITE_BATCH]
        supabase.table(table).insert(chunk).execute()


def create_session_metadata(
    supabase: Client,
    session_id: str,
    query_text: str,
    query_intent: Dict,
    dry_run: bool,
) -> None:
    """创建 session 元数据记录"""
    if dry_run:
        return
    row = {
        "session_id": session_id,
        "query_text": query_text,
        "query_intent": query_intent,
        "status": "running",
    }
    supabase.table("session_metadata").insert(row).execute()


def update_session_metadata(
    supabase: Client,
    session_id: str,
    updates: Dict,
    dry_run: bool,
) -> None:
    """更新 session 元数据"""
    if dry_run:
        return
    supabase.table("session_metadata").update(updates).eq("session_id", session_id).execute()


# =====================================================
# 场景过滤核心逻辑
# =====================================================
def filter_items_with_scene_rules(
    pipeline: DynamicFilterPipeline,
    query: str,
    items: List[Dict],
    text_field: str,
    session_id: str,
) -> Tuple[List[Dict], List[str]]:
    """
    对一批数据项应用场景规则过滤。

    Returns:
        passed_rows: 通过的记录（用于写 session 表）
        passed_ids : 通过的 id 列表（用于后续联动）
    """
    # 提取文本列表
    texts = []
    for item in items:
        # 如果是帖子，拼接 title + content
        if "title" in item and item.get("title"):
            text = f"{item['title']} {item.get(text_field, '')}".strip()
        else:
            text = item.get(text_field) or ""
        texts.append(text)

    # 调用 DynamicFilterPipeline 批量过滤
    result = pipeline.filter_with_query(
        query=query,
        texts=texts,
        auto_generate_rules=False,  # Layer-2 阶段不自动生成规则（可选）
    )

    passed_rows: List[Dict] = []
    passed_ids: List[str] = []

    for item, filter_res in zip(items, result["results"]):
        # is_spam=False 表示通过（不是垃圾）
        if not filter_res.get("is_spam", False):
            # 构建 session 表记录
            session_row = {
                **item,  # 复制全部原始字段
                "session_id": session_id,
                "query_text": query,
                "scene_matched_rules": filter_res.get("matched_rules", []),
            }
            passed_rows.append(session_row)
            passed_ids.append(item["id"])

    return passed_rows, passed_ids


# =====================================================
# 主流程
# =====================================================
def run(args) -> None:
    supabase = create_supabase()
    use_llm = not args.no_llm
    auto_generate = not args.no_generate_rules
    severity = SEVERITY_MAP[args.severity]
    session_id = f"sess_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    print(f"{'='*60}")
    print(f"  Layer-2 场景规则过滤")
    print(f"  session_id : {session_id}")
    print(f"  query      : {args.query}")
    print(f"  severity   : {args.severity}")
    print(f"  use_llm    : {use_llm}")
    print(f"  auto_gen   : {auto_generate}")
    print(f"  platform   : {args.platform or '全平台'}")
    print(f"  dry_run    : {args.dry_run}")
    print(f"{'='*60}\n")

    # 初始化 DynamicFilterPipeline
    config = DynamicFilterConfig(
        enable_dynamic_rules=True,
        enable_rule_generation=auto_generate,
        auto_save_generated_rules=False,  # Layer-2 不自动保存，避免污染规则库
    )
    pipeline = DynamicFilterPipeline(use_llm=use_llm, config=config)

    # 分析 query 意图
    print("── 分析查询意图 ──")
    intent = pipeline.analyze_query(
        query=args.query,
        explicit_severity=args.severity,
    )
    print(f"  场景: {intent.scenario.value}")
    print(f"  严格度: {intent.severity.value}")
    print(f"  额外类别: {intent.extra_categories}")
    print(f"  自定义关键词: {intent.custom_keywords}\n")

    # 创建 session 元数据
    create_session_metadata(
        supabase, session_id, args.query, intent.to_dict(), args.dry_run
    )

    # --------------------------------------------------
    # Step 1-4: 帖子过滤
    # --------------------------------------------------
    print("── Step 1-4: 帖子场景过滤 ──")
    t0 = time.time()

    all_post_rows: List[Dict] = []
    all_valid_post_ids: List[str] = []
    post_total = 0
    page = 0

    while True:
        rows = fetch_filtered_posts_page(supabase, page, args.page_size, args.platform)
        if not rows:
            break

        post_total += len(rows)
        passed_rows, passed_ids = filter_items_with_scene_rules(
            pipeline=pipeline,
            query=args.query,
            items=rows,
            text_field="content",
            session_id=session_id,
        )

        all_post_rows.extend(passed_rows)
        all_valid_post_ids.extend(passed_ids)

        print(
            f"  帖子第 {page+1} 页：读取 {len(rows)} 条，"
            f"通过 {len(passed_ids)} 条，"
            f"累计通过 {len(all_valid_post_ids)} 条"
        )
        page += 1

    # 写入 session_l2_posts
    batch_insert_session_data(supabase, "session_l2_posts", all_post_rows, args.dry_run)

    post_elapsed = time.time() - t0
    post_pass_rate = len(all_valid_post_ids) / post_total if post_total else 0
    print(
        f"\n  帖子过滤完成：总计 {post_total} 条，"
        f"通过 {len(all_valid_post_ids)} 条 ({post_pass_rate:.1%})，"
        f"耗时 {post_elapsed:.1f}s\n"
    )

    # 更新 session 元数据
    update_session_metadata(
        supabase,
        session_id,
        {
            "l1_total_posts": post_total,
            "l2_passed_posts": len(all_valid_post_ids),
        },
        args.dry_run,
    )

    # --------------------------------------------------
    # Step 5-6: 评论过滤
    # --------------------------------------------------
    print("── Step 5-6: 评论场景过滤 ──")
    t1 = time.time()

    # 根据模式决定拉取哪些评论
    if args.filter_comments_mode == "valid-posts-only":
        if not all_valid_post_ids:
            print("⚠️  没有帖子通过 Layer-2，跳过评论过滤。")
            comment_total = 0
            all_comment_rows = []
        else:
            print(f"  仅处理 {len(all_valid_post_ids)} 个有效帖子下的评论")
            # 分批拉取评论
            comment_batch_size = 100
            all_comments = []
            for i in range(0, len(all_valid_post_ids), comment_batch_size):
                chunk_ids = all_valid_post_ids[i: i + comment_batch_size]
                comments = fetch_filtered_comments_by_post_ids(supabase, chunk_ids, args.platform)
                all_comments.extend(comments)
            comment_total = len(all_comments)
            print(f"  共拉取 {comment_total} 条评论")
    else:
        # 全量拉取评论
        print("  处理全量评论")
        all_comments = []
        page = 0
        while True:
            rows = fetch_filtered_comments_page(supabase, page, args.page_size, args.platform)
            if not rows:
                break
            all_comments.extend(rows)
            page += 1
        comment_total = len(all_comments)
        print(f"  共拉取 {comment_total} 条评论")

    # 对评论应用场景规则
    all_comment_rows: List[Dict] = []
    comment_valid_count = 0

    if comment_total > 0:
        # 分批处理
        chunk = args.page_size
        for i in range(0, len(all_comments), chunk):
            batch = all_comments[i: i + chunk]
            passed_rows, passed_ids = filter_items_with_scene_rules(
                pipeline=pipeline,
                query=args.query,
                items=batch,
                text_field="content",
                session_id=session_id,
            )
            comment_valid_count += len(passed_ids)
            all_comment_rows.extend(passed_rows)
            print(
                f"  评论第 {i // chunk + 1} 批：处理 {len(batch)} 条，"
                f"通过 {len(passed_ids)} 条"
            )

        # 写入 session_l2_comments
        batch_insert_session_data(supabase, "session_l2_comments", all_comment_rows, args.dry_run)

    comment_elapsed = time.time() - t1
    comment_pass_rate = comment_valid_count / comment_total if comment_total else 0
    print(
        f"\n  评论过滤完成：总计 {comment_total} 条，"
        f"通过 {comment_valid_count} 条 ({comment_pass_rate:.1%})，"
        f"耗时 {comment_elapsed:.1f}s\n"
    )

    # 更新 session 元数据
    update_session_metadata(
        supabase,
        session_id,
        {
            "l1_total_comments": comment_total,
            "l2_passed_comments": comment_valid_count,
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
        args.dry_run,
    )

    # --------------------------------------------------
    # 统计与总结
    # --------------------------------------------------
    total_elapsed = time.time() - t0
    print(f"{'='*60}")
    print(f"  ✅ Layer-2 场景过滤完成")
    print(f"  session_id : {session_id}")
    print(f"  场景       : {intent.scenario.value}")
    print(f"  帖子: {post_total} → {len(all_valid_post_ids)} 条通过 ({post_pass_rate:.1%})")
    print(f"  评论: {comment_total} → {comment_valid_count} 条通过 ({comment_pass_rate:.1%})")
    print(f"  总耗时: {total_elapsed:.1f}s")
    if args.dry_run:
        print(f"  ⚠️  dry-run 模式，数据库未写入")
    else:
        print(f"  数据已写入 session_l2_posts / session_l2_comments")
        print(f"  下一步：运行 batch_llm_filter.py --session-id {session_id}")
    print(f"{'='*60}\n")

    # 显示规则选择统计
    pipeline_stats = pipeline.get_stats()
    print("── 规则选择统计 ──")
    print(f"  场景识别: {pipeline_stats['session']['current_scenario']}")
    print(f"  规则总数: {pipeline_stats['session']['rules_selected']}")
    if pipeline_stats.get("rules_generated", 0) > 0:
        print(f"  ⚠️  检测到 {pipeline_stats['rules_generated']} 条规则缺口（未自动保存）")
    print()


if __name__ == "__main__":
    parser = build_arg_parser()
    run(parser.parse_args())
