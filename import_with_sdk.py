# -*- coding: utf-8 -*-
"""
使用 Supabase Python SDK 导入统一格式数据
支持导入 data/unified/ 目录下的标准化JSON数据
"""
import json
import os
from supabase import create_client, Client
from datetime import datetime

# ===== Supabase 配置 =====
# 从 Supabase Dashboard → Settings → API 获取
SUPABASE_URL = "https://rynxtsbrwvexytmztcyh.supabase.co"  # Project URL
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ5bnh0c2Jyd3ZleHl0bXp0Y3loIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc4NTA5ODUsImV4cCI6MjA4MzQyNjk4NX0.0AGziOeTUQjv1cpaCfNCBST3xz97VxkMs_ggzaxthgo"  # anon/public key

# 如果你有 service_role key (更高权限，用于服务端)
# SUPABASE_SERVICE_KEY = "你的_SERVICE_ROLE_KEY"

def create_supabase_client():
    """创建 Supabase 客户端"""
    try:
        # 使用 anon key (公开密钥)
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase 客户端创建成功")
        return supabase
    except Exception as e:
        print(f"❌ 创建客户端失败: {e}")
        return None

def test_connection(supabase: Client):
    """测试连接和表是否存在"""
    try:
        # 测试帖子表
        supabase.table('posts').select("count", count='exact').limit(0).execute()
        print(f"✅ 连接测试成功！表 posts 存在")
        
        # 测试评论表
        supabase.table('comments').select("count", count='exact').limit(0).execute()
        print(f"✅ 表 comments 存在")
        
        return True
    except Exception as e:
        if "relation" in str(e) and "does not exist" in str(e):
            print("❌ 表不存在")
            print("💡 请先执行 database/schema_supabase.sql 创建表结构")
        else:
            print(f"❌ 连接测试失败: {e}")
        return False

def parse_datetime(time_str):
    """
    解析各种格式的时间字符串为ISO格式
    
    支持格式：
    - "2026-01-13 10:00:00" (ISO)
    - "Sat Jan 10 07:56:36 +0800 2026" (微博格式)
    - Unix时间戳
    """
    if not time_str:
        return None
    
    # 已经是ISO格式
    if isinstance(time_str, str) and len(time_str) == 19 and time_str[10] == ' ':
        return time_str
    
    # 尝试解析微博格式: "Sat Jan 10 07:56:36 +0800 2026"
    try:
        # 移除时区信息
        parts = time_str.split()
        if len(parts) == 6:  # 有时区
            time_str_clean = ' '.join(parts[:-1])  # 移除时区
        else:
            time_str_clean = time_str
        
        dt = datetime.strptime(time_str_clean, '%a %b %d %H:%M:%S %Y')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        pass
    
    # 尝试解析时间戳
    try:
        dt = datetime.fromtimestamp(int(time_str))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        pass
    
    return None


