# -*- coding: utf-8 -*-
"""
爬虫运行器
负责运行各个平台的爬虫
"""
import os
import sys
import json
import asyncio
import subprocess
import time
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from . import config as cfg
from .logger import get_logger, TaskLogger

logger = get_logger(__name__)


@dataclass
class CrawlResult:
    """爬取结果"""
    platform: str
    keyword: str
    success: bool
    posts_count: int = 0
    comments_count: int = 0
    error: str = ""
    duration: float = 0


class CrawlerRunner:
    """
    爬虫运行器
    负责运行微博、小红书、网易新闻三个爬虫
    """
    
    def __init__(self, keywords: List[str]):
        self.keywords = keywords
        self.results: List[CrawlResult] = []
        self.project_root = cfg.PROJECT_ROOT
    
    async def run_all(self, parallel_all: bool = False) -> Dict[str, List[CrawlResult]]:
        """
        运行所有启用的爬虫（队列顺序执行模式）
        
        Args:
            parallel_all: 保留参数但不再使用，所有爬虫按顺序执行
        
        Returns:
            各平台的爬取结果
        """
        all_results = {
            'weibo': [],
            'xhs': [],
            'web': [],
        }
        
        # 构建任务队列
        task_queue = []
        
        if cfg.ENABLE_WEIBO:
            task_queue.append(('weibo', self.run_weibo_crawler))
        
        if cfg.ENABLE_XHS:
            task_queue.append(('xhs', self.run_xhs_crawler))
        
        if cfg.ENABLE_WEB:
            task_queue.append(('web', self.run_web_crawler))
        
        logger.info("=" * 60)
        logger.info(f"队列顺序执行模式：共 {len(task_queue)} 个爬虫任务")
        logger.info(f"执行顺序: {' -> '.join([t[0] for t in task_queue])}")
        logger.info("=" * 60)
        
        # 按顺序执行每个爬虫
        for idx, (platform_name, crawler_func) in enumerate(task_queue, 1):
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"[{idx}/{len(task_queue)}] 开始运行 {platform_name} 爬虫")
            logger.info("=" * 60)
            
            try:
                result = await crawler_func()
                all_results[platform_name] = result
                
                # 统计本次结果
                success_count = sum(1 for r in result if r.success)
                total_count = len(result)
                posts_count = sum(r.posts_count for r in result)
                comments_count = sum(r.comments_count for r in result)
                
                logger.info(f"[{idx}/{len(task_queue)}] {platform_name} 完成: "
                           f"成功 {success_count}/{total_count}, "
                           f"帖子 {posts_count}, 评论 {comments_count}")
                
            except Exception as e:
                logger.error(f"[{idx}/{len(task_queue)}] {platform_name} 爬虫异常: {e}")
                all_results[platform_name] = []
            
            # 爬虫之间间隔，避免资源冲突
            if idx < len(task_queue):
                logger.info(f"等待 3 秒后执行下一个爬虫...")
                await asyncio.sleep(3)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("所有爬虫任务执行完毕")
        logger.info("=" * 60)
        
        return all_results
    
    async def run_weibo_crawler(self) -> List[CrawlResult]:
        """
        运行微博爬虫
        微博爬虫支持多关键词，一次性传入所有关键词
        """
        task_logger = TaskLogger('weibo')
        task_logger.start()
        results = []
        
        try:
            # 读取微博配置
            weibo_config = self._load_weibo_config()
            if not weibo_config.get('cookie'):
                task_logger.error("微博 Cookie 未配置")
                return results
            
            # 更新配置文件中的关键词
            weibo_config['keywords'] = self.keywords
            weibo_config['max_pages'] = cfg.WEIBO_MAX_PAGES
            self._save_weibo_config(weibo_config)
            
            # 生成任务ID
            task_id = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 运行微博爬虫
            start_time = time.time()
            
            # 构建命令 - 在项目根目录运行
            weibo_main = os.path.join(
                'weibo_crawler', 'weibo_crawler', 'main.py'
            )
            
            success, output = await self._run_subprocess(
                ['uv', 'run', weibo_main],  # uv run 直接运行脚本
                cwd=self.project_root,
                timeout=cfg.CRAWLER_TIMEOUT * len(self.keywords)
            )
            
            duration = time.time() - start_time
            
            if success:
                # 统计结果
                posts, comments = self._count_weibo_data()
                result = CrawlResult(
                    platform='weibo',
                    keyword=','.join(self.keywords),
                    success=True,
                    posts_count=posts,
                    comments_count=comments,
                    duration=duration
                )
                results.append(result)
                task_logger.success(','.join(self.keywords[:3]) + '...', posts, comments)
            else:
                # 重试
                for attempt in range(1, cfg.RETRY_COUNT + 1):
                    task_logger.retry('微博爬虫', attempt, cfg.RETRY_COUNT)
                    await asyncio.sleep(cfg.RETRY_DELAY)
                    
                    success, output = await self._run_subprocess(
                        ['uv', 'run', weibo_main],  # uv run 直接运行脚本
                        cwd=self.project_root,
                        timeout=cfg.CRAWLER_TIMEOUT * len(self.keywords)
                    )
                    
                    if success:
                        posts, comments = self._count_weibo_data()
                        result = CrawlResult(
                            platform='weibo',
                            keyword=','.join(self.keywords),
                            success=True,
                            posts_count=posts,
                            comments_count=comments,
                            duration=time.time() - start_time
                        )
                        results.append(result)
                        task_logger.success(','.join(self.keywords[:3]) + '...', posts, comments)
                        break
                else:
                    result = CrawlResult(
                        platform='weibo',
                        keyword=','.join(self.keywords),
                        success=False,
                        error=output[:200] if output else "Unknown error",
                        duration=time.time() - start_time
                    )
                    results.append(result)
                    task_logger.fail('微博爬虫', output[:200] if output else "Unknown error")
        
        except Exception as e:
            task_logger.error(f"微博爬虫异常: {e}")
            results.append(CrawlResult(
                platform='weibo',
                keyword=','.join(self.keywords),
                success=False,
                error=str(e)
            ))
        
        task_logger.end()
        return results
    
    async def run_xhs_crawler(self) -> List[CrawlResult]:
        """
        运行小红书爬虫
        小红书爬虫一次只能处理一个关键词，需要分多次运行
        """
        task_logger = TaskLogger('xhs')
        task_logger.start()
        results = []
        
        # 记录爬虫运行前的数据量
        initial_posts, initial_comments = self._count_xhs_data_today()
        
        for keyword in self.keywords:
            result = await self._run_single_xhs(keyword, task_logger)
            results.append(result)
            
            # 关键词之间间隔，避免被封
            if keyword != self.keywords[-1]:
                await asyncio.sleep(5)
        
        # 计算实际新增的数据量
        final_posts, final_comments = self._count_xhs_data_today()
        actual_posts = final_posts - initial_posts
        actual_comments = final_comments - initial_comments
        
        # 更新 task_logger 的统计（覆盖累加的错误值）
        task_logger.stats['posts'] = actual_posts
        task_logger.stats['comments'] = actual_comments
        
        task_logger.end()
        return results
    
    async def _run_single_xhs(self, keyword: str, task_logger: TaskLogger) -> CrawlResult:
        """
        运行单个关键词的小红书爬虫
        """
        start_time = time.time()
        
        try:
            # 修改配置文件
            self._update_xhs_config(keyword)
            
            # 运行爬虫
            main_py = 'main.py'
            
            for attempt in range(cfg.RETRY_COUNT + 1):
                if attempt > 0:
                    task_logger.retry(keyword, attempt, cfg.RETRY_COUNT)
                    await asyncio.sleep(cfg.RETRY_DELAY)
                
                success, output = await self._run_subprocess(
                    ['uv', 'run', main_py],  # uv run 直接运行脚本
                    cwd=self.project_root,
                    timeout=cfg.CRAWLER_TIMEOUT
                )
                
                if success:
                    # 统计新增数据
                    posts, comments = self._count_xhs_data(keyword)
                    duration = time.time() - start_time
                    
                    task_logger.success(keyword, posts, comments)
                    return CrawlResult(
                        platform='xhs',
                        keyword=keyword,
                        success=True,
                        posts_count=posts,
                        comments_count=comments,
                        duration=duration
                    )
            
            # 所有重试都失败
            task_logger.fail(keyword, output[:200] if output else "Unknown error")
            return CrawlResult(
                platform='xhs',
                keyword=keyword,
                success=False,
                error=output[:200] if output else "Unknown error",
                duration=time.time() - start_time
            )
            
        except Exception as e:
            task_logger.fail(keyword, str(e))
            return CrawlResult(
                platform='xhs',
                keyword=keyword,
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def run_web_crawler(self) -> List[CrawlResult]:
        """
        运行网易新闻爬虫
        """
        task_logger = TaskLogger('web')
        task_logger.start()
        results = []
        
        try:
            # 更新 spider.py 中的关键词
            self._update_web_config(self.keywords)
            
            start_time = time.time()
            spider_py = os.path.join('web_crawler', 'spider.py')
            
            for attempt in range(cfg.RETRY_COUNT + 1):
                if attempt > 0:
                    task_logger.retry('网易新闻', attempt, cfg.RETRY_COUNT)
                    await asyncio.sleep(cfg.RETRY_DELAY)
                
                success, output = await self._run_subprocess(
                    ['uv', 'run', spider_py],  # uv run 直接运行脚本
                    cwd=self.project_root,
                    timeout=cfg.CRAWLER_TIMEOUT * len(self.keywords)
                )
                
                if success:
                    posts, comments = self._count_web_data()
                    duration = time.time() - start_time
                    
                    task_logger.success(','.join(self.keywords[:3]) + '...', posts, comments)
                    results.append(CrawlResult(
                        platform='web',
                        keyword=','.join(self.keywords),
                        success=True,
                        posts_count=posts,
                        comments_count=comments,
                        duration=duration
                    ))
                    break
            else:
                task_logger.fail('网易新闻', output[:200] if output else "Unknown error")
                results.append(CrawlResult(
                    platform='web',
                    keyword=','.join(self.keywords),
                    success=False,
                    error=output[:200] if output else "Unknown error",
                    duration=time.time() - start_time
                ))
                
        except Exception as e:
            task_logger.error(f"网易新闻爬虫异常: {e}")
            results.append(CrawlResult(
                platform='web',
                keyword=','.join(self.keywords),
                success=False,
                error=str(e)
            ))
        
        task_logger.end()
        return results
    
    async def _run_subprocess(
        self, 
        cmd: List[str], 
        cwd: str, 
        timeout: int
    ) -> Tuple[bool, str]:
        """
        运行子进程
        
        Returns:
            (是否成功, 输出/错误信息)
        """
        try:
            logger.debug(f"运行命令: {' '.join(cmd)}")
            logger.debug(f"工作目录: {cwd}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # 合并 stderr 到 stdout
            )
            
            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                output = stdout.decode('utf-8', errors='replace')
                
                # 打印输出到日志
                if output:
                    for line in output.split('\n')[-30:]:  # 最后30行
                        if line.strip():
                            logger.info(f"[子进程] {line}")
                
                if process.returncode == 0:
                    return True, output
                else:
                    logger.warning(f"进程返回码: {process.returncode}")
                    return False, output
                    
            except asyncio.TimeoutError:
                process.kill()
                logger.error(f"进程超时 ({timeout}s)")
                return False, f"Timeout after {timeout}s"
                
        except Exception as e:
            logger.error(f"运行子进程失败: {e}")
            return False, str(e)
    
    def _load_weibo_config(self) -> dict:
        """加载微博配置"""
        try:
            with open(cfg.WEIBO_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_weibo_config(self, config: dict):
        """保存微博配置"""
        with open(cfg.WEIBO_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def _update_xhs_config(self, keyword: str):
        """
        更新小红书配置（修改 config/base_config.py 中的 KEYWORDS）
        """
        config_path = os.path.join(self.project_root, 'config', 'base_config.py')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则替换 KEYWORDS
        import re
        pattern = r'KEYWORDS\s*=\s*["\'].*?["\']'
        replacement = f'KEYWORDS = "{keyword}"'
        new_content = re.sub(pattern, replacement, content)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.debug(f"已更新小红书关键词: {keyword}")
    
    def _update_web_config(self, keywords: List[str]):
        """
        更新网易新闻爬虫配置（修改 spider.py 中的 KEYWORDS）
        """
        spider_path = os.path.join(self.project_root, 'web_crawler', 'spider.py')
        
        with open(spider_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则替换 KEYWORDS
        import re
        keywords_str = json.dumps(keywords, ensure_ascii=False)
        pattern = r'KEYWORDS\s*=\s*\[.*?\]'
        replacement = f'KEYWORDS = {keywords_str}'
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # 同时更新 MAX_ARTICLES
        pattern2 = r'MAX_ARTICLES\s*=\s*\d+'
        replacement2 = f'MAX_ARTICLES = {cfg.WEB_MAX_ARTICLES}'
        new_content = re.sub(pattern2, replacement2, new_content)
        
        with open(spider_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.debug(f"已更新网易新闻关键词: {keywords[:3]}...")
    
    def _count_weibo_data(self) -> Tuple[int, int]:
        """统计微博数据量"""
        return self._count_unified_data('weibo')
    
    def _count_xhs_data(self, keyword: str) -> Tuple[int, int]:
        """统计小红书数据量（只统计今天的数据）- 用于单次爬取后显示"""
        return self._count_xhs_data_today()
    
    def _count_xhs_data_today(self) -> Tuple[int, int]:
        """统计今天的小红书数据量"""
        data_dir = os.path.join(self.project_root, 'data', 'xhs', 'json')
        posts = 0
        comments = 0
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            for filename in os.listdir(data_dir):
                # 只统计今天的数据文件
                if filename.endswith('.json') and today in filename:
                    filepath = os.path.join(data_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            if 'comment' in filename.lower():
                                comments += len(data)
                            else:
                                posts += len(data)
        except Exception as e:
            logger.debug(f"统计小红书数据失败: {e}")
        
        return posts, comments
    
    def _count_web_data(self) -> Tuple[int, int]:
        """统计网易新闻数据量"""
        return self._count_unified_data('wangyi')
    
    def _count_unified_data(self, platform: str) -> Tuple[int, int]:
        """统计统一格式数据量"""
        data_dir = os.path.join(cfg.UNIFIED_DIR, platform)
        posts = 0
        comments = 0
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            posts_file = os.path.join(data_dir, f'search_posts_{today}.json')
            if os.path.exists(posts_file):
                with open(posts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    posts = len(data) if isinstance(data, list) else 0
            
            comments_file = os.path.join(data_dir, f'search_comments_{today}.json')
            if os.path.exists(comments_file):
                with open(comments_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    comments = len(data) if isinstance(data, list) else 0
                    
        except Exception as e:
            logger.debug(f"统计 {platform} 数据失败: {e}")
        
        return posts, comments
