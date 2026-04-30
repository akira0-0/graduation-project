"""
降级策略测试脚本
=================
验证 L3=0 时 XHSFilterNode 自动降级到 L2 数据的流程：

  Step1  POST /api/filter/auto/async   → 提交过滤任务
  Step2  GET  /api/frontend/sessions/{id}/status (轮询)
  Step3  GET  /api/frontend/sessions/{id}/dataset   → L3 结果
  Step3b 若 L3=0: GET /api/frontend/sessions/{id}/l2dataset → L2 降级
"""
import time
import json
import requests
import argparse

FILTER_API = "http://localhost:8081"
POLL_INTERVAL = 3
POLL_TIMEOUT = 300

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

def ok(msg):    print(f"{GREEN}✅ {msg}{RESET}")
def warn(msg):  print(f"{YELLOW}⚠️  {msg}{RESET}")
def err(msg):   print(f"{RED}❌ {msg}{RESET}")
def info(msg):  print(f"{CYAN}ℹ️  {msg}{RESET}")


def submit_filter(query: str, max_posts: int, platform: str = None) -> str:
    """提交过滤任务，返回 session_id"""
    payload = {"query": query, "max_posts": max_posts, "auto_save": True}
    if platform:
        payload["platform"] = platform

    r = requests.post(f"{FILTER_API}/api/filter/auto/async", json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    session_id = data.get("session_id")
    if not session_id:
        raise ValueError(f"未返回 session_id: {data}")
    ok(f"任务已提交 | session_id={session_id}")
    return session_id


def wait_completion(session_id: str) -> dict:
    """轮询直到 completed，返回 stats"""
    url = f"{FILTER_API}/api/frontend/sessions/{session_id}/status"
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 404:
                time.sleep(POLL_INTERVAL); continue
            r.raise_for_status()
            d = r.json()
        except Exception as e:
            warn(f"轮询异常，重试: {e}")
            time.sleep(POLL_INTERVAL); continue

        status   = d.get("status", "processing")
        progress = d.get("progress", 0)
        stats    = d.get("stats", {})
        info(f"轮询中 status={status} progress={progress}%")

        if status == "completed":
            ok(f"任务完成 | stats={stats}")
            return stats
        if status == "failed":
            raise RuntimeError(f"任务失败: {d.get('error')}")

        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"等待超时 ({POLL_TIMEOUT}s)")


def get_l3_dataset(session_id: str) -> list:
    r = requests.get(
        f"{FILTER_API}/api/frontend/sessions/{session_id}/dataset",
        params={"limit": 1000}, timeout=30
    )
    r.raise_for_status()
    data = r.json()
    posts = data.get("data") or []
    info(f"L3 dataset: total={data.get('total')}, returned={len(posts)}")
    return posts


def get_l2_dataset(session_id: str) -> list:
    r = requests.get(
        f"{FILTER_API}/api/frontend/sessions/{session_id}/l2dataset",
        params={"limit": 1000}, timeout=30
    )
    r.raise_for_status()
    data = r.json()
    posts = data.get("data") or []
    info(f"L2 dataset: total={data.get('total')}, returned={len(posts)}, fallback_layer={data.get('fallback_layer')}")
    return posts


def print_sample(posts: list, n: int = 3, label: str = "样本"):
    print(f"\n  --- {label}（前{n}条）---")
    for p in posts[:n]:
        print(f"  id       : {p.get('id','')[:20]}...")
        print(f"  user     : {p.get('user')}")
        print(f"  platform : {p.get('platform')}")
        print(f"  likes    : {p.get('likes')}")
        print(f"  fallback : {p.get('_fallback_layer', 'none')}")
        print(f"  content  : {(p.get('content') or '')[:80]}...")
        print()


