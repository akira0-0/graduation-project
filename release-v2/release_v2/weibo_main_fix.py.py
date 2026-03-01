import sys
import io

# Force UTF-8 encoding for stdout/stderr to prevent encoding errors
# when outputting Chinese characters and Unicode symbols in non-UTF-8 terminals (Windows GBK)
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'buffer'):
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import os
import datetime
from pathlib import Path
from crawler import WeiboCrawler
from file_writer import WeiboFileWriter

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = Path(__file__).parent.resolve()

# 定义数据保存目录：E:\xhs-crawler\data\unified\weibo
# 向上两级到 xhs-crawler 目录，然后进入 data/unified/weibo
DATA_DIR = SCRIPT_DIR.parent.parent / "data" / "unified" / "weibo"

def load_config(config_path="config.json"):
    # 转换为绝对路径
    config_path = SCRIPT_DIR / config_path
    
    if not config_path.exists():
        print(f"Config file {config_path} not found. Creating a template.")
        default_config = {
            "cookie": "",
            "keywords": ["Python", "AI"],
            "max_pages": 2
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    print("=== Weibo Crawler for Academic Research ===")
    print("=" * 50)
    
    # 1. Load Configuration
    config = load_config("config.json")
    cookie = config.get("cookie")
    keywords = config.get("keywords")
    max_pages = config.get("max_pages", 2)
    
    print(f"✓ Config loaded from: {SCRIPT_DIR / 'config.json'}")
    print(f"✓ Data will be saved to: {DATA_DIR}")
    print(f"✓ Keywords: {keywords}")
    print(f"✓ Max pages per keyword: {max_pages}")
    print(f"✓ Cookie: {'Valid' if cookie and len(cookie) > 50 else 'Invalid or Missing'}")
    print("=" * 50)
    
    if not cookie or cookie == "YOUR_WEIBO_COOKIE_HERE" or cookie == "":
        print("\n❌ WARNING: No valid cookie found in config.json.")
        print("Weibo API requires a cookie for most operations (especially comments).")
        print("Please log in to m.weibo.cn, copy your Cookie header, and paste it into config.json.\n")
        # We proceed anyway, but results might be limited
    
    # 2. Setup Task
    task_id = f"task_{datetime.datetime.now().strftime('%Y%m%d')}"
    
    # 3. Init Crawler & File Writer
    crawler = WeiboCrawler(cookie)
    file_writer = WeiboFileWriter(base_path=str(DATA_DIR))
    
    # 4. Run Crawler
    print(f"\n🚀 Starting crawl...\n")
    posts, comments = crawler.run(keywords, max_pages, task_id)
    
    # 5. Save Results (增量保存，按日期合并)
    print(f"\n💾 Saving results...\n")
    total_posts = file_writer.save_posts(posts)
    total_comments = file_writer.save_comments(comments)
    
    print(f"\n{'=' * 50}")
    print("✅ Crawl completed successfully!")
    print(f"{'=' * 50}\n")

if __name__ == "__main__":
    main()