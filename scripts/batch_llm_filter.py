# -*- coding: utf-8 -*-
"""
批量 LLM 语义过滤脚本 - Layer-3 相关性过滤
处理流程（联动逻辑）：
  Step 1: 从 session_l2_posts（Layer-2 已通过）中读取帖子
  Step 2: 用 RelevanceFilter 对帖子做语义相关性判断
          - 关键词高分 (>=0.6)  → 直接判高相关，不调 LLM
          - 关键词极低 (<0.3)   → 直接判不相关，不调 LLM
          - 中间地带             → 调用 LLM 判断（每批 10 条）
  Step 3: 收集通过相关性检验的帖子（valid_post_ids）
  Step 4: 从 session_l2_comments 中读取这些帖子的评论
  Step 5: 构建帖子+评论嵌套结构，写入 session_l3_results 表

用法:
    uv run python scripts/batch_llm_filter.py --session-id sess_20260408_abc123 --query "丽江有什么好玩的"
    uv run python scripts/batch_llm_filter.py --session-id sess_xxx --query "西安美食推荐" --min-relevance medium
    uv run python scripts/batch_llm_filter.py --session-id sess_xxx --query "成都旅游攻略" --dry-run
    uv run python scripts/batch_llm_filter.py --session-id sess_xxx --query "北京景点" --min-relevance high

说明:
    - 本脚本必须先跑 batch_scene_filter.py 生成 session_l2_* 表数据
    - 输入：session_l2_posts / session_l2_comments
    - 输出：session_l3_results（帖子+评论嵌套 JSON）
    - --min-relevance 控制哪些帖子会被写入最终结果
      选项: high / medium / low，默认 medium
    - 最终结果格式：[{post: {..., relevance_score: 0.87}, comments: [{...}, ...]}, ...]
"""

import sys
import os
import argparse
import uuid
import time
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from supabase import create_client, Client
from filter_engine.core.relevance_filter import RelevanceFilter, RelevanceLevel

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
DEFAULT_PAGE_SIZE = 200       # 每页从 filtered_posts 拉取的条数
DEFAULT_WRITE_BATCH = 50      # 每次 update 写入的条数

RELEVANCE_LEVEL_MAP = {
    "high": RelevanceLevel.HIGH,
    "medium": RelevanceLevel.MEDIUM,
    "low": RelevanceLevel.LOW,
}


