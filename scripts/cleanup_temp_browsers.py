# -*- coding: utf-8 -*-
"""
清理临时浏览器数据目录
用于清理由自动化爬虫创建的临时 user_data_dir

使用方法:
    python scripts/cleanup_temp_browsers.py
    python scripts/cleanup_temp_browsers.py --dry-run  # 仅显示，不删除
    python scripts/cleanup_temp_browsers.py --keep-latest 5  # 保留最新的5个
"""
import os
import shutil
import re
import argparse
from pathlib import Path
from datetime import datetime


def parse_temp_dir_info(dirname: str) -> dict:
    """
    从目录名中解析信息
    格式: xhs_user_data_dir_pid12345_1234567890123
    或: cdp_xhs_user_data_dir_pid12345_1234567890123
    
    Returns:
        {'platform': 'xhs', 'pid': 12345, 'timestamp': 1234567890123, 'is_cdp': False}
    """
    # 匹配模式: (cdp_)?platform_user_data_dir_pidXXXX_timestamp
    pattern = r'(cdp_)?(\w+)_user_data_dir_pid(\d+)_(\d+)'
    match = re.match(pattern, dirname)
    
    if not match:
        return None
    
    return {
        'is_cdp': bool(match.group(1)),
        'platform': match.group(2),
        'pid': int(match.group(3)),
        'timestamp': int(match.group(4)),
        'dirname': dirname
    }


def find_temp_browser_dirs(browser_data_dir: str = None) -> list:
    """
    查找所有临时浏览器目录
    
    Args:
        browser_data_dir: 浏览器数据目录路径，默认为 ./browser_data
        
    Returns:
        临时目录信息列表
    """
    if browser_data_dir is None:
        browser_data_dir = os.path.join(os.getcwd(), 'browser_data')
    
    if not os.path.exists(browser_data_dir):
        return []
    
    temp_dirs = []
    
    for item in os.listdir(browser_data_dir):
        item_path = os.path.join(browser_data_dir, item)
        if not os.path.isdir(item_path):
            continue
        
        info = parse_temp_dir_info(item)
        if info:
            info['path'] = item_path
            # 计算目录大小
            info['size_mb'] = get_dir_size(item_path) / (1024 * 1024)
            # 转换时间戳为可读格式
            info['created_time'] = datetime.fromtimestamp(info['timestamp'] / 1000)
            temp_dirs.append(info)
    
    # 按时间戳排序（最新的在前）
    temp_dirs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return temp_dirs


def get_dir_size(path: str) -> int:
    """获取目录大小（字节）"""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat(follow_symlinks=False).st_size
            elif entry.is_dir(follow_symlinks=False):
                total += get_dir_size(entry.path)
    except PermissionError:
        pass
    return total


def cleanup_temp_dirs(temp_dirs: list, keep_latest: int = 0, dry_run: bool = False):
    """
    清理临时目录
    
    Args:
        temp_dirs: 临时目录列表
        keep_latest: 保留最新的 N 个目录
        dry_run: 仅显示，不实际删除
    """
    if keep_latest > 0:
        dirs_to_delete = temp_dirs[keep_latest:]
    else:
        dirs_to_delete = temp_dirs
    
    if not dirs_to_delete:
        print("✓ 没有需要清理的临时目录")
        return
    
    print(f"\n{'[试运行] ' if dry_run else ''}准备清理 {len(dirs_to_delete)} 个临时目录:")
    print("=" * 80)
    
    total_size = 0
    for info in dirs_to_delete:
        status = "跳过" if dry_run else "删除"
        print(f"{status}: {info['dirname']}")
        print(f"  平台: {info['platform']} {'(CDP)' if info['is_cdp'] else ''}")
        print(f"  创建时间: {info['created_time']}")
        print(f"  大小: {info['size_mb']:.2f} MB")
        print(f"  路径: {info['path']}")
        total_size += info['size_mb']
        
        if not dry_run:
            try:
                shutil.rmtree(info['path'], ignore_errors=True)
                print(f"  ✓ 已删除")
            except Exception as e:
                print(f"  ✗ 删除失败: {e}")
        print()
    
    print("=" * 80)
    print(f"总计: {len(dirs_to_delete)} 个目录, {total_size:.2f} MB")
    if dry_run:
        print("\n提示: 使用不带 --dry-run 参数运行以实际删除")


def main():
    parser = argparse.ArgumentParser(
        description='清理临时浏览器数据目录',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 清理所有临时目录
  python scripts/cleanup_temp_browsers.py
  
  # 仅查看，不删除
  python scripts/cleanup_temp_browsers.py --dry-run
  
  # 保留最新的5个目录，删除其他
  python scripts/cleanup_temp_browsers.py --keep-latest 5
  
  # 指定浏览器数据目录
  python scripts/cleanup_temp_browsers.py --dir /path/to/browser_data
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅显示将要删除的目录，不实际删除'
    )
    
    parser.add_argument(
        '--keep-latest', '-k',
        type=int,
        default=0,
        help='保留最新的 N 个目录（默认: 0，删除所有）'
    )
    
    parser.add_argument(
        '--dir', '-d',
        type=str,
        default=None,
        help='浏览器数据目录路径（默认: ./browser_data）'
    )
    
    args = parser.parse_args()
    
    print("🔍 扫描临时浏览器目录...")
    temp_dirs = find_temp_browser_dirs(args.dir)
    
    if not temp_dirs:
        print("✓ 未找到临时浏览器目录")
        return
    
    print(f"\n找到 {len(temp_dirs)} 个临时浏览器目录:")
    print("=" * 80)
    
    total_size = 0
    for i, info in enumerate(temp_dirs, 1):
        print(f"{i}. {info['dirname']}")
        print(f"   平台: {info['platform']} {'(CDP)' if info['is_cdp'] else ''}")
        print(f"   创建: {info['created_time']}")
        print(f"   大小: {info['size_mb']:.2f} MB")
        total_size += info['size_mb']
    
    print("=" * 80)
    print(f"总计: {len(temp_dirs)} 个目录, {total_size:.2f} MB\n")
    
    if args.keep_latest > 0:
        print(f"将保留最新的 {args.keep_latest} 个目录\n")
    
    # 执行清理
    cleanup_temp_dirs(temp_dirs, args.keep_latest, args.dry_run)


if __name__ == '__main__':
    main()
