# -*- coding: utf-8 -*-
"""
查询意图分析器
分析用户查询意图，确定过滤场景和规则选择策略
"""
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class FilterScenario(Enum):
    """过滤场景"""
    NORMAL = "normal"           # 通用场景
    ECOMMERCE = "ecommerce"     # 电商场景
    NEWS = "news"               # 新闻资讯
    SOCIAL = "social"           # 社交内容
    FINANCE = "finance"         # 金融财经
    MEDICAL = "medical"         # 医疗健康
    EDUCATION = "education"     # 教育培训
    CUSTOM = "custom"           # 自定义场景


class FilterSeverity(Enum):
    """过滤严格程度"""
    RELAXED = "relaxed"     # 宽松 - 仅过滤明显违规
    NORMAL = "normal"       # 正常 - 标准过滤
    STRICT = "strict"       # 严格 - 严格过滤


@dataclass
class QueryIntent:
    """查询意图"""
    scenario: FilterScenario = FilterScenario.NORMAL
    severity: FilterSeverity = FilterSeverity.NORMAL
    extra_categories: List[str] = field(default_factory=list)  # 额外关注的类别
    custom_keywords: List[str] = field(default_factory=list)   # 自定义关键词
    exclude_categories: List[str] = field(default_factory=list)  # 排除的类别
    metadata: Dict[str, Any] = field(default_factory=dict)     # 附加元数据
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario.value,
            "severity": self.severity.value,
            "extra_categories": self.extra_categories,
            "custom_keywords": self.custom_keywords,
            "exclude_categories": self.exclude_categories,
            "metadata": self.metadata,
        }


