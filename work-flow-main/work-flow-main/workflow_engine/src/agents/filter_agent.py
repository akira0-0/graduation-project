"""
信息过滤智能体（增强版）
支持多种过滤规则：关键词过滤、质量评分、去重、时间范围等
集成数据存储服务，支持从数据库读取和保存过滤结果
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import re
import hashlib
from collections import Counter
from ..database import get_session, AgentMemoryService
from ..utils.logger import get_logger

logger = get_logger("filter_agent")


class FilterAgent:
    """
    信息过滤智能体（增强版）
    支持多种过滤策略和规则管理
    集成数据存储服务，支持从数据库读取和保存过滤结果
    """
    
    def __init__(self, workflow_id: str, auto_save: bool = True):
        """
        初始化智能体
        
        Args:
            workflow_id: 工作流 ID
            auto_save: 是否自动保存过滤结果到数据库（默认True）
        """
        self.workflow_id = workflow_id
        self.db = get_session()
        self.memory_service = AgentMemoryService(self.db)
        # 延迟导入避免循环依赖
        from ..services.data_storage_service import DataStorageService
        self.storage_service = DataStorageService(workflow_id)
        self.auto_save = auto_save
        
        # 初始化默认过滤规则
        self._initialize_default_rules()
        
        logger.info(f"信息过滤智能体初始化: {workflow_id}")
    
    def _initialize_default_rules(self):
        """初始化默认的过滤规则"""
        default_rules = [
            {
                "rule_id": "min_length",
                "description": "最小内容长度规则",
                "field": "content",
                "condition": "length >= 10",
                "action": "filter"
            },
            {
                "rule_id": "max_length",
                "description": "最大内容长度规则",
                "field": "content",
                "condition": "length <= 10000",
                "action": "filter"
            },
            {
                "rule_id": "exclude_duplicates",
                "description": "去重规则",
                "field": "content",
                "condition": "unique",
                "action": "deduplicate"
            },
            {
                "rule_id": "exclude_keywords",
                "description": "排除关键词规则",
                "field": "content",
                "keywords": ["广告", "推广", "营销", "advertisement", "spam"],
                "action": "filter"
            }
        ]
        
        # 检查是否已有默认规则
        existing_rules = self.memory_service.get_rules(
            self.workflow_id,
            "filter"
        )
        
        if not existing_rules:
            for rule in default_rules:
                self.memory_service.save_memory(
                    workflow_id=self.workflow_id,
                    agent_type="filter",
                    memory_type="rule",
                    key=rule["rule_id"],
                    value=rule,
                    extra_data={"category": "default_rule"}
                )
            
            logger.info("创建默认过滤规则")
    
    def filter_data(
        self,
        data: List[Dict[str, Any]],
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        过滤数据
        
        Args:
            data: 待过滤的数据列表
            filter_criteria: 过滤条件（可选）
                - keywords: 包含的关键词列表
                - exclude_keywords: 排除的关键词列表
                - min_length: 最小内容长度
                - max_length: 最大内容长度
                - min_confidence: 最小置信度
                - exclude_duplicates: 是否去重
                - time_range: 时间范围 {"start": "...", "end": "..."}
                - sort_by: 排序字段
                - limit: 结果数量限制
                - quality_threshold: 质量阈值
                
        Returns:
            过滤后的数据
        """
        logger.info(f"开始过滤数据，原始数据量: {len(data)}")
        
        if not data:
            logger.warning("没有数据需要过滤")
            return {
                "filtered_data": [],
                "filtered_count": 0,
                "original_count": 0,
                "filter_criteria": filter_criteria or {},
                "filter_stats": {}
            }
        
        filter_criteria = filter_criteria or {}
        original_count = len(data)
        filtered_data = data.copy()
        filter_stats = {
            "original_count": original_count,
            "filter_steps": []
        }
        
        # 1. 去重
        if filter_criteria.get("exclude_duplicates", True):
            filtered_data, dedup_stats = self._deduplicate_data(filtered_data)
            filter_stats["filter_steps"].append({
                "step": "deduplicate",
                "input_count": original_count,
                "output_count": len(filtered_data),
                "removed_count": dedup_stats["removed_count"]
            })
        
        # 2. 关键词过滤
        keywords = filter_criteria.get("keywords", [])
        exclude_keywords = filter_criteria.get("exclude_keywords", [])
        
        if keywords or exclude_keywords:
            filtered_data, keyword_stats = self._filter_by_keywords(
                filtered_data,
                keywords,
                exclude_keywords
            )
            filter_stats["filter_steps"].append({
                "step": "keyword_filter",
                "input_count": filter_stats["filter_steps"][-1]["output_count"] if filter_stats["filter_steps"] else original_count,
                "output_count": len(filtered_data),
                "matched_keywords": keyword_stats["matched_keywords"],
                "excluded_count": keyword_stats["excluded_count"]
            })
        
        # 3. 长度过滤
        min_length = filter_criteria.get("min_length", 0)
        max_length = filter_criteria.get("max_length", float('inf'))
        
        if min_length > 0 or max_length < float('inf'):
            filtered_data, length_stats = self._filter_by_length(
                filtered_data,
                min_length,
                max_length
            )
            filter_stats["filter_steps"].append({
                "step": "length_filter",
                "input_count": filter_stats["filter_steps"][-1]["output_count"] if filter_stats["filter_steps"] else original_count,
                "output_count": len(filtered_data),
                "too_short": length_stats["too_short"],
                "too_long": length_stats["too_long"]
            })
        
        # 4. 时间范围过滤
        time_range = filter_criteria.get("time_range", {})
        if time_range:
            filtered_data, time_stats = self._filter_by_time_range(
                filtered_data,
                time_range
            )
            filter_stats["filter_steps"].append({
                "step": "time_filter",
                "input_count": filter_stats["filter_steps"][-1]["output_count"] if filter_stats["filter_steps"] else original_count,
                "output_count": len(filtered_data),
                "out_of_range": time_stats["out_of_range"]
            })
        
        # 5. 置信度过滤
        min_confidence = filter_criteria.get("min_confidence", 0.0)
        if min_confidence > 0.0:
            filtered_data, confidence_stats = self._filter_by_confidence(
                filtered_data,
                min_confidence
            )
            filter_stats["filter_steps"].append({
                "step": "confidence_filter",
                "input_count": filter_stats["filter_steps"][-1]["output_count"] if filter_stats["filter_steps"] else original_count,
                "output_count": len(filtered_data),
                "below_threshold": confidence_stats["below_threshold"]
            })
        
        # 6. 质量评分过滤
        quality_threshold = filter_criteria.get("quality_threshold", 0.0)
        if quality_threshold > 0.0:
            filtered_data, quality_stats = self._filter_by_quality(
                filtered_data,
                quality_threshold
            )
            filter_stats["filter_steps"].append({
                "step": "quality_filter",
                "input_count": filter_stats["filter_steps"][-1]["output_count"] if filter_stats["filter_steps"] else original_count,
                "output_count": len(filtered_data),
                "low_quality": quality_stats["low_quality"]
            })
        
        # 7. 排序
        sort_by = filter_criteria.get("sort_by", "timestamp")
        reverse = filter_criteria.get("sort_reverse", True)
        filtered_data = self._sort_data(filtered_data, sort_by, reverse)
        
        # 8. 限制数量
        limit = filter_criteria.get("limit", None)
        if limit and limit > 0:
            filtered_data = filtered_data[:limit]
            filter_stats["filter_steps"].append({
                "step": "limit",
                "input_count": len(filtered_data),
                "output_count": min(len(filtered_data), limit),
                "removed_count": max(0, len(filtered_data) - limit)
            })
        
        # 保存过滤统计
        self._save_filter_stats(filter_stats, filter_criteria)
        
        # 自动保存过滤结果到数据库
        if self.auto_save and filtered_data:
            self._save_to_database(filtered_data, filter_stats, filter_criteria)
        
        logger.info(f"过滤完成，原始: {original_count}, 过滤后: {len(filtered_data)}")
        
        return {
            "filtered_data": filtered_data,
            "filtered_count": len(filtered_data),
            "original_count": original_count,
            "filter_criteria": filter_criteria,
            "filter_stats": filter_stats,
            "extra_data": {
                "workflow_id": self.workflow_id,
                "filtered_at": datetime.utcnow().isoformat(),
                "status": "success"
            }
        }
    
    def _save_to_database(
        self,
        filtered_data: List[Dict[str, Any]],
        filter_stats: Dict[str, Any],
        filter_criteria: Dict[str, Any]
    ):
        """
        保存过滤结果到数据库
        
        Args:
            filtered_data: 过滤后的数据
            filter_stats: 过滤统计
            filter_criteria: 过滤条件
        """
        try:
            # 保存过滤后的数据
            self.storage_service.store_collected_data(
                data=filtered_data,
                agent_type="filter",
                workflow_id=self.workflow_id
            )
            
            # 保存过滤统计作为分析结果
            self.storage_service.store_analysis_result(
                result={
                    "filter_stats": filter_stats,
                    "filter_criteria": filter_criteria,
                    "filtered_count": len(filtered_data)
                },
                analysis_type="filter",
                agent_type="filter",
                workflow_id=self.workflow_id
            )
            
            logger.info(f"过滤结果已保存到数据库: {len(filtered_data)}条")
        except Exception as e:
            logger.error(f"保存过滤结果失败: {e}")
    
    def filter_from_database(
        self,
        filter_criteria: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        从数据库读取数据进行过滤
        
        Args:
            filter_criteria: 过滤条件
            source: 数据来源（可选）
            limit: 读取的最大数量
            
        Returns:
            过滤结果
        """
        logger.info("从数据库读取数据进行过滤")
        
        # 从数据库读取收集的数据
        collected_data = self.storage_service.get_collected_data(
            workflow_id=self.workflow_id,
            source=source,
            limit=limit
        )
        
        if not collected_data:
            logger.warning("数据库中没有数据")
            return {
                "filtered_data": [],
                "filtered_count": 0,
                "original_count": 0,
                "filter_criteria": filter_criteria or {},
                "filter_stats": {},
                "message": "数据库中没有数据"
            }
        
        # 执行过滤
        return self.filter_data(collected_data, filter_criteria)
    
    def _deduplicate_data(
        self,
        data: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        数据去重
        
        Args:
            data: 数据列表
            
        Returns:
            (去重后的数据, 统计信息)
        """
        seen_hashes = set()
        deduplicated = []
        duplicate_count = 0
        
        for item in data:
            # 使用内容生成哈希值
            content = item.get("content", "")
            item_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            
            if item_hash not in seen_hashes:
                seen_hashes.add(item_hash)
                deduplicated.append(item)
            else:
                duplicate_count += 1
        
        stats = {
            "removed_count": duplicate_count,
            "unique_count": len(deduplicated)
        }
        
        logger.info(f"去重完成，移除 {duplicate_count} 条重复数据")
        return deduplicated, stats
    
    def _filter_by_keywords(
        self,
        data: List[Dict[str, Any]],
        keywords: List[str],
        exclude_keywords: List[str]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        关键词过滤
        
        Args:
            data: 数据列表
            keywords: 包含的关键词列表
            exclude_keywords: 排除的关键词列表
            
        Returns:
            (过滤后的数据, 统计信息)
        """
        filtered = []
        excluded_count = 0
        matched_keywords = Counter()
        
        for item in data:
            content = item.get("content", "").lower()
            
            # 检查排除关键词
            exclude = False
            for keyword in exclude_keywords:
                if keyword.lower() in content:
                    exclude = True
                    excluded_count += 1
                    break
            
            if exclude:
                continue
            
            # 检查包含关键词（如果指定了）
            if keywords:
                matched = False
                for keyword in keywords:
                    if keyword.lower() in content:
                        matched = True
                        matched_keywords[keyword] += 1
                        break
                
                if matched:
                    filtered.append(item)
            else:
                filtered.append(item)
        
        stats = {
            "matched_keywords": dict(matched_keywords),
            "excluded_count": excluded_count
        }
        
        logger.info(f"关键词过滤完成，排除 {excluded_count} 条，匹配关键词: {dict(matched_keywords)}")
        return filtered, stats
    
    def _filter_by_length(
        self,
        data: List[Dict[str, Any]],
        min_length: int,
        max_length: int
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        长度过滤
        
        Args:
            data: 数据列表
            min_length: 最小长度
            max_length: 最大长度
            
        Returns:
            (过滤后的数据, 统计信息)
        """
        filtered = []
        too_short = 0
        too_long = 0
        
        for item in data:
            content = item.get("content", "")
            length = len(content)
            
            if length < min_length:
                too_short += 1
                continue
            
            if length > max_length:
                too_long += 1
                continue
            
            filtered.append(item)
        
        stats = {
            "too_short": too_short,
            "too_long": too_long
        }
        
        logger.info(f"长度过滤完成，过短: {too_short}, 过长: {too_long}")
        return filtered, stats
    
    def _filter_by_time_range(
        self,
        data: List[Dict[str, Any]],
        time_range: Dict[str, str]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        时间范围过滤
        
        Args:
            data: 数据列表
            time_range: 时间范围 {"start": "...", "end": "..."}
            
        Returns:
            (过滤后的数据, 统计信息)
        """
        filtered = []
        out_of_range = 0
        
        start_time = datetime.fromisoformat(time_range["start"]) if "start" in time_range else None
        end_time = datetime.fromisoformat(time_range["end"]) if "end" in time_range else None
        
        for item in data:
            timestamp_str = item.get("timestamp", "")
            
            if not timestamp_str:
                # 如果没有时间戳，保留数据
                filtered.append(item)
                continue
            
            try:
                item_time = datetime.fromisoformat(timestamp_str)
                
                if start_time and item_time < start_time:
                    out_of_range += 1
                    continue
                
                if end_time and item_time > end_time:
                    out_of_range += 1
                    continue
                
                filtered.append(item)
            except (ValueError, TypeError):
                # 时间解析失败，保留数据
                filtered.append(item)
        
        stats = {
            "out_of_range": out_of_range
        }
        
        logger.info(f"时间过滤完成，超出范围: {out_of_range}")
        return filtered, stats
    
    def _filter_by_confidence(
        self,
        data: List[Dict[str, Any]],
        min_confidence: float
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        置信度过滤
        
        Args:
            data: 数据列表
            min_confidence: 最小置信度
            
        Returns:
            (过滤后的数据, 统计信息)
        """
        filtered = []
        below_threshold = 0
        
        for item in data:
            confidence = item.get("confidence", 1.0)
            
            if confidence < min_confidence:
                below_threshold += 1
                continue
            
            filtered.append(item)
        
        stats = {
            "below_threshold": below_threshold
        }
        
        logger.info(f"置信度过滤完成，低于阈值: {below_threshold}")
        return filtered, stats
    
    def _filter_by_quality(
        self,
        data: List[Dict[str, Any]],
        quality_threshold: float
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        质量评分过滤
        
        Args:
            data: 数据列表
            quality_threshold: 质量阈值
            
        Returns:
            (过滤后的数据, 统计信息)
        """
        filtered = []
        low_quality = 0
        
        for item in data:
            # 计算质量分数
            quality_score = self._calculate_quality_score(item)
            
            if quality_score < quality_threshold:
                low_quality += 1
                continue
            
            # 添加质量分数到数据项
            item_with_quality = item.copy()
            item_with_quality["quality_score"] = quality_score
            filtered.append(item_with_quality)
        
        stats = {
            "low_quality": low_quality
        }
        
        logger.info(f"质量过滤完成，低质量: {low_quality}")
        return filtered, stats
    
    def _calculate_quality_score(self, item: Dict[str, Any]) -> float:
        """
        计算数据项的质量分数
        
        Args:
            item: 数据项
            
        Returns:
            质量分数 (0.0 - 1.0)
        """
        score = 0.0
        
        # 1. 内容长度评分 (30%)
        content = item.get("content", "")
        length = len(content)
        if length >= 50:
            score += 0.3
        elif length >= 20:
            score += 0.2
        elif length >= 10:
            score += 0.1
        
        # 2. 信息完整性 (30%)
        if item.get("title"):
            score += 0.1
        if item.get("source"):
            score += 0.1
        if item.get("timestamp"):
            score += 0.1
        
        # 3. 情感丰富度 (20%)
        if item.get("sentiment"):
            score += 0.1
        if item.get("sentiment_score"):
            score += 0.1
        
        # 4. 元数据完整性 (20%)
        if item.get("metadata"):
            metadata = item["metadata"]
            if isinstance(metadata, dict):
                if metadata.get("author"):
                    score += 0.1
                if metadata.get("likes") or metadata.get("shares") or metadata.get("comments"):
                    score += 0.1
        
        return min(score, 1.0)
    
    def _sort_data(
        self,
        data: List[Dict[str, Any]],
        sort_by: str,
        reverse: bool = True
    ) -> List[Dict[str, Any]]:
        """
        排序数据
        
        Args:
            data: 数据列表
            sort_by: 排序字段
            reverse: 是否倒序
            
        Returns:
            排序后的数据
        """
        def sort_key(item):
            value = item.get(sort_by, "")
            
            # 处理时间戳
            if sort_by == "timestamp" and value:
                try:
                    return datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    return datetime.min
            
            # 处理数值
            if isinstance(value, (int, float)):
                return value
            
            # 处理字符串
            return str(value)
        
        try:
            return sorted(data, key=sort_key, reverse=reverse)
        except Exception as e:
            logger.warning(f"排序失败: {e}，返回原始顺序")
            return data
    
    def _save_filter_stats(
        self,
        filter_stats: Dict[str, Any],
        filter_criteria: Dict[str, Any]
    ):
        """
        保存过滤统计到记忆
        
        Args:
            filter_stats: 过滤统计
            filter_criteria: 过滤条件
        """
        self.memory_service.save_memory(
            workflow_id=self.workflow_id,
            agent_type="filter",
            memory_type="domain_knowledge",
            key=f"filter_stats_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            value={
                "filter_stats": filter_stats,
                "filter_criteria": filter_criteria
            },
            extra_data={"category": "filter_statistics"}
        )
    
    def add_filter_rule(
        self,
        rule_id: str,
        rule_definition: Dict[str, Any]
    ):
        """
        添加过滤规则
        
        Args:
            rule_id: 规则 ID
            rule_definition: 规则定义
        """
        self.memory_service.save_memory(
            workflow_id=self.workflow_id,
            agent_type="filter",
            memory_type="rule",
            key=rule_id,
            value=rule_definition,
            extra_data={"category": "custom_rule"}
        )
        
        logger.info(f"添加过滤规则: {rule_id}")
    
    def get_filter_rules(self) -> List[Dict[str, Any]]:
        """
        获取过滤规则
        
        Returns:
            过滤规则列表
        """
        rules = self.memory_service.get_rules(
            self.workflow_id,
            "filter"
        )
        
        # get_rules 返回的是列表而不是字典
        return rules if rules else []
    
    def remove_filter_rule(self, rule_id: str) -> bool:
        """
        删除过滤规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            是否成功删除
        """
        # 注意：需要实现记忆删除功能
        logger.info(f"尝试删除过滤规则: {rule_id}")
        return True
    
    def get_stored_results(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取已存储的过滤结果
        
        Args:
            limit: 返回的最大数量
            
        Returns:
            过滤结果列表
        """
        return self.storage_service.get_analysis_results(
            workflow_id=self.workflow_id,
            analysis_type="filter"
        )[:limit]
    
    def close(self):
        """关闭数据库连接"""
        if self.storage_service:
            self.storage_service.close()
        if self.db:
            self.db.close()