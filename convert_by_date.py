# -*- coding: utf-8 -*-
"""
按日期转换数据格式
将指定日期的小红书原始数据转换为统一格式

用法:
    python convert_by_date.py                   # 转换今天的数据
    python convert_by_date.py 2026-03-01       # 转换指定日期的数据
    python convert_by_date.py 2026-03-01 xhs   # 转换指定日期的特定平台
"""
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.data_format_converter import (
    convert_xhs_to_unified,
    convert_xhs_comment_to_unified,
    batch_convert_xhs_data,
    batch_convert_xhs_comments
)


def find_files_by_date(data_dir: str, target_date: str, file_pattern: str) -> list:
    """
    查找指定日期的数据文件
    
    Args:
        data_dir: 数据目录
        target_date: 目标日期 (YYYY-MM-DD)
        file_pattern: 文件名模式 (如 'note', 'comment')
    
    Returns:
        匹配的文件路径列表
    """
    if not os.path.exists(data_dir):
        return []
    
    files = []
    for filename in os.listdir(data_dir):
        if (target_date in filename and 
            file_pattern in filename and 
            filename.endswith('.json')):
            files.append(os.path.join(data_dir, filename))
    
    return files


def convert_xhs_by_date(target_date: str = None):
    """
    转换指定日期的小红书数据
    
    Args:
        target_date: 目标日期 (YYYY-MM-DD)，默认今天
    """
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 60)
    print(f"📅 转换日期: {target_date}")
    print(f"📁 平台: 小红书 (XHS)")
    print("=" * 60)
    
    # 数据目录
    xhs_json_dir = 'data/xhs/json'
    unified_dir = 'data/unified/xhs'
    
    # 确保输出目录存在
    os.makedirs(unified_dir, exist_ok=True)
    
    total_posts = 0
    total_comments = 0
    
    # ========== 转换帖子数据 ==========
    print(f"\n{'='*60}")
    print("📝 转换帖子数据...")
    print(f"{'='*60}")
    
    # 小红书帖子文件名格式: search_contents_2026-03-01.json
    post_files = find_files_by_date(xhs_json_dir, target_date, 'contents')
    
    if not post_files:
        print(f"⚠️ 未找到 {target_date} 的帖子数据文件")
        print(f"   查找目录: {xhs_json_dir}")
        print(f"   查找模式: *{target_date}*contents*.json")
    else:
        all_posts = []
        
        for file_path in post_files:
            filename = os.path.basename(file_path)
            print(f"\n📖 读取: {filename}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                
                if isinstance(raw_data, list):
                    print(f"   找到 {len(raw_data)} 条原始数据")
                    converted = batch_convert_xhs_data(raw_data)
                    all_posts.extend(converted)
                    print(f"   ✅ 转换完成: {len(converted)} 条")
                else:
                    print(f"   ⚠️ 数据格式错误（应为列表）")
                    
            except Exception as e:
                print(f"   ❌ 转换失败: {e}")
        
        # 保存转换后的帖子数据
        if all_posts:
            output_file = os.path.join(unified_dir, f'search_posts_{target_date}.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_posts, f, ensure_ascii=False, indent=2)
            
            total_posts = len(all_posts)
            print(f"\n✅ 帖子数据已保存: {output_file}")
            print(f"   总计: {total_posts} 条")
    
    # ========== 转换评论数据 ==========
    print(f"\n{'='*60}")
    print("💬 转换评论数据...")
    print(f"{'='*60}")
    
    # 小红书评论文件名格式: search_comments_2026-03-01.json
    comment_files = find_files_by_date(xhs_json_dir, target_date, 'comment')
    
    if not comment_files:
        print(f"⚠️ 未找到 {target_date} 的评论数据文件")
        print(f"   查找目录: {xhs_json_dir}")
        print(f"   查找模式: *{target_date}*comment*.json")
    else:
        all_comments = []
        
        for file_path in comment_files:
            filename = os.path.basename(file_path)
            print(f"\n📖 读取: {filename}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                
                if isinstance(raw_data, list):
                    print(f"   找到 {len(raw_data)} 条原始数据")
                    converted = batch_convert_xhs_comments(raw_data)
                    all_comments.extend(converted)
                    print(f"   ✅ 转换完成: {len(converted)} 条")
                else:
                    print(f"   ⚠️ 数据格式错误（应为列表）")
                    
            except Exception as e:
                print(f"   ❌ 转换失败: {e}")
        
        # 保存转换后的评论数据
        if all_comments:
            output_file = os.path.join(unified_dir, f'search_comments_{target_date}.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_comments, f, ensure_ascii=False, indent=2)
            
            total_comments = len(all_comments)
            print(f"\n✅ 评论数据已保存: {output_file}")
            print(f"   总计: {total_comments} 条")
    
    # ========== 总结 ==========
    print(f"\n{'='*60}")
    print("🎉 转换完成！")
    print(f"{'='*60}")
    print(f"📊 总计:")
    print(f"   帖子: {total_posts} 条")
    print(f"   评论: {total_comments} 条")
    print(f"\n📁 输出目录: {unified_dir}")
    
    return total_posts, total_comments


def convert_weibo_by_date(target_date: str = None):
    """
    转换指定日期的微博数据（如果需要）
    
    Args:
        target_date: 目标日期 (YYYY-MM-DD)
    """
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 60)
    print(f"📅 转换日期: {target_date}")
    print(f"📁 平台: 微博 (Weibo)")
    print("=" * 60)
    print("💡 微博爬虫已内置统一格式转换，无需额外处理")
    print(f"   数据位置: data/unified/weibo/search_*_{target_date}.json")
    
    # 检查文件是否存在
    weibo_dir = 'data/unified/weibo'
    if os.path.exists(weibo_dir):
        files = [f for f in os.listdir(weibo_dir) if target_date in f]
        if files:
            print(f"\n✅ 找到 {len(files)} 个文件:")
            for f in files:
                print(f"   - {f}")
        else:
            print(f"\n⚠️ 未找到 {target_date} 的微博数据")
    else:
        print(f"\n⚠️ 微博数据目录不存在: {weibo_dir}")


def convert_web_by_date(target_date: str = None):
    """
    转换指定日期的网易新闻数据（如果需要）
    
    Args:
        target_date: 目标日期 (YYYY-MM-DD)
    """
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 60)
    print(f"📅 转换日期: {target_date}")
    print(f"📁 平台: 网易新闻 (Wangyi)")
    print("=" * 60)
    print("💡 网易新闻爬虫已内置统一格式转换，无需额外处理")
    print(f"   数据位置: data/unified/wangyi/search_*_{target_date}.json")
    
    # 检查文件是否存在
    web_dir = 'data/unified/wangyi'
    if os.path.exists(web_dir):
        files = [f for f in os.listdir(web_dir) if target_date in f]
        if files:
            print(f"\n✅ 找到 {len(files)} 个文件:")
            for f in files:
                print(f"   - {f}")
        else:
            print(f"\n⚠️ 未找到 {target_date} 的网易新闻数据")
    else:
        print(f"\n⚠️ 网易新闻数据目录不存在: {web_dir}")


def main():
    """主函数"""
    args = sys.argv[1:]
    
    # 解析参数
    target_date = None
    platform = None
    
    if len(args) == 0:
        print("💡 未指定日期，转换今天的数据")
        target_date = datetime.now().strftime('%Y-%m-%d')
    elif len(args) == 1:
        if args[0] in ['--help', '-h']:
            print(__doc__)
            return
        elif args[0] in ['xhs', 'weibo', 'wangyi', 'web']:
            platform = args[0]
            target_date = datetime.now().strftime('%Y-%m-%d')
        else:
            target_date = args[0]
    elif len(args) == 2:
        target_date = args[0]
        platform = args[1]
    else:
        print("❌ 参数错误")
        print(__doc__)
        return
    
    # 验证日期格式
    try:
        datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ 日期格式错误: {target_date}")
        print("   请使用 YYYY-MM-DD 格式，如: 2026-03-01")
        return
    
    # 转换数据
    if platform is None or platform == 'xhs':
        convert_xhs_by_date(target_date)
        print()
    
    if platform is None or platform == 'weibo':
        if platform == 'xhs':
            print()  # 空行分隔
        convert_weibo_by_date(target_date)
        print()
    
    if platform is None or platform in ['wangyi', 'web']:
        if platform in ['xhs', 'weibo']:
            print()
        convert_web_by_date(target_date)


if __name__ == '__main__':
    main()
