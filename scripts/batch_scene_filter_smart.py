#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Layer-2 智能场景批量过滤脚本（SmartRuleMatcher + Session 模式）

核心特性：
1. ✅ LLM 思维链分析（4步推理：意图提取 → 规则匹配 → 缺口分析 → 补充规则）
2. ✅ 场景自动识别（纯 LLM 语义识别，准确率高）
3. ✅ 动态规则组合（已有规则 + 即时生成规则）
4. ✅ 规则复用优化（仅对帖子调用 LLM，评论复用相同规则）
5. ✅ 联动过滤（帖子 → 评论）
6. ✅ Session 临时表隔离

三层架构：
  Layer-1: FilterPipeline(通用规则) → filtered_posts/comments
  Layer-2: SmartRuleMatcher(LLM思维链+场景规则) → session_l2_posts/comments  ← 本脚本
  Layer-3: LLM 语义过滤 → session_l3_results

使用示例：
  # 标准模式（自动 LLM 分析）
  uv run python scripts/batch_scene_filter_smart.py --query "过滤电商平台的广告评论"

  # 强制指定场景（跳过场景识别）
  uv run python scripts/batch_scene_filter_smart.py --query "..." --force-scenario ecommerce

  # 仅过滤有效帖子的评论
  uv run python scripts/batch_scene_filter_smart.py --query "..." --filter-comments-mode valid-posts-only

  # 保存补充规则到数据库（永久生效）
  uv run python scripts/batch_scene_filter_smart.py --query "..." --save-gap-rules

  # Dry-run 测试
  uv run python scripts/batch_scene_filter_smart.py --query "..." --dry-run

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
import json
import re
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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

# =====================================================
# 参数解析
# =====================================================
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Layer-2 智能场景规则过滤：LLM 思维链分析 + 动态规则组合"
    )
    p.add_argument(
        "--query", type=str, required=True,
        help="查询描述，如 '过滤电商广告' / '旅游攻略' / '美食推荐'，用于 LLM 意图分析",
    )
    p.add_argument(
        "--platform", type=str, default=None,
        help="只处理指定平台（如 xhs / weibo），不填则全平台",
    )
    p.add_argument(
        "--force-scenario", type=str, default=None,
        choices=["normal", "ecommerce", "news", "social", "finance", "medical", "education"],
        help="强制指定场景（跳过 LLM 场景识别）",
    )
    p.add_argument(
        "--page-size", type=int, default=DEFAULT_PAGE_SIZE,
        help=f"每页拉取条数，默认 {DEFAULT_PAGE_SIZE}",
    )
    p.add_argument(
        "--write-batch-size", type=int, default=DEFAULT_WRITE_BATCH,
        help=f"批量写入时每批条数，默认 {DEFAULT_WRITE_BATCH}（避免超时）",
    )
    p.add_argument(
        "--save-gap-rules", action="store_true",
        help="将 LLM 生成的补充规则保存到数据库（永久生效）",
    )
    p.add_argument(
        "--filter-comments-mode", type=str, default="valid-posts-only",
        choices=["all", "valid-posts-only"],
        help="评论过滤模式：all(全量评论) / valid-posts-only(仅 L2 通过帖子的评论)，默认 valid-posts-only",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="试运行，只输出统计，不写数据库",
    )
    p.add_argument(
        "--skip-layer3", action="store_true",
        help="跳过 Layer-3 语义过滤（仅执行 Layer-2）",
    )
    p.add_argument(
        "--min-relevance", type=str, default="medium",
        choices=["high", "medium", "low"],
        help="Layer-3 最低相关性要求：high / medium / low，默认 medium",
    )
    p.add_argument(
        "--no-llm-layer3", action="store_true",
        help="Layer-3 禁用 LLM，只用关键词匹配（快速模式）",
    )
    p.add_argument(
        "--auto-cleanup", action="store_true",
        help="执行前自动清理 2 小时前的旧 session 数据",
    )
    p.add_argument(
        "--cleanup-hours", type=int, default=2,
        help="自动清理超过指定小时数的 session，默认 2 小时",
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
    page_size: int,
) -> list:
    """根据帖子 ID 列表获取其评论（支持联动过滤）"""
    all_comments = []
    for i in range(0, len(post_ids), page_size):
        batch = post_ids[i:i + page_size]
        resp = supabase.table("filtered_comments").select("*").in_("content_id", batch).execute()
        all_comments.extend(resp.data or [])
    return all_comments


