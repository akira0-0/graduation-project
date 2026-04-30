# -*- coding: utf-8 -*-
"""
4.1 测试数据集构建
==================
从 filtered_posts 中导出帖子，调用 LLM（GPT-4o）作为 Oracle 自动标注，
生成带 Ground Truth 的 JSON 数据集文件。

用法：
    uv run python experiments/build_dataset.py --query "丽江旅游攻略" --limit 300
    uv run python experiments/build_dataset.py --query "健身减脂" --limit 300
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 项目根目录加入 path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from supabase import create_client


# ── Oracle LLM 标注（用 GPT-4o / Qwen-Max 判断是否"对 query 有价值"）─────
ORACLE_SYSTEM = """你是一名数据标注专家。
你的任务是判断一条小红书帖子对于指定用户查询是否"有价值"。

判断标准：
- label=1（有价值）：帖子主要内容与查询直接相关，包含有用信息（真实经历/攻略/推荐/评测）
- label=0（无价值）：满足以下任一条件
    a. 广告/引流/推广（含联系方式、二维码引导、"私信我"等）
    b. 内容与查询主题完全无关
    c. 内容极度空洞（如只有表情、打卡签到无实质信息）
    d. 主题大方向相关但具体内容偏题（如问丽江旅游，帖子讲的是云南其他城市）

请只返回 JSON：{"label": 0 或 1, "reason": "一句话理由"}
"""


def oracle_label(client_llm, query: str, post: dict) -> dict:
    """调用 LLM 对单条帖子打标"""
    title = post.get("title") or ""
    content = (post.get("content") or "")[:500]  # 截断避免超 token
    text = f"[标题] {title}\n[正文] {content}"

    messages = [
        {"role": "system", "content": ORACLE_SYSTEM},
        {"role": "user", "content": f"用户查询：{query}\n\n帖子内容：\n{text}"},
    ]

    try:
        resp = client_llm.chat(messages, temperature=0.0)
        raw = resp.content.strip()
        # 提取 JSON
        import re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"  ⚠️  Oracle 标注失败: {e}")

    return {"label": -1, "reason": "标注失败"}


def fetch_posts(supabase, platform: str | None, limit: int) -> list:
    """从 filtered_posts 分页读取帖子"""
    q = supabase.table("filtered_posts").select("*")
    if platform:
        q = q.eq("platform", platform)

    posts, page_size, offset = [], 500, 0
    while len(posts) < limit:
        resp = q.range(offset, offset + page_size - 1).execute()
        data = resp.data or []
        if not data:
            break
        posts.extend(data)
        offset += page_size
        if len(data) < page_size:
            break

    return posts[:limit]


def main():
    parser = argparse.ArgumentParser(description="构建实验用标注数据集")
    parser.add_argument("--query", required=True, help="实验查询，如 '丽江旅游攻略'")
    parser.add_argument("--limit", type=int, default=300, help="从 DB 取多少条帖子（最终标注集）")
    parser.add_argument("--platform", default=None, help="限制平台，如 xhs")
    parser.add_argument("--output", default=None, help="输出文件路径（默认自动生成）")
    parser.add_argument("--skip-oracle", action="store_true", help="跳过 LLM 标注（只导出原始数据）")
    args = parser.parse_args()

    # ── 初始化 Supabase ──────────────────────────────────────────────
    SUPABASE_URL = os.environ["SUPABASE_URL"]
    SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ── 读取帖子 ──────────────────────────────────────────────────────
    print(f"📖 读取帖子（platform={args.platform}, limit={args.limit}）...")
    posts = fetch_posts(supabase, args.platform, args.limit)
    print(f"  ✅ 读取 {len(posts)} 条\n")

    if not posts:
        print("❌ 数据库中无帖子，请先运行爬虫")
        return

    if args.skip_oracle:
        # 只导出原始数据，label=-1 表示未标注
        dataset = [
            {
                "id": p["id"],
                "platform": p.get("platform"),
                "title": p.get("title"),
                "content": p.get("content"),
                "tags": p.get("tags"),
                "publish_time": p.get("publish_time"),
                "label": -1,
                "label_reason": "未标注",
            }
            for p in posts
        ]
    else:
        # ── 初始化 Oracle LLM ────────────────────────────────────────
        from filter_engine.llm.client import create_llm_client
        llm = create_llm_client(
            provider=os.environ.get("LLM_PROVIDER", "qwen"),
            api_key=os.environ.get("LLM_API_KEY"),
            model=os.environ.get("LLM_MODEL", "qwen-max"),
        )

        # ── 逐条标注 ─────────────────────────────────────────────────
        print(f"🤖 Oracle 标注（query='{args.query}'）...")
        dataset = []
        labeled_1, labeled_0, failed = 0, 0, 0

        for i, post in enumerate(posts):
            result = oracle_label(llm, args.query, post)
            label = result.get("label", -1)

            dataset.append({
                "id": post["id"],
                "platform": post.get("platform"),
                "title": post.get("title"),
                "content": post.get("content"),
                "tags": post.get("tags"),
                "publish_time": post.get("publish_time"),
                "label": label,
                "label_reason": result.get("reason", ""),
            })

            if label == 1:
                labeled_1 += 1
            elif label == 0:
                labeled_0 += 1
            else:
                failed += 1

            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{len(posts)} | 有效={labeled_1} 无效={labeled_0} 失败={failed}")
            time.sleep(0.3)  # 避免 API 限频

        print(f"\n✅ 标注完成: 有效={labeled_1} | 无效={labeled_0} | 失败={failed}")

    # ── 保存数据集 ────────────────────────────────────────────────────
    output = args.output or str(
        ROOT / "experiments" / "data" /
        f"dataset_{args.query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    meta = {
        "query": args.query,
        "platform": args.platform,
        "total": len(dataset),
        "positive": sum(1 for x in dataset if x["label"] == 1),
        "negative": sum(1 for x in dataset if x["label"] == 0),
        "unknown": sum(1 for x in dataset if x["label"] == -1),
        "created_at": datetime.now().isoformat(),
    }

    with open(output, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "data": dataset}, f, ensure_ascii=False, indent=2)

    print(f"\n💾 数据集已保存: {output}")
    print(f"   总量={meta['total']} | 正例={meta['positive']} | 负例={meta['negative']}")


if __name__ == "__main__":
    main()
