# -*- coding: utf-8 -*-
"""
网易新闻爬虫 - 统一格式版本
集成到 xhs-crawler 项目
支持输出统一数据格式到 data/unified/wangyi/
"""
import sys
import io
import json
import time
import datetime
import hashlib
import os
import platform

# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    if sys.stdout and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 尝试导入库
try:
    from DrissionPage import WebPage, ChromiumOptions
except ImportError as e:
    print(f"[ERROR] 缺少必要库: {e}")
    print("请运行: uv add DrissionPage")
    sys.exit(1)

# ==================== 配置中心 ====================
KEYWORDS = ["小时", "霍启刚", "笔记", "谭松韵", "手机", "田曦薇", "草莓", "巴黎", "速览", "邝兆镭", "伊朗", "男子", "逐玉", "奥巴马", "女孩"] 
MAX_ARTICLES = 25  # 每个关键词爬取文章数
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'unified', 'wangyi')

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 文件命名：按日期保存
TODAY = datetime.datetime.now().strftime('%Y-%m-%d')
POSTS_FILE = os.path.join(DATA_DIR, f'search_posts_{TODAY}.json')
COMMENTS_FILE = os.path.join(DATA_DIR, f'search_comments_{TODAY}.json')
# ====================================================

GLOBAL_POSTS = []
GLOBAL_COMMENTS = []

def get_timestamp():
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)

def gen_id(text):
    """生成MD5哈希ID"""
    return hashlib.md5(text.encode()).hexdigest()

