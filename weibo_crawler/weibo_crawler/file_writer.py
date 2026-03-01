# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class WeiboFileWriter:
    """微博数据文件写入器 - 按日期增量保存"""
    
    def __init__(self, base_path: str = "data/unified/weibo"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def _get_file_path(self, item_type: str) -> Path:
        """
        获取文件路径，按日期命名
        :param item_type: 'posts' or 'comments'
        :return: Path对象
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_name = f"search_{item_type}_{date_str}.json"
        return self.base_path / file_name
    
    def _load_existing_data(self, file_path: Path) -> List[Dict]:
        """
        加载已存在的数据
        :param file_path: 文件路径
        :return: 数据列表
        """
        if not file_path.exists() or file_path.stat().st_size == 0:
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    return []
                data = json.loads(content)
                # 确保返回列表
                if not isinstance(data, list):
                    return [data]
                return data
        except json.JSONDecodeError:
            print(f"⚠️ Warning: Failed to parse {file_path}, starting fresh.")
            return []
        except Exception as e:
            print(f"⚠️ Warning: Error reading {file_path}: {e}")
            return []
    
    def save_posts(self, new_posts: List[Dict]) -> int:
        """
        增量保存帖子数据
        :param new_posts: 新的帖子列表
        :return: 保存后的总数量
        """
        if not new_posts:
            return 0
        
        file_path = self._get_file_path('posts')
        existing_data = self._load_existing_data(file_path)
        
        # 去重：基于 mid 字段
        existing_mids = {post.get('mid') for post in existing_data if post.get('mid')}
        new_unique_posts = [post for post in new_posts if post.get('mid') not in existing_mids]
        
        # 合并数据
        all_data = existing_data + new_unique_posts
        
        # 保存
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Posts saved: {len(new_unique_posts)} new, {len(existing_data)} existing → Total: {len(all_data)}")
        print(f"  File: {file_path}")
        
        return len(all_data)
    
    def save_comments(self, new_comments: List[Dict]) -> int:
        """
        增量保存评论数据
        :param new_comments: 新的评论列表
        :return: 保存后的总数量
        """
        if not new_comments:
            return 0
        
        file_path = self._get_file_path('comments')
        existing_data = self._load_existing_data(file_path)
        
        # 去重：基于 comment_id 字段
        existing_ids = {c.get('comment_id') for c in existing_data if c.get('comment_id')}
        new_unique_comments = [c for c in new_comments if c.get('comment_id') not in existing_ids]
        
        # 合并数据
        all_data = existing_data + new_unique_comments
        
        # 保存
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Comments saved: {len(new_unique_comments)} new, {len(existing_data)} existing → Total: {len(all_data)}")
        print(f"  File: {file_path}")
        
        return len(all_data)