def insert_session_l2_posts_batch(
    supabase: Client,
    session_id: str,
    posts: List[Dict],
    matched_rules: List[str],
    dry_run: bool,
    batch_size: int = 50,  # 每批最多 50 条
) -> int:
    """批量写入 session_l2_posts（分批处理避免超时）"""
    if not posts:
        return 0
    
    rows = []
    for post in posts:
        # 生成唯一的 session-level ID（使用哈希缩短长度）
        # 组合 session_id + 原始 id，然后取 MD5 前 16 位 + 原始 id 后 8 位
        original_id = str(post.get('id', ''))
        hash_prefix = hashlib.md5(f"{session_id}_{original_id}".encode()).hexdigest()[:16]
        id_suffix = original_id[-8:] if len(original_id) >= 8 else original_id
        unique_id = f"{hash_prefix}_{id_suffix}"  # 最多 16 + 1 + 8 = 25 字符
        
        rows.append({
            "id": unique_id,  # 主键：哈希前缀 + 原始 id 后缀
            "session_id": session_id,
            "platform": post.get("platform", "xhs"),
            "type": post.get("type"),
            "url": post.get("url") or post.get("note_url"),
            "title": post.get("title"),
            "content": post.get("content", ""),
            "publish_time": post.get("publish_time"),
            # 作者信息
            "author_id": post.get("author_id"),
            "author_nickname": post.get("author_nickname"),
            "author_ip_location": post.get("author_ip_location"),
            "author_is_verified": post.get("author_is_verified", False),
            # 互动指标
            "metrics_likes": post.get("metrics_likes", 0),
            "metrics_collects": post.get("metrics_collects", 0),
            "metrics_comments": post.get("metrics_comments", 0),
            "metrics_shares": post.get("metrics_shares", 0),
            # 标签
            "tags": post.get("tags"),
            "source_keyword": post.get("source_keyword"),
            # Layer-2 元数据
            "scene_matched_rules": json.dumps(matched_rules, ensure_ascii=False),
            "filter_batch_id": post.get("filter_batch_id"),
        })
    
    if dry_run:
        print(f"  [DRY-RUN] 将写入 {len(rows)} 条帖子到 session_l2_posts")
        return len(rows)
    
    # 分批插入避免超时
    total_inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        supabase.table("session_l2_posts").insert(batch).execute()
        total_inserted += len(batch)
        print(f"  ✅ 已写入 {total_inserted}/{len(rows)} 条帖子...")
    
    return total_inserted


def insert_session_l2_comments_batch(
    supabase: Client,
    session_id: str,
    comments: List[Dict],
    matched_rules: List[str],
    dry_run: bool,
    batch_size: int = 50,  # 每批最多 50 条
) -> int:
    """批量写入 session_l2_comments（分批处理避免超时）"""
    if not comments:
        return 0
    
    rows = []
    for comment in comments:
        # 生成唯一的 session-level ID（使用哈希缩短长度）
        original_id = str(comment.get('id', ''))
        hash_prefix = hashlib.md5(f"{session_id}_{original_id}".encode()).hexdigest()[:16]
        id_suffix = original_id[-8:] if len(original_id) >= 8 else original_id
        unique_id = f"{hash_prefix}_{id_suffix}"  # 最多 25 字符
        
        rows.append({
            "id": unique_id,  # 主键：哈希前缀 + 原始 id 后缀
            "session_id": session_id,
            "content_id": comment.get("content_id"),  # 关联的帖子 ID
            "platform": comment.get("platform", "xhs"),
            "content": comment.get("content", ""),
            "publish_time": comment.get("publish_time"),
            # 作者信息
            "author_id": comment.get("author_id"),
            "author_nickname": comment.get("author_nickname"),
            "author_ip_location": comment.get("author_ip_location"),
            # 互动指标
            "metrics_likes": comment.get("metrics_likes", 0),
            "metrics_sub_comments": comment.get("metrics_sub_comments", 0),
            # 评论层级
            "parent_comment_id": comment.get("parent_comment_id"),
            "root_comment_id": comment.get("root_comment_id"),
            "reply_to_user_id": comment.get("reply_to_user_id"),
            "reply_to_user_nickname": comment.get("reply_to_user_nickname"),
            "comment_level": comment.get("comment_level", 1),
            # Layer-2 元数据
            "scene_matched_rules": json.dumps(matched_rules, ensure_ascii=False),
            "filter_batch_id": comment.get("filter_batch_id"),
        })
    
    if dry_run:
        print(f"  [DRY-RUN] 将写入 {len(rows)} 条评论到 session_l2_comments")
        return len(rows)
    
    # 分批插入避免超时
    total_inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        supabase.table("session_l2_comments").insert(batch).execute()
        total_inserted += len(batch)
        print(f"  ✅ 已写入 {total_inserted}/{len(rows)} 条评论...")
    
    return total_inserted


