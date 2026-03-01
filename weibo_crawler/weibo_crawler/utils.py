import json
import time
from datetime import datetime
import re

def format_time(weibo_time_str):
    """
    Format Weibo time string to standard YYYY-MM-DD HH:MM:SS format.
    Weibo API returns various time formats like "Just now", "x minutes ago", "Today HH:MM", "MM-DD", "YYYY-MM-DD".
    This is a simplified handler. For robust academic use, more complex parsing is needed.
    """
    if not weibo_time_str:
        return ""
        
    # In a real scenario, this needs complex parsing logic. 
    # For now, we return current time if parsing fails or return the string as is if it looks like a date.
    # Academic research might need precise parsing.
    
    # Simple fallback: return current time for "Just now" or relative times to avoid complex date math dependencies for this demo
    if "前" in weibo_time_str or "刚才" in weibo_time_str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if "昨天" in weibo_time_str:
        # Handle "Yesterday" logic if needed, simplify for now
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Placeholder
        
    # Attempt to handle MM-DD (Current Year)
    if "-" in weibo_time_str and len(weibo_time_str) <= 5:
        year = datetime.now().year
        return f"{year}-{weibo_time_str} 00:00:00"

    return weibo_time_str # Return original if it's already a date or unhandled

def clean_text(text):
    """Remove HTML tags and extra whitespace."""
    if not text:
        return ""
    # Simple tag removal (for better results, use BeautifulSoup)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def build_post_data(post_data, task_id=""):
    """
    Construct the post JSON object following unified data format.
    Matches unified schema defined in docs/DATA_FORMAT_STANDARD.md
    """
    user = post_data.get('user', {})
    content_id = str(post_data.get('id', ''))
    text = clean_text(post_data.get('text', ''))
    
    post_info = {
        # 基础信息
        "id": content_id,
        "platform": "weibo",
        "type": "video" if post_data.get('page_info', {}).get('type') == 'video' else "image" if post_data.get('pics') else "text",
        "url": f"https://m.weibo.cn/detail/{content_id}",
        "title": text[:50] + "..." if len(text) > 50 else text,
        "content": text,
        "publish_time": post_data.get('created_at', ''),
        "last_update_time": post_data.get('created_at', ''),
        
        # 作者信息
        "author": {
            "id": str(user.get('id', '')),
            "nickname": user.get('screen_name', ''),
            "avatar": user.get('avatar_hd', user.get('profile_image_url', '')),
            "is_verified": user.get('verified', False),
            "ip_location": post_data.get('region_name', '')
        },
        
        # 媒体资源
        "media": {
            "images": [p.get('large', {}).get('url', '') for p in post_data.get('pics', [])] if post_data.get('pics') else [],
            "video_url": post_data.get('page_info', {}).get('urls', {}).get('mp4_720p_mp4', '') if post_data.get('page_info', {}).get('type') == 'video' else ""
        },
        
        # 互动数据
        "metrics": {
            "likes": post_data.get('attitudes_count', 0),
            "collects": post_data.get('pending_approval_count', 0),
            "comments": post_data.get('comments_count', 0),
            "shares": post_data.get('reposts_count', 0)
        },
        
        # 标签和任务信息
        "tags": [],
        "source_keyword": "",
        "task_id": task_id,
        "crawl_time": int(time.time()),
        
        # 平台特有字段
        "extra": {
            "weibo_mid": post_data.get('mid', ''),
            "source": post_data.get('source', ''),
            "is_long_text": post_data.get('isLongText', False)
        }
    }
    
    return post_info

def build_comments_data(comments_data, content_id):
    """
    Construct the comments JSON object list following unified data format.
    Matches unified schema defined in docs/DATA_FORMAT_STANDARD.md
    """
    formatted_comments = []
    for c in comments_data:
        c_user = c.get('user', {})
        comment_id = str(c.get('id', ''))
        
        formatted_comments.append({
            # 基础信息
            "id": comment_id,
            "content_id": content_id,
            "platform": "weibo",
            "content": clean_text(c.get('text', '')),
            "publish_time": c.get('created_at', ''),
            
            # 作者信息
            "author": {
                "id": str(c_user.get('id', '')),
                "nickname": c_user.get('screen_name', 'Unknown'),
                "avatar": c_user.get('profile_image_url', ''),
                "ip_location": c.get('source', '')
            },
            
            # 互动数据
            "metrics": {
                "likes": c.get('like_count', 0),
                "sub_comments": c.get('total_number', 0)
            },
            
            # 评论层级
            "parent_comment_id": str(c.get('reply_id', '')) if c.get('reply_id') else None,
            "root_comment_id": str(c.get('rootid', comment_id)),
            
            # 任务信息
            "task_id": "",
            "crawl_time": int(time.time())
        })
    return formatted_comments