# =====================================================
# 参数解析
# =====================================================
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Layer-3 LLM 语义相关性过滤：先过滤帖子，再从有效帖子里过滤评论"
    )
    p.add_argument(
        "--session-id", type=str, required=True,
        help="Session ID（由 batch_scene_filter.py 生成），格式: sess_yyyymmdd_hhmmss_xxxx",
    )
    p.add_argument(
        "--query", type=str, required=True,
        help="语义查询，如 '丽江有什么好玩的' / '成都美食推荐'",
    )
    p.add_argument(
        "--min-relevance", type=str, default="medium",
        choices=["high", "medium", "low"],
        help="最低相关性要求：high / medium / low，默认 medium",
    )
    p.add_argument(
        "--no-llm", action="store_true",
        help="禁用 LLM，只用关键词匹配判断相关性（快速模式）",
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


def fetch_session_l2_posts(
    supabase: Client,
    session_id: str,
) -> list:
    """从 session_l2_posts 拉取 Layer-2 通过的帖子"""
    resp = supabase.table("session_l2_posts").select("*").eq("session_id", session_id).execute()
    return resp.data or []


def fetch_session_l2_comments_by_post_ids(
    supabase: Client,
    session_id: str,
    post_ids: List[str],
) -> list:
    """从 session_l2_comments 中拉取指定帖子的评论"""
    if not post_ids:
        return []
    resp = supabase.table("session_l2_comments").select("*") \
        .eq("session_id", session_id) \
        .in_("content_id", post_ids) \
        .execute()
    return resp.data or []


def batch_insert_l3_results(
    supabase: Client,
    session_id: str,
    results: List[Dict],
    dry_run: bool,
) -> None:
    """批量写入 session_l3_results 表"""
    if dry_run or not results:
        return
    rows = []
    for item in results:
        rows.append({
            "session_id": session_id,
            "post_id": item["post"]["id"],
            "post_data": item["post"],
            "comments": item["comments"],
            "comment_count": len(item["comments"]),
            "query_text": item.get("query_text", ""),
        })
    
    # 批量插入
    for i in range(0, len(rows), DEFAULT_WRITE_BATCH):
        chunk = rows[i: i + DEFAULT_WRITE_BATCH]
        supabase.table("session_l3_results").insert(chunk).execute()


def update_session_metadata_l3(
    supabase: Client,
    session_id: str,
    passed_posts: int,
    dry_run: bool,
) -> None:
    """更新 session 元数据的 Layer-3 统计"""
    if dry_run:
        return
    supabase.table("session_metadata").update({
        "l3_passed_posts": passed_posts,
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("session_id", session_id).execute()


# =====================================================
# 相关性判断核心逻辑
# =====================================================
def judge_posts_relevance(
    rf: RelevanceFilter,
    query: str,
    posts: List[Dict],
    min_relevance: RelevanceLevel,
    use_llm: bool,
) -> Tuple[List[Dict], List[str]]:
    """
    对帖子做相关性判断。

    Returns:
        valid_posts: 通过相关性检验的帖子列表（含 relevance_score）
        valid_ids  : 通过的帖子 id 列表
    """
    # 拼接 title + content
    texts = [
        f"{post.get('title') or ''} {post.get('content') or ''}".strip()
        for post in posts
    ]

    result = rf.filter_by_relevance(
        query=query,
        texts=texts,
        min_relevance=min_relevance,
        use_llm_for_uncertain=use_llm,
    )

    relevance_order = {
        RelevanceLevel.HIGH: 3,
        RelevanceLevel.MEDIUM: 2,
        RelevanceLevel.LOW: 1,
        RelevanceLevel.IRRELEVANT: 0,
    }
    min_order = relevance_order[min_relevance]

    valid_posts: List[Dict] = []
    valid_ids: List[str] = []

    for post, res_dict in zip(posts, result["results"]):
        score = float(res_dict.get("score", 0.0))
        level_str = res_dict.get("relevance", "irrelevant")
        level = RelevanceLevel(level_str) if level_str in [e.value for e in RelevanceLevel] else RelevanceLevel.IRRELEVANT
        passed = relevance_order[level] >= min_order

        if passed:
            # 构建包含 relevance_score 的帖子数据
            post_with_score = {
                **post,
                "relevance_score": round(score, 3),
                "relevance_level": level_str,
            }
            valid_posts.append(post_with_score)
            valid_ids.append(post["id"])

    return valid_posts, valid_ids


# =====================================================
# 主流程
# =====================================================
def run(args) -> None:
    supabase = create_supabase()
    use_llm = not args.no_llm
    min_relevance = RELEVANCE_LEVEL_MAP[args.min_relevance]
    session_id = args.session_id

    print(f"{'='*60}")
    print(f"  Layer-3 LLM 语义过滤")
    print(f"  session_id : {session_id}")
    print(f"  query      : {args.query}")
    print(f"  min_rel    : {args.min_relevance}")
    print(f"  use_llm    : {use_llm}")
    print(f"  dry_run    : {args.dry_run}")
    print(f"{'='*60}\n")

    # 初始化 RelevanceFilter
    rf = RelevanceFilter(use_llm=use_llm)

    # --------------------------------------------------
    # Step 1-2: 从 session_l2_posts 读取并过滤帖子
    # --------------------------------------------------
    print("── Step 1-2: 帖子相关性过滤 ──")
    t0 = time.time()

    all_l2_posts = fetch_session_l2_posts(supabase, session_id)
    post_total = len(all_l2_posts)
    
    if post_total == 0:
        print(f"⚠️  session {session_id} 中没有 Layer-2 通过的帖子，请先运行 batch_scene_filter.py")
        return

    print(f"  从 session_l2_posts 读取 {post_total} 条帖子")

    # 批量判断相关性
    valid_posts, valid_post_ids = judge_posts_relevance(
        rf=rf,
        query=args.query,
        posts=all_l2_posts,
        min_relevance=min_relevance,
        use_llm=use_llm,
    )

    post_elapsed = time.time() - t0
    post_pass_rate = len(valid_post_ids) / post_total if post_total else 0
    print(
        f"\n  帖子过滤完成：总计 {post_total} 条，"
        f"通过 {len(valid_post_ids)} 条 ({post_pass_rate:.1%})，"
        f"耗时 {post_elapsed:.1f}s\n"
    )

    if not valid_post_ids:
        print("⚠️  没有帖子通过相关性检验，流程结束。")
        update_session_metadata_l3(supabase, session_id, 0, args.dry_run)
        return

    # --------------------------------------------------
    # Step 3-4: 读取有效帖子的评论，构建嵌套结构
    # --------------------------------------------------
    print("── Step 3-4: 读取评论并构建帖子+评论结构 ──")
    t1 = time.time()

    # 分批拉取评论（post_ids 太多时分批查询）
    comment_batch_size = 100
    all_comments = []
    for i in range(0, len(valid_post_ids), comment_batch_size):
        chunk_ids = valid_post_ids[i: i + comment_batch_size]
        comments = fetch_session_l2_comments_by_post_ids(supabase, session_id, chunk_ids)
        all_comments.extend(comments)

    comment_total = len(all_comments)
    print(f"  共读取 {comment_total} 条评论（来自 {len(valid_post_ids)} 个有效帖子）")

    # 按 content_id 分组评论
    comments_by_post: Dict[str, List[Dict]] = {}
    for comment in all_comments:
        content_id = comment.get("content_id")
        if content_id not in comments_by_post:
            comments_by_post[content_id] = []
        comments_by_post[content_id].append(comment)

    # 构建最终结果：帖子 + 评论嵌套
    final_results = []
    for post in valid_posts:
        post_id = post["id"]
        comments = comments_by_post.get(post_id, [])
        final_results.append({
            "post": post,
            "comments": comments,
            "query_text": args.query,
        })

    print(f"  构建 {len(final_results)} 个帖子+评论嵌套结果")

    # --------------------------------------------------
    # Step 5: 写入 session_l3_results
    # --------------------------------------------------
    print("\n── Step 5: 写入 session_l3_results ──")
    batch_insert_l3_results(supabase, session_id, final_results, args.dry_run)

    # 更新 session 元数据
    update_session_metadata_l3(supabase, session_id, len(valid_post_ids), args.dry_run)

    result_elapsed = time.time() - t1
    print(f"  写入完成，耗时 {result_elapsed:.1f}s\n")

    # --------------------------------------------------
    # 汇总
    # --------------------------------------------------
    total_elapsed = time.time() - t0
    print(f"{'='*60}")
    print(f"  ✅ Layer-3 语义过滤完成")
    print(f"  session_id : {session_id}")
    print(f"  帖子: {post_total} → {len(valid_post_ids)} 条通过 ({post_pass_rate:.1%})")
    print(f"  评论: {comment_total} 条（来自有效帖子）")
    print(f"  最终结果: {len(final_results)} 个帖子+评论对象")
    print(f"  总耗时: {total_elapsed:.1f}s")
    if args.dry_run:
        print(f"  ⚠️  dry-run 模式，数据库未写入")
    else:
        print(f"  数据已写入 session_l3_results")
        print(f"  查询结果: SELECT * FROM session_l3_results WHERE session_id = '{session_id}';")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = build_arg_parser()
    run(parser.parse_args())