def update_session_metadata(
    supabase: Client,
    session_id: str,
    query_text: str,
    l1_total_posts: int,
    l1_total_comments: int,
    l2_passed_posts: int,
    l2_passed_comments: int,
    dry_run: bool,
):
    """更新 session 元数据"""
    if dry_run:
        print(f"  [DRY-RUN] 将更新 session_metadata: {session_id}")
        return
    
    supabase.table("session_metadata").insert({
        "session_id": session_id,
        "query_text": query_text,
        "l1_total_posts": l1_total_posts,
        "l1_total_comments": l1_total_comments,
        "l2_passed_posts": l2_passed_posts,
        "l2_passed_comments": l2_passed_comments,
        "l3_passed_posts": 0,  # Layer-3 会更新
        "status": "completed",
    }).execute()


# =====================================================
# Session 清理功能
# =====================================================
def cleanup_old_sessions(supabase: Client, hours: int, dry_run: bool = False) -> dict:
    """
    清理超过指定小时数的旧 session 数据
    
    Returns:
        清理统计 {"sessions": X, "l2_posts": Y, "l2_comments": Z, "l3_results": W}
    """
    from datetime import timedelta
    
    print(f"\n{'=' * 80}")
    print(f"🧹 自动清理旧 Session 数据")
    print(f"{'=' * 80}")
    print(f"⏰ 清理超过 {hours} 小时的 session")
    
    # 获取过期的 session
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff_time.isoformat()
    
    resp = supabase.table("session_metadata") \
        .select("session_id, created_at, query_text") \
        .lt("created_at", cutoff_str) \
        .execute()
    
    old_sessions = resp.data or []
    
    if not old_sessions:
        print(f"✅ 没有需要清理的旧 session")
        return {"sessions": 0, "l2_posts": 0, "l2_comments": 0, "l3_results": 0}
    
    print(f"📊 找到 {len(old_sessions)} 个过期 session")
    
    if dry_run:
        print(f"🧪 DRY-RUN: 仅显示，不实际删除")
        for session in old_sessions[:5]:  # 最多显示 5 个
            print(f"   - {session['session_id'][:16]}... ({session.get('query_text', '')[:30]}...)")
        if len(old_sessions) > 5:
            print(f"   ... 还有 {len(old_sessions) - 5} 个")
        return {"sessions": len(old_sessions), "l2_posts": 0, "l2_comments": 0, "l3_results": 0}
    
    # 执行清理
    total_stats = {
        "sessions": 0,
        "l2_posts": 0,
        "l2_comments": 0,
        "l3_results": 0,
    }
    
    for session in old_sessions:
        session_id = session["session_id"]
        
        # 删除 L2 数据
        resp = supabase.table("session_l2_posts").delete().eq("session_id", session_id).execute()
        total_stats["l2_posts"] += len(resp.data or [])
        
        resp = supabase.table("session_l2_comments").delete().eq("session_id", session_id).execute()
        total_stats["l2_comments"] += len(resp.data or [])
        
        # 删除 L3 数据
        resp = supabase.table("session_l3_results").delete().eq("session_id", session_id).execute()
        total_stats["l3_results"] += len(resp.data or [])
        
        # 删除元数据
        supabase.table("session_metadata").delete().eq("session_id", session_id).execute()
        total_stats["sessions"] += 1
    
    print(f"✅ 清理完成:")
    print(f"   - 清理 session: {total_stats['sessions']} 个")
    print(f"   - 删除 L2 帖子: {total_stats['l2_posts']} 条")
    print(f"   - 删除 L2 评论: {total_stats['l2_comments']} 条")
    print(f"   - 删除 L3 结果: {total_stats['l3_results']} 条")
    
    return total_stats


