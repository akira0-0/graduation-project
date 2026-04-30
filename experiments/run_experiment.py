# -*- coding: utf-8 -*-
"""
4.3 对比实验运行器
==================
对同一数据集分别运行三种过滤方法，记录每条帖子的判断结果和耗时。

三组方法：
  Method A  纯规则过滤   只走 SmartRuleMatcher（L2）规则匹配，跳过 L3 LLM
  Method B  纯LLM过滤    跳过 L2 规则，全量帖子直送 L3 LLM 相关性判断
  Method C  协同系统     完整 L2（规则过滤）→ L3（LLM精判）流水线

用法：
    uv run python experiments/run_experiment.py \\
        --dataset experiments/data/dataset_丽江旅游攻略_xxx.json \\
        --query "丽江旅游攻略"
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


# ─────────────────────────────────────────────────────────────────────────────
# 公共工具
# ─────────────────────────────────────────────────────────────────────────────

def apply_rules_to_posts(matcher, query: str, posts: list, force_scenario=None):
    """
    调用 SmartRuleMatcher，对帖子列表执行 L2 规则匹配。
    返回 (passed_posts, match_result, elapsed)
    """
    import asyncio
    from filter_engine.api import apply_rules_to_contents

    async def _run():
        t0 = time.time()
        match_result = await matcher.match(query, force_scenario=force_scenario)
        contents = [
            f"{p.get('title') or ''} {p.get('content') or ''} {' '.join(p.get('tags') or [])}".strip()
            for p in posts
        ]
        pass_flags, _ = apply_rules_to_contents(
            matcher, contents, match_result.matched_rules, match_result.gap_rules
        )
        passed = [p for p, flag in zip(posts, pass_flags) if flag]
        return passed, match_result, time.time() - t0

    return asyncio.run(_run())


def apply_llm_relevance(sf, query: str, posts: list, min_relevance: str = "medium"):
    """
    调用 SmartDataFilter（L3），对帖子列表做 LLM 相关性过滤。
    返回 (passed_posts, elapsed)
    """
    from filter_engine.core.relevance_filter import RelevanceLevel

    RELEVANCE_MAP = {
        "high": RelevanceLevel.HIGH,
        "medium": RelevanceLevel.MEDIUM,
        "low": RelevanceLevel.LOW,
    }
    RELEVANCE_ORDER = {RelevanceLevel.HIGH: 3, RelevanceLevel.MEDIUM: 2,
                       RelevanceLevel.LOW: 1, RelevanceLevel.IRRELEVANT: 0}
    min_rel = RELEVANCE_MAP.get(min_relevance, RelevanceLevel.MEDIUM)
    min_order = RELEVANCE_ORDER[min_rel]

    texts = [f"{p.get('title') or ''} {p.get('content') or ''}".strip() for p in posts]

    t0 = time.time()
    result = sf.relevance_filter.filter_by_relevance(
        query=query,
        texts=texts,
        min_relevance=min_rel,
        use_llm_for_uncertain=True,
        llm_only=True,
    )
    elapsed = time.time() - t0

    passed = []
    for post, res_dict in zip(posts, result["results"]):
        level_str = res_dict.get("relevance", "irrelevant")
        try:
            level = RelevanceLevel(level_str)
        except ValueError:
            level = RelevanceLevel.IRRELEVANT
        if RELEVANCE_ORDER[level] >= min_order:
            passed.append({**post, "relevance_score": res_dict.get("score", 0.0),
                            "relevance_level": level_str})

    return passed, elapsed


def post_ids(posts: list) -> set:
    return {p["id"] for p in posts}


# ─────────────────────────────────────────────────────────────────────────────
# 方法 A：纯规则过滤
# ─────────────────────────────────────────────────────────────────────────────

def method_a_rule_only(matcher, query: str, posts: list) -> Dict:
    """只走 L2 规则，不调用任何 LLM（匹配阶段 LLM 用于理解 query，但不做内容语义判断）"""
    print("\n[方法A] 纯规则过滤...")
    t_start = time.time()

    passed, match_result, t_l2 = apply_rules_to_posts(matcher, query, posts)
    total_elapsed = time.time() - t_start

    return {
        "method": "A_rule_only",
        "passed_ids": [p["id"] for p in passed],
        "passed_count": len(passed),
        "input_count": len(posts),
        "scenario": match_result.detected_scenario,
        "matched_rules": len(match_result.matched_rules),
        "gap_rules": len(match_result.gap_rules),
        "llm_calls": 1,                   # 只有场景识别 1 次 LLM 调用
        "elapsed_total": round(total_elapsed, 3),
        "elapsed_l2": round(t_l2, 3),
        "elapsed_l3": 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 方法 B：纯 LLM 过滤
# ─────────────────────────────────────────────────────────────────────────────

def method_b_llm_only(sf, query: str, posts: list, min_relevance: str = "medium") -> Dict:
    """跳过 L2 规则，全量帖子直送 L3 LLM 相关性判断"""
    print("\n[方法B] 纯LLM过滤...")
    t_start = time.time()

    passed, t_l3 = apply_llm_relevance(sf, query, posts, min_relevance)
    total_elapsed = time.time() - t_start

    # LLM 调用次数估算：每批约 10 条，ceiling
    import math
    estimated_llm_calls = math.ceil(len(posts) / 10)

    return {
        "method": "B_llm_only",
        "passed_ids": [p["id"] for p in passed],
        "passed_count": len(passed),
        "input_count": len(posts),
        "llm_calls": estimated_llm_calls,
        "elapsed_total": round(total_elapsed, 3),
        "elapsed_l2": 0,
        "elapsed_l3": round(t_l3, 3),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 方法 C：协同系统（L2 规则 → L3 LLM）
# ─────────────────────────────────────────────────────────────────────────────

def method_c_hybrid(matcher, sf, query: str, posts: list, min_relevance: str = "medium") -> Dict:
    """完整 L2 → L3 流水线"""
    print("\n[方法C] 协同过滤系统...")
    t_start = time.time()

    # L2 规则过滤
    l2_passed, match_result, t_l2 = apply_rules_to_posts(matcher, query, posts)
    print(f"  L2 通过: {len(l2_passed)}/{len(posts)}")

    # L3 LLM 精判
    l3_passed, t_l3 = apply_llm_relevance(sf, query, l2_passed, min_relevance)
    print(f"  L3 通过: {len(l3_passed)}/{len(l2_passed)}")

    total_elapsed = time.time() - t_start

    import math
    estimated_llm_calls = 1 + math.ceil(len(l2_passed) / 10)  # 场景识别 + 相关性判断

    return {
        "method": "C_hybrid",
        "passed_ids": [p["id"] for p in l3_passed],
        "passed_count": len(l3_passed),
        "l2_passed_count": len(l2_passed),
        "input_count": len(posts),
        "scenario": match_result.detected_scenario,
        "matched_rules": len(match_result.matched_rules),
        "gap_rules": len(match_result.gap_rules),
        "llm_calls": estimated_llm_calls,
        "elapsed_total": round(total_elapsed, 3),
        "elapsed_l2": round(t_l2, 3),
        "elapsed_l3": round(t_l3, 3),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="运行三组对比实验")
    parser.add_argument("--dataset", required=True, help="标注数据集 JSON 文件路径")
    parser.add_argument("--query", required=True, help="实验查询")
    parser.add_argument("--min-relevance", default="medium", help="L3 最低相关性阈值")
    parser.add_argument("--methods", default="ABC", help="运行哪些方法，如 AC 只跑A和C")
    parser.add_argument("--output", default=None, help="结果输出路径")
    args = parser.parse_args()

    # ── 加载数据集 ────────────────────────────────────────────────────
    print(f"📂 加载数据集: {args.dataset}")
    with open(args.dataset, encoding="utf-8") as f:
        ds = json.load(f)

    posts = ds["data"]
    # 只取已标注的样本
    labeled_posts = [p for p in posts if p["label"] != -1]
    ground_truth = {p["id"]: p["label"] for p in labeled_posts}

    print(f"  总量={len(posts)} | 已标注={len(labeled_posts)}")
    print(f"  正例={sum(v==1 for v in ground_truth.values())} | "
          f"负例={sum(v==0 for v in ground_truth.values())}\n")

    if not labeled_posts:
        print("❌ 无已标注数据，请先运行 build_dataset.py")
        return

    # ── 初始化模型 ─────────────────────────────────────────────────────
    from filter_engine.config import settings
    from filter_engine.rules import RuleManager
    from filter_engine.llm.smart_matcher import SmartRuleMatcher
    from filter_engine.core.relevance_filter import SmartDataFilter

    rule_manager = RuleManager(settings.DATABASE_PATH)
    matcher = SmartRuleMatcher(rule_manager=rule_manager, db_path=settings.DATABASE_PATH)
    sf = SmartDataFilter(use_llm=True)

    results = {}

    # ── 运行各方法 ─────────────────────────────────────────────────────
    if "A" in args.methods:
        results["A"] = method_a_rule_only(matcher, args.query, labeled_posts)

    if "B" in args.methods:
        results["B"] = method_b_llm_only(sf, args.query, labeled_posts, args.min_relevance)

    if "C" in args.methods:
        results["C"] = method_c_hybrid(matcher, sf, args.query, labeled_posts, args.min_relevance)

    # ── 附加 ground_truth 到结果 ──────────────────────────────────────
    for key, res in results.items():
        res["ground_truth"] = ground_truth

    # ── 保存原始结果 ───────────────────────────────────────────────────
    output = args.output or str(
        ROOT / "experiments" / "results" /
        f"experiment_{args.query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump({
            "query": args.query,
            "dataset": args.dataset,
            "min_relevance": args.min_relevance,
            "run_at": datetime.now().isoformat(),
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 实验结果已保存: {output}")
    print("👉 运行 python experiments/evaluate.py --result <上方路径> 生成评估报告")


if __name__ == "__main__":
    main()