def format_datetime(timestamp_ms=None):
    """
    格式化时间为 ISO 格式
    Args:
        timestamp_ms: 毫秒时间戳，None则使用当前时间
    Returns:
        str: "2026-01-14 10:30:00"
    """
    if timestamp_ms:
        dt = datetime.datetime.fromtimestamp(timestamp_ms / 1000)
    else:
        dt = datetime.datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def load_existing_data(file_path):
    """加载已存在的数据文件"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(posts, comments):
    """保存数据到JSON文件（增量保存）"""
    # 加载已有数据
    existing_posts = load_existing_data(POSTS_FILE)
    existing_comments = load_existing_data(COMMENTS_FILE)
    
    # 去重合并
    post_ids = {p['id'] for p in existing_posts}
    comment_ids = {c['id'] for c in existing_comments}
    
    new_posts = [p for p in posts if p['id'] not in post_ids]
    new_comments = [c for c in comments if c['id'] not in comment_ids]
    
    all_posts = existing_posts + new_posts
    all_comments = existing_comments + new_comments
    
    # 保存
    with open(POSTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)
    
    with open(COMMENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=2)
    
    print(f"      💾 [保存] 新增帖子 {len(new_posts)}, 新增评论 {len(new_comments)}")
    print(f"      📊 [总计] 帖子 {len(all_posts)}, 评论 {len(all_comments)}")
    
    return len(new_posts), len(new_comments)

# ==================== 🛠️ 监听获取评论（统一格式） ====================
def capture_comments_via_listener(page, post_id):
    """
    监听网易评论API，返回统一格式的评论列表
    
    返回格式：
    {
        "id": "评论ID",
        "content_id": "帖子ID",
        "platform": "wangyi",
        "content": "评论内容",
        "publish_time": "2026-01-14 10:30:00",
        "author": {
            "id": "作者ID",
            "nickname": "昵称",
            "avatar": "头像URL",
            "ip_location": "IP归属地"
        },
        "metrics": {
            "likes": 10,
            "sub_comments": 5
        },
        "parent_comment_id": null,  # 顶级评论为null
        "root_comment_id": "根评论ID",
        "reply_to_user_id": null,
        "reply_to_user_nickname": null,
        "comment_level": 1,
        "task_id": "",
        "crawl_time": 1736825400000
    }
    """
    print(f"      -> 正在监听评论数据包...")
    page.listen.start('comment.api.163.com')
    
    # 滚动触发加载
    page.scroll.to_bottom()
    time.sleep(1)
    page.scroll.up(300)
    time.sleep(1.5)
    
    final_comments = []
    
    # 服务器网络可能波动，超时设为 6 秒
    for packet in page.listen.steps(timeout=6):
        try:
            if 'newList' in packet.url or 'comments' in packet.url:
                resp = packet.response.body
                data = None
                if isinstance(resp, dict):
                    data = resp
                elif isinstance(resp, str):
                    try:
                        if '(' in resp and ')' in resp:
                            import re
                            match = re.search(r'\((.*)\)', resp)
                            if match: data = json.loads(match.group(1))
                        else:
                            data = json.loads(resp)
                    except: pass
                
                if not data: continue

                comment_dict = data.get('comments', {})
                if not comment_dict and 'data' in data:
                     comment_dict = data['data'].get('comments', {})

                if comment_dict:
                    print(f"      -> 🎯 捕获到 API 数据")
                    for k, v in comment_dict.items():
                        try:
                            content = v.get('content', '').strip()
                            if not content: continue
                            
                            user_nickname = v.get('user', {}).get('nickname', '网易网友')
                            user_avatar = v.get('user', {}).get('avatarUrl', '')
                            likes = int(v.get('vote', 0))
                            sub_count = int(v.get('replyCount', 0))
                            parent_id_raw = v.get('parent', 0)
                            
                            # 处理parent_id（0转为null）
                            parent_id = None if (parent_id_raw == 0 or parent_id_raw == '0') else str(parent_id_raw)
                            
                            comment_id = gen_id(f"{post_id}_{content}_{user_nickname}")
                            author_id = gen_id(user_nickname)
                            crawl_time_ms = get_timestamp()

                            # 🌟 统一格式
                            comment_item = {
                                "id": comment_id,
                                "content_id": post_id,
                                "platform": "wangyi",
                                "content": content,
                                "publish_time": format_datetime(crawl_time_ms),  # 网易API不返回发布时间，用爬取时间
                                
                                # 作者信息
                                "author": {
                                    "id": author_id,
                                    "nickname": user_nickname,
                                    "avatar": user_avatar,
                                    "ip_location": v.get('ip', '')
                                },
                                
                                # 互动数据
                                "metrics": {
                                    "likes": likes,
                                    "sub_comments": sub_count
                                },
                                
                                # 层级关系
                                "parent_comment_id": parent_id,
                                "root_comment_id": parent_id if parent_id else comment_id,  # 顶级评论的root是自己
                                "reply_to_user_id": None,  # 网易API不直接提供
                                "reply_to_user_nickname": None,
                                "comment_level": 1 if not parent_id else 2,  # 简单判断层级
                                
                                # 其他
                                "task_id": "",
                                "crawl_time": crawl_time_ms
                            }
                            
                            if not any(c['id'] == comment_id for c in final_comments):
                                final_comments.append(comment_item)
                        except Exception as e:
                            print(f"      -> ⚠️ 解析评论失败: {e}")
                            continue
        except: 
            continue
            
    page.listen.stop()
    print(f"      -> 本页截获 {len(final_comments)} 条评论")
    return final_comments

# ==================== 🚀 主程序（统一格式版本） ====================
def run():
    """
    主爬虫流程
    输出统一格式数据到 data/unified/wangyi/
    """
    # 🌟 自动判断运行环境
    system_type = platform.system().lower()
    is_linux = 'linux' in system_type
    
    print("=" * 60)
    print(f"🚀 网易新闻爬虫启动 (统一格式版本)")
    print(f"   环境: {system_type}")
    print(f"   数据目录: {DATA_DIR}")
    print(f"   关键词: {', '.join(KEYWORDS)}")
    print("=" * 60)
    
    # 配置浏览器选项
    co = ChromiumOptions()
    co.auto_port()
    
    # 🌟 智能配置浏览器参数
    if is_linux:
        print(">>> 🐧 启用服务器无头模式...")
        co.headless(True)
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        co.set_argument('--disable-dev-shm-usage')
    else:
        print(">>> 🪟 启用本地有头模式 (请勿关闭弹出的浏览器)...")
        co.headless(False)
    
    co.set_argument('--ignore-certificate-errors')
    co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # 启动浏览器
    try:
        page = WebPage(chromium_options=co)
        if not is_linux:
            page.set.window.max()
    except Exception as e:
        print(f"❌ 浏览器启动失败: {e}")
        if is_linux:
            print("💡 提示: 服务器请确保安装了 Chrome")
            print("   sudo apt install google-chrome-stable")
        sys.exit()

    # 遍历关键词
    for keyword in KEYWORDS:
        print(f"\n{'='*60}")
        print(f"🔍 关键词: {keyword}")
        print(f"{'='*60}")
        
        try:
            page.get(f'https://www.163.com/search?keyword={keyword}')
            time.sleep(3)
            
            # 提取搜索结果链接
            links = page.eles('css:h3 a')
            valid_links = []
            for a in links:
                l_url = a.attr('href')
                l_title = a.text.strip()
                if l_url and ('163.com' in l_url) and len(l_title) > 4:
                    valid_links.append({'title': l_title, 'url': l_url})

            print(f"   ✅ 发现 {len(valid_links)} 条链接")

            # 处理每篇文章
            for idx, item in enumerate(valid_links):
                if idx >= MAX_ARTICLES: 
                    break
                    
                title = item['title']
                url = item['url']
                post_id = gen_id(url)
                
                print(f"\n   [{idx+1}/{min(MAX_ARTICLES, len(valid_links))}] {title[:30]}...")
                
                try:
                    # 打开文章页
                    tab = page.new_tab(url)
                    tab.wait.load_start()
                    time.sleep(2)
                    
                    # 获取评论
                    comments_list = capture_comments_via_listener(tab, post_id)
                    
                    # 提取正文
                    content = title
                    try:
                        content_ele = tab.ele('.post_body')
                        if content_ele:
                            content = content_ele.text[:500].replace('\n', ' ')
                    except: 
                        pass
                    
                    tab.close()

                    # 🌟 转换为统一格式 - 帖子
                    crawl_time_ms = get_timestamp()
                    post_item = {
                        "id": post_id,
                        "platform": "wangyi",
                        "type": "text",  # 网易新闻主要是文字
                        "url": url,
                        "title": title,
                        "content": content,
                        "publish_time": format_datetime(crawl_time_ms),  # 网易不提供发布时间，用爬取时间
                        "last_update_time": format_datetime(crawl_time_ms),
                        
                        # 作者信息（网易新闻官方）
                        "author": {
                            "id": gen_id("网易新闻"),
                            "nickname": "网易新闻",
                            "avatar": "",
                            "is_verified": True,
                            "ip_location": ""
                        },
                        
                        # 媒体信息
                        "media": {
                            "images": [],  # 网易新闻图片需单独提取
                            "video_url": ""
                        },
                        
                        # 互动数据
                        "metrics": {
                            "likes": 0,  # 网易不显示点赞
                            "collects": 0,
                            "comments": len(comments_list),
                            "shares": 0
                        },
                        
                        # 其他
                        "tags": [keyword, "网易新闻"],
                        "source_keyword": keyword,
                        "task_id": "",
                        "crawl_time": crawl_time_ms
                    }

                    # 添加到全局列表
                    GLOBAL_POSTS.append(post_item)
                    GLOBAL_COMMENTS.extend(comments_list)
                    
                    # 实时保存
                    save_data(GLOBAL_POSTS, GLOBAL_COMMENTS)

                except Exception as e:
                    print(f"   ❌ 处理页面错误: {e}")
                    if 'tab' in locals(): 
                        try: 
                            tab.close()
                        except: 
                            pass

                # 礼貌延迟
                time.sleep(2)

        except Exception as e:
            print(f"   ❌ 搜索页错误: {e}")

    # 完成
    print(f"\n{'='*60}")
    print("🎉 全部完成！")
    print(f"{'='*60}")
    print(f"📊 统计:")
    print(f"   帖子: {len(GLOBAL_POSTS)} 条")
    print(f"   评论: {len(GLOBAL_COMMENTS)} 条")
    print(f"\n📂 文件位置:")
    print(f"   {POSTS_FILE}")
    print(f"   {COMMENTS_FILE}")
    print(f"\n💡 提示: 使用 import_with_sdk.py 导入到 Supabase")
    
    page.quit()

if __name__ == '__main__':
    run()