# =====================================================
# 核心过滤逻辑
# =====================================================
def apply_rules_to_contents(
    matcher: SmartRuleMatcher,
    contents: List[str],
    matched_rules: List,  # List[MatchedRuleInfo]
    gap_rules: List,      # List[GapRule]
) -> Tuple[List[bool], Dict[str, int]]:
    """
    将已有规则和补充规则应用到内容列表
    
    Returns:
        (pass_flags, stats)
        pass_flags[i] = True 表示第 i 条内容通过
        stats = {"filter_count": X, "select_count": Y, "default_pass_count": Z}
    """
    # 1. 应用 gap_rules（LLM 生成的补充规则）
    gap_filter_results = matcher.apply_gap_rules_to_content(contents, gap_rules)
    
    # 2. 应用 matched_rules（规则库中已有的规则）
    matched_filter_results = []
    if matched_rules:
        rule_manager = matcher.rule_manager
        for i, text in enumerate(contents):
            matched = False
            matched_name = None
            matched_purpose = None
            text_lower = text.lower()
            
            for rule_info in matched_rules:
                rule = rule_manager.get(rule_info.rule_id)
                if not rule:
                    continue
                
                # 应用规则
                hit = False
                try:
                    import json
                    content = json.loads(rule.content) if rule.content else []
                    if rule.type.value == "keyword":
                        hit = any(str(kw).lower() in text_lower for kw in content if kw)
                    elif rule.type.value == "regex":
                        for pat in content:
                            try:
                                if re.search(pat, text, re.IGNORECASE):
                                    hit = True
                                    break
                            except re.error:
                                pass
                except Exception:
                    pass
                
                if hit:
                    matched = True
                    matched_name = rule.name
                    matched_purpose = rule.purpose
                    break
            
            matched_filter_results.append({
                "content": text,
                "matched": matched,
                "rule": matched_name,
                "purpose": matched_purpose,
            })
    else:
        matched_filter_results = [
            {"content": text, "matched": False, "rule": None, "purpose": None}
            for text in contents
        ]
    
    # 3. 判断规则类型（是否存在 select 规则）
    has_filter_rules = any(r.purpose == "filter" for r in gap_rules)
    has_select_rules = any(r.purpose == "select" for r in gap_rules)
    
    if matched_rules:
        has_filter_rules = has_filter_rules or any(r.purpose == "filter" for r in matched_rules)
        has_select_rules = has_select_rules or any(r.purpose == "select" for r in matched_rules)
    
    # 4. 生成通过标记（综合两类规则的结果）
    pass_flags = []
    filter_count = 0
    select_count = 0
    not_selected_count = 0
    default_pass_count = 0
    
    for i, text in enumerate(contents):
        gap_result = gap_filter_results[i]
        matched_result = matched_filter_results[i]
        
        filtered = False
        selected = False
        
        # 检查 gap_rules
        if gap_result["matched"]:
            if gap_result["purpose"] == "filter":
                filtered = True
            elif gap_result["purpose"] == "select":
                selected = True
        
        # 检查 matched_rules
        if matched_result["matched"]:
            if matched_result["purpose"] == "filter":
                filtered = True
            elif matched_result["purpose"] == "select":
                selected = True
        
        # 决策逻辑（修正）
        if filtered:
            # 命中 filter 规则 → 拦截
            pass_flags.append(False)
            filter_count += 1
        elif has_select_rules:
            # 如果存在 select 规则，必须命中才能通过
            if selected:
                pass_flags.append(True)
                select_count += 1
            else:
                pass_flags.append(False)  # 未命中 select → 拦截
                not_selected_count += 1
        else:
            # 没有任何规则 → 默认通过（保守策略）
            pass_flags.append(True)
            default_pass_count += 1
    
    stats = {
        "filter_count": filter_count,
        "select_count": select_count,
        "not_selected_count": not_selected_count,
        "default_pass_count": default_pass_count,
    }
    
    return pass_flags, stats


