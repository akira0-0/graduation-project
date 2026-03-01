# -*- coding: utf-8 -*-
"""
Project: 全栈热点自动调度器 (Master Scheduler) - 精简版
Description: 抓取热搜 -> 修改配置 -> 分发给XHS/微博/Web三端爬虫 -> 依次执行
"""
import schedule
import time
import subprocess
import sys
import os
import json
import datetime
import re
from playwright.sync_api import sync_playwright

# ================= 配置区 =================
RUN_TIME = "09:00"      # 每天运行时间
TOP_N = 5               # 热搜抓取数量
FIXED_KEYWORDS = ["人工智能", "旅游"] # 固定关键词

# ================= 测试模式配置 =================
TEST_MODE = True          # ✅ 开启测试模式
TEST_XHS_MAX_NOTES = 2     # 小红书笔记数限制
TEST_XHS_MAX_COMMENTS = 3  # 小红书评论数限制
TEST_WEIBO_MAX_PAGES = 1   # 微博页数限制
TEST_WEB_MAX_ARTICLES = 2  # Web文章数限制

# ================= 平台开关配置 =================
ENABLE_XHS = True    
ENABLE_WEIBO = True   
ENABLE_WEB = True    

# ================= 路径配置 =================
XHS_SCRIPT = "main.py" 
WEIBO_DIR = os.path.join("weibo_crawler", "weibo_crawler") 
WEIBO_SCRIPT = "main.py"
WEIBO_CONFIG = "config.json"
WEB_DIR = "web_crawler"
WEB_SCRIPT = "spider.py"

# ==============================================================================
# 核心功能函数
# ==============================================================================

def get_weibo_hot_search():
    """🔥 获取热搜 (Playwright版)"""
    print(">>> 🔍 正在嗅探今日热搜...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://s.weibo.com/top/summary")
            page.wait_for_selector("td.td-02 a", timeout=15000) # 增加超时时间防止网络慢
            items = page.locator("td.td-02 a").all_inner_texts()
            browser.close()
            
            valid = [w.strip() for w in items if len(w.strip()) > 1]
            final = valid[:TOP_N]
            print(f"    ✅ 捕获热搜: {final}")
            return final
    except Exception as e:
        print(f"    ❌ 获取热搜失败: {e}")
        return []

def update_sub_config(folder, config_name, new_keywords, test_mode=False, max_pages=None):
    """📝 修改子爬虫的 config.json (适用于微博)"""
    config_path = os.path.join(os.getcwd(), folder, config_name)
    if not os.path.exists(config_path):
        print(f"    ⚠️ 未找到配置文件: {config_path}，跳过")
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 更新关键词
        current_kws = data.get("keywords", [])
        data["keywords"] = list(set(current_kws + new_keywords))
        
        # 测试模式更新
        if test_mode and max_pages is not None:
            data["max_pages"] = max_pages
            print(f"    🧪 [微博] 测试模式：max_pages = {max_pages}")
            
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"    ✅ 已更新 {folder} 配置")
        
    except Exception as e:
        print(f"    ❌ 更新 {folder} 配置失败: {e}")

def update_xhs_config_for_test(max_notes, max_comments):
    """📝 修改小红书 base_config.py (通过正则替换)"""
    config_path = os.path.join(os.getcwd(), "config", "base_config.py")
    if not os.path.exists(config_path):
        return None, False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 正则替换配置项
        content = re.sub(r"CRAWLER_MAX_NOTES_COUNT\s*=\s*\d+", f"CRAWLER_MAX_NOTES_COUNT = {max_notes}", content)
        content = re.sub(r"CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES\s*=\s*\d+", f"CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = {max_comments}", content)
        
        if content != original_content:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"    🧪 [小红书] 测试模式：笔记={max_notes}, 评论={max_comments}")
            return original_content, True
        return None, False
    except Exception as e:
        print(f"    ❌ 更新小红书配置失败: {e}")
        return None, False

