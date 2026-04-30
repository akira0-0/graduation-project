"""
端到端测试：数据过滤引擎 -> XHSFilterNode -> 智能体工作流
============================================================
测试链路：
  [过滤引擎 :8081]  ->  XHSFilterNode  ->  SentimentAgent  ->  R        if status == "completed":
            break
        if status == "failed":
            error_msg = data.get("error") or "（未捕获到错误详情，请查看过滤引擎终端输出）"
            fail(f"过滤任务失败!")
            print(f"\n  错误详情:\n{error_msg[:1000]}")
            print(f"\n  提示: 先访问 http://localhost:8081/api/debug/components 诊断各组件状态")
            return NoneAgent
                          ^
                  [工作流引擎 :8123]

运行方式（在 work-flow-main/work-flow-main 目录下）：

  uv run python test_e2e_filter_to_workflow.py

  # 快速冒烟测试（跳过耗时的完整工作流）：
  uv run python test_e2e_filter_to_workflow.py --smoke-only

  # 指定查询主题：
  uv run python test_e2e_filter_to_workflow.py --topic "大学生旅游攻略"

  # 小规模测试（只取 20 条帖子，速度快）：
  uv run python test_e2e_filter_to_workflow.py --max-posts 20
"""

import json
import sys
import time
import argparse
import requests

# ── 服务地址 ─────────────────────────────────────────────
FILTER_API  = "http://localhost:8081"
WORKFLOW_API = "http://localhost:8123"

# ── 颜色输出 ─────────────────────────────────────────────
G = "\033[92m"  # 绿
R = "\033[91m"  # 红
Y = "\033[93m"  # 黄
B = "\033[94m"  # 蓝
RESET = "\033[0m"

def ok(msg):  print(f"  {G}✅ {msg}{RESET}")
def fail(msg):print(f"  {R}❌ {msg}{RESET}")
def warn(msg):print(f"  {Y}⚠️  {msg}{RESET}")
def info(msg):print(f"  {B}ℹ️  {msg}{RESET}")
def section(title): print(f"\n{'─'*60}\n{B}▶ {title}{RESET}")


# ═══════════════════════════════════════════════════════════
# 阶段1：服务健康检查
# ═══════════════════════════════════════════════════════════

def check_services() -> bool:
    section("阶段1：服务健康检查")
    all_ok = True

    # 1-A 过滤引擎（无 /health，用 /api/stats 代替）
    try:
        r = requests.get(f"{FILTER_API}/api/stats", timeout=5)
        if r.status_code == 200:
            ok(f"过滤引擎 {FILTER_API} 正常")
        else:
            fail(f"过滤引擎返回 {r.status_code}")
            all_ok = False
    except Exception as e:
        fail(f"过滤引擎无法连接: {e}")
        info("启动命令（必须在 e:\\xhs-crawler 目录下执行）:")
        info("  uv run uvicorn filter_engine.api:app --host 127.0.0.1 --port 8081 --reload")
        all_ok = False

    # 1-B 工作流引擎
    try:
        r = requests.get(f"{WORKFLOW_API}/health", timeout=5)
        if r.status_code == 200:
            ok(f"工作流引擎 {WORKFLOW_API} 正常")
        else:
            fail(f"工作流引擎返回 {r.status_code}")
            all_ok = False
    except Exception as e:
        fail(f"工作流引擎无法连接: {e}")
        info("启动命令（在 workflow_engine 目录下执行）:")
        info("  uv run python api/server.py")
        all_ok = False

    return all_ok


# ═══════════════════════════════════════════════════════════
# 阶段2：数据库预检（确认有数据可用）
# ═══════════════════════════════════════════════════════════

def check_database() -> dict:
    section("阶段2：数据库数据量预检")

    try:
        r = requests.get(f"{FILTER_API}/api/db/stats", timeout=10)
        r.raise_for_status()
        stats = r.json()

        total = stats.get("total_posts", 0)
        platforms = stats.get("platforms", {})

        print(f"  {'帖子总量':<12}: {total:,} 条")
        for p, n in platforms.items():
            print(f"  {'  ' + p:<12}: {n:,} 条")

        if total == 0:
            fail("数据库中没有帖子！请先运行爬虫或导入数据。")
            return {}
        elif total < 50:
            warn(f"仅有 {total} 条帖子，过滤后可能结果为空，建议补充数据")
        else:
            ok(f"数据充足（{total:,} 条），可以开始过滤")

        return stats

    except Exception as e:
        fail(f"数据库检查失败: {e}")
        return {}


# ═══════════════════════════════════════════════════════════
# 阶段3：单独测试过滤引擎（不经过工作流）
# ═══════════════════════════════════════════════════════════

