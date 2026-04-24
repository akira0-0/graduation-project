# -*- coding: utf-8 -*-
"""
过滤 API 公共工具函数

提取 complete_filter / auto_filter 中的重复逻辑：
- fetch_posts_from_db      分页读取 filtered_posts
- run_layer2               Layer-2 场景规则过滤
- run_layer3               Layer-3 LLM 相关性过滤
- fetch_comments           批量读取评论
- save_session             Session 写库（三张表）
"""
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .core.relevance_filter import RelevanceLevel

# ── 相关性等级映射（全局复用）──────────────────────────────────────────────
RELEVANCE_MAP = {
    "high": RelevanceLevel.HIGH,
    "medium": RelevanceLevel.MEDIUM,
    "low": RelevanceLevel.LOW,
}

RELEVANCE_ORDER = {
    RelevanceLevel.HIGH: 3,
    RelevanceLevel.MEDIUM: 2,
    RelevanceLevel.LOW: 1,
    RelevanceLevel.IRRELEVANT: 0,
}


# ── 公共函数 ────────────────────────────────────────────────────────────────

def fetch_posts_from_db(
    supabase,
    platform: Optional[str] = None,
    max_posts: int = 500,
) -> Tuple[List[dict], float]:
    """
    分页读取 filtered_posts 表

    Returns:
        (posts, elapsed_seconds)
    """
    t0 = time.time()
    query_builder = supabase.table("filtered_posts").select("*")
    if platform:
        query_builder = query_builder.eq("platform", platform)

    posts: List[dict] = []
    page_size = 1000
    offset = 0

    while len(posts) < max_posts:
        resp = query_builder.range(offset, offset + page_size - 1).execute()
        data = resp.data or []
        if not data:
            break
        posts.extend(data)
        offset += page_size
        if len(data) < page_size:
            break

    posts = posts[:max_posts]
    return posts, time.time() - t0


async def run_layer2(
    matcher,
    query: str,
    posts: List[dict],
    force_scenario: Optional[str] = None,
) -> Tuple[List[dict], object, float]:
    """
    Layer-2 场景规则过滤

    Returns:
        (passed_posts, match_result, elapsed_seconds)
    """
    from .api import apply_rules_to_contents  # 避免循环导入

    t0 = time.time()
    match_result = await matcher.match(query, force_scenario=force_scenario)

    post_contents = [
        f"{p.get('title') or ''} {p.get('content') or ''} {' '.join(p.get('tags') or [])}".strip()
        for p in posts
    ]
    pass_flags, _ = apply_rules_to_contents(
        matcher, post_contents, match_result.matched_rules, match_result.gap_rules
    )

    passed = [p for p, flag in zip(posts, pass_flags) if flag]
    return passed, match_result, time.time() - t0


def run_layer3(
    sf,
    query: str,
    posts: List[dict],
    min_relevance: str = "medium",
    llm_only: bool = True,
    min_score: Optional[float] = None,
) -> Tuple[List[dict], List[str], float]:
    """
    Layer-3 LLM 相关性过滤

    Returns:
        (valid_posts_with_score, valid_post_ids, elapsed_seconds)
    """
    t0 = time.time()
    min_rel = RELEVANCE_MAP.get(min_relevance, RelevanceLevel.MEDIUM)
    min_order = RELEVANCE_ORDER[min_rel]

    post_texts = [
        f"{p.get('title') or ''} {p.get('content') or ''}".strip()
        for p in posts
    ]

    rel_result = sf.relevance_filter.filter_by_relevance(
        query=query,
        texts=post_texts,
        min_relevance=min_rel,
        use_llm_for_uncertain=True,
        llm_only=llm_only,
    )

    valid_posts: List[dict] = []
    valid_ids: List[str] = []

    for post, res in zip(posts, rel_result["results"]):
        score = float(res.get("score", 0.0))
        level_str = res.get("relevance", "irrelevant")
        try:
            level = RelevanceLevel(level_str)
        except ValueError:
            level = RelevanceLevel.IRRELEVANT

        if RELEVANCE_ORDER[level] >= min_order:
            if min_score is None or score >= min_score:
                valid_posts.append({**post, "relevance_score": round(score, 3), "relevance_level": level_str})
                valid_ids.append(post["id"])

    return valid_posts, valid_ids, time.time() - t0


