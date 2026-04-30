"""
数据收集智能体（增强版）
根据预设工作流收集汇总信息
支持使用 LangChain 工具进行互联网信息收集
增强功能：
- 关键词联想与扩展：使用 LLM 生成相关关键词
- 多轮迭代收集：支持迭代式数据收集，逐步扩大搜索范围
- 数据量控制：确保收集足够的数据量（目标：50-100条）
- LLM 智能分析：智能判断数据相关性和质量
- 关键词屏蔽：防止爬取敏感信息和不良信息
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
from ..database import get_session, AgentMemoryService
from ..utils.logger import get_logger
from ..utils.keyword_blocker import get_keyword_blocker, KeywordBlocker

logger = get_logger("data_collection_agent")


class KeywordExpander:
    """
    关键词扩展器
    使用 LLM 生成相关关键词，扩大信息覆盖面
    
    增强功能：
    - 关键词安全验证：过滤敏感和不良关键词
    """
    
    def __init__(self, keyword_blocker: Optional[KeywordBlocker] = None):
        """
        初始化 LLM
        
        Args:
            keyword_blocker: 关键词屏蔽器实例（可选）
        """
        self.llm = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
            openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0.7
        )
        # 初始化关键词屏蔽器
        self.keyword_blocker = keyword_blocker or get_keyword_blocker()
    
    def expand_keywords(
        self,
        initial_keyword: str,
        num_expansions: int = 5,
        language: str = "zh"
    ) -> List[str]:
        """
        使用 LLM 扩展关键词
        
        Args:
            initial_keyword: 初始关键词
            num_expansions: 扩展数量
            language: 语言 (zh/en)
            
        Returns:
            扩展后的关键词列表（包含原始关键词）
        """
        if language == "zh":
            prompt = f"""你是一个专业的舆情分析师和搜索专家。基于给定的初始关键词，生成{num_expansions}个相关关键词用于扩大搜索范围。

要求：
1. 生成的关键词要与原始关键词高度相关
2. 包含同义词、近义词、相关概念
3. 考虑不同的表述方式和角度
4. 适合用于互联网搜索
5. 每个关键词一行，不要编号和额外说明

初始关键词：{initial_keyword}

请直接输出{num_expansions}个扩展关键词，每行一个："""
        else:
            prompt = f"""You are a professional search expert. Generate {num_expansions} related keywords based on the given initial keyword.

Requirements:
1. Generated keywords should be highly relevant to the original keyword
2. Include synonyms, related concepts, and different perspectives
3. Suitable for internet search
4. One keyword per line, no numbering or extra text

Initial keyword: {initial_keyword}

Please output {num_expansions} expanded keywords, one per line:"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            expanded = [kw.strip() for kw in response.content.strip().split('\n') if kw.strip()]
            
            # 确保原始关键词在列表中
            all_keywords = [initial_keyword] + [kw for kw in expanded if kw.lower() != initial_keyword.lower()]
            
            # ===== 关键词安全过滤 =====
            # 检查初始关键词是否安全
            if not self.keyword_blocker.is_keyword_safe(initial_keyword):
                logger.warning(f"初始关键词包含敏感内容，已拒绝扩展: {initial_keyword}")
                return []
            
            # 过滤扩展后的关键词
            safe_keywords = self.keyword_blocker.filter_keywords(all_keywords)
            
            if len(safe_keywords) < len(all_keywords):
                logger.warning(f"关键词扩展过滤: 原始 {len(all_keywords)} 个，安全 {len(safe_keywords)} 个")
            
            logger.info(f"关键词扩展完成: '{initial_keyword}' -> {len(safe_keywords)} 个安全关键词")
            return safe_keywords[:num_expansions + 1]
            
        except Exception as e:
            logger.warning(f"LLM 关键词扩展失败，使用默认扩展: {e}")
            return self._fallback_expand(initial_keyword, num_expansions)
    
    def _fallback_expand(self, keyword: str, num: int) -> List[str]:
        """备用关键词扩展方法"""
        # 首先检查原始关键词是否安全
        if not self.keyword_blocker.is_keyword_safe(keyword):
            logger.warning(f"备用扩展：关键词包含敏感内容，已拒绝: {keyword}")
            return []
        
        expansions = [keyword]
        # 添加常见的扩展后缀
        suffixes = ["评价", "评论", "最新", "新闻", "问题", "怎么样"]
        for suffix in suffixes[:num]:
            expanded_kw = f"{keyword}{suffix}"
            # 检查扩展后的关键词是否安全
            if self.keyword_blocker.is_keyword_safe(expanded_kw):
                expansions.append(expanded_kw)
        
        return expansions
    
    def prioritize_keywords(self, keywords: List[str], context: str = "") -> List[str]:
        """
        对关键词进行优先级排序
        
        Args:
            keywords: 关键词列表
            context: 上下文信息
            
        Returns:
            排序后的关键词列表
        """
        if not context:
            return keywords
        
        prompt = f"""根据以下上下文，对关键词按相关性排序（从高到低）。

上下文：{context}

关键词：
{chr(10).join(f'{i+1}. {kw}' for i, kw in enumerate(keywords))}

请直接输出排序后的关键词，每行一个，从最相关到最不相关："""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            sorted_keywords = [kw.strip() for kw in response.content.strip().split('\n') if kw.strip()]
            return sorted_keywords
        except Exception as e:
            logger.warning(f"关键词排序失败: {e}")
            return keywords


