# -*- coding: utf-8 -*-
"""
4.2 评估指标计算 & 报告生成
============================
读取实验结果 JSON，计算准确率/召回率/F1 和效率指标，生成对比报告。

用法：
    uv run python experiments/evaluate.py \\
        --result experiments/results/experiment_丽江旅游攻略_xxx.json
"""
import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# 核心指标计算
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(passed_ids: List[str], ground_truth: Dict[str, int], input_count: int,
                    elapsed: float, llm_calls: int) -> Dict:
    """
    计算单组方法的全部评估指标。

    系统视角：passed = "认为有效（相关）"，filtered_out = "认为无效"
    Ground Truth：label=1 为真正有价值（positive），label=0 为无价值（negative）

    混淆矩阵：
      TP：系统通过 & 实际有效 (正确保留)
      FP：系统通过 & 实际无效 (误留，过滤失败)
      FN：系统过滤 & 实际有效 (误删，召回损失)
      TN：系统过滤 & 实际无效 (正确过滤)
    """
    passed_set = set(passed_ids)
    all_ids = set(ground_truth.keys())

    tp = sum(1 for pid in passed_set if ground_truth.get(pid) == 1)
    fp = sum(1 for pid in passed_set if ground_truth.get(pid) == 0)
    fn = sum(1 for pid in (all_ids - passed_set) if ground_truth.get(pid) == 1)
    tn = sum(1 for pid in (all_ids - passed_set) if ground_truth.get(pid) == 0)

    precision  = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall     = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1         = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy   = (tp + tn) / len(ground_truth) if ground_truth else 0.0

    # 过滤精度（过滤掉的数据中真正无效的比例）
    filter_precision = tn / (tn + fn) if (tn + fn) > 0 else 0.0

    # 效率指标
    throughput = round(input_count / elapsed, 2) if elapsed > 0 else float("inf")  # 条/秒
    avg_latency_ms = round(elapsed / input_count * 1000, 1) if input_count > 0 else 0  # ms/条
    llm_calls_per_100 = round(llm_calls / input_count * 100, 2) if input_count > 0 else 0

    return {
        # 准确性指标
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision":  round(precision, 4),
        "recall":     round(recall, 4),
        "f1":         round(f1, 4),
        "accuracy":   round(accuracy, 4),
        "filter_precision": round(filter_precision, 4),
        # 效率指标
        "input_count":      input_count,
        "passed_count":     len(passed_ids),
        "elapsed_s":        round(elapsed, 3),
        "throughput_per_s": throughput,
        "avg_latency_ms":   avg_latency_ms,
        "llm_calls":        llm_calls,
        "llm_calls_per_100": llm_calls_per_100,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 报告输出
# ─────────────────────────────────────────────────────────────────────────────

METHOD_NAMES = {
    "A": "纯规则过滤 (Rule-Only)",
    "B": "纯LLM过滤 (LLM-Only)",
    "C": "协同过滤系统 (Hybrid)",
}


def print_report(query: str, metrics_by_method: Dict[str, Dict]):
    SEP = "=" * 72
    print(f"\n{SEP}")
    print(f"  实验评估报告  |  Query: {query}")
    print(SEP)

    # ── 准确性对比 ───────────────────────────────────────────────────
    print("\n【准确性指标】")
    header = f"{'方法':<28} {'准确率':>8} {'精确率':>8} {'召回率':>8} {'F1':>8} {'过滤精度':>8}"
    print(header)
    print("-" * 72)
    for key, m in metrics_by_method.items():
        name = METHOD_NAMES.get(key, key)
        print(f"{name:<28} {m['accuracy']:>8.4f} {m['precision']:>8.4f} "
              f"{m['recall']:>8.4f} {m['f1']:>8.4f} {m['filter_precision']:>8.4f}")

    # ── 混淆矩阵 ─────────────────────────────────────────────────────
    print("\n【混淆矩阵（TP/FP/FN/TN）】")
    header2 = f"{'方法':<28} {'TP':>6} {'FP':>6} {'FN':>6} {'TN':>6}"
    print(header2)
    print("-" * 52)
    for key, m in metrics_by_method.items():
        name = METHOD_NAMES.get(key, key)
        print(f"{name:<28} {m['TP']:>6} {m['FP']:>6} {m['FN']:>6} {m['TN']:>6}")

    # ── 效率对比 ─────────────────────────────────────────────────────
    print("\n【效率指标】")
    header3 = f"{'方法':<28} {'总耗时(s)':>10} {'吞吐(条/s)':>11} {'延迟(ms/条)':>11} {'LLM调用':>8} {'LLM/百条':>8}"
    print(header3)
    print("-" * 80)
    for key, m in metrics_by_method.items():
        name = METHOD_NAMES.get(key, key)
        print(f"{name:<28} {m['elapsed_s']:>10.3f} {m['throughput_per_s']:>11.1f} "
              f"{m['avg_latency_ms']:>11.1f} {m['llm_calls']:>8} {m['llm_calls_per_100']:>8.2f}")

    # ── 综合结论 ─────────────────────────────────────────────────────
    print(f"\n【综合结论】")
    if len(metrics_by_method) >= 2:
        best_f1 = max(metrics_by_method.items(), key=lambda x: x[1]["f1"])
        best_thr = max(metrics_by_method.items(), key=lambda x: x[1]["throughput_per_s"])
        least_llm = min(metrics_by_method.items(), key=lambda x: x[1]["llm_calls"])
        print(f"  最高 F1 值:   {METHOD_NAMES.get(best_f1[0], best_f1[0])}  →  F1={best_f1[1]['f1']:.4f}")
        print(f"  最高吞吐量:   {METHOD_NAMES.get(best_thr[0], best_thr[0])}  →  {best_thr[1]['throughput_per_s']:.1f} 条/s")
        print(f"  最少LLM调用: {METHOD_NAMES.get(least_llm[0], least_llm[0])}  →  {least_llm[1]['llm_calls']} 次")

    print(f"\n{SEP}\n")


def save_csv(metrics_by_method: Dict[str, Dict], output_path: str):
    """保存为 CSV 方便导入 Excel"""
    import csv
    fields = ["method", "accuracy", "precision", "recall", "f1", "filter_precision",
              "TP", "FP", "FN", "TN",
              "elapsed_s", "throughput_per_s", "avg_latency_ms",
              "llm_calls", "llm_calls_per_100", "input_count", "passed_count"]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for key, m in metrics_by_method.items():
            writer.writerow({"method": METHOD_NAMES.get(key, key), **m})

    print(f"📊 CSV 已保存: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="计算评估指标并生成报告")
    parser.add_argument("--result", required=True, help="实验结果 JSON 文件路径")
    parser.add_argument("--csv", default=None, help="同时输出 CSV 文件（可选）")
    args = parser.parse_args()

    with open(args.result, encoding="utf-8") as f:
        exp = json.load(f)

    query = exp["query"]
    raw_results = exp["results"]

    metrics_by_method = {}

    for key, res in raw_results.items():
        ground_truth = res["ground_truth"]
        m = compute_metrics(
            passed_ids=res["passed_ids"],
            ground_truth=ground_truth,
            input_count=res["input_count"],
            elapsed=res["elapsed_total"],
            llm_calls=res["llm_calls"],
        )
        metrics_by_method[key] = m

    print_report(query, metrics_by_method)

    # 保存增强版 JSON
    report_path = args.result.replace(".json", "_metrics.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"query": query, "metrics": metrics_by_method}, f,
                  ensure_ascii=False, indent=2)
    print(f"📄 指标 JSON 已保存: {report_path}")

    # 可选 CSV
    csv_path = args.csv or args.result.replace(".json", "_metrics.csv")
    save_csv(metrics_by_method, csv_path)


if __name__ == "__main__":
    main()