async def apply_smart_filter(
    matcher: SmartRuleMatcher,
    query: str,
    contents: List[str],
    content_type: str,
    force_scenario: Optional[str],
) -> Tuple[SmartMatchResult, List[bool]]:
    """
    使用 SmartRuleMatcher 对内容列表进行过滤
    
    Returns:
        (match_result, pass_flags)  # pass_flags[i] = True 表示第 i 条内容通过
    """
    # Step 1: LLM 思维链分析（只需执行一次）
    print(f"\n{'=' * 60}")
    print(f"🧠 LLM 思维链分析 - {content_type}")
    print(f"{'=' * 60}")
    
    match_result = await matcher.match(query, force_scenario=force_scenario)
    
    if not match_result.success:
        print(f"❌ 智能匹配失败: {match_result.error}")
        return match_result, [False] * len(contents)
    
    # 打印分析结果
    print(f"\n✅ 场景识别: {match_result.detected_scenario} ({match_result.detected_scenario})")
    print(f"📋 匹配已有规则: {len(match_result.matched_rules)} 条")
    for rule in match_result.matched_rules:
        print(f"   - [ID:{rule.rule_id}] {rule.rule_name} ({rule.purpose})")
    
    print(f"🔧 LLM 生成补充规则: {len(match_result.gap_rules)} 条")
    for gap in match_result.gap_rules:
        # 显示规则的实际内容（前 5 个关键词）
        content_preview = gap.content[:5] if len(gap.content) <= 5 else gap.content[:5] + ["..."]
        print(f"   - {gap.name} ({gap.purpose}) - {len(gap.content)} 个关键词: {content_preview}")
    
    print(f"🎯 需要 Layer-3 语义过滤: {match_result.needs_llm_filter}")
    if match_result.needs_llm_filter:
        print(f"   原因: {match_result.llm_filter_reason}")
    
    # ⚠️  关键检查：如果没有任何规则，给出警告
    if not match_result.matched_rules and not match_result.gap_rules:
        print(f"\n⚠️  警告: LLM 未匹配到已有规则，也未生成补充规则！")
        print(f"   这将导致所有内容默认通过（通过率 ~100%）")
        print(f"   建议检查:")
        print(f"   1. Query 是否明确: '{query}'")
        print(f"   2. 规则库是否包含相关场景规则: {match_result.detected_scenario}")
        print(f"   3. LLM 原始响应:\n{match_result.raw_response[:500] if match_result.raw_response else 'None'}...")

    
    # Step 2: 应用规则到内容列表
    print(f"\n📊 应用规则到 {len(contents)} 条{content_type}...")
    
    pass_flags, stats = apply_rules_to_contents(
        matcher, contents, match_result.matched_rules, match_result.gap_rules
    )
    
    pass_count = sum(pass_flags)
    print(f"✅ 通过: {pass_count} / {len(contents)} ({pass_count/len(contents)*100:.1f}%)")
    print(f"   - 被 filter 规则拦截: {stats['filter_count']} 条")
    print(f"   - 被 select 规则保留: {stats['select_count']} 条")
    print(f"   - 未命中 select 规则（被拦截）: {stats.get('not_selected_count', 0)} 条")
    print(f"   - 无规则命中（默认通过）: {stats['default_pass_count']} 条")
    
    if stats['default_pass_count'] > len(contents) * 0.8:
        print(f"\n⚠️  警告: {stats['default_pass_count']/len(contents)*100:.1f}% 内容无规则命中！")
        print(f"   可能原因: LLM 未生成补充规则 或 规则库缺少相关规则")
        print(f"   建议: 使用 --save-gap-rules 保存补充规则，或手动添加规则")
    
    return match_result, pass_flags

    
    return match_result, pass_flags