class QueryAnalyzer:
    """
    查询意图分析器
    
    根据用户的查询和上下文，分析出：
    1. 过滤场景（电商/新闻/社交等）
    2. 严格程度（宽松/正常/严格）
    3. 需要额外关注的类别
    4. 自定义关键词
    """
    
    # 场景关键词映射
    SCENARIO_KEYWORDS = {
        FilterScenario.ECOMMERCE: [
            "商品", "购物", "电商", "淘宝", "京东", "拼多多", "店铺", 
            "价格", "优惠", "促销", "折扣", "销量", "好评", "差评",
            "发货", "物流", "退款", "售后", "客服"
        ],
        FilterScenario.NEWS: [
            "新闻", "资讯", "报道", "时事", "政治", "政策", "官方",
            "声明", "公告", "发布会", "记者", "媒体", "舆论"
        ],
        FilterScenario.SOCIAL: [
            "评论", "帖子", "动态", "分享", "点赞", "转发", "关注",
            "粉丝", "博主", "网红", "社区", "论坛", "私信"
        ],
        FilterScenario.FINANCE: [
            "股票", "基金", "理财", "投资", "金融", "银行", "贷款",
            "利率", "收益", "风险", "A股", "港股", "美股", "期货"
        ],
        FilterScenario.MEDICAL: [
            "医疗", "健康", "药品", "医院", "医生", "治疗", "疾病",
            "症状", "诊断", "处方", "保健", "养生"
        ],
        FilterScenario.EDUCATION: [
            "教育", "培训", "课程", "学习", "考试", "学校", "老师",
            "学生", "辅导", "网课", "证书", "考研", "考公"
        ],
    }
    
    # 严格程度关键词
    SEVERITY_KEYWORDS = {
        FilterSeverity.STRICT: [
            "严格", "严格过滤", "全部过滤", "零容忍", "高标准",
            "敏感", "重要", "官方", "正式"
        ],
        FilterSeverity.RELAXED: [
            "宽松", "放宽", "仅过滤", "只过滤", "简单过滤",
            "大概", "粗略", "快速"
        ],
    }
    
    # 类别关键词映射
    CATEGORY_KEYWORDS = {
        "ad": ["广告", "推广", "引流", "营销", "宣传"],
        "spam": ["垃圾", "刷屏", "骚扰", "无意义"],
        "sensitive": ["敏感", "违规", "违法", "政治"],
        "profanity": ["脏话", "辱骂", "低俗", "色情"],
    }
    
    def __init__(self, use_llm: bool = False, llm_engine=None):
        """
        初始化分析器
        
        Args:
            use_llm: 是否使用LLM进行高级分析
            llm_engine: LLM引擎实例
        """
        self.use_llm = use_llm
        self.llm_engine = llm_engine
    
    def analyze(
        self,
        query: str,
        context: Dict[str, Any] = None,
        explicit_scenario: str = None,
        explicit_severity: str = None,
    ) -> QueryIntent:
        """
        分析查询意图
        
        Args:
            query: 用户查询/过滤请求描述
            context: 上下文信息（如数据来源、用户偏好等）
            explicit_scenario: 显式指定的场景
            explicit_severity: 显式指定的严格程度
            
        Returns:
            QueryIntent: 分析结果
        """
        intent = QueryIntent()
        context = context or {}
        
        # 1. 确定场景
        if explicit_scenario:
            intent.scenario = self._parse_scenario(explicit_scenario)
        else:
            intent.scenario = self._detect_scenario(query, context)
        
        # 2. 确定严格程度
        if explicit_severity:
            intent.severity = self._parse_severity(explicit_severity)
        else:
            intent.severity = self._detect_severity(query, context)
        
        # 3. 提取额外关注类别
        intent.extra_categories = self._extract_categories(query)
        
        # 4. 提取自定义关键词
        intent.custom_keywords = self._extract_custom_keywords(query)
        
        # 5. 使用LLM增强分析（如果启用）
        if self.use_llm and self.llm_engine:
            intent = self._enhance_with_llm(query, intent, context)
        
        # 6. 添加元数据
        intent.metadata = {
            "original_query": query,
            "context": context,
            "analyzed_at": self._get_timestamp(),
        }
        
        return intent
    
    def _parse_scenario(self, scenario_str: str) -> FilterScenario:
        """解析场景字符串"""
        scenario_str = scenario_str.lower().strip()
        for scenario in FilterScenario:
            if scenario.value == scenario_str:
                return scenario
        return FilterScenario.NORMAL
    
    def _parse_severity(self, severity_str: str) -> FilterSeverity:
        """解析严格程度字符串"""
        severity_str = severity_str.lower().strip()
        for severity in FilterSeverity:
            if severity.value == severity_str:
                return severity
        return FilterSeverity.NORMAL
    
    def _detect_scenario(self, query: str, context: Dict) -> FilterScenario:
        """自动检测场景"""
        query_lower = query.lower()
        
        # 从上下文获取数据来源
        source = context.get("source", "").lower()
        if "xhs" in source or "小红书" in source:
            return FilterScenario.SOCIAL
        if "weibo" in source or "微博" in source:
            return FilterScenario.SOCIAL
        if "taobao" in source or "jd" in source:
            return FilterScenario.ECOMMERCE
        
        # 根据关键词检测
        scores = {scenario: 0 for scenario in FilterScenario}
        
        for scenario, keywords in self.SCENARIO_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[scenario] += 1
        
        # 返回得分最高的场景
        max_scenario = max(scores, key=scores.get)
        if scores[max_scenario] > 0:
            return max_scenario
        
        return FilterScenario.NORMAL
    
    def _detect_severity(self, query: str, context: Dict) -> FilterSeverity:
        """自动检测严格程度"""
        query_lower = query.lower()
        
        for severity, keywords in self.SEVERITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return severity
        
        # 根据上下文判断
        if context.get("official", False) or context.get("important", False):
            return FilterSeverity.STRICT
        
        return FilterSeverity.NORMAL
    
    def _extract_categories(self, query: str) -> List[str]:
        """提取需要额外关注的类别"""
        categories = []
        query_lower = query.lower()
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    if category not in categories:
                        categories.append(category)
                    break
        
        return categories
    
    def _extract_custom_keywords(self, query: str) -> List[str]:
        """提取自定义关键词"""
        keywords = []
        
        # 匹配引号内的关键词
        # "关键词1" "关键词2"
        quoted = re.findall(r'["\']([^"\']+)["\']', query)
        keywords.extend(quoted)
        
        # 匹配【】内的关键词
        bracketed = re.findall(r'【([^】]+)】', query)
        keywords.extend(bracketed)
        
        # 匹配"过滤xxx"模式
        filter_patterns = re.findall(r'过滤[：:]\s*([^\s,，]+)', query)
        keywords.extend(filter_patterns)
        
        return list(set(keywords))
    
    def _enhance_with_llm(
        self,
        query: str,
        intent: QueryIntent,
        context: Dict
    ) -> QueryIntent:
        """使用LLM增强分析结果"""
        # TODO: 实现LLM增强分析
        # 这里可以调用LLM来：
        # 1. 验证场景判断是否准确
        # 2. 发现更多隐含的过滤需求
        # 3. 生成更精确的自定义关键词
        return intent
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# 便捷函数
def analyze_query(query: str, **kwargs) -> QueryIntent:
    """分析查询意图的便捷函数"""
    analyzer = QueryAnalyzer()
    return analyzer.analyze(query, **kwargs)