def test_fallback(query: str, max_posts: int, platform: str = None):
    print(f"\n{'='*60}")
    print(f"  降级策略测试")
    print(f"  query={query!r}  max_posts={max_posts}  platform={platform}")
    print(f"{'='*60}\n")

    # ── Step 1: 提交任务 ──────────────────────────────────────────
    print("[Step 1] 提交过滤任务...")
    try:
        session_id = submit_filter(query, max_posts, platform)
    except Exception as e:
        err(f"提交失败: {e}"); return False

    # ── Step 2: 等待完成 ─────────────────────────────────────────
    print("\n[Step 2] 等待过滤完成...")
    try:
        stats = wait_completion(session_id)
    except Exception as e:
        err(f"等待失败: {e}"); return False

    l1 = stats.get("l1_total_posts", 0)
    l2 = stats.get("l2_passed_posts", 0)
    l3 = stats.get("l3_passed_posts", 0)
    print(f"\n  过滤漏斗: L1={l1} → L2={l2} → L3={l3}")

    # ── Step 3: 获取 L3 数据 ────────────────────────────────────
    print("\n[Step 3] 获取 L3 数据集...")
    try:
        l3_posts = get_l3_dataset(session_id)
    except Exception as e:
        err(f"L3 接口失败: {e}"); l3_posts = []

    # ── Step 3b: 降级逻辑 ───────────────────────────────────────
    fallback_used = False
    final_posts   = l3_posts

    if len(l3_posts) == 0:
        warn(f"L3 结果为空，触发降级逻辑，尝试获取 L2 数据...")
        print("\n[Step 3b] 获取 L2 降级数据集...")
        try:
            l2_posts = get_l2_dataset(session_id)
        except Exception as e:
            err(f"L2 接口失败: {e}"); l2_posts = []

        if l2_posts:
            final_posts  = l2_posts
            fallback_used = True
            ok(f"降级成功！使用 L2 数据 {len(l2_posts)} 条")
        else:
            warn("L2 数据也为空，两层过滤后均无数据")

    else:
        ok(f"L3 有数据 {len(l3_posts)} 条，无需降级")

    # ── 结果汇总 ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  测试结果汇总")
    print(f"{'='*60}")
    print(f"  session_id  : {session_id}")
    print(f"  过滤漏斗    : L1={l1} → L2={l2} → L3={l3}")
    print(f"  最终数据量  : {len(final_posts)} 条")
    print(f"  是否降级    : {'是 (L2 数据)' if fallback_used else '否 (L3 数据)'}")

    # 验证降级数据的 _fallback_layer 标记
    if fallback_used and final_posts:
        has_flag = all(p.get("_fallback_layer") == "l2" for p in final_posts)
        if has_flag:
            ok("降级标记 _fallback_layer='l2' 验证通过 ✓")
        else:
            warn("部分数据缺少 _fallback_layer 标记")
        print_sample(final_posts, label="L2 降级样本")

    elif final_posts:
        has_no_flag = all(p.get("_fallback_layer") is None for p in final_posts)
        if has_no_flag:
            ok("L3 数据无降级标记 ✓")
        print_sample(final_posts, label="L3 样本")

    success = len(final_posts) > 0
    if success:
        ok("测试通过：降级策略工作正常")
    else:
        warn("数据量为零，请检查数据库是否有该主题的数据")

    return success


def test_l2_api_exists(session_id: str):
    """单独验证 /l2dataset 接口是否正常响应"""
    print(f"\n[API检查] 验证 /l2dataset 接口...")
    try:
        r = requests.get(
            f"{FILTER_API}/api/frontend/sessions/{session_id}/l2dataset",
            params={"limit": 5}, timeout=10
        )
        if r.status_code == 200:
            d = r.json()
            ok(f"/l2dataset 接口正常 | total={d.get('total')} | fallback_layer={d.get('fallback_layer')}")
            return True
        elif r.status_code == 404:
            err(f"/l2dataset 接口返回 404，请确认过滤引擎已重启以加载新接口")
            return False
        else:
            err(f"/l2dataset 接口异常 {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        err(f"/l2dataset 接口请求失败: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试 L3→L2 降级策略")
    parser.add_argument("--query",     default="丽江旅游攻略", help="搜索主题")
    parser.add_argument("--max-posts", type=int, default=100,  help="最大读取帖子数")
    parser.add_argument("--platform",  default=None,           help="平台: xhs/weibo")
    parser.add_argument("--session-id", default=None,          help="直接指定已有 session_id 跳过过滤")
    args = parser.parse_args()

    if args.session_id:
        # 直接测试已有 session 的 L2 接口
        print(f"\n使用已有 session_id={args.session_id} 测试接口...")
        ok_flag = test_l2_api_exists(args.session_id)
        if ok_flag:
            print("\n获取 L2 数据:")
            posts = get_l2_dataset(args.session_id)
            if posts:
                print_sample(posts, label="L2 样本")
            else:
                warn("L2 数据为空（该 session 可能没有 L2 数据）")
    else:
        test_fallback(
            query=args.query,
            max_posts=args.max_posts,
            platform=args.platform,
        )