async def process_layer2_filter(
    supabase: Client,
    matcher: SmartRuleMatcher,
    query: str,
    platform: Optional[str],
    force_scenario: Optional[str],
    page_size: int,
    write_batch_size: int,
    filter_comments_mode: str,
    save_gap_rules: bool,
    dry_run: bool,
) -> str:
    """
    Layer-2 核心处理流程
    
    Returns:
        session_id
    """
    session_id = str(uuid.uuid4())
    print(f"\n🆔 Session ID: {session_id}")
    
    # =====================================================
    # Step 1: 处理帖子
    # =====================================================
    print(f"\n{'=' * 80}")
    print(f"📝 STEP 1: 处理帖子 (filtered_posts → session_l2_posts)")
    print(f"{'=' * 80}")
    
    all_posts = []
    page = 0
    while True:
        posts = fetch_filtered_posts_page(supabase, page, page_size, platform)
        if not posts:
            break
        all_posts.extend(posts)
        page += 1
    
    print(f"📊 从 Layer-1 读取帖子: {len(all_posts)} 条")
    
    if not all_posts:
        print("⚠️  无帖子数据，跳过")
        return session_id
    
    # 执行智能过滤
    # 综合 title + content + tags 作为匹配内容
    post_contents = []
    for p in all_posts:
        parts = []
        if p.get("title"):
            parts.append(p.get("title"))
        if p.get("content"):
            parts.append(p.get("content"))
        if p.get("tags"):
            # tags 可能是 list 或 JSON 字符串
            tags = p.get("tags")
            if isinstance(tags, list):
                parts.extend(tags)
            elif isinstance(tags, str):
                try:
                    import json
                    tags_list = json.loads(tags)
                    if isinstance(tags_list, list):
                        parts.extend(tags_list)
                except:
                    parts.append(tags)
        # 用空格连接所有部分
        post_contents.append(" ".join(parts))
    
    match_result_post, post_pass_flags = await apply_smart_filter(
        matcher, query, post_contents, "帖子", force_scenario
    )
    
    # 写入通过的帖子
    passed_posts = [p for p, flag in zip(all_posts, post_pass_flags) if flag]
    matched_rule_names = [r.rule_name for r in match_result_post.matched_rules]
    gap_rule_names = [g.name for g in match_result_post.gap_rules]
    all_rule_names = matched_rule_names + gap_rule_names
    
    l2_passed_posts_count = insert_session_l2_posts_batch(
        supabase, session_id, passed_posts, all_rule_names, dry_run, write_batch_size
    )
    
    print(f"\n✅ Layer-2 帖子通过: {l2_passed_posts_count} / {len(all_posts)}")
    
    # =====================================================
    # Step 2: 处理评论（复用帖子的规则，不再调用 LLM）
    # =====================================================
    print(f"\n{'=' * 80}")
    print(f"💬 STEP 2: 处理评论 (filtered_comments → session_l2_comments)")
    print(f"{'=' * 80}")
    
    if filter_comments_mode == "valid-posts-only":
        print(f"🔗 联动模式: 仅过滤 Layer-2 通过的 {len(passed_posts)} 条帖子的评论")
        passed_post_ids = [p.get("id") for p in passed_posts if p.get("id")]
        all_comments = fetch_filtered_comments_by_post_ids(supabase, passed_post_ids, page_size)
    else:
        print(f"🌐 全量模式: 过滤所有 Layer-1 通过的评论")
        all_comments = []
        page = 0
        while True:
            comments = fetch_filtered_comments_page(supabase, page, page_size, platform)
            if not comments:
                break
            all_comments.extend(comments)
            page += 1
    
    print(f"📊 待过滤评论: {len(all_comments)} 条")
    
    l2_passed_comments_count = 0
    if not all_comments:
        print("⚠️  无评论数据，跳过")
    else:
        # 复用帖子分析得到的规则（不再调用 LLM）
        print(f"\n🔄 复用帖子分析的规则")
        print(f"   - 已有规则: {len(match_result_post.matched_rules)} 条")
        print(f"   - 补充规则: {len(match_result_post.gap_rules)} 条")
        
        # 评论只有 content 字段（无 title/tags）
        comment_contents = [c.get("content", "") for c in all_comments]
        
        # 应用相同的规则到评论
        print(f"\n📊 应用规则到 {len(comment_contents)} 条评论...")
        comment_pass_flags, comment_stats = apply_rules_to_contents(
            matcher, comment_contents,
            match_result_post.matched_rules,
            match_result_post.gap_rules
        )
        
        pass_count = sum(comment_pass_flags)
        print(f"✅ 通过: {pass_count} / {len(comment_contents)} ({pass_count/len(comment_contents)*100:.1f}%)")
        print(f"   - 被 filter 规则拦截: {comment_stats['filter_count']} 条")
        print(f"   - 被 select 规则保留: {comment_stats['select_count']} 条")
        print(f"   - 无规则命中（默认通过）: {comment_stats['default_pass_count']} 条")
        
        if comment_stats['default_pass_count'] > len(comment_contents) * 0.8:
            print(f"\n⚠️  警告: {comment_stats['default_pass_count']/len(comment_contents)*100:.1f}% 评论无规则命中！")
        
        # 写入通过的评论
        passed_comments = [c for c, flag in zip(all_comments, comment_pass_flags) if flag]
        l2_passed_comments_count = insert_session_l2_comments_batch(
            supabase, session_id, passed_comments, all_rule_names, dry_run, write_batch_size
        )
        
        print(f"\n✅ Layer-2 评论通过: {l2_passed_comments_count} / {len(all_comments)}")
    
    # =====================================================
    # Step 3: 保存补充规则（可选）
    # =====================================================
    if save_gap_rules and match_result_post.suggest_save:
        print(f"\n{'=' * 80}")
        print(f"💾 STEP 3: 保存补充规则到数据库")
        print(f"{'=' * 80}")
        
        saved_ids = matcher.save_suggested_rules(match_result_post.suggest_save)
        print(f"✅ 成功保存 {len(saved_ids)} 条规则: {saved_ids}")
    
    # =====================================================
    # Step 4: 更新元数据
    # =====================================================
    update_session_metadata(
        supabase,
        session_id,
        query_text=query,
        l1_total_posts=len(all_posts),
        l1_total_comments=len(all_comments) if all_comments else 0,
        l2_passed_posts=l2_passed_posts_count,
        l2_passed_comments=l2_passed_comments_count,
        dry_run=dry_run,
    )
    
    return session_id


