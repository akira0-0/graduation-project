# -*- coding: utf-8 -*-
"""
按日期导入数据到 Supabase
用法:
    python import_by_date.py                    # 导入今天的数据
    python import_by_date.py 2026-03-01        # 导入指定日期的数据
    python import_by_date.py 2026-03-01 weibo  # 导入指定日期的特定平台
"""
import sys
import os
from datetime import datetime, timedelta
from import_with_sdk import (
    create_supabase_client,
    import_posts_with_sdk,
    import_comments_with_sdk
)

def import_by_date(target_date: str = None, platform: str = None):
    """
    按日期导入数据
    
    Args:
        target_date: 目标日期 (YYYY-MM-DD)，默认今天
        platform: 平台名称 (weibo/xhs/wangyi)，默认全部
    """
    # 默认今天
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    # 验证日期格式
    try:
        datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ 日期格式错误: {target_date}，请使用 YYYY-MM-DD 格式")
        return
    
    print("=" * 60)
    print(f"📅 导入日期: {target_date}")
    print("=" * 60)
    
    # 创建客户端
    supabase = create_supabase_client()
    if not supabase:
        return
    
    # 确定要导入的平台
    if platform:
        platforms = [platform]
    else:
        platforms = ['weibo', 'xhs', 'wangyi']
    
    total_posts = 0
    total_comments = 0
    
    for plat in platforms:
        data_dir = f'data/unified/{plat}'
        
        if not os.path.exists(data_dir):
            print(f"⚠️ 目录不存在: {data_dir}")
            continue
        
        print(f"\n{'='*60}")
        print(f"📁 处理 {plat.upper()} ({target_date})")
        print(f"{'='*60}")
        
        # 查找指定日期的文件
        all_files = os.listdir(data_dir)
        
        # 帖子文件
        post_files = [f for f in all_files 
                      if target_date in f 
                      and ('posts' in f or 'contents' in f) 
                      and f.endswith('.json')]
        
        for file in post_files:
            file_path = os.path.join(data_dir, file)
            print(f"\n📝 导入帖子: {file}")
            count = import_posts_with_sdk(supabase, file_path)
            total_posts += count
        
        if not post_files:
            print(f"⚠️ 未找到 {target_date} 的帖子文件")
        
        # 评论文件
        comment_files = [f for f in all_files 
                        if target_date in f 
                        and 'comments' in f 
                        and f.endswith('.json')]
        
        for file in comment_files:
            file_path = os.path.join(data_dir, file)
            print(f"\n💬 导入评论: {file}")
            count = import_comments_with_sdk(supabase, file_path)
            total_comments += count
        
        if not comment_files:
            print(f"⚠️ 未找到 {target_date} 的评论文件")
    
    print(f"\n{'='*60}")
    print("🎉 导入完成！")
    print(f"{'='*60}")
    print(f"📊 总计:")
    print(f"   帖子: {total_posts} 条")
    print(f"   评论: {total_comments} 条")


if __name__ == '__main__':
    # 解析命令行参数
    args = sys.argv[1:]
    
    if len(args) == 0:
        # 无参数：导入今天
        print("💡 未指定日期，导入今天的数据")
        import_by_date()
    elif len(args) == 1:
        if args[0] in ['--help', '-h']:
            print(__doc__)
        elif args[0] in ['weibo', 'xhs', 'wangyi']:
            # 单个参数是平台：导入今天的该平台
            import_by_date(platform=args[0])
        else:
            # 单个参数是日期：导入该日期的所有平台
            import_by_date(target_date=args[0])
    elif len(args) == 2:
        # 两个参数：日期 + 平台
        import_by_date(target_date=args[0], platform=args[1])
    else:
        print("❌ 参数错误")
        print(__doc__)
