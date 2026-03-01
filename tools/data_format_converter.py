# -*- coding: utf-8 -*-
"""
数据格式统一转换工具
将小红书和微博的数据转换为统一格式
"""

import json
import time
from datetime import datetime
from typing import Dict, List


def convert_xhs_to_unified(xhs_data: Dict) -> Dict:
    """
    将小红书数据格式转换为统一格式
    
    Args:
        xhs_data: 小红书原始数据
        
    Returns:
        统一格式的数据
    """
    # 解析图片列表
    images = []
    image_list_str = xhs_data.get('image_list', '')
    if image_list_str:
        images = [img.strip() for img in image_list_str.split(',') if img.strip()]
    
    # 解析标签
    tags = []
    tag_list_str = xhs_data.get('tag_list', '')
    if tag_list_str:
        tags = [tag.strip() for tag in tag_list_str.split(',') if tag.strip()]
    
    # 将时间戳转换为标准格式
    def timestamp_to_str(ts):
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
        return ts
    
    unified_data = {
        # 基础信息
        "id": xhs_data.get('note_id', ''),
        "platform": "xhs",
        "type": xhs_data.get('type', 'normal'),
        "url": xhs_data.get('note_url', ''),
        "title": xhs_data.get('title', ''),
        "content": xhs_data.get('desc', ''),
        "publish_time": timestamp_to_str(xhs_data.get('time', '')),
        "last_update_time": timestamp_to_str(xhs_data.get('last_update_time', '')),
        
        # 作者信息
        "author": {
            "id": xhs_data.get('user_id', ''),
            "nickname": xhs_data.get('nickname', ''),
            "avatar": xhs_data.get('avatar', ''),
            "is_verified": False,  # 小红书数据中未提供，默认False
            "ip_location": xhs_data.get('ip_location', '')
        },
        
        # 媒体资源
        "media": {
            "images": images,
            "video_url": xhs_data.get('video_url', '')
        },
        
        # 互动数据
        "metrics": {
            "likes": parse_count(xhs_data.get('liked_count', '0')),
            "collects": parse_count(xhs_data.get('collected_count', '0')),
            "comments": parse_count(xhs_data.get('comment_count', '0')),
            "shares": parse_count(xhs_data.get('share_count', '0'))
        },
        
        # 标签和任务信息
        "tags": tags,
        "source_keyword": xhs_data.get('source_keyword', ''),
        "task_id": "",
        "crawl_time": xhs_data.get('last_modify_ts', int(time.time() * 1000)) // 1000,
        
        # 平台特有字段
        "extra": {
            "xsec_token": xhs_data.get('xsec_token', '')
        }
    }
    
    return unified_data


def parse_count(count_str: str) -> int:
    """
    解析点赞/收藏数（支持 "1.2万" 这种格式）
    
    Args:
        count_str: 数量字符串
        
    Returns:
        整数值
    """
    if isinstance(count_str, int):
        return count_str
    
    if not isinstance(count_str, str):
        return 0
    
    count_str = count_str.strip()
    
    # 处理 "1.2万" 格式
    if '万' in count_str:
        try:
            num = float(count_str.replace('万', ''))
            return int(num * 10000)
        except:
            return 0
    
    # 处理普通数字
    try:
        return int(count_str)
    except:
        return 0


def convert_xhs_comment_to_unified(comment_data: Dict) -> Dict:
    """
    将小红书评论数据转换为统一格式
    
    Args:
        comment_data: 小红书评论原始数据
        
    Returns:
        统一格式的评论数据
    """
    unified_comment = {
        # 基础信息
        "id": comment_data.get('comment_id', ''),
        "content_id": comment_data.get('note_id', ''),
        "platform": "xhs",
        "content": comment_data.get('content', ''),
        "publish_time": datetime.fromtimestamp(
            comment_data.get('create_time', 0) / 1000
        ).strftime('%Y-%m-%d %H:%M:%S') if comment_data.get('create_time') else '',
        
        # 作者信息
        "author": {
            "id": comment_data.get('user_id', ''),
            "nickname": comment_data.get('nickname', ''),
            "avatar": comment_data.get('avatar', ''),
            "ip_location": comment_data.get('ip_location', '')
        },
        
        # 互动数据
        "metrics": {
            "likes": parse_count(comment_data.get('like_count', '0')),
            "sub_comments": comment_data.get('sub_comment_count', 0)
        },
        
        # 评论层级
        "parent_comment_id": comment_data.get('parent_comment_id', None),
        "root_comment_id": comment_data.get('comment_id', ''),
        
        # 任务信息
        "task_id": "",
        "crawl_time": int(time.time())
    }
    
    return unified_comment


def batch_convert_xhs_data(xhs_data_list: List[Dict]) -> List[Dict]:
    """
    批量转换小红书数据
    
    Args:
        xhs_data_list: 小红书数据列表
        
    Returns:
        统一格式数据列表
    """
    return [convert_xhs_to_unified(data) for data in xhs_data_list]


def batch_convert_xhs_comments(comment_list: List[Dict]) -> List[Dict]:
    """
    批量转换小红书评论数据
    
    Args:
        comment_list: 小红书评论列表
        
    Returns:
        统一格式评论列表
    """
    return [convert_xhs_comment_to_unified(comment) for comment in comment_list]


if __name__ == "__main__":
    # 测试转换
    sample_xhs_data = {
        "note_id": "6932df71000000001e00d1f4",
        "type": "video",
        "title": "去丽江一定要拍的人生转场！",
        "desc": "超简单！！包会的",
        "time": 1764941681000,
        "user_id": "597767756a6a6964241d282e",
        "nickname": "真里牙",
        "liked_count": "6.8万",
        "collected_count": "2.6万",
        "comment_count": "310",
        "share_count": "5883"
    }
    
    result = convert_xhs_to_unified(sample_xhs_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