def test_filter_engine_standalone(topic: str, max_posts: int) -> str | None:
    """
    直接调用过滤引擎，验证三层过滤流程和数据结构。
    返回 session_id（成功）或 None（失败）。
    """
    section("阶段3：单独测试过滤引擎（三层过滤）")

    # 3-A 提交异步过滤任务
    print("  提交过滤任务...")
    try:
        r = requests.post(
            f"{FILTER_API}/api/filter/auto/async",
            json={"query": topic, "max_posts": max_posts, "auto_save": True},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        session_id = data["session_id"]
        ok(f"任务已提交，session_id = {session_id}")
    except Exception as e:
        fail(f"提交过滤任务失败: {e}")
        return None

    # 3-B 轮询状态
    print("  等待过滤完成（L2+L3 需要一定时间）...")
    deadline = time.time() + 300
    last_progress = -1

    while time.time() < deadline:
        try:
            r = requests.get(
                f"{FILTER_API}/api/frontend/sessions/{session_id}/status",
                timeout=10,
            )
            r.raise_for_status()
            status_data = r.json()
        except Exception as e:
            warn(f"轮询出错，重试: {e}")
            time.sleep(3)
            continue

        status   = status_data.get("status")
        progress = status_data.get("progress", 0)
        stats    = status_data.get("stats", {})

        if progress != last_progress:
            print(f"    [{progress:3d}%] status={status}  "
                  f"L1={stats.get('l1_total_posts',0)}  "
                  f"L2={stats.get('l2_passed_posts',0)}  "
                  f"L3={stats.get('l3_passed_posts',0)}")
            last_progress = progress

        if status == "completed":
            break
        if status == "failed":
            fail(f"过滤任务失败: {status_data.get('error')}")
            return None

        time.sleep(3)
    else:
        fail("过滤任务超时（5分钟）")
        return None

    # 3-C 验证过滤统计
    l1 = stats.get("l1_total_posts", 0)
    l2 = stats.get("l2_passed_posts", 0)
    l3 = stats.get("l3_passed_posts", 0)

    ok(f"过滤完成: L1={l1} → L2={l2} → L3={l3}")

    if l3 == 0 and l2 == 0:
        fail("三层过滤后结果为空！")
        warn("建议: 换一个更通用的主题（如'大学生旅游'），或降低 min_relevance")
        return None
    elif l3 == 0:
        warn(f"L3 结果为空（L2 有 {l2} 条），L3 阈值可能过高")
    else:
        ok(f"L3 保留了 {l3} 条高质量帖子")

    # 3-D 验证数据结构
    print("  验证数据格式（CommentData 结构）...")
    try:
        r = requests.get(
            f"{FILTER_API}/api/frontend/sessions/{session_id}/dataset",
            params={"limit": 3},
            timeout=15,
        )
        r.raise_for_status()
        dataset = r.json()
        rows = dataset.get("data", [])

        if not rows:
            warn("dataset 返回空数组（可能 L3 结果为空）")
        else:
            row = rows[0]
            required_fields = ["id", "user", "content", "platform", "timestamp", "likes", "status"]
            missing = [f for f in required_fields if f not in row]
            if missing:
                fail(f"数据字段缺失: {missing}")
            else:
                ok(f"数据结构正确，共 {dataset.get('total', 0)} 条")
                info(f"示例: platform={row.get('platform')}  "
                     f"user={row.get('user')}  "
                     f"status={row.get('status')}")
    except Exception as e:
        fail(f"获取 dataset 失败: {e}")
        return None

    return session_id


# ═══════════════════════════════════════════════════════════
# 阶段4：完整工作流执行（过滤 → 情感分析 → 报告）
# ═══════════════════════════════════════════════════════════

def test_full_workflow(topic: str, max_posts: int) -> bool:
    section("阶段4：完整工作流执行（XHSFilterAgent → SentimentAgent → ReportAgent）")

    # 加载工作流 JSON
    import os
    json_path = os.path.join(os.path.dirname(__file__), "test_data", "xhs_opinion_workflow.json")
    try:
        with open(json_path, encoding="utf-8") as f:
            workflow_def = json.load(f)
        # 覆盖 topic 和 max_posts
        workflow_def["variables"]["topic"] = topic
        for node in workflow_def.get("nodes", []):
            if node.get("type") == "XHSFilterAgent":
                node["config"]["params"]["max_posts"] = max_posts
        ok(f"工作流 JSON 加载成功: {json_path}")
    except FileNotFoundError:
        fail(f"找不到工作流文件: {json_path}")
        return False

    # 调用 /api/v1/workflows/execute
    print(f"  提交到工作流引擎（topic='{topic}'，max_posts={max_posts}）...")
    print("  注意：包含 LLM 调用，可能需要 1~5 分钟...")

    t0 = time.time()
    try:
        r = requests.post(
            f"{WORKFLOW_API}/api/v1/workflows/execute",
            json={"workflow": workflow_def, "enable_monitoring": True},
            timeout=600,   # 10 分钟超时（LLM 调用链较长）
        )
        elapsed = time.time() - t0
        r.raise_for_status()
        result = r.json()
    except requests.exceptions.Timeout:
        fail(f"工作流执行超时（>{600}s）")
        return False
    except Exception as e:
        fail(f"工作流执行失败: {e}")
        try:
            print(f"  响应体: {r.text[:500]}")
        except Exception:
            pass
        return False

    # 验证执行结果
    status = result.get("status", "unknown")
    ok(f"工作流执行完成 (status={status}, 耗时={elapsed:.1f}s)")

    # 检查各节点输出
    node_outputs = result.get("result", {}).get("node_outputs", {})
    print(f"\n  节点输出概览:")

    # XHSFilterAgent
    xhs_out = node_outputs.get("xhs_filter", {})
    if xhs_out.get("status") == "success":
        collected = xhs_out.get("collected_data", [])
        stats = xhs_out.get("filter_stats", {})
        ok(f"XHSFilterAgent → 输出 {len(collected)} 条帖子")
        info(f"  过滤统计: L1={stats.get('l1_total_posts',0)} "
             f"→ L2={stats.get('l2_passed_posts',0)} "
             f"→ L3={stats.get('l3_passed_posts',0)}")

        if not collected:
            fail("XHSFilterAgent 输出为空，数据没有传递到后续节点！")
            warn("建议: 换更宽泛的 topic，或增大 max_posts")
    elif xhs_out.get("status") == "error":
        fail(f"XHSFilterAgent 报错: {xhs_out.get('error')}")
    else:
        warn(f"XHSFilterAgent 输出: {str(xhs_out)[:200]}")

    # SentimentAgent
    sentiment_out = node_outputs.get("sentiment", {})
    if sentiment_out:
        ok(f"SentimentAgent → 输出存在，情感分析已完成")
        _print_truncated("情感分析结果", sentiment_out)
    else:
        warn("SentimentAgent 无输出（可能 XHS 过滤结果为空）")

    # ReportAgent
    report_out = node_outputs.get("report", {})
    report_content = result.get("report_content") or report_out.get("report_content") or ""
    if report_content:
        ok(f"ReportAgent → 报告已生成（{len(report_content)} 字符）")
        # 打印报告前 300 字
        preview = report_content[:300].replace("\n", "\n    ")
        print(f"\n  报告预览:\n    {preview}...\n")
    elif report_out:
        warn("ReportAgent 有输出但未找到 report_content 字段")
        _print_truncated("报告节点输出", report_out)
    else:
        warn("ReportAgent 无输出")

    # 执行 ID
    execution_id = result.get("execution_id")
    if execution_id:
        info(f"执行记录 ID: {execution_id}")
        info(f"详情查询: GET {WORKFLOW_API}/api/v1/executions/{execution_id}")

    return status in ("success", "completed")


def _print_truncated(label: str, obj, max_len: int = 300):
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    if len(text) > max_len:
        text = text[:max_len] + "..."
    print(f"  {label}: {text}")


# ═══════════════════════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="端到端集成测试：过滤引擎 → 工作流引擎")
    parser.add_argument("--topic",      default="丽江旅游攻略", help="查询主题")
    parser.add_argument("--max-posts",  type=int, default=100, help="最多处理帖子数（默认100，小数值更快）")
    parser.add_argument("--smoke-only", action="store_true",   help="只跑阶段1-3，跳过完整工作流")
    args = parser.parse_args()

    topic     = args.topic
    max_posts = args.max_posts

    print(f"""
╔══════════════════════════════════════════════════════════╗
║    端到端集成测试：数据过滤引擎 → 智能体工作流               ║
╚══════════════════════════════════════════════════════════╝
  主题 (topic)  : {topic}
  最大帖子数     : {max_posts}
  仅冒烟测试     : {args.smoke_only}
""")

    # 阶段1
    if not check_services():
        print(f"\n{R}❌ 服务未全部启动，请先启动后再运行测试{RESET}")
        sys.exit(1)

    # 阶段2
    db_stats = check_database()
    if not db_stats:
        print(f"\n{R}❌ 数据库为空，请先运行爬虫{RESET}")
        sys.exit(1)

    # 阶段3
    session_id = test_filter_engine_standalone(topic, max_posts)
    if session_id is None:
        print(f"\n{R}❌ 过滤引擎测试失败，终止{RESET}")
        sys.exit(1)

    if args.smoke_only:
        print(f"\n{G}✅ 冒烟测试通过（--smoke-only 模式，跳过完整工作流）{RESET}")
        print(f"  可用 session_id: {session_id}")
        print(f"  数据预览: GET {FILTER_API}/api/frontend/sessions/{session_id}/dataset\n")
        sys.exit(0)

    # 阶段4
    success = test_full_workflow(topic, max_posts)

    # 最终结论
    print(f"\n{'═'*60}")
    if success:
        print(f"{G}✅ 端到端测试全部通过！{RESET}")
        print(f"  数据过滤引擎 → XHSFilterAgent → SentimentAgent → ReportAgent 链路正常")
    else:
        print(f"{R}❌ 端到端测试存在问题，请查看上方错误详情{RESET}")
    print()


if __name__ == "__main__":
    main()
