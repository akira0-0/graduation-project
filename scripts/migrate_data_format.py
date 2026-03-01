#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据格式迁移脚本
将现有的小红书和微博数据转换为统一格式
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.data_format_converter import batch_convert_xhs_data, batch_convert_xhs_comments


def migrate_xhs_data(data_dir: str = "data/xhs/json"):
    """
    迁移小红书数据到统一格式
    
    Args:
        data_dir: 小红书数据目录
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"❌ 目录不存在: {data_dir}")
        return
    
    # 创建统一格式目录
    unified_dir = Path("data/unified/xhs")
    unified_dir.mkdir(parents=True, exist_ok=True)
    
    # 处理所有JSON文件
    json_files = list(data_path.glob("*.json"))
    print(f"📁 找到 {len(json_files)} 个文件")
    
    for json_file in json_files:
        print(f"\n处理文件: {json_file.name}")
        
        try:
            # 读取原始数据
            with open(json_file, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            
            if not isinstance(original_data, list):
                print(f"⚠️  跳过非列表文件: {json_file.name}")
                continue
            
            print(f"  📊 原始数据数量: {len(original_data)}")
            
            # 转换为统一格式
            if "comments" in json_file.name.lower():
                unified_data = batch_convert_xhs_comments(original_data)
            else:
                unified_data = batch_convert_xhs_data(original_data)
            
            # 保存统一格式数据
            output_file = unified_dir / json_file.name
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(unified_data, f, ensure_ascii=False, indent=2)
            
            print(f"  ✅ 转换完成: {len(unified_data)} 条数据")
            print(f"  💾 保存到: {output_file}")
            
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")


def migrate_weibo_data(data_dir: str = "data/weibo"):
    """
    迁移微博数据到统一格式
    
    注意：微博数据已经在新版爬虫中使用统一格式，
    这里只是将旧格式数据迁移
    
    Args:
        data_dir: 微博数据目录
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"❌ 目录不存在: {data_dir}")
        return
    
    # 创建统一格式目录
    unified_dir = Path("data/unified/weibo")
    unified_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查是否有旧格式文件
    old_format_files = list(data_path.glob("task_*_posts_*.json"))
    
    if old_format_files:
        print(f"📁 找到 {len(old_format_files)} 个旧格式文件")
        print("⚠️  微博数据需要手动检查字段映射")
        print("   旧字段 note_id → 新字段 id")
        print("   旧字段 images → 新字段 media.images")
        print("   等等...")
    else:
        print("✅ 未发现旧格式文件，可能已使用统一格式")


def show_format_comparison():
    """显示格式对比"""
    print("\n" + "="*60)
    print("📊 数据格式对比")
    print("="*60)
    
    print("\n【小红书旧格式】")
    print("  note_id, user_id, nickname, liked_count, image_list...")
    
    print("\n【微博旧格式】")
    print("  note_id, user_id, nickname, likes, images...")
    
    print("\n【统一新格式】")
    print("  id, platform, type, author.id, author.nickname,")
    print("  metrics.likes, media.images...")
    
    print("\n详细规范请查看: docs/DATA_FORMAT_STANDARD.md")
    print("="*60 + "\n")


def main():
    """主函数"""
    print("🚀 数据格式迁移工具")
    print("="*60)
    
    # 显示格式对比
    show_format_comparison()
    
    # 迁移小红书数据
    print("\n1️⃣ 迁移小红书数据...")
    migrate_xhs_data()
    
    # 检查微博数据
    print("\n2️⃣ 检查微博数据...")
    migrate_weibo_data()
    
    print("\n✅ 迁移完成！")
    print("📁 统一格式数据保存在: data/unified/")
    print("\n💡 提示:")
    print("  - 旧数据保留在原目录")
    print("  - 新数据存储在 data/unified/ 目录")
    print("  - 后续爬虫将直接使用统一格式")


if __name__ == "__main__":
    main()