def import_posts_with_sdk(supabase: Client, file_path: str):
    """导入帖子数据（统一格式）"""
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            posts = json.load(f)
        print(f"📖 读取到 {len(posts)} 条帖子数据")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return 0
    
    # 去重
    seen_ids = set()
    unique_posts = []
    for post in posts:
        post_id = post.get('id')
        if post_id and post_id not in seen_ids:
            seen_ids.add(post_id)
            unique_posts.append(post)
    
    if len(unique_posts) < len(posts):
        print(f"⚠️  发现 {len(posts) - len(unique_posts)} 条重复数据，已自动去重")
    
    success_count = 0
    batch_size = 20
    
    for i in range(0, len(unique_posts), batch_size):
        batch = unique_posts[i:i + batch_size]
        batch_data = []
        
        for post in batch:
            try:
                author = post.get('author', {})
                media = post.get('media', {})
                metrics = post.get('metrics', {})
                
                data = {
                    'id': post.get('id'),
                    'platform': post.get('platform'),
                    'type': post.get('type'),
                    'url': post.get('url'),
                    'title': post.get('title'),
                    'content': post.get('content'),
                    'publish_time': parse_datetime(post.get('publish_time')),
                    'last_update_time': parse_datetime(post.get('last_update_time')),
                    
                    # 作者信息
                    'author_id': author.get('id'),
                    'author_nickname': author.get('nickname'),
                    'author_avatar': author.get('avatar'),
                    'author_is_verified': author.get('is_verified', False),
                    'author_ip_location': author.get('ip_location'),
                    
                    # 媒体信息（JSON）
                    'media_images': media.get('images', []),
                    'media_video_url': media.get('video_url'),
                    
                    # 互动数据
                    'metrics_likes': metrics.get('likes', 0),
                    'metrics_collects': metrics.get('collects', 0),
                    'metrics_comments': metrics.get('comments', 0),
                    'metrics_shares': metrics.get('shares', 0),
                    
                    # 其他
                    'tags': post.get('tags', []),
                    'source_keyword': post.get('source_keyword'),
                    'task_id': post.get('task_id'),
                    'crawl_time': post.get('crawl_time'),
                    'extra': post.get('extra', {})
                }
                
                batch_data.append(data)
                
            except Exception as e:
                print(f"❌ 处理帖子 {post.get('id')} 失败: {e}")
                continue
        
        # 批量插入
        if batch_data:
            try:
                result = supabase.table('posts').upsert(
                    batch_data,
                    on_conflict='id'
                ).execute()
                
                success_count += len(batch_data)
                print(f"📊 已导入 {success_count}/{len(unique_posts)} 条帖子")
                
            except Exception as e:
                print(f"❌ 批量插入失败: {e}")
                # 逐条插入
                print("🔄 尝试逐条插入...")
                for item in batch_data:
                    try:
                        supabase.table('posts').upsert([item], on_conflict='id').execute()
                        success_count += 1
                        print(f"  ✅ {item['id']}")
                    except Exception as e2:
                        print(f"  ❌ {item.get('id')}: {str(e2)[:100]}")
    
    print(f"✅ 帖子导入完成: {success_count}/{len(unique_posts)} 条")
    return success_count