# =====================================================
# 主函数
# =====================================================
async def main_async():
    parser = build_arg_parser()
    args = parser.parse_args()
    
    print(f"\n{'=' * 80}")
    print(f"🚀 Layer-2 智能场景批量过滤 (SmartRuleMatcher)")
    print(f"{'=' * 80}")
    print(f"🔍 Query: {args.query}")
    print(f"📱 Platform: {args.platform or '全平台'}")
    print(f"🎯 Force Scenario: {args.force_scenario or '自动识别'}")
    print(f"� 批量写入大小: {args.write_batch_size} 条/批")
    print(f"�💾 保存补充规则: {'是' if args.save_gap_rules else '否'}")
    print(f"💬 评论过滤模式: {args.filter_comments_mode}")
    print(f"🧪 Dry-run: {'是' if args.dry_run else '否'}")
    
    # 初始化
    supabase = create_supabase()
    matcher = SmartRuleMatcher()
    
    # 自动清理旧 session（可选）
    if args.auto_cleanup:
        cleanup_old_sessions(supabase, args.cleanup_hours, dry_run=args.dry_run)
    
    # 执行过滤
    session_id = await process_layer2_filter(
        supabase=supabase,
        matcher=matcher,
        query=args.query,
        platform=args.platform,
        force_scenario=args.force_scenario,
        page_size=args.page_size,
        write_batch_size=args.write_batch_size,
        filter_comments_mode=args.filter_comments_mode,
        save_gap_rules=args.save_gap_rules,
        dry_run=args.dry_run,
    )
    
    print(f"\n{'=' * 80}")
    print(f"✅ Layer-2 过滤完成！")
    print(f"{'=' * 80}")
    print(f"🆔 Session ID: {session_id}")
    
    # =====================================================
    # 自动衔接 Layer-3 语义过滤
    # =====================================================
    if not args.skip_layer3 and not args.dry_run:
        print(f"\n{'=' * 80}")
        print(f"� 自动启动 Layer-3 语义相关性过滤")
        print(f"{'=' * 80}")
        
        # 导入 Layer-3 模块
        from filter_engine.core.relevance_filter import RelevanceFilter, RelevanceLevel
        
        # 初始化相关性过滤器
        use_llm_layer3 = not args.no_llm_layer3
        min_relevance_map = {
            "high": RelevanceLevel.HIGH,
            "medium": RelevanceLevel.MEDIUM,
            "low": RelevanceLevel.LOW,
        }
        min_relevance = min_relevance_map[args.min_relevance]
        
        rf = RelevanceFilter(use_llm=use_llm_layer3)
        
        print(f"📊 Layer-3 参数:")
        print(f"   - Query: {args.query}")
        print(f"   - 最低相关性: {args.min_relevance}")
        print(f"   - 使用 LLM: {use_llm_layer3}")
        
        # 执行 Layer-3 过滤
        await run_layer3_filter(
            supabase=supabase,
            rf=rf,
            session_id=session_id,
            query=args.query,
            min_relevance=min_relevance,
            use_llm=use_llm_layer3,
        )
    elif args.skip_layer3:
        print(f"\n⏭️  跳过 Layer-3（使用 --skip-layer3 参数）")
        print(f"\n📌 手动执行 Layer-3:")
        print(f"   uv run python scripts/batch_llm_filter.py --session-id {session_id} --query \"{args.query}\"")
    else:
        print(f"\n⏭️  Dry-run 模式，跳过 Layer-3")
    
    print(f"\n📊 查询结果:")
    print(f"   SELECT * FROM session_l2_posts WHERE session_id = '{session_id}';")
    print(f"   SELECT * FROM session_l2_comments WHERE session_id = '{session_id}';")
    print(f"   SELECT * FROM session_l3_results WHERE session_id = '{session_id}';")
    print(f"   SELECT * FROM session_metadata WHERE session_id = '{session_id}';")