def update_web_spider_keywords(web_dir, script_name, new_keywords, test_mode=False, max_articles=None):
    """📝 修改Web爬虫 spider.py (通过正则替换)"""
    script_path = os.path.join(os.getcwd(), web_dir, script_name)
    if not os.path.exists(script_path):
        print(f"    ⚠️ 未找到脚本: {script_path}，跳过")
        return
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 构造Python列表字符串
        keywords_str = str(new_keywords) # 直接转成 "['a', 'b']" 格式
        
        # 替换 KEYWORDS = [...]
        new_content = re.sub(r"KEYWORDS\s*=\s*\[.*?\]", f"KEYWORDS = {keywords_str}", content, flags=re.DOTALL)
        
        if test_mode and max_articles is not None:
             # 替换 MAX_ARTICLES = ...
            new_content = re.sub(r"MAX_ARTICLES\s*=\s*\d+", f"MAX_ARTICLES = {max_articles}", new_content)
            print(f"    🧪 [Web] 测试模式：MAX_ARTICLES = {max_articles}")

        if new_content != content:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"    ✅ 已更新 {web_dir} 关键词")
            
    except Exception as e:
        print(f"    ❌ 更新 Web 配置失败: {e}")

def run_subprocess(cmd, work_dir):
    """🚀 通用子进程执行器 (只负责跑，不负责装环境)"""
    print(f"\n>>> 启动: {' '.join(cmd)}")
    print(f">>> 目录: {work_dir}")
    print(f"{'-'*60}")
    
    try:
        # 区分 Windows 和 Linux 的 Shell 模式
        use_shell = True if sys.platform == "win32" else False
        cmd_input = ' '.join(cmd) if sys.platform == "win32" else cmd

        process = subprocess.Popen(
            cmd_input,
            cwd=work_dir,
            shell=use_shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 实时打印输出
        for line in iter(process.stdout.readline, ''):
            print(line.rstrip())
            
        process.wait()
        
        if process.returncode == 0:
            print(f"✅ 执行成功")
        else:
            print(f"⚠️ 执行异常 (Code: {process.returncode})")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
    print(f"{'='*60}\n")

# ==============================================================================
# 主调度逻辑
# ==============================================================================

def job_master_runner():
    print(f"\n{'='*60}")
    print(f"⏰ [全栈调度触发] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 获取热词
    hot_words = get_weibo_hot_search()
    all_keywords = list(set(hot_words + FIXED_KEYWORDS))
    
    if not all_keywords:
        print("❌ 未获取到任何关键词，跳过本次任务")
        return

    print(f"🎯 今日目标: {','.join(all_keywords)}")
    
    # 2. 小红书任务
    if ENABLE_XHS:
        print(f"---------- 启动小红书爬虫 ----------")
        # 修改配置
        if TEST_MODE:
            update_xhs_config_for_test(TEST_XHS_MAX_NOTES, TEST_XHS_MAX_COMMENTS)
        
        # 运行
        xhs_cmd = [sys.executable, XHS_SCRIPT, "--keywords", ",".join(all_keywords), "--type", "search", "--save_data_option", "json"]
        run_subprocess(xhs_cmd, os.getcwd())

    # 3. 微博任务
    if ENABLE_WEIBO:
        print(f"---------- 启动微博爬虫 ----------")
        # 修改配置
        max_pages = TEST_WEIBO_MAX_PAGES if TEST_MODE else None
        update_sub_config(WEIBO_DIR, WEIBO_CONFIG, all_keywords, test_mode=TEST_MODE, max_pages=max_pages)
        
        # 运行
        weibo_work_dir = os.path.join(os.getcwd(), WEIBO_DIR)
        if os.path.exists(weibo_work_dir):
            run_subprocess([sys.executable, WEIBO_SCRIPT], weibo_work_dir)
        else:
            print(f"❌ 目录不存在: {weibo_work_dir}")

    # 4. Web任务
    if ENABLE_WEB:
        print(f"---------- 启动Web爬虫 ----------")
        # 修改配置
        max_articles = TEST_WEB_MAX_ARTICLES if TEST_MODE else None
        update_web_spider_keywords(WEB_DIR, WEB_SCRIPT, all_keywords, test_mode=TEST_MODE, max_articles=max_articles)
        
        # 运行
        web_work_dir = os.path.join(os.getcwd(), WEB_DIR)
        run_subprocess([sys.executable, WEB_SCRIPT], web_work_dir)

    print(f"✅ 所有任务调度结束")

def start_service():
    print(f">>> 🤖 全栈热点调度器已启动")
    print(f">>> 📅 定时时间: {RUN_TIME}")
    print(f">>> 🧪 测试模式: {'开启' if TEST_MODE else '关闭'}")
    
    schedule.every().day.at(RUN_TIME).do(job_master_runner)
    
    # === 测试用：每分钟跑一次 ===
    schedule.every(0.1).minutes.do(job_master_runner)
    
    print(f">>> ⏳ 等待触发...")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    start_service()