# -*- coding: utf-8 -*-
"""
小红书爬虫 API 服务

启动命令: uv run python api.py
API 文档: http://localhost:8080/docs

支持平台: Windows / Linux / macOS
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, List

# Windows 兼容性修复（Linux/macOS 不需要）
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import config
from media_platform.xhs import XiaoHongShuCrawler
from tools.data_format_converter import batch_convert_xhs_data, batch_convert_xhs_comments

# Supabase 配置（从 import_with_sdk.py 同步）
SUPABASE_URL = "https://rynxtsbrwvexytmztcyh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ5bnh0c2Jyd3ZleHl0bXp0Y3loIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc4NTA5ODUsImV4cCI6MjA4MzQyNjk4NX0.0AGziOeTUQjv1cpaCfNCBST3xz97VxkMs_ggzaxthgo"


# ==================== 数据模型 ====================

class CrawlRequest(BaseModel):
    """爬虫请求"""
    keywords: str = Field(..., description="搜索关键词，多个用逗号分隔", example="美食,旅行")
    max_notes: int = Field(20, ge=1, le=200, description="最大爬取笔记数量")
    enable_comments: bool = Field(True, description="是否爬取评论")


class CrawlResponse(BaseModel):
    """爬虫响应"""
    success: bool = True
    message: str = "ok"
    keywords: str = ""
    notes_count: int = 0


class ConvertRequest(BaseModel):
    """数据转换请求"""
    source_dir: str = Field("data/xhs/json", description="源数据目录")
    target_dir: str = Field("data/unified/xhs", description="目标目录")
    filename: Optional[str] = Field(None, description="指定文件名（可选，不填则转换全部）")


class ConvertResponse(BaseModel):
    """数据转换响应"""
    success: bool = True
    message: str = "ok"
    converted_files: List[str] = []
    total_records: int = 0


class ImportRequest(BaseModel):
    """数据库导入请求"""
    platform: str = Field("xhs", description="平台: xhs, weibo, wangyi, all")
    data_dir: Optional[str] = Field(None, description="数据目录（可选，默认 data/unified/{platform}）")


class ImportResponse(BaseModel):
    """数据库导入响应"""
    success: bool = True
    message: str = "ok"
    posts_count: int = 0
    comments_count: int = 0


class WeiboCrawlRequest(BaseModel):
    """微博爬虫请求"""
    keywords: List[str] = Field(..., description="搜索关键词列表", example=["Python", "AI"])
    max_pages: int = Field(2, ge=1, le=10, description="每个关键词最大爬取页数")


class WeiboCrawlResponse(BaseModel):
    """微博爬虫响应"""
    success: bool = True
    message: str = "ok"
    keywords: List[str] = []
    posts_count: int = 0
    comments_count: int = 0


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="小红书爬虫 API",
    description="输入关键词执行爬虫任务，数据自动保存到配置的存储位置",
    version="1.0.0",
)


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "running", "message": "小红书爬虫 API 服务运行中"}


@app.post("/xhs_crawl", response_model=CrawlResponse)
async def crawl(request: CrawlRequest):
    """
    执行爬虫搜索任务
    
    - **keywords**: 搜索关键词，多个用英文逗号分隔
    - **max_notes**: 最大爬取笔记数量，默认20
    - **enable_comments**: 是否爬取评论，默认开启
    
    数据会自动保存到配置的存储位置（JSON/Excel/数据库）
    """
    # 保存原始配置
    original_keywords = config.KEYWORDS
    original_crawler_type = config.CRAWLER_TYPE
    original_max_notes = config.CRAWLER_MAX_NOTES_COUNT
    original_enable_comments = config.ENABLE_GET_COMMENTS
    
    crawler = None
    try:
        # 设置爬虫参数
        config.KEYWORDS = request.keywords
        config.CRAWLER_TYPE = "search"
        config.CRAWLER_MAX_NOTES_COUNT = request.max_notes
        config.ENABLE_GET_COMMENTS = request.enable_comments
        
        # 执行爬虫
        crawler = XiaoHongShuCrawler()
        await crawler.start()
        
        return CrawlResponse(
            success=True,
            message="爬取完成",
            keywords=request.keywords,
            notes_count=request.max_notes,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 清理爬虫资源
        if crawler:
            if getattr(crawler, "cdp_manager", None):
                try:
                    await crawler.cdp_manager.cleanup(force=True)
                except Exception:
                    pass
            elif getattr(crawler, "browser_context", None):
                try:
                    await crawler.browser_context.close()
                except Exception:
                    pass
        
        # 恢复原始配置
        config.KEYWORDS = original_keywords
        config.CRAWLER_TYPE = original_crawler_type
        config.CRAWLER_MAX_NOTES_COUNT = original_max_notes
        config.ENABLE_GET_COMMENTS = original_enable_comments


@app.post("/convert", response_model=ConvertResponse)
async def convert_data(request: ConvertRequest):
    """
    将小红书原始数据转换为统一格式
    
    - **source_dir**: 源数据目录，默认 data/xhs/json
    - **target_dir**: 目标目录，默认 data/unified/xhs
    - **filename**: 指定单个文件（可选）
    """
    source_path = Path(request.source_dir)
    target_path = Path(request.target_dir)
    
    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"源目录不存在: {request.source_dir}")
    
    # 创建目标目录
    target_path.mkdir(parents=True, exist_ok=True)
    
    # 获取要处理的文件
    if request.filename:
        json_files = [source_path / request.filename]
        if not json_files[0].exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {request.filename}")
    else:
        json_files = list(source_path.glob("*.json"))
    
    if not json_files:
        raise HTTPException(status_code=404, detail="未找到JSON文件")
    
    converted_files = []
    total_records = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            
            if not isinstance(original_data, list):
                continue
            
            # 根据文件名判断是评论还是内容
            if "comment" in json_file.name.lower():
                unified_data = batch_convert_xhs_comments(original_data)
            else:
                unified_data = batch_convert_xhs_data(original_data)
            
            # 保存到目标目录
            output_file = target_path / json_file.name
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(unified_data, f, ensure_ascii=False, indent=2)
            
            converted_files.append(json_file.name)
            total_records += len(unified_data)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"处理文件 {json_file.name} 失败: {str(e)}")
    
    return ConvertResponse(
        success=True,
        message=f"转换完成，共处理 {len(converted_files)} 个文件",
        converted_files=converted_files,
        total_records=total_records,
    )


@app.get("/files")
async def list_files(dir: str = "data/xhs/json"):
    """
    列出目录下的JSON文件
    
    - **dir**: 目录路径
    """
    path = Path(dir)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"目录不存在: {dir}")
    
    files = [f.name for f in path.glob("*.json")]
    return {"dir": dir, "files": files, "count": len(files)}


# ==================== 数据库导入辅助函数 ====================

def parse_datetime(time_str):
    """解析时间字符串为ISO格式"""
    from datetime import datetime
    
    if not time_str:
        return None
    
    if isinstance(time_str, str) and len(time_str) == 19 and time_str[10] == ' ':
        return time_str
    
    # 尝试解析微博格式
    try:
        parts = time_str.split()
        if len(parts) == 6:
            time_str_clean = ' '.join(parts[:-1])
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


def import_posts_to_supabase(supabase, file_path: str) -> int:
    """导入帖子到 Supabase"""
    with open(file_path, 'r', encoding='utf-8') as f:
        posts = json.load(f)
    
    # 去重
    seen_ids = set()
    unique_posts = []
    for post in posts:
        post_id = post.get('id')
        if post_id and post_id not in seen_ids:
            seen_ids.add(post_id)
            unique_posts.append(post)
    
    success_count = 0
    batch_size = 20
    
    for i in range(0, len(unique_posts), batch_size):
        batch = unique_posts[i:i + batch_size]
        batch_data = []
        
        for post in batch:
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
                'author_id': author.get('id'),
                'author_nickname': author.get('nickname'),
                'author_avatar': author.get('avatar'),
                'author_is_verified': author.get('is_verified', False),
                'author_ip_location': author.get('ip_location'),
                'media_images': media.get('images', []),
                'media_video_url': media.get('video_url'),
                'metrics_likes': metrics.get('likes', 0),
                'metrics_collects': metrics.get('collects', 0),
                'metrics_comments': metrics.get('comments', 0),
                'metrics_shares': metrics.get('shares', 0),
                'tags': post.get('tags', []),
                'source_keyword': post.get('source_keyword'),
                'task_id': post.get('task_id'),
                'crawl_time': post.get('crawl_time'),
                'extra': post.get('extra', {})
            }
            batch_data.append(data)
        
        if batch_data:
            supabase.table('posts').upsert(batch_data, on_conflict='id').execute()
            success_count += len(batch_data)
    
    return success_count


def import_comments_to_supabase(supabase, file_path: str) -> int:
    """导入评论到 Supabase"""
    with open(file_path, 'r', encoding='utf-8') as f:
        comments = json.load(f)
    
    # 去重
    seen_ids = set()
    unique_comments = []
    for comment in comments:
        comment_id = comment.get('id')
        if comment_id and comment_id not in seen_ids:
            seen_ids.add(comment_id)
            unique_comments.append(comment)
    
    success_count = 0
    batch_size = 20
    
    for i in range(0, len(unique_comments), batch_size):
        batch = unique_comments[i:i + batch_size]
        batch_data = []
        
        for comment in batch:
            author = comment.get('author', {})
            metrics = comment.get('metrics', {})
            
            parent_id = comment.get('parent_comment_id')
            if parent_id == 0 or parent_id == "0":
                parent_id = None
            
            data = {
                'id': comment.get('id'),
                'content_id': comment.get('content_id'),
                'platform': comment.get('platform'),
                'content': comment.get('content'),
                'publish_time': parse_datetime(comment.get('publish_time')),
                'author_id': author.get('id'),
                'author_nickname': author.get('nickname'),
                'author_avatar': author.get('avatar'),
                'author_ip_location': author.get('ip_location'),
                'metrics_likes': metrics.get('likes', 0),
                'metrics_sub_comments': metrics.get('sub_comments', 0),
                'parent_comment_id': parent_id,
                'root_comment_id': comment.get('root_comment_id'),
                'reply_to_user_id': comment.get('reply_to_user_id'),
                'reply_to_user_nickname': comment.get('reply_to_user_nickname'),
                'comment_level': comment.get('comment_level', 1),
                'task_id': comment.get('task_id'),
                'crawl_time': comment.get('crawl_time'),
                'extra': comment.get('extra', {})
            }
            batch_data.append(data)
        
        if batch_data:
            supabase.table('comments').upsert(batch_data, on_conflict='id').execute()
            success_count += len(batch_data)
    
    return success_count


@app.post("/import", response_model=ImportResponse)
async def import_to_database(request: ImportRequest):
    """
    将统一格式数据导入到 Supabase 数据库
    
    - **platform**: 平台名称 (xhs, weibo, wangyi, all)
    - **data_dir**: 数据目录（可选）
    """
    try:
        from supabase import create_client
    except ImportError:
        raise HTTPException(status_code=500, detail="请安装 supabase: pip install supabase")
    
    # 创建 Supabase 客户端
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接数据库失败: {str(e)}")
    
    # 确定要处理的平台
    if request.platform == "all":
        platforms = ["xhs", "weibo", "wangyi"]
    else:
        platforms = [request.platform]
    
    total_posts = 0
    total_comments = 0
    
    for platform in platforms:
        data_dir = request.data_dir or f"data/unified/{platform}"
        data_path = Path(data_dir)
        
        if not data_path.exists():
            continue
        
        # 导入帖子
        post_files = [f for f in data_path.glob("*.json") if 'posts' in f.name or 'contents' in f.name]
        for file in post_files:
            try:
                total_posts += import_posts_to_supabase(supabase, str(file))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"导入帖子失败 {file.name}: {str(e)}")
        
        # 导入评论
        comment_files = [f for f in data_path.glob("*.json") if 'comments' in f.name]
        for file in comment_files:
            try:
                total_comments += import_comments_to_supabase(supabase, str(file))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"导入评论失败 {file.name}: {str(e)}")
    
    return ImportResponse(
        success=True,
        message=f"导入完成",
        posts_count=total_posts,
        comments_count=total_comments,
    )


# ==================== 微博爬虫 ====================

@app.post("/weibo_crawl", response_model=WeiboCrawlResponse)
async def weibo_crawl(request: WeiboCrawlRequest):
    """
    执行微博爬虫搜索任务
    
    - **keywords**: 搜索关键词列表
    - **max_pages**: 每个关键词最大爬取页数，默认2
    
    数据自动保存到 data/unified/weibo/ 目录
    """
    import datetime
    import importlib.util
    
    # 动态导入微博爬虫模块
    weibo_crawler_path = Path("weibo_crawler/weibo_crawler").resolve()
    
    try:
        # 先导入 utils 模块（crawler 依赖它）
        utils_spec = importlib.util.spec_from_file_location(
            "utils", weibo_crawler_path / "utils.py"
        )
        utils_module = importlib.util.module_from_spec(utils_spec)
        sys.modules["utils"] = utils_module
        utils_spec.loader.exec_module(utils_module)
        
        # 导入 crawler 模块
        crawler_spec = importlib.util.spec_from_file_location(
            "crawler", weibo_crawler_path / "crawler.py"
        )
        crawler_module = importlib.util.module_from_spec(crawler_spec)
        sys.modules["crawler"] = crawler_module
        crawler_spec.loader.exec_module(crawler_module)
        WeiboCrawler = crawler_module.WeiboCrawler
        
        # 导入 file_writer 模块
        writer_spec = importlib.util.spec_from_file_location(
            "file_writer", weibo_crawler_path / "file_writer.py"
        )
        writer_module = importlib.util.module_from_spec(writer_spec)
        sys.modules["file_writer"] = writer_module
        writer_spec.loader.exec_module(writer_module)
        WeiboFileWriter = writer_module.WeiboFileWriter
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入微博爬虫模块失败: {str(e)}")
    
    # 读取微博配置
    config_path = Path("weibo_crawler/weibo_crawler/config.json")
    if not config_path.exists():
        raise HTTPException(status_code=500, detail="微博配置文件不存在，请先配置 weibo_crawler/weibo_crawler/config.json")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            weibo_config = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取微博配置失败: {str(e)}")
    
    cookie = weibo_config.get("cookie", "")
    if not cookie or len(cookie) < 50:
        raise HTTPException(status_code=400, detail="微博 Cookie 无效，请在 config.json 中配置有效的 Cookie")
    
    try:
        # 初始化爬虫和文件写入器
        task_id = f"task_{datetime.datetime.now().strftime('%Y%m%d')}"
        data_dir = Path("data/unified/weibo")
        
        crawler = WeiboCrawler(cookie)
        file_writer = WeiboFileWriter(base_path=str(data_dir))
        
        # 执行爬虫（同步执行，因为微博爬虫是同步的）
        loop = asyncio.get_event_loop()
        posts, comments = await loop.run_in_executor(
            None, 
            lambda: crawler.run(request.keywords, request.max_pages, task_id)
        )
        
        # 保存结果
        total_posts = file_writer.save_posts(posts)
        total_comments = file_writer.save_comments(comments)
        
        return WeiboCrawlResponse(
            success=True,
            message="微博爬取完成",
            keywords=request.keywords,
            posts_count=len(posts),
            comments_count=len(comments),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"微博爬虫执行失败: {str(e)}")


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