def import_comments_with_sdk(supabase: Client, file_path: str):
    """导入评论数据（统一格式）"""
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        print(f"📖 读取到 {len(comments)} 条评论数据")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return 0
    
    # 去重
    seen_ids = set()
    unique_comments = []
    for comment in comments:
        comment_id = comment.get('id')
        if comment_id and comment_id not in seen_ids:
            seen_ids.add(comment_id)
            unique_comments.append(comment)
    
    if len(unique_comments) < len(comments):
        print(f"⚠️  发现 {len(comments) - len(unique_comments)} 条重复数据，已自动去重")
    
    success_count = 0
    batch_size = 20
    
    for i in range(0, len(unique_comments), batch_size):
        batch = unique_comments[i:i + batch_size]
        batch_data = []
        
        for comment in batch:
            try:
                author = comment.get('author', {})
                metrics = comment.get('metrics', {})
                
                # 处理parent_comment_id（None转为null）
                parent_id = comment.get('parent_comment_id')
                if parent_id == 0 or parent_id == "0":
                    parent_id = None
                
                data = {
                    'id': comment.get('id'),
                    'content_id': comment.get('content_id'),
                    'platform': comment.get('platform'),
                    'content': comment.get('content'),
                    'publish_time': parse_datetime(comment.get('publish_time')),
                    
                    # 作者信息
                    'author_id': author.get('id'),
                    'author_nickname': author.get('nickname'),
                    'author_avatar': author.get('avatar'),
                    'author_ip_location': author.get('ip_location'),
                    
                    # 互动数据
                    'metrics_likes': metrics.get('likes', 0),
                    'metrics_sub_comments': metrics.get('sub_comments', 0),
                    
                    # 层级关系
                    'parent_comment_id': parent_id,
                    'root_comment_id': comment.get('root_comment_id'),
                    'reply_to_user_id': comment.get('reply_to_user_id'),
                    'reply_to_user_nickname': comment.get('reply_to_user_nickname'),
                    'comment_level': comment.get('comment_level', 1),
                    
                    # 其他
                    'task_id': comment.get('task_id'),
                    'crawl_time': comment.get('crawl_time'),
                    'extra': comment.get('extra', {})
                }
                
                batch_data.append(data)
                
            except Exception as e:
                print(f"❌ 处理评论 {comment.get('id')} 失败: {e}")
                continue
        
        # 批量插入
        if batch_data:
            try:
                result = supabase.table('comments').upsert(
                    batch_data,
                    on_conflict='id'
                ).execute()
                
                success_count += len(batch_data)
                print(f"📊 已导入 {success_count}/{len(unique_comments)} 条评论")
                
            except Exception as e:
                print(f"❌ 批量插入失败: {e}")
                # 逐条插入
                print("🔄 尝试逐条插入...")
                for item in batch_data:
                    try:
                        supabase.table('comments').upsert([item], on_conflict='id').execute()
                        success_count += 1
                        print(f"  ✅ {item['id']}")
                    except Exception as e2:
                        print(f"  ❌ {item.get('id')}: {str(e2)[:100]}")
    
    print(f"✅ 评论导入完成: {success_count}/{len(unique_comments)} 条")
    return success_count

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 使用 Supabase SDK 导入统一格式数据")
    print("=" * 60)
    
    # 检查配置
    if SUPABASE_KEY == "your_supabase_anon_key":
        print("❌ 请先配置 SUPABASE_KEY")
        print("\n📋 获取步骤：")
        print("1. 登录 Supabase Dashboard")
        print("2. 选择你的项目")
        print("3. Settings → API")
        print("4. 复制 'anon' 或 'public' key")
        print("5. 粘贴到本文件第13行")
        return
    
    # 创建客户端
    supabase = create_supabase_client()
    if not supabase:
        return
    
    # 测试连接
    if not test_connection(supabase):
        print("\n💡 请先执行 database/schema_supabase.sql 创建表结构")
        return
    
    # 选择平台
    print("\n请选择要导入的平台数据:")
    print("1. 微博 (data/unified/weibo/)")
    print("2. 小红书 (data/unified/xhs/)")
    print("3. 网易新闻 (data/unified/wangyi/)")
    print("4. 全部")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    platforms = []
    if choice == '1':
        platforms = ['weibo']
    elif choice == '2':
        platforms = ['xhs']
    elif choice == '3':
        platforms = ['wangyi']
    elif choice == '4':
        platforms = ['weibo', 'xhs', 'wangyi']
    else:
        print("❌ 无效选项")
        return
    
    # 导入数据
    total_posts = 0
    total_comments = 0
    
    for platform in platforms:
        data_dir = f'data/unified/{platform}'
        
        if not os.path.exists(data_dir):
            print(f"⚠️ 目录不存在: {data_dir}")
            continue
        
        print(f"\n{'='*60}")
        print(f"📁 处理 {platform.upper()} 数据")
        print(f"{'='*60}")
        
        # 查找帖子文件（支持 posts 和 contents 两种命名）
        all_files = os.listdir(data_dir)
        post_files = [f for f in all_files if ('posts' in f or 'contents' in f) and f.endswith('.json')]
        for file in post_files:
            file_path = os.path.join(data_dir, file)
            print(f"\n📝 导入帖子: {file}")
            total_posts += import_posts_with_sdk(supabase, file_path)
        
        # 查找评论文件
        comment_files = [f for f in os.listdir(data_dir) if 'comments' in f and f.endswith('.json')]
        for file in comment_files:
            file_path = os.path.join(data_dir, file)
            print(f"\n💬 导入评论: {file}")
            total_comments += import_comments_with_sdk(supabase, file_path)
    
    print(f"\n{'='*60}")
    print("🎉 导入完成！")
    print(f"{'='*60}")
    print(f"📊 总计导入:")
    print(f"   帖子: {total_posts} 条")
    print(f"   评论: {total_comments} 条")
    print(f"\n🌐 访问 Supabase Dashboard 查看数据:")
    print(f"   {SUPABASE_URL}/project/_/editor")

if __name__ == '__main__':
    main()
