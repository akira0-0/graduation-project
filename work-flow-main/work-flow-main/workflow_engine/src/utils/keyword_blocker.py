"""
关键词屏蔽模块
用于防止数据收集智能体发散关键词爬取敏感信息和不良信息
"""
import re
from typing import List, Dict, Optional, Set, Any
from pathlib import Path
import json
from ..utils.logger import get_logger

logger = get_logger("keyword_blocker")

# 默认配置文件路径（相对于项目根目录）
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "blocked_keywords.json"


class KeywordBlocker:
    """
    关键词屏蔽器
    
    功能：
    - 敏感词过滤：阻止搜索敏感政治、暴力、色情等关键词
    - 关键词验证：在搜索前验证关键词是否安全
    - 结果过滤：过滤搜索结果中的不良内容
    """
    
    # 默认敏感词类别
    DEFAULT_CATEGORIES = [
        "sensitive_political",    # 敏感政治
        "violence",               # 暴力
        "pornography",           # 色情
        "gambling",              # 赌博
        "drugs",                 # 毒品
        "fraud",                 # 诈骗
        "hate_speech",           # 仇恨言论
        "illegal_activities"     # 非法活动
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化关键词屏蔽器
        
        Args:
            config_path: 配置文件路径（可选，默认使用 workflow_engine/config/blocked_keywords.json）
        """
        self.blocked_keywords: Set[str] = set()
        self.blocked_patterns: List[re.Pattern] = []
        self.category_keywords: Dict[str, List[str]] = {}
        
        # 确定配置文件路径
        actual_config_path = config_path
        if actual_config_path is None:
            actual_config_path = str(DEFAULT_CONFIG_PATH)
        
        # 加载配置文件
        self._load_config(actual_config_path)
        
        logger.info(f"关键词屏蔽器初始化完成，已加载 {len(self.blocked_keywords)} 个屏蔽关键词")
    
    def _load_config(self, config_path: str) -> None:
        """
        从配置文件加载屏蔽关键词
        
        Args:
            config_path: 配置文件路径
        """
        try:
            path = Path(config_path)
            if not path.exists():
                logger.error(f"配置文件不存在: {config_path}")
                logger.warning("关键词屏蔽器未加载任何屏蔽词，请检查配置文件")
                return
            
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载各类别关键词
            for category, keywords in config.get("blocked_keywords", {}).items():
                if isinstance(keywords, list):
                    self.category_keywords[category] = keywords
                    self.blocked_keywords.update(keywords)
            
            # 加载自定义关键词
            custom_keywords = config.get("custom_keywords", [])
            if custom_keywords and isinstance(custom_keywords, list):
                self.category_keywords["custom"] = custom_keywords
                self.blocked_keywords.update(custom_keywords)
                logger.info(f"加载自定义屏蔽关键词: {len(custom_keywords)} 个")
            
            # 加载正则模式
            for pattern in config.get("blocked_patterns", []):
                try:
                    self.blocked_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.warning(f"无效的正则模式: {pattern}, 错误: {e}")
            
            logger.info(f"从配置文件加载屏蔽关键词: {config_path}")
            
        except json.JSONDecodeError as e:
            logger.error(f"配置文件 JSON 解析失败: {e}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    
    
    
    def is_keyword_safe(self, keyword: str) -> bool:
        """
        检查关键词是否安全
        
        Args:
            keyword: 要检查的关键词
            
        Returns:
            True 如果关键词安全，False 如果关键词被屏蔽
        """
        if not keyword or not keyword.strip():
            return False
        
        keyword_lower = keyword.lower().strip()
        
        # 检查直接匹配
        for blocked in self.blocked_keywords:
            if blocked.lower() in keyword_lower:
                logger.warning(f"关键词包含屏蔽词: {keyword} (匹配: {blocked})")
                return False
        
        # 检查正则模式
        for pattern in self.blocked_patterns:
            if pattern.search(keyword):
                logger.warning(f"关键词匹配屏蔽模式: {keyword}")
                return False
        
        return True
    
    def filter_keywords(self, keywords: List[str]) -> List[str]:
        """
        过滤关键词列表，移除不安全的关键词
        
        Args:
            keywords: 关键词列表
            
        Returns:
            过滤后的安全关键词列表
        """
        safe_keywords = []
        blocked_count = 0
        
        for keyword in keywords:
            if self.is_keyword_safe(keyword):
                safe_keywords.append(keyword)
            else:
                blocked_count += 1
        
        if blocked_count > 0:
            logger.info(f"关键词过滤完成: 保留 {len(safe_keywords)} 个，屏蔽 {blocked_count} 个")
        
        return safe_keywords
    
    def filter_content(self, content: str, replacement: str = "[已屏蔽]") -> str:
        """
        过滤内容中的敏感词
        
        Args:
            content: 要过滤的内容
            replacement: 替换文本
            
        Returns:
            过滤后的内容
        """
        filtered_content = content
        
        # 替换敏感词
        for keyword in self.blocked_keywords:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            filtered_content = pattern.sub(replacement, filtered_content)
        
        # 应用正则模式
        for pattern in self.blocked_patterns:
            filtered_content = pattern.sub(replacement, filtered_content)
        
        return filtered_content
    
    def filter_search_results(
        self,
        results: List[Dict[str, Any]],
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        过滤搜索结果中的敏感内容
        
        Args:
            results: 搜索结果列表
            fields: 要检查的字段列表（默认: title, snippet, content）
            
        Returns:
            过滤后的搜索结果
        """
        if fields is None:
            fields = ["title", "snippet", "content"]
        
        filtered_results = []
        blocked_count = 0
        
        for result in results:
            is_safe = True
            
            # 检查指定字段
            for field in fields:
                if field in result and result[field]:
                    if not self.is_keyword_safe(str(result[field])):
                        is_safe = False
                        break
            
            if is_safe:
                # 过滤内容中的敏感词
                filtered_result = result.copy()
                for field in fields:
                    if field in filtered_result and filtered_result[field]:
                        filtered_result[field] = self.filter_content(str(filtered_result[field]))
                filtered_results.append(filtered_result)
            else:
                blocked_count += 1
        
        if blocked_count > 0:
            logger.info(f"搜索结果过滤完成: 保留 {len(filtered_results)} 条，屏蔽 {blocked_count} 条")
        
        return filtered_results
    
    def get_blocked_categories(self) -> List[str]:
        """获取所有屏蔽类别"""
        return list(self.category_keywords.keys())
    
    def get_keywords_by_category(self, category: str) -> List[str]:
        """
        获取指定类别的屏蔽关键词
        
        Args:
            category: 类别名称
            
        Returns:
            该类别的关键词列表
        """
        return self.category_keywords.get(category, [])
    
    def add_blocked_keyword(self, keyword: str, category: str = "custom") -> None:
        """
        添加屏蔽关键词
        
        Args:
            keyword: 要屏蔽的关键词
            category: 类别（默认: custom）
        """
        if category not in self.category_keywords:
            self.category_keywords[category] = []
        
        if keyword not in self.category_keywords[category]:
            self.category_keywords[category].append(keyword)
            self.blocked_keywords.add(keyword)
            logger.info(f"添加屏蔽关键词: {keyword} (类别: {category})")
    
    def remove_blocked_keyword(self, keyword: str) -> bool:
        """
        移除屏蔽关键词
        
        Args:
            keyword: 要移除的关键词
            
        Returns:
            True 如果成功移除，False 如果关键词不存在
        """
        if keyword in self.blocked_keywords:
            self.blocked_keywords.remove(keyword)
            
            for category in self.category_keywords:
                if keyword in self.category_keywords[category]:
                    self.category_keywords[category].remove(keyword)
            
            logger.info(f"移除屏蔽关键词: {keyword}")
            return True
        
        return False
    
    def export_config(self, config_path: str) -> None:
        """
        导出配置到文件
        
        Args:
            config_path: 配置文件路径
        """
        config = {
            "blocked_keywords": self.category_keywords,
            "blocked_patterns": [p.pattern for p in self.blocked_patterns]
        }
        
        try:
            path = Path(config_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置导出成功: {config_path}")
        except Exception as e:
            logger.error(f"配置导出失败: {e}")
            raise


# 全局单例实例
_keyword_blocker_instance: Optional[KeywordBlocker] = None


def get_keyword_blocker(config_path: Optional[str] = None, reload: bool = False) -> KeywordBlocker:
    """
    获取关键词屏蔽器单例
    
    Args:
        config_path: 配置文件路径（可选，默认使用 workflow_engine/config/blocked_keywords.json）
        reload: 是否重新加载配置（默认 False）
        
    Returns:
        KeywordBlocker 实例
    """
    global _keyword_blocker_instance
    
    # 如果指定了配置路径、或者实例不存在、或者需要重新加载
    if _keyword_blocker_instance is None or reload:
        # 优先使用指定的配置路径，否则使用默认配置文件
        actual_config_path = config_path
        if actual_config_path is None:
            # 检查默认配置文件是否存在
            if DEFAULT_CONFIG_PATH.exists():
                actual_config_path = str(DEFAULT_CONFIG_PATH)
                logger.info(f"使用默认配置文件: {actual_config_path}")
            else:
                logger.info("默认配置文件不存在，使用内置默认配置")
        
        _keyword_blocker_instance = KeywordBlocker(actual_config_path)
    
    return _keyword_blocker_instance