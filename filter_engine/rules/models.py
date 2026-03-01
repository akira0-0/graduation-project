# -*- coding: utf-8 -*-
"""
规则数据模型
定义规则和过滤结果的数据结构
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class RuleType(str, Enum):
    """规则类型"""
    KEYWORD = "keyword"      # 关键词列表
    REGEX = "regex"          # 正则表达式
    PATTERN = "pattern"      # 模式规则（组合）
    

class RuleCategory(str, Enum):
    """规则分类"""
    SPAM = "spam"            # 垃圾信息
    AD = "ad"                # 广告
    SENSITIVE = "sensitive"  # 敏感内容
    PROFANITY = "profanity"  # 不当言论
    OTHER = "other"          # 其他


class RuleBase(BaseModel):
    """规则基础模型"""
    name: str = Field(..., description="规则名称", max_length=100)
    type: RuleType = Field(..., description="规则类型")
    content: str = Field(..., description="规则内容(JSON格式)")
    category: Optional[RuleCategory] = Field(None, description="规则分类")
    priority: int = Field(0, description="优先级(越大越先匹配)", ge=0, le=100)
    enabled: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="规则描述")


class RuleCreate(RuleBase):
    """创建规则请求"""
    pass


class RuleUpdate(BaseModel):
    """更新规则请求（所有字段可选）"""
    name: Optional[str] = Field(None, max_length=100)
    type: Optional[RuleType] = None
    content: Optional[str] = None
    category: Optional[RuleCategory] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    enabled: Optional[bool] = None
    description: Optional[str] = None


class Rule(RuleBase):
    """完整规则模型（包含数据库字段）"""
    id: int = Field(..., description="规则ID")
    version: int = Field(1, description="版本号")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True


class RuleVersion(BaseModel):
    """规则版本历史"""
    id: int
    rule_id: int
    version: int
    content: str
    created_at: datetime


class MatchedRule(BaseModel):
    """匹配到的规则信息"""
    rule_id: int
    rule_name: str
    rule_type: RuleType
    category: Optional[RuleCategory] = None
    matched_text: str = Field(..., description="匹配到的文本片段")
    confidence: float = Field(1.0, description="匹配置信度", ge=0, le=1)


class RuleEngineResult(BaseModel):
    """规则引擎过滤结果"""
    is_matched: bool = Field(False, description="是否命中规则")
    confidence: float = Field(0.0, description="置信度", ge=0, le=1)
    matched_rules: List[MatchedRule] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list, description="命中的分类")


class LLMResult(BaseModel):
    """LLM过滤结果"""
    is_spam: bool = Field(False, description="是否为垃圾信息")
    confidence: float = Field(0.0, description="置信度", ge=0, le=1)
    reason: Optional[str] = Field(None, description="判断理由")
    category: Optional[str] = Field(None, description="内容分类")
    raw_response: Optional[str] = Field(None, description="原始响应")


class FilterResult(BaseModel):
    """最终过滤结果"""
    id: str = Field("", description="数据ID")
    content: str = Field("", description="原始内容")
    is_spam: bool = Field(False, description="是否为垃圾信息")
    confidence: float = Field(0.0, description="综合置信度", ge=0, le=1)
    matched_rules: List[str] = Field(default_factory=list, description="命中的规则名称")
    llm_reason: Optional[str] = Field(None, description="LLM判断理由")
    category: Optional[str] = Field(None, description="内容分类")
    source: str = Field("rule", description="判断来源: rule/llm/combined")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()


class BatchFilterResult(BaseModel):
    """批量过滤结果统计"""
    total: int = Field(0, description="总数")
    spam_count: int = Field(0, description="垃圾信息数")
    clean_count: int = Field(0, description="正常数据数")
    suspicious_count: int = Field(0, description="疑似垃圾数")
    categories: Dict[str, int] = Field(default_factory=dict, description="各分类数量")