def fetch_comments(
    supabase,
    post_ids: List[str],
    batch_size: int = 100,
) -> Tuple[Dict[str, List[dict]], int, float]:
    """
    批量读取 filtered_comments 并按 content_id 分组

    Returns:
        (comments_by_post_id, total_count, elapsed_seconds)
    """
    t0 = time.time()
    all_comments: List[dict] = []

    for i in range(0, len(post_ids), batch_size):
        chunk = post_ids[i:i + batch_size]
        resp = supabase.table("filtered_comments").select("*").in_("content_id", chunk).execute()
        all_comments.extend(resp.data or [])

    grouped: Dict[str, List[dict]] = {}
    for c in all_comments:
        cid = c.get("content_id")
        grouped.setdefault(cid, []).append(c)

    return grouped, len(all_comments), time.time() - t0


def save_session(
    supabase,
    session_id: str,
    query: str,
    scenario: str,
    stats: dict,
    l2_posts: List[dict],
    l3_posts: List[dict],
    batch_size: int = 100,
) -> float:
    """
    将 Session 结果写入三张表：
      - session_metadata
      - session_l2_results
      - session_l3_results

    Returns:
        elapsed_seconds
    """
    t0 = time.time()

    # ── session_metadata ────────────────────────────────────────────────────
    supabase.table("session_metadata").insert({
        "session_id": session_id,
        "query": query,
        "scenario": scenario,
        "l1_total_posts": stats.get("l1_total_posts", 0),
        "l2_passed_posts": stats.get("l2_passed_posts", 0),
        "l3_passed_posts": stats.get("l3_passed_posts", 0),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # ── session_l2_results ──────────────────────────────────────────────────
    if l2_posts:
        rows = [
            {
                "session_id": session_id,
                "post_id": p["id"],
                "title": p.get("title"),
                "content": p.get("content"),
                "platform": p.get("platform"),
            }
            for p in l2_posts
        ]
        _batch_insert(supabase, "session_l2_results", rows, batch_size)

    # ── session_l3_results ──────────────────────────────────────────────────
    if l3_posts:
        rows = [
            {
                "session_id": session_id,
                "post_id": p["id"],
                "relevance_score": p.get("relevance_score"),
                "relevance_level": p.get("relevance_level"),
            }
            for p in l3_posts
        ]
        _batch_insert(supabase, "session_l3_results", rows, batch_size)

    return time.time() - t0


# ── 内部工具 ────────────────────────────────────────────────────────────────

def _batch_insert(supabase, table: str, rows: List[dict], batch_size: int = 100):
    """分批插入数据库"""
    for i in range(0, len(rows), batch_size):
        supabase.table(table).insert(rows[i:i + batch_size]).execute()


def make_session_id() -> str:
    """生成唯一 Session ID"""
    import uuid
    return f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def print_banner(title: str, **kv):
    """打印统一格式的任务头"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")
    for k, v in kv.items():
        print(f"  {k}: {v}")
    print(f"{'='*80}\n")


def print_summary(stats: dict, perf: dict, session_id: Optional[str] = None):
    """打印统一格式的任务摘要"""
    l1 = stats.get("l1_total_posts", 0)
    l2 = stats.get("l2_passed_posts", 0)
    l3 = stats.get("l3_passed_posts", 0)
    ret = stats.get("final_returned", l3)

    print(f"\n{'='*80}")
    print(f"✅ 过滤完成")
    print(f"  L1 → L2 → L3 → 返回: {l1} → {l2} → {l3} → {ret}")
    print(f"  耗时: L1={perf.get('layer1', 0):.1f}s  L2={perf.get('layer2', 0):.1f}s  "
          f"L3={perf.get('layer3', 0):.1f}s  总计={perf.get('total', 0):.1f}s")
    if session_id:
        print(f"  Session: {session_id}")
    print(f"{'='*80}\n")
