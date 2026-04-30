"""
外部数据适配器
将外部信息过滤组件的输出适配为本项目的数据格式

外部数据格式字段说明：
- id: 数据唯一标识
- original_id: 原始平台ID
- platform: 平台来源（weibo, twitter等）
- type: 内容类型（image, video, text等）
- url: 内容链接
- title: 标题
- content: 正文内容
- publish_time: 发布时间
- author_id: 作者ID
- author_nickname: 作者昵称
- author_ip_location: 作者IP属地
- author_is_verified: 作者是否认证
- metrics_likes: 点赞数
- metrics_collects: 收藏数
- metrics_comments: 评论数
- metrics_shares: 转发数
- tags: 标签列表
- source_keyword: 来源关键词
- filter_batch_id: 过滤批次ID
- filter_passed_rules: 通过的过滤规则
- filter_rejected_rules: 被拒绝的过滤规则
- quality_score: 质量评分
- relevance_score: 相关度评分
- filter_layer: 过滤层级
- created_at: 创建时间
- relevance_level: 相关度级别
- comments: 评论列表
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger("external_data_adapter")


class ExternalDataAdapter:
    """
    外部数据适配器
    将外部信息过滤组件的输出转换为本项目标准格式
    
    采用防御性编程，处理各种异常情况：
    - 缺失字段
    - 字段类型不匹配
    - 空值处理
    - 嵌套对象解析
    """
    
    # 字段映射：外部字段 -> 内部字段
    FIELD_MAPPING = {
        # 基本信息
        "id": "id",
        "original_id": "original_id",
        "platform": "source",
        "type": "content_type",
        "url": "url",
        "title": "title",
        "content": "content",
        
        # 作者信息
        "author_id": "author_id",
        "author_nickname": "author",
        "author_ip_location": "author_location",
        "author_is_verified": "author_verified",
        
        # 时间信息
        "publish_time": "publish_time",
        "created_at": "collected_at",
        
        # 指标数据
        "metrics_likes": "likes",
        "metrics_collects": "collects",
        "metrics_comments": "comments_count",
        "metrics_shares": "shares",
        
        # 过滤相关
        "filter_batch_id": "filter_batch_id",
        "filter_passed_rules": "filter_passed_rules",
        "filter_rejected_rules": "filter_rejected_rules",
        "filter_layer": "filter_layer",
        
        # 评分
        "quality_score": "quality_score",
        "relevance_score": "relevance_score",
        "relevance_level": "relevance_level",
        
        # 其他
        "tags": "tags",
        "source_keyword": "source_keyword",
    }
    
    def __init__(self, strict_mode: bool = False):
        """
        初始化适配器
        
        Args:
            strict_mode: 严格模式，开启后会抛出更多异常
        """
        self.strict_mode = strict_mode
        self.adapter_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "warnings": []
        }
    
    def adapt_single(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        适配单条数据
        
        Args:
            external_data: 外部数据源的单条数据
            
        Returns:
            适配后的标准格式数据
        """
        self.adapter_stats["total_processed"] += 1
        
        if not external_data:
            self._log_warning("空数据输入")
            self.adapter_stats["failed"] += 1
            return self._get_empty_result()
        
        try:
            result = self._do_adapt_single(external_data)
            self.adapter_stats["successful"] += 1
            return result
        except Exception as e:
            self.adapter_stats["failed"] += 1
            error_msg = f"适配数据失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            if self.strict_mode:
                raise
            return self._get_empty_result(error=str(e))
    
    def _do_adapt_single(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单条数据的适配逻辑
        
        Args:
            external_data: 外部数据源的单条数据
            
        Returns:
            适配后的标准格式数据
        """
        result = {}
        
        # 1. 基本字段映射（包含None值以保持字段完整性）
        for external_field, internal_field in self.FIELD_MAPPING.items():
            if external_field in external_data:
                value = external_data[external_field]
                result[internal_field] = self._normalize_value(value, external_field)
        
        # 2. 确保必要字段存在
        result = self._ensure_required_fields(result, external_data)
        
        # 3. 处理时间字段
        result = self._normalize_time_fields(result)
        
        # 4. 处理评论数据（嵌套对象）
        if "comments" in external_data:
            result["comments"] = self._adapt_comments(external_data["comments"])
        
        # 5. 计算衍生字段
        result = self._compute_derived_fields(result)
        
        # 6. 添加元数据
        result["adapter_info"] = {
            "adapter_version": "1.0.0",
            "adapted_at": datetime.utcnow().isoformat(),
            "source_platform": self._safe_get(external_data, "platform", "unknown")
        }
        
        return result
    
    def adapt_batch(
        self, 
        external_data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量适配数据
        
        Args:
            external_data_list: 外部数据源的数据列表
            
        Returns:
            包含适配结果和统计信息的字典
        """
        if not external_data_list:
            return {
                "data": [],
                "stats": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0
                }
            }
        
        adapted_data = []
        for item in external_data_list:
            adapted = self.adapt_single(item)
            if adapted.get("id"):  # 只保留有效数据
                adapted_data.append(adapted)
        
        return {
            "data": adapted_data,
            "stats": {
                "total": len(external_data_list),
                "successful": len(adapted_data),
                "failed": len(external_data_list) - len(adapted_data)
            }
        }
    
    def _safe_get(
        self, 
        data: Dict[str, Any], 
        key: str, 
        default: Any = None
    ) -> Any:
        """
        安全获取字典值
        
        Args:
            data: 数据字典
            key: 键名
            default: 默认值
            
        Returns:
            获取的值或默认值
        """
        if data is None:
            return default
        return data.get(key, default)
    
    def _normalize_value(self, value: Any, field_name: str) -> Any:
        """
        根据字段类型规范化值
        
        Args:
            value: 原始值
            field_name: 字段名
            
        Returns:
            规范化后的值
        """
        if value is None:
            return None
        
        # 处理特定字段类型
        if field_name in ["metrics_likes", "metrics_collects", "metrics_comments", 
                          "metrics_shares", "filter_layer"]:
            return self._safe_int(value)
        
        if field_name in ["quality_score", "relevance_score"]:
            return self._safe_float(value)
        
        if field_name in ["author_is_verified"]:
            return self._safe_bool(value)
        
        if field_name in ["tags", "filter_passed_rules", "filter_rejected_rules"]:
            return self._safe_list(value)
        
        return value
    
    def _safe_int(self, value: Any) -> int:
        """安全转换为整数"""
        if value is None:
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_bool(self, value: Any) -> bool:
        """安全转换为布尔值"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    
    def _safe_list(self, value: Any) -> List[Any]:
        """安全转换为列表"""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # 尝试解析JSON字符串
            try:
                import json
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # 作为单个元素
            return [value] if value else []
        return [value]
    
    def _ensure_required_fields(
        self, 
        result: Dict[str, Any], 
        original_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        确保必要字段存在
        
        Args:
            result: 当前结果
            original_data: 原始数据
            
        Returns:
            补充必要字段后的结果
        """
        # ID是必需的
        if not result.get("id"):
            result["id"] = self._safe_get(
                original_data, 
                "original_id",
                f"unknown_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
            )
        
        # content 或 title 至少需要一个
        if not result.get("content") and not result.get("title"):
            result["content"] = "[无内容]"
            self._log_warning(f"数据 {result.get('id')} 缺少 content 和 title 字段")
        
        # source/platform
        if not result.get("source"):
            result["source"] = "external"
        
        # timestamp
        if not result.get("timestamp"):
            result["timestamp"] = datetime.utcnow().isoformat()
        
        # sentiment 默认值
        if "sentiment" not in result:
            result["sentiment"] = "unknown"
        
        return result
    
    def _normalize_time_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        规范化时间字段
        
        Args:
            result: 当前结果
            
        Returns:
            处理时间字段后的结果
        """
        # 处理 publish_time
        if "publish_time" in result and result["publish_time"]:
            result["publish_time"] = self._parse_datetime(result["publish_time"])
        
        # 处理 collected_at
        if "collected_at" in result and result["collected_at"]:
            result["collected_at"] = self._parse_datetime(result["collected_at"])
        
        # 设置统一的 timestamp
        if "timestamp" not in result or not result["timestamp"]:
            result["timestamp"] = result.get("publish_time") or \
                                  result.get("collected_at") or \
                                  datetime.utcnow().isoformat()
        
        return result
    
    def _parse_datetime(self, value: Any) -> Optional[str]:
        """
        解析日期时间
        
        Args:
            value: 日期时间值
            
        Returns:
            ISO格式的日期时间字符串
        """
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value.isoformat()
        
        if isinstance(value, str):
            # 尝试解析常见的日期格式
            formats = [
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(value.replace("Z", "+00:00").split("+")[0], fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # 如果解析失败，返回原始字符串
            return value
        
        return None
    
    def _adapt_comments(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        适配评论数据
        
        Args:
            comments: 评论列表
            
        Returns:
            适配后的评论列表
        """
        if not comments:
            return []
        
        adapted_comments = []
        for comment in comments:
            try:
                adapted_comment = {
                    "id": self._safe_get(comment, "id"),
                    "content": self._safe_get(comment, "content", "[无内容]"),
                    "author": self._safe_get(comment, "author_nickname", "匿名用户"),
                    "author_id": self._safe_get(comment, "author_id"),
                    "author_location": self._safe_get(comment, "author_ip_location"),
                    "likes": self._safe_int(self._safe_get(comment, "metrics_likes")),
                    "publish_time": self._parse_datetime(self._safe_get(comment, "publish_time")),
                    "parent_id": self._safe_get(comment, "parent_comment_id"),
                    "reply_to": self._safe_get(comment, "reply_to_user_nickname"),
                    "comment_level": self._safe_int(self._safe_get(comment, "comment_level", 1)),
                    "filter_passed_rules": self._safe_list(
                        self._safe_get(comment, "filter_passed_rules")
                    ),
                    "filter_rejected_rules": self._safe_list(
                        self._safe_get(comment, "filter_rejected_rules")
                    ),
                }
                adapted_comments.append(adapted_comment)
            except Exception as e:
                self._log_warning(f"适配评论失败: {str(e)}")
                continue
        
        return adapted_comments
    
    def _compute_derived_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算衍生字段
        
        Args:
            result: 当前结果
            
        Returns:
            添加衍生字段后的结果
        """
        # 计算互动总量
        result["total_engagement"] = (
            self._safe_int(result.get("likes", 0)) +
            self._safe_int(result.get("collects", 0)) +
            self._safe_int(result.get("comments_count", 0)) +
            self._safe_int(result.get("shares", 0))
        )
        
        # 计算内容长度
        content = result.get("content", "")
        result["content_length"] = len(content) if content else 0
        
        # 判断是否通过过滤
        result["passed_filter"] = len(result.get("filter_rejected_rules", [])) == 0
        
        # 相关度评估
        relevance_score = result.get("relevance_score")
        if relevance_score is not None:
            if relevance_score >= 0.7:
                result["relevance_category"] = "high"
            elif relevance_score >= 0.4:
                result["relevance_category"] = "medium"
            else:
                result["relevance_category"] = "low"
        else:
            result["relevance_category"] = "unknown"
        
        return result
    
    def _get_empty_result(self, error: Optional[str] = None) -> Dict[str, Any]:
        """
        获取空的默认结果
        
        Args:
            error: 错误信息
            
        Returns:
            默认的空结果
        """
        result = {
            "id": f"empty_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            "content": "",
            "source": "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "sentiment": "unknown",
            "adapter_info": {
                "adapter_version": "1.0.0",
                "adapted_at": datetime.utcnow().isoformat(),
                "error": error
            }
        }
        return result
    
    def _log_warning(self, message: str):
        """
        记录警告信息
        
        Args:
            message: 警告消息
        """
        logger.warning(f"[ExternalDataAdapter] {message}")
        self.adapter_stats["warnings"].append(message)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取适配统计信息
        
        Returns:
            统计信息字典
        """
        return self.adapter_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.adapter_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "warnings": []
        }


def adapt_external_filter_output(
    external_data: List[Dict[str, Any]],
    strict_mode: bool = False
) -> Dict[str, Any]:
    """
    便捷函数：适配外部过滤组件输出
    
    Args:
        external_data: 外部数据列表
        strict_mode: 是否启用严格模式
        
    Returns:
        适配结果，包含数据和统计信息
    """
    adapter = ExternalDataAdapter(strict_mode=strict_mode)
    return adapter.adapt_batch(external_data)