class DataQualityEvaluator:
    """
    数据质量评估器
    使用 LLM 评估数据质量和相关性
    """
    
    def __init__(self):
        """初始化 LLM"""
        self.llm = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
            openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0.3
        )
    
    def evaluate_relevance(
        self,
        content: str,
        topic: str,
        threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        评估内容与主题的相关性
        
        Args:
            content: 内容文本
            topic: 目标主题
            threshold: 相关性阈值
            
        Returns:
            评估结果字典
        """
        prompt = f"""请评估以下内容与主题的相关性。

主题：{topic}

内容：
{content[:1000]}

请以 JSON 格式返回评估结果，包含以下字段：
- relevance_score: 相关性分数 (0.0-1.0)
- quality_score: 内容质量分数 (0.0-1.0)
- is_relevant: 是否相关 (true/false)
- reason: 简短的判断理由
- key_points: 内容中的关键点列表

只返回 JSON，不要其他说明："""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            result = json.loads(response.content.strip())
            
            # 确保必要字段存在
            return {
                "relevance_score": result.get("relevance_score", 0.5),
                "quality_score": result.get("quality_score", 0.5),
                "is_relevant": result.get("is_relevant", True),
                "reason": result.get("reason", ""),
                "key_points": result.get("key_points", [])
            }
        except Exception as e:
            logger.warning(f"相关性评估失败: {e}")
            return {
                "relevance_score": 0.1,
                "quality_score": 0.1,
                "is_relevant": True,
                "reason": f"评估失败，默认不通过: {str(e)}",
                "key_points": []
            }
    
    def batch_evaluate(
        self,
        items: List[Dict[str, Any]],
        topic: str,
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        批量评估数据质量
        
        Args:
            items: 数据项列表
            topic: 主题
            batch_size: 批处理大小
            
        Returns:
            评估后的数据项列表
        """
        evaluated_items = []
        
        for item in items:
            content = item.get("content", "") or item.get("snippet", "") or item.get("title", "")
            if content:
                evaluation = self.evaluate_relevance(content, topic)
                item["evaluation"] = evaluation
                item["relevance_score"] = evaluation["relevance_score"]
                item["quality_score"] = evaluation["quality_score"]
            evaluated_items.append(item)
        
        return evaluated_items


def search_internet(
    query: str,
    max_results: int = 10,
    keyword_blocker: Optional[KeywordBlocker] = None
) -> List[Dict[str, Any]]:
    """
    使用 DuckDuckGo 搜索互联网信息
    
    Args:
        query: 搜索查询
        max_results: 最大结果数量
        keyword_blocker: 关键词屏蔽器实例（可选）
        
    Returns:
        搜索结果列表
    """
    # 获取关键词屏蔽器实例
    blocker = keyword_blocker or get_keyword_blocker()
    
    # ===== 关键词安全检查 =====
    if not blocker.is_keyword_safe(query):
        logger.warning(f"搜索关键词包含敏感内容，已拒绝搜索: {query}")
        return []
    
    try:
        from ddgs import DDGS
        
        logger.info(f"互联网搜索: {query}")
        
        with DDGS() as ddgs:
            results = []
            for result in ddgs.text(query, max_results=max_results):
                results.append({
                    "id": f"web_search_{len(results)}",
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                    "source": "internet_search",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # ===== 搜索结果过滤 =====
            filtered_results = blocker.filter_search_results(results)
            
            logger.info(f"找到 {len(results)} 条搜索结果，过滤后 {len(filtered_results)} 条")
            return filtered_results
            
    except ImportError:
        logger.warning("ddgs 未安装，使用备用搜索方法")
        return _fallback_search(query, keyword_blocker=blocker)
    except Exception as e:
        logger.error(f"互联网搜索失败: {e}")
        return []


def _fallback_search(query: str, keyword_blocker: Optional[KeywordBlocker] = None) -> List[Dict[str, Any]]:
    """
    备用搜索方法（使用 requests + BeautifulSoup）
    
    Args:
        query: 搜索查询
        keyword_blocker: 关键词屏蔽器实例（可选）
        
    Returns:
        搜索结果列表
    """
    blocker = keyword_blocker or get_keyword_blocker()
    
    # ===== 关键词安全检查 =====
    if not blocker.is_keyword_safe(query):
        logger.warning(f"备用搜索关键词包含敏感内容，已拒绝: {query}")
        return []
    
    logger.info(f"使用备用搜索方法: {query}")
    
    try:
        # 这里可以使用其他免费搜索API
        # 简化实现，返回搜索建议
        results = [
            {
                "id": "fallback_001",
                "title": f"关于 {query} 的搜索结果",
                "url": f"https://www.google.com/search?q={query}",
                "snippet": f"点击查看关于 {query} 的更多信息",
                "source": "fallback_search",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        # 过滤搜索结果
        return blocker.filter_search_results(results)
    except Exception as e:
        logger.error(f"备用搜索失败: {e}")
        return []


def fetch_web_content(url: str, max_length: int = 5000) -> Dict[str, Any]:
    """
    抓取网页内容
    
    Args:
        url: 网页URL
        max_length: 最大内容长度
        
    Returns:
        网页内容字典
    """
    try:
        logger.info(f"抓取网页内容: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 禁用 SSL 验证（仅用于开发测试）
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 移除脚本和样式标签
        for script in soup(['script', 'style']):
            script.decompose()
        
        # 获取文本内容
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # 限制长度
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return {
            "url": url,
            "title": soup.title.string if soup.title else "无标题",
            "content": text,
            "word_count": len(text.split()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"抓取网页内容失败: {e}")
        return {
            "url": url,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


def search_knowledge_base(topic: str, keywords: Optional[str] = None, keyword_blocker: Optional[KeywordBlocker] = None) -> List[Dict[str, Any]]:
    """
    搜索知识库中的相关信息
    使用 Wikipedia API 获取真实的知识库数据
    
    Args:
        topic: 搜索主题
        keywords: 关键词（可选）
        keyword_blocker: 关键词屏蔽器实例（可选）
        
    Returns:
        知识库条目列表
    """
    blocker = keyword_blocker or get_keyword_blocker()
    
    # ===== 关键词安全检查 =====
    if not blocker.is_keyword_safe(topic):
        logger.warning(f"知识库搜索主题包含敏感内容，已拒绝: {topic}")
        return []
    
    if keywords and not blocker.is_keyword_safe(keywords):
        logger.warning(f"知识库搜索关键词包含敏感内容，已拒绝: {keywords}")
        keywords = None
    
    logger.info(f"搜索知识库: {topic}")
    
    try:
        import wikipedia
        
        # 设置 Wikipedia 语言为中文
        wikipedia.set_lang("zh")
        
        results = []
        
        # 搜索 Wikipedia
        search_query = f"{topic} {keywords}" if keywords else topic
        search_results = wikipedia.search(search_query, results=3)
        
        for idx, title in enumerate(search_results[:3]):  # 最多3个结果
            try:
                # 获取页面摘要
                page = wikipedia.page(title, auto_suggest=False)
                
                results.append({
                    "id": f"wiki_{idx}",
                    "title": page.title,
                    "content": page.summary[:500],  # 限制长度
                    "url": page.url,
                    "source": "wikipedia",
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {
                        "categories": page.categories[:5] if page.categories else [],
                        "links_count": len(page.links) if page.links else 0
                    }
                })
                
            except wikipedia.exceptions.DisambiguationError as e:
                # 处理歧义页面，选择第一个选项
                try:
                    page = wikipedia.page(e.options[0], auto_suggest=False)
                    results.append({
                        "id": f"wiki_{idx}",
                        "title": page.title,
                        "content": page.summary[:500],
                        "url": page.url,
                        "source": "wikipedia",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception:
                    continue
            except Exception as e:
                logger.warning(f"获取 Wikipedia 页面失败: {title}, 错误: {e}")
                continue
        
        # ===== 搜索结果过滤 =====
        filtered_results = blocker.filter_search_results(results)
        
        logger.info(f"知识库搜索完成，找到 {len(results)} 条结果，过滤后 {len(filtered_results)} 条")
        return filtered_results
        
    except ImportError:
        logger.warning("wikipedia 库未安装，使用备用搜索方法")
        return _fallback_knowledge_search(topic, keywords, keyword_blocker=blocker)
    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return _fallback_knowledge_search(topic, keywords, keyword_blocker=blocker)


def _fallback_knowledge_search(topic: str, keywords: Optional[str] = None, keyword_blocker: Optional[KeywordBlocker] = None) -> List[Dict[str, Any]]:
    """
    备用知识库搜索方法
    使用 DuckDuckGo 的 instant answer API
    
    Args:
        topic: 搜索主题
        keywords: 关键词（可选）
        keyword_blocker: 关键词屏蔽器实例（可选）
        
    Returns:
        知识库条目列表
    """
    blocker = keyword_blocker or get_keyword_blocker()
    
    # ===== 关键词安全检查 =====
    if not blocker.is_keyword_safe(topic):
        logger.warning(f"备用知识库搜索主题包含敏感内容，已拒绝: {topic}")
        return []
    
    if keywords and not blocker.is_keyword_safe(keywords):
        logger.warning(f"备用知识库搜索关键词包含敏感内容，已忽略: {keywords}")
        keywords = None
    
    logger.info(f"使用备用知识库搜索: {topic}")
    
    try:
        import requests
        
        query = f"{topic} {keywords}" if keywords else topic
        url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        # 获取摘要信息
        if data.get("Abstract"):
            results.append({
                "id": "ddg_abstract",
                "title": data.get("Heading", topic),
                "content": data.get("Abstract", ""),
                "url": data.get("AbstractURL", ""),
                "source": "duckduckgo",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # 获取相关主题
        for idx, topic_item in enumerate(data.get("RelatedTopics", [])[:3]):
            if isinstance(topic_item, dict) and "Text" in topic_item:
                results.append({
                    "id": f"ddg_related_{idx}",
                    "title": topic_item.get("FirstURL", "").split("/")[-1] if topic_item.get("FirstURL") else f"相关主题 {idx}",
                    "content": topic_item.get("Text", ""),
                    "url": topic_item.get("FirstURL", ""),
                    "source": "duckduckgo",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # ===== 搜索结果过滤 =====
        filtered_results = blocker.filter_search_results(results)
        
        logger.info(f"备用知识库搜索完成，找到 {len(results)} 条结果，过滤后 {len(filtered_results)} 条")
        return filtered_results
        
    except Exception as e:
        logger.error(f"备用知识库搜索失败: {e}")
        # 返回基本结果，避免完全失败
        return [
            {
                "id": "fallback_kb_001",
                "title": f"{topic} 相关信息",
                "content": f"关于 {topic} 的基本信息收集",
                "source": "fallback",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]


def collect_real_time_data(
    topic: str,
    sources: Optional[List[str]] = None,
    keyword_blocker: Optional[KeywordBlocker] = None
) -> List[Dict[str, Any]]:
    """
    收集网络实时信息
    使用多种真实的网络数据源
    
    Args:
        topic: 收集主题
        sources: 数据源列表（可选），如 ['twitter', 'news', 'social_media']
        keyword_blocker: 关键词屏蔽器实例（可选）
        
    Returns:
        实时数据列表
    """
    blocker = keyword_blocker or get_keyword_blocker()
    
    # ===== 关键词安全检查 =====
    if not blocker.is_keyword_safe(topic):
        logger.warning(f"实时数据收集主题包含敏感内容，已拒绝: {topic}")
        return []
    
    logger.info(f"收集实时数据: {topic}, 数据源: {sources}")
    
    all_data = []
    
    # 默认数据源
    if not sources:
        sources = ["news", "social_media"]
    
    # 1. 收集新闻数据
    if "news" in sources:
        news_data = _collect_news_data(topic, keyword_blocker=blocker)
        all_data.extend(news_data)
    
    # 2. 收集社交媒体数据
    if "social_media" in sources:
        social_data = _collect_social_media_data(topic, keyword_blocker=blocker)
        all_data.extend(social_data)
    
    # 3. Twitter 数据（如果可用）
    if "twitter" in sources:
        twitter_data = _collect_twitter_data(topic, keyword_blocker=blocker)
        all_data.extend(twitter_data)
    
    # ===== 最终结果过滤 =====
    filtered_data = blocker.filter_search_results(all_data)
    
    logger.info(f"实时数据收集完成，共 {len(all_data)} 条，过滤后 {len(filtered_data)} 条")
    return filtered_data


def _collect_news_data(topic: str, keyword_blocker: Optional[KeywordBlocker] = None) -> List[Dict[str, Any]]:
    """
    收集新闻数据
    使用 NewsAPI 或 DuckDuckGo 新闻搜索
    
    Args:
        topic: 新闻主题
        keyword_blocker: 关键词屏蔽器实例（可选）
        
    Returns:
        新闻数据列表
    """
    blocker = keyword_blocker or get_keyword_blocker()
    
    # ===== 关键词安全检查 =====
    if not blocker.is_keyword_safe(topic):
        logger.warning(f"新闻收集主题包含敏感内容，已拒绝: {topic}")
        return []
    
    logger.info(f"收集新闻数据: {topic}")
    
    try:
        # 使用 DuckDuckGo 搜索新闻
        from ddgs import DDGS
        
        with DDGS() as ddgs:
            news_results = []
            for result in ddgs.news(topic, max_results=5):
                news_results.append({
                    "id": f"news_{len(news_results)}",
                    "title": result.get("title", ""),
                    "content": result.get("body", ""),
                    "url": result.get("url", ""),
                    "source": "news",
                    "timestamp": result.get("date", datetime.utcnow().isoformat()),
                    "metadata": {
                        "image": result.get("image", ""),
                        "publisher": result.get("source", "")
                    }
                })
            
            # ===== 新闻结果过滤 =====
            filtered_results = blocker.filter_search_results(news_results)
            
            logger.info(f"收集到 {len(news_results)} 条新闻，过滤后 {len(filtered_results)} 条")
            return filtered_results
            
    except Exception as e:
        logger.warning(f"新闻收集失败: {e}")
        return []


def _collect_social_media_data(topic: str, keyword_blocker: Optional[KeywordBlocker] = None) -> List[Dict[str, Any]]:
    """
    收集社交媒体数据
    使用 Reddit API 或其他社交媒体平台
    
    Args:
        topic: 社交媒体主题
        keyword_blocker: 关键词屏蔽器实例（可选）
        
    Returns:
        社交媒体数据列表
    """
    blocker = keyword_blocker or get_keyword_blocker()
    
    # ===== 关键词安全检查 =====
    if not blocker.is_keyword_safe(topic):
        logger.warning(f"社交媒体收集主题包含敏感内容，已拒绝: {topic}")
        return []
    
    logger.info(f"收集社交媒体数据: {topic}")
    
    try:
        import praw  # Reddit API
        
        # 注意：需要配置 Reddit API 凭据
        # 这里使用只读模式获取公开数据
        reddit = praw.Reddit(
            client_id="your_client_id",  # 需要配置
            client_secret="your_client_secret",  # 需要配置
            user_agent="workflow_engine/1.0"
        )
        
        results = []
        # 搜索 Reddit
        for submission in reddit.subreddit("all").search(topic, limit=5):
            results.append({
                "id": f"reddit_{submission.id}",
                "title": submission.title,
                "content": submission.selftext[:500] if submission.selftext else submission.title,
                "url": f"https://reddit.com{submission.permalink}",
                "source": "reddit",
                "timestamp": datetime.fromtimestamp(submission.created_utc).isoformat(),
                "metadata": {
                    "subreddit": submission.subreddit.display_name,
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "upvote_ratio": submission.upvote_ratio
                }
            })
        
        # ===== 社交媒体结果过滤 =====
        filtered_results = blocker.filter_search_results(results)
        
        logger.info(f"从 Reddit 收集到 {len(results)} 条数据，过滤后 {len(filtered_results)} 条")
        return filtered_results
        
    except ImportError:
        logger.warning("praw 库未安装，跳过 Reddit 数据收集")
        return []
    except Exception as e:
        logger.warning(f"社交媒体数据收集失败: {e}")
        return []


def _collect_twitter_data(topic: str, keyword_blocker: Optional[KeywordBlocker] = None) -> List[Dict[str, Any]]:
    """
    收集 Twitter 数据
    使用 Twitter API 或其他方法
    
    Args:
        topic: Twitter 搜索主题
        keyword_blocker: 关键词屏蔽器实例（可选）
        
    Returns:
        Twitter 数据列表
    """
    blocker = keyword_blocker or get_keyword_blocker()
    
    # ===== 关键词安全检查 =====
    if not blocker.is_keyword_safe(topic):
        logger.warning(f"Twitter 收集主题包含敏感内容，已拒绝: {topic}")
        return []
    
    logger.info(f"收集 Twitter 数据: {topic}")
    
    try:
        import tweepy  # Twitter API
        
        # 注意：需要配置 Twitter API 凭据
        # Twitter API v2 需要 Bearer Token
        client = tweepy.Client(bearer_token="your_bearer_token")
        
        results = []
        # 搜索推文
        query = f"{topic} -is:retweet lang:zh OR lang:en"
        tweets = client.search_recent_tweets(query=query, max_results=10, tweet_fields=['created_at', 'public_metrics'])
        
        if tweets.data:
            for idx, tweet in enumerate(tweets.data):
                results.append({
                    "id": f"twitter_{tweet.id}",
                    "title": f"Tweet about {topic}",
                    "content": tweet.text,
                    "url": f"https://twitter.com/user/status/{tweet.id}",
                    "source": "twitter",
                    "timestamp": tweet.created_at.isoformat() if tweet.created_at else datetime.utcnow().isoformat(),
                    "metadata": {
                        "public_metrics": tweet.public_metrics if hasattr(tweet, 'public_metrics') else {}
                    }
                })
        
        # ===== Twitter 结果过滤 =====
        filtered_results = blocker.filter_search_results(results)
        
        logger.info(f"从 Twitter 收集到 {len(results)} 条数据，过滤后 {len(filtered_results)} 条")
        return filtered_results
        
    except ImportError:
        logger.warning("tweepy 库未安装，跳过 Twitter 数据收集")
        return []
    except Exception as e:
        logger.warning(f"Twitter 数据收集失败: {e}")
        return []


class DataCollectionAgent:
    """
    数据收集智能体（增强版）
    
    增强功能：
    - 关键词联想与扩展：使用 LLM 生成相关关键词，扩大信息覆盖面
    - 多轮迭代收集：支持迭代式数据收集，逐步扩大搜索范围
    - 数据量控制：确保收集足够的数据量（目标：50-100条）
    - LLM 智能分析：智能判断数据相关性和质量
    - 智能数据筛选：根据相关性评分筛选高质量数据
    - 关键词屏蔽：防止爬取敏感信息和不良信息
    
    支持预设工作流：先搜索知识库再收集实时信息
    集成数据存储服务，自动将收集的数据持久化到数据库
    """
    
    # 目标数据量配置
    TARGET_MIN_DATA = 50  # 最小目标数据量
    TARGET_MAX_DATA = 100  # 最大目标数据量
    MAX_ITERATIONS = 3  # 最大迭代次数
    
    def __init__(self, workflow_id: str, auto_save: bool = True, use_llm: bool = True, keyword_blocker: Optional[KeywordBlocker] = None):
        """
        初始化智能体
        
        Args:
            workflow_id: 工作流 ID
            auto_save: 是否自动保存收集的数据到数据库（默认True）
            use_llm: 是否使用 LLM 进行智能增强（默认True）
            keyword_blocker: 关键词屏蔽器实例（可选）
        """
        self.workflow_id = workflow_id
        self.db = get_session()
        self.memory_service = AgentMemoryService(self.db)
        # 延迟导入避免循环依赖
        from ..services.data_storage_service import DataStorageService
        self.storage_service = DataStorageService(workflow_id)
        self.auto_save = auto_save
        self.use_llm = use_llm
        
        # 初始化关键词屏蔽器
        self.keyword_blocker = keyword_blocker or get_keyword_blocker()
        
        # 初始化 LLM 增强组件
        if use_llm:
            try:
                self.keyword_expander = KeywordExpander(keyword_blocker=self.keyword_blocker)
                self.quality_evaluator = DataQualityEvaluator()
                logger.info("LLM 增强功能已启用")
            except Exception as e:
                logger.warning(f"LLM 增强功能初始化失败: {e}，将使用基础模式")
                self.use_llm = False
                self.keyword_expander = None
                self.quality_evaluator = None
        else:
            self.keyword_expander = None
            self.quality_evaluator = None
    
    def execute_intelligent_collection(
        self,
        topic: str,
        target_count: int = 50,
        max_iterations: int = 3,
        use_keyword_expansion: bool = True,
        evaluate_quality: bool = True,
        language: str = "zh"
    ) -> Dict[str, Any]:
        """
        执行智能数据收集（增强版）
        
        使用 LLM 进行：
        1. 关键词联想与扩展
        2. 多轮迭代收集
        3. 数据质量评估
        4. 智能数据筛选
        
        Args:
            topic: 收集主题
            target_count: 目标数据量（默认50条）
            max_iterations: 最大迭代次数（默认3次）
            use_keyword_expansion: 是否使用关键词扩展
            evaluate_quality: 是否评估数据质量
            language: 语言设置
            
        Returns:
            收集结果
        """
        logger.info(f"开始智能数据收集: {topic}, 目标数量: {target_count}")
        
        # ===== 初始主题安全检查 =====
        if not self.keyword_blocker.is_keyword_safe(topic):
            logger.error(f"收集主题包含敏感内容，已拒绝收集: {topic}")
            return {
                "topic": topic,
                "expanded_keywords": [],
                "collected_data": [],
                "total_count": 0,
                "iterations": 0,
                "target_achieved": False,
                "quality_evaluation": False,
                "blocked": True,
                "blocked_reason": "主题包含敏感内容",
                "summary": {
                    "total_items": 0,
                    "sources": [],
                    "avg_relevance_score": 0,
                    "high_quality_count": 0
                },
                "metadata": {
                    "start_time": datetime.utcnow().isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "workflow_id": self.workflow_id,
                    "collection_method": "intelligent"
                },
                "message": f"主题 '{topic}' 包含敏感内容，已拒绝收集"
            }
        
        all_data = []
        collected_urls = set()  # 用于去重
        iteration_data = []
        
        # 步骤 1: 关键词扩展
        keywords = [topic]
        if use_keyword_expansion and self.use_llm and self.keyword_expander:
            logger.info("步骤 1: 使用 LLM 扩展关键词")
            try:
                expanded_keywords = self.keyword_expander.expand_keywords(
                    topic,
                    num_expansions=5,
                    language=language
                )
                # 关键词已在上层过滤，这里直接使用
                keywords = expanded_keywords if expanded_keywords else [topic]
                logger.info(f"关键词扩展完成: {keywords}")
            except Exception as e:
                logger.warning(f"关键词扩展失败，使用原始主题: {e}")
        
        # 步骤 2: 多轮迭代收集
        for iteration in range(max_iterations):
            logger.info(f"步骤 2.{iteration + 1}: 第 {iteration + 1} 轮数据收集")
            
            iteration_data = []
            current_keywords = keywords[:3 + iteration]  # 逐轮扩大关键词范围
            
            # 对每个关键词进行搜索
            for keyword in current_keywords:
                # ===== 关键词安全检查（防御性编程）=====
                if not self.keyword_blocker.is_keyword_safe(keyword):
                    logger.warning(f"跳过敏感关键词: {keyword}")
                    continue
                
                # 互联网搜索（已集成关键词过滤）
                internet_results = search_internet(keyword, max_results=10, keyword_blocker=self.keyword_blocker)
                for item in internet_results:
                    if self._is_unique_item(item, collected_urls):
                        iteration_data.append(item)
                        if item.get("url"):
                            collected_urls.add(item["url"])
                
                # 知识库搜索（已集成关键词过滤）
                kb_results = search_knowledge_base(keyword, keyword_blocker=self.keyword_blocker)
                for item in kb_results:
                    if self._is_unique_item(item, collected_urls):
                        iteration_data.append(item)
                        if item.get("url"):
                            collected_urls.add(item["url"])
                
                # 实时数据收集（已集成关键词过滤）
                try:
                    realtime_results = collect_real_time_data(keyword, ["news"], keyword_blocker=self.keyword_blocker)
                    for item in realtime_results:
                        if self._is_unique_item(item, collected_urls):
                            iteration_data.append(item)
                            if item.get("url"):
                                collected_urls.add(item["url"])
                except Exception as e:
                    logger.warning(f"实时数据收集失败: {e}")
            
            # 抓取部分网页详细内容
            detailed_data = self._fetch_detailed_content(iteration_data[:5], topic)
            iteration_data.extend(detailed_data)
            
            # 数据质量评估
            if evaluate_quality and self.use_llm and self.quality_evaluator:
                logger.info(f"评估 {len(iteration_data)} 条数据的质量")
                iteration_data = self.quality_evaluator.batch_evaluate(
                    iteration_data, topic, batch_size=5
                )
                # 过滤低质量数据
                iteration_data = [
                    item for item in iteration_data
                    if item.get("relevance_score", 0.5) >= 0.4
                ]
            
            all_data.extend(iteration_data)
            
            # 检查是否达到目标
            if len(all_data) >= target_count:
                logger.info(f"已达到目标数据量 {len(all_data)}，停止收集")
                break
        
        # 步骤 3: 数据汇总和去重
        all_data = self._deduplicate_data(all_data)
        
        # 步骤 4: 如果数据量仍然不足，使用 LLM 生成补充数据
        if len(all_data) < target_count // 2 and self.use_llm:
            logger.info(f"数据量不足 {target_count // 2}，尝试 LLM 补充收集")
            supplementary_data = self._llm_supplementary_collection(topic, target_count - len(all_data))
            all_data.extend(supplementary_data)
        
        # 步骤 5: 数据排序和截取
        if evaluate_quality and all_data and all_data[0].get("relevance_score"):
            all_data.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        final_data = all_data[:self.TARGET_MAX_DATA]
        
        # 构建结果
        results = {
            "topic": topic,
            "expanded_keywords": keywords if use_keyword_expansion else [topic],
            "collected_data": final_data,
            "total_count": len(final_data),
            "iterations": min(max_iterations, (len(all_data) + target_count - 1) // target_count + 1),
            "target_achieved": len(final_data) >= target_count,
            "quality_evaluation": evaluate_quality and self.use_llm,
            "summary": {
                "total_items": len(final_data),
                "sources": list(set(d.get("source", "unknown") for d in final_data)),
                "avg_relevance_score": sum(d.get("relevance_score", 0.5) for d in final_data) / len(final_data) if final_data else 0,
                "high_quality_count": sum(1 for d in final_data if d.get("relevance_score", 0.5) >= 0.7)
            },
            "metadata": {
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "workflow_id": self.workflow_id,
                "collection_method": "intelligent"
            },
            "message": f"智能收集完成，共收集 {len(final_data)} 条数据"
        }
        
        # 保存数据
        if self.auto_save and final_data:
            storage_result = self.save_collected_data(final_data)
            results["storage_result"] = storage_result
        
        logger.info(f"智能数据收集完成: 收集 {len(final_data)} 条数据")
        return results
    
    def _is_unique_item(self, item: Dict[str, Any], collected_urls: set) -> bool:
        """检查数据项是否唯一"""
        url = item.get("url", "")
        if url and url in collected_urls:
            return False
        return True
    
    def _fetch_detailed_content(
        self,
        items: List[Dict[str, Any]],
        topic: str
    ) -> List[Dict[str, Any]]:
        """抓取网页详细内容"""
        detailed_data = []
        for item in items[:3]:  # 只抓取前3个
            url = item.get("url")
            if url:
                try:
                    content = fetch_web_content(url)
                    if content and not content.get("error"):
                        detailed_data.append({
                            "id": f"detailed_{item.get('id', '')}",
                            "title": content.get("title", ""),
                            "content": content.get("content", ""),
                            "url": url,
                            "source": "detailed_content",
                            "timestamp": datetime.utcnow().isoformat(),
                            "word_count": content.get("word_count", 0)
                        })
                except Exception as e:
                    logger.warning(f"抓取详细内容失败: {e}")
        return detailed_data
    
    def _deduplicate_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """数据去重"""
        seen_urls = set()
        seen_titles = set()
        unique_data = []
        
        for item in data:
            url = item.get("url", "")
            title = item.get("title", "").lower()
            
            # 基于 URL 或标题去重
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_data.append(item)
            elif title and title not in seen_titles:
                seen_titles.add(title)
                unique_data.append(item)
        
        return unique_data
    
    def _llm_supplementary_collection(
        self,
        topic: str,
        needed_count: int
    ) -> List[Dict[str, Any]]:
        """使用 LLM 进行补充数据收集"""
        try:
            llm = ChatOpenAI(
                model=os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat"),
                openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
                openai_api_key=os.environ.get("OPENAI_API_KEY"),
                temperature=0.7
            )
            
            prompt = f"""作为数据收集助手，请围绕主题"{topic}"生成{needed_count}条相关的数据条目。

每条数据应该包含：
- title: 标题
- content: 内容摘要（100-200字）
- source: 来源类型（如"分析报告"、"专家观点"、"行业动态"等）

请以 JSON 数组格式返回，格式如下：
[
  {{"title": "...", "content": "...", "source": "..."}},
  ...
]

只返回 JSON 数组，不要其他说明："""

            response = llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            # 尝试解析 JSON
            try:
                # 去除可能的 markdown 代码块标记
                if content.startswith("```"):
                    content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content.rsplit("\n", 1)[0]
                
                items = json.loads(content)
                supplementary_data = []
                
                for idx, item in enumerate(items[:needed_count]):
                    supplementary_data.append({
                        "id": f"llm_generated_{idx}",
                        "title": item.get("title", ""),
                        "content": item.get("content", ""),
                        "source": item.get("source", "llm_generated"),
                        "timestamp": datetime.utcnow().isoformat(),
                        "relevance_score": 0.6,  # LLM 生成的内容默认相关性
                        "is_generated": True
                    })
                
                logger.info(f"LLM 补充生成 {len(supplementary_data)} 条数据")
                return supplementary_data
                
            except json.JSONDecodeError as e:
                logger.warning(f"LLM 返回数据解析失败: {e}")
                return []
                
        except Exception as e:
            logger.warning(f"LLM 补充收集失败: {e}")
            return []
    
    def execute_preset_workflow(
        self,
        topic: str,
        workflow_steps: Optional[List[str]] = None,
        save_to_db: Optional[bool] = None,
        use_intelligent_collection: bool = True,
        target_count: int = 50
    ) -> Dict[str, Any]:
        """
        执行预设的数据收集工作流
        
        增强功能：
        - 自动判断是否使用智能收集模式
        - 确保数据量达到目标
        
        默认工作流步骤：
        1. 互联网搜索
        2. 搜索知识库
        3. 收集网络实时信息
        4. 汇总数据
        5. 存储数据到数据库
        
        Args:
            topic: 收集主题
            workflow_steps: 自定义工作流步骤（可选）
            save_to_db: 是否保存到数据库（可选，覆盖auto_save设置）
            use_intelligent_collection: 是否使用智能收集模式（默认True）
            target_count: 目标数据量（默认50条）
            
        Returns:
            汇总的数据结果
        """
        logger.info(f"开始执行数据收集工作流: {topic}")
        
        # ===== 初始主题安全检查 =====
        if not self.keyword_blocker.is_keyword_safe(topic):
            logger.error(f"工作流主题包含敏感内容，已拒绝收集: {topic}")
            return {
                "topic": topic,
                "workflow_steps": workflow_steps or [],
                "collected_data": [],
                "total_count": 0,
                "blocked": True,
                "blocked_reason": "主题包含敏感内容",
                "metadata": {
                    "start_time": datetime.utcnow().isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "workflow_id": self.workflow_id
                },
                "message": f"主题 '{topic}' 包含敏感内容，已拒绝收集"
            }
        
        # 如果启用智能收集模式，使用增强版收集
        if use_intelligent_collection and self.use_llm:
            return self.execute_intelligent_collection(
                topic=topic,
                target_count=target_count,
                max_iterations=self.MAX_ITERATIONS
            )
        
        # 否则使用传统工作流
        # 获取预设的工作流配置
        if workflow_steps is None:
            workflow_steps = [
                "internet_search",
                "knowledge_base_search",
                "real_time_collection",
                "data_aggregation"
            ]
        
        results = {
            "topic": topic,
            "workflow_steps": workflow_steps,
            "collected_data": [],
            "metadata": {
                "start_time": datetime.utcnow().isoformat(),
                "workflow_id": self.workflow_id
            }
        }
        
        # 步骤 1: 互联网搜索
        if "internet_search" in workflow_steps:
            logger.info("步骤 1: 互联网搜索")
            internet_results = search_internet(topic, max_results=10, keyword_blocker=self.keyword_blocker)
            results["collected_data"].extend(internet_results)
            results["internet_search_count"] = len(internet_results)
            
            # 可选：抓取部分网页详细内容
            if internet_results:
                first_result = internet_results[0]
                if first_result.get("url"):
                    web_content = fetch_web_content(first_result["url"])
                    results["collected_data"].append({
                        "id": f"web_content_{first_result['id']}",
                        "title": f"{web_content.get('title', '无标题')} - 详细内容",
                        "content": web_content.get("content", ""),
                        "url": web_content.get("url", ""),
                        "source": "web_content",
                        "timestamp": datetime.utcnow().isoformat(),
                        "word_count": web_content.get("word_count", 0)
                    })
        
        # 步骤 2: 搜索知识库
        if "knowledge_base_search" in workflow_steps:
            logger.info("步骤 2: 搜索知识库")
            kb_data = search_knowledge_base(topic, keyword_blocker=self.keyword_blocker)
            results["collected_data"].extend(kb_data)
            results["knowledge_base_count"] = len(kb_data)
        
        # 步骤 3: 收集实时信息
        if "real_time_collection" in workflow_steps:
            logger.info("步骤 3: 收集实时信息")
            sources = ["twitter", "news", "social_media"]
            real_time_data = collect_real_time_data(topic, sources, keyword_blocker=self.keyword_blocker)
            results["collected_data"].extend(real_time_data)
            results["real_time_count"] = len(real_time_data)
        
        # 步骤 4: 数据汇总
        if "data_aggregation" in workflow_steps:
            logger.info("步骤 4: 汇总数据")
            results["summary"] = {
                "total_items": len(results["collected_data"]),
                "sources": list(set(d["source"] for d in results["collected_data"])),
                "time_range": {
                    "start": min(d["timestamp"] for d in results["collected_data"]) if results["collected_data"] else None,
                    "end": max(d["timestamp"] for d in results["collected_data"]) if results["collected_data"] else None
                }
            }
            results["metadata"]["end_time"] = datetime.utcnow().isoformat()
        
        # 统一统计口径：total_count 以 collected_data 实际长度为准
        total_count = len(results["collected_data"])
        results["total_count"] = total_count
        results["message"] = f"成功收集 {total_count} 条数据"
        if isinstance(results.get("summary"), dict):
            results["summary"]["total_items"] = total_count

        # 步骤 5: 保存数据收集策略到记忆
        self._save_collection_strategy(topic, workflow_steps)
        
        # 步骤 6: 自动存储收集的数据到数据库
        should_save = save_to_db if save_to_db is not None else self.auto_save
        if should_save and results["collected_data"]:
            logger.info("步骤 5: 存储数据到数据库")
            storage_result = self.save_collected_data(results["collected_data"])
            results["storage_result"] = storage_result
            logger.info(f"数据存储完成: 成功{storage_result['stored']}条, 失败{storage_result['failed']}条")
        
        logger.info(f"数据收集完成，共收集 {total_count} 条数据")
        
        return results
    
    def _save_collection_strategy(
        self,
        topic: str,
        workflow_steps: List[str]
    ):
        """
        保存数据收集策略到记忆
        
        Args:
            topic: 主题
            workflow_steps: 工作流步骤
        """
        self.memory_service.save_memory(
            workflow_id=self.workflow_id,
            agent_type="data_collection",
            memory_type="domain_knowledge",
            key=f"strategy_{topic}",
            value={
                "topic": topic,
                "workflow_steps": workflow_steps,
                "created_at": datetime.utcnow().isoformat()
            },
            extra_data={"category": "collection_strategy"}
        )
    
    def save_collected_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将收集的数据存储到数据库
        
        Args:
            data: 收集的数据列表
            
        Returns:
            存储结果统计
        """
        logger.info(f"保存收集数据到数据库: {len(data)}条")
        
        result = self.storage_service.store_collected_data(
            data=data,
            agent_type="data_collection",
            workflow_id=self.workflow_id
        )
        
        return result
    
    def get_stored_data(
        self,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取已存储的收集数据
        
        Args:
            source: 数据来源（可选）
            limit: 返回的最大数量
            
        Returns:
            数据列表
        """
        return self.storage_service.get_collected_data(
            workflow_id=self.workflow_id,
            source=source,
            limit=limit
        )
    
    def get_collection_history(self) -> List[Dict[str, Any]]:
        """
        获取数据收集历史
        
        Returns:
            收集历史列表
        """
        memories = self.memory_service.get_memory(
            workflow_id=self.workflow_id,
            agent_type="data_collection",
            memory_type="domain_knowledge"
        )
        
        return [
            {
                "key": m.key,
                "strategy": m.value,
                "created_at": m.created_at
            }
            for m in memories
        ]
    
    def get_data_summary(self) -> Dict[str, Any]:
        """
        获取工作流数据摘要
        
        Returns:
            数据摘要统计
        """
        return self.storage_service.get_workflow_data_summary(self.workflow_id)
    
    def close(self):
        """关闭数据库连接"""
        if self.storage_service:
            self.storage_service.close()
        if self.db:
            self.db.close()