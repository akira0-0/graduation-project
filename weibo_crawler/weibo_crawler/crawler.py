import requests
import time
import random
from fake_useragent import UserAgent
from utils import build_post_data, build_comments_data
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeiboCrawler:
    def __init__(self, cookie):
        self.base_url = "https://m.weibo.cn"
        self.headers = {
            "User-Agent": UserAgent().random,
            "Cookie": cookie,
            "Accept": "application/json, text/plain, */*",
            "MWeibo-Pwa": "1",
            "Referer": "https://m.weibo.cn/search?containerid=100103type%3D1%26q%3D%E6%B5%8B%E8%AF%95",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.session = requests.Session()

    def _sleep(self):
        """Random sleep to avoid rate limiting"""
        time.sleep(random.uniform(2, 5))

    def search_posts(self, keyword, page=1):
        """
        Search for posts by keyword.
        API: /api/container/getIndex
        """
        params = {
            "containerid": f"100103type=1&q={keyword}",
            "page_type": "searchall",
            "page": page
        }
        try:
            url = f"{self.base_url}/api/container/getIndex"
            logger.info(f"Searching keyword: {keyword}, page: {page}")
            response = self.session.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                logger.error(f"Search request failed: {response.status_code}")
                return []

            data = response.json()
            if data.get("ok") != 1:
                logger.warning(f"Search API returned non-ok status: {data}")
                return []

            cards = data.get("data", {}).get("cards", [])
            posts = []
            for card in cards:
                # Type 9 is usually a standard post card
                if card.get("card_type") == 9:
                    mblog = card.get("mblog")
                    if mblog:
                        posts.append(mblog)
            return posts
        
        except Exception as e:
            logger.error(f"Error in search_posts: {e}")
            return []

    def get_comments(self, mid, max_id=0):
        """
        Fetch comments for a specific post (mid).
        API: /comments/hotflow
        """
        comments = []
        try:
            url = f"{self.base_url}/comments/hotflow"
            params = {
                "id": mid,
                "mid": mid,
                "max_id_type": 0
            }
            if max_id:
                params["max_id"] = max_id

            logger.info(f"Fetching comments for post {mid}...")
            response = self.session.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") == 1:
                    data_data = data.get("data", {})
                    comments.extend(data_data.get("data", []))
                else:
                    logger.warning(f"Comments API returned non-ok: {data}")
            else:
                logger.warning(f"Failed to fetch comments: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching comments for {mid}: {e}")
            
        return comments

    def get_long_text(self, mid):
        """
        For long posts, 'text' field is truncated. Need to fetch full text.
        API: /statuses/extend
        """
        try:
            url = f"{self.base_url}/statuses/extend?id={mid}"
            response = self.session.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") == 1:
                    return data.get("data", {}).get("longTextContent", "")
        except Exception:
            pass
        return None

    def run(self, keywords, max_pages=1, task_id="task_001"):
        all_posts = []
        all_comments = []
        
        for keyword in keywords:
            for page in range(1, max_pages + 1):
                posts = self.search_posts(keyword, page)
                if not posts:
                    logger.info("No more posts found or reached limit.")
                    break
                
                for post in posts:
                    mid = post.get("id")
                    note_id = str(mid)
                    
                    # Check if long text is needed
                    if post.get("isLongText"):
                        full_text = self.get_long_text(mid)
                        if full_text:
                            post["text"] = full_text
                    
                    # 1. Process Post
                    formatted_post = build_post_data(post, task_id)
                    # Add keyword as a tag
                    if keyword not in formatted_post["tags"]:
                        formatted_post["tags"].append(keyword)
                    all_posts.append(formatted_post)
                    
                    # 2. Process Comments
                    comments = self.get_comments(mid)
                    formatted_comments = build_comments_data(comments, note_id)
                    all_comments.extend(formatted_comments)
                    
                    self._sleep() # Be polite
                    
                    logger.info(f"Processed post {mid} with {len(formatted_comments)} comments.")
                
                self._sleep()
                
        return all_posts, all_comments