async def run_layer3_filter(
    supabase: Client,
    rf,  # RelevanceFilter
    session_id: str,
    query: str,
    min_relevance,  # RelevanceLevel
    use_llm: bool,
) -> None:
    """
    执行 Layer-3 语义相关性过滤
    """
    import time
    from typing import Dict
    
    print(f"\n{'─' * 60}")
    print(f"📝 Step 1: 读取 Layer-2 通过的帖子")
    print(f"{'─' * 60}")
    
    t0 = time.time()
    
    # 读取 Layer-2 通过的帖子（分页读取，突破 1000 条限制）
    all_l2_posts = []
    page_size = 1000
    offset = 0
    
    while True:
        resp = supabase.table("session_l2_posts") \
            .select("*") \
            .eq("session_id", session_id) \
            .range(offset, offset + page_size - 1) \
            .execute()
        
        data = resp.data or []
        if not data:
            break
        
        all_l2_posts.extend(data)
        
        # 如果返回数据少于 page_size，说明已经是最后一页
        if len(data) < page_size:
            break
        
        offset += page_size
    
    post_total = len(all_l2_posts)
    
    if post_total == 0:
        print(f"⚠️  Session {session_id} 中没有 Layer-2 通过的帖子")
        return
    
    print(f"✅ 读取到 {post_total} 条帖子")
    
    # 拼接 title + content 作为相关性判断文本
    texts = [
        f"{post.get('title') or ''} {post.get('content') or ''}".strip()
        for post in all_l2_posts
    ]
    
    print(f"\n{'─' * 60}")
    print(f"🧠 Step 2: 相关性判断（完全依赖 LLM）")
    print(f"{'─' * 60}")
    
    # 批量判断相关性（使用 LLM Only 模式）
    result = rf.filter_by_relevance(
        query=query,
        texts=texts,
        min_relevance=min_relevance,
        use_llm_for_uncertain=use_llm,
        llm_only=True,  # Layer-3 完全依赖 LLM
    )
    
    # 定义相关性级别顺序
    from filter_engine.core.relevance_filter import RelevanceLevel
    relevance_order = {
        RelevanceLevel.HIGH: 3,
        RelevanceLevel.MEDIUM: 2,
        RelevanceLevel.LOW: 1,
        RelevanceLevel.IRRELEVANT: 0,
    }
    min_order = relevance_order[min_relevance]
    
    # 收集通过的帖子
    valid_posts = []
    valid_post_ids = []
    
    for post, res_dict in zip(all_l2_posts, result["results"]):
        score = float(res_dict.get("score", 0.0))
        level_str = res_dict.get("relevance", "irrelevant")
        level = RelevanceLevel(level_str) if level_str in [e.value for e in RelevanceLevel] else RelevanceLevel.IRRELEVANT
        passed = relevance_order[level] >= min_order
        
        if passed:
            post_with_score = {
                **post,
                "relevance_score": round(score, 3),
                "relevance_level": level_str,
            }
            valid_posts.append(post_with_score)
            valid_post_ids.append(post["id"])
    
    post_elapsed = time.time() - t0
    post_pass_rate = len(valid_post_ids) / post_total if post_total else 0
    
    print(f"✅ 帖子过滤完成: {post_total} → {len(valid_post_ids)} 条通过 ({post_pass_rate:.1%})")
    print(f"   - 耗时: {post_elapsed:.1f}s")
    
    if not valid_post_ids:
        print("⚠️  没有帖子通过相关性检验，Layer-3 结束")
        # 更新元数据
        supabase.table("session_metadata").update({
            "l3_passed_posts": 0,
            "status": "completed",
        }).eq("session_id", session_id).execute()
        return
    
    print(f"\n{'─' * 60}")
    print(f"💬 Step 3: 读取有效帖子的评论")
    print(f"{'─' * 60}")
    
    # 分批读取评论
    comment_batch_size = 100
    all_comments = []
    for i in range(0, len(valid_post_ids), comment_batch_size):
        chunk_ids = valid_post_ids[i: i + comment_batch_size]
        resp = supabase.table("session_l2_comments").select("*") \
            .eq("session_id", session_id) \
            .in_("content_id", chunk_ids) \
            .execute()
        all_comments.extend(resp.data or [])
    
    comment_total = len(all_comments)
    print(f"✅ 读取到 {comment_total} 条评论（来自 {len(valid_post_ids)} 个有效帖子）")
    
    # 按 content_id 分组评论
    comments_by_post: Dict[str, list] = {}
    for comment in all_comments:
        content_id = comment.get("content_id")
        if content_id not in comments_by_post:
            comments_by_post[content_id] = []
        comments_by_post[content_id].append(comment)
    
    # 构建最终结果
    final_results = []
    for post in valid_posts:
        post_id = post["id"]
        comments = comments_by_post.get(post_id, [])
        final_results.append({
            "post": post,
            "comments": comments,
            "query_text": query,
        })
    
    print(f"✅ 构建 {len(final_results)} 个帖子+评论嵌套结果")
    
    print(f"\n{'─' * 60}")
    print(f"💾 Step 4: 写入 session_l3_results")
    print(f"{'─' * 60}")
    
    # 批量写入（使用 upsert 避免主键冲突）
    rows = []
    for item in final_results:
        rows.append({
            "session_id": session_id,
            "post_id": item["post"]["id"],
            "post_data": item["post"],
            "comments": item["comments"],
            "comment_count": len(item["comments"]),
            "query_text": query,
        })
    
    # 分批 upsert
    batch_size = 50
    total_written = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i: i + batch_size]
        supabase.table("session_l3_results").upsert(chunk).execute()
        total_written += len(chunk)
        if len(rows) > batch_size:
            print(f"  ✅ 已写入 {total_written}/{len(rows)} 条...")
    
    print(f"✅ 写入完成: {len(rows)} 条记录")
    
    # 更新 session 元数据
    from datetime import datetime, timezone
    supabase.table("session_metadata").update({
        "l3_passed_posts": len(valid_post_ids),
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("session_id", session_id).execute()
    
    total_elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"✅ Layer-3 语义过滤完成")
    print(f"{'=' * 60}")
    print(f"   - 帖子: {post_total} → {len(valid_post_ids)} 条通过 ({post_pass_rate:.1%})")
    print(f"   - 评论: {comment_total} 条（来自有效帖子）")
    print(f"   - 总耗时: {total_elapsed:.1f}s")
    print(f"   - 数据已写入 session_l3_results")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
