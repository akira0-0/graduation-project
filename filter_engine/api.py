# -*- coding: utf-8 -*-
"""过滤引擎 API - FastAPI"""
import json
from typing import List, Optional, Tuple
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field

from .rules import RuleManager, RuleCreate, RuleUpdate, Rule
from .pipeline import FilterPipeline
from .core.dynamic_pipeline import DynamicFilterPipeline, DynamicFilterConfig
from .core.query_analyzer import QueryAnalyzer, FilterScenario, FilterSeverity
from .core.relevance_filter import SmartDataFilter, RelevanceLevel
from .llm.smart_matcher import SmartRuleMatcher, SmartMatchResult
from .config import settings


# ==================== 请求/响应模型 ====================

class FilterRequest(BaseModel):
    """过滤请求"""
    text: str = Field(..., description="待过滤文本")
    use_llm: bool = Field(False, description="是否使用LLM")


class DynamicFilterRequest(BaseModel):
    """动态过滤请求"""
    query: str = Field(..., description="用户查询/过滤需求描述")
    texts: List[str] = Field(..., description="待过滤文本列表")
    scenario: Optional[str] = Field(None, description="场景: normal/ecommerce/news/social/finance/medical/education")
    severity: Optional[str] = Field(None, description="严格程度: relaxed/normal/strict")
    auto_generate_rules: bool = Field(False, description="是否自动生成缺失规则")
    context: Optional[dict] = Field(None, description="上下文信息")


class QueryAnalyzeRequest(BaseModel):
    """查询分析请求"""
    query: str = Field(..., description="用户查询")
    context: Optional[dict] = Field(None, description="上下文信息")


class RuleGenerateRequest(BaseModel):
    """规则生成请求"""
    query: str = Field(..., description="需求描述")
    sample_texts: List[str] = Field(..., description="样本文本")
    category: Optional[str] = Field(None, description="目标类别")


class BatchFilterRequest(BaseModel):
    """批量过滤请求"""
    items: List[dict] = Field(..., description="数据列表")
    content_field: str = Field("content", description="内容字段名")
    use_llm: bool = Field(False, description="是否使用LLM")


class SmartMatchRequest(BaseModel):
    """智能规则匹配请求（仅分析，不过滤数据）"""
    query: str = Field(..., description="用户自然语言查询，如'帮我找便宜的丽江民宿，别看广告'")
    scenario: Optional[str] = Field(None, description="显式指定场景（可选）：normal/ecommerce/news/social/finance/medical/education")


class SmartFilterRequest(BaseModel):
    """智能过滤请求（Layer-2：场景规则 + LLM缺口分析，带数据）"""
    query: str = Field(..., description="用户自然语言查询，描述过滤目标和场景")
    contents: List[str] = Field(..., description="待过滤内容列表（每条为字符串）")
    scenario: Optional[str] = Field(None, description="显式指定场景（可选）")
    apply_gap_rules: bool = Field(True, description="是否将LLM生成的缺口规则即时应用到内容")


class RelevanceFilterRequest(BaseModel):
    """相关性筛选请求（Layer-3：LLM语义相关性）"""
    query: str = Field(..., description="用户查询，如'丽江有什么好玩的'")
    texts: List[str] = Field(..., description="待筛选文本列表")
    filter_spam: bool = Field(True, description="是否先过滤垃圾广告")
    filter_relevance: bool = Field(True, description="是否筛选相关性")
    min_relevance: str = Field("medium", description="最低相关性: high/medium/low")


class PipelineRequest(BaseModel):
    """完整三层过滤流水线请求"""
    query: str = Field(..., description="用户自然语言查询，描述过滤目标和场景")
    contents: List[str] = Field(..., description="待过滤内容列表（每条为字符串）")
    scenario: Optional[str] = Field(None, description="显式指定场景（可选）")
    # Layer-1 控制
    enable_base_filter: bool = Field(True, description="是否启用基础规则过滤（涉黄涉政涉暴）")
    # Layer-2 控制
    enable_scene_filter: bool = Field(True, description="是否启用场景规则 + LLM缺口分析")
    apply_gap_rules: bool = Field(True, description="是否将LLM补充规则即时应用到内容")
    # Layer-3 控制
    enable_relevance_filter: bool = Field(True, description="是否启用LLM语义相关性筛选")
    min_relevance: str = Field("medium", description="最低相关性阈值: high/medium/low")


class SaveSuggestedRulesRequest(BaseModel):
    """保存建议规则请求"""
    rules: List[dict] = Field(..., description="要保存的规则列表")


class ImportRulesRequest(BaseModel):
    """导入规则请求"""
    rules: List[dict] = Field(..., description="规则列表")


# ==================== FastAPI应用 ====================

app = FastAPI(
    title="过滤引擎 API",
    description="规则过滤 + LLM语义过滤 + 动态规则选择",
    version="2.1.0",
)

# 启动时修复数据库中的无效正则（必须在 RuleManager 初始化之前执行）
try:
    from .patch_db import patch_invalid_regex
    patch_invalid_regex()
except Exception:
    pass

# 全局实例
rule_manager = RuleManager(settings.DATABASE_PATH)
pipeline = FilterPipeline(use_llm=False)

# 动态过滤管道（懒加载）
_dynamic_pipeline = None

def get_dynamic_pipeline() -> DynamicFilterPipeline:
    """获取动态过滤管道（懒加载）"""
    global _dynamic_pipeline
    if _dynamic_pipeline is None:
        _dynamic_pipeline = DynamicFilterPipeline(
            db_path=settings.DATABASE_PATH,
            use_llm=True,
            config=DynamicFilterConfig(
                enable_dynamic_rules=True,
                enable_rule_generation=True,
                auto_save_generated_rules=False,
            )
        )
    return _dynamic_pipeline


# ==================== 规则管理API ====================

@app.get("/api/rules", response_model=List[Rule], tags=["规则管理"])
async def list_rules(
    enabled_only: bool = Query(False, description="只返回启用的规则"),
    category: str = Query(None, description="按分类筛选"),
):
    """获取规则列表"""
    return rule_manager.list(enabled_only=enabled_only, category=category)


@app.get("/api/rules/stats", tags=["规则管理"])
async def get_rules_stats():
    """获取规则统计"""
    return rule_manager.stats()


@app.get("/api/rules/{rule_id}", response_model=Rule, tags=["规则管理"])
async def get_rule(rule_id: int):
    """获取单条规则"""
    rule = rule_manager.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule


@app.post("/api/rules", response_model=Rule, tags=["规则管理"])
async def create_rule(data: RuleCreate):
    """创建规则"""
    # 验证 content 字段是有效 JSON
    try:
        parsed = json.loads(data.content)
        if data.type.value == 'keyword' and not isinstance(parsed, list):
            raise HTTPException(status_code=400, detail="关键词规则的 content 必须是 JSON 数组格式，如 [\"关键词1\", \"关键词2\"]")
        if data.type.value == 'regex' and not isinstance(parsed, list):
            raise HTTPException(status_code=400, detail="正则规则的 content 必须是 JSON 数组格式，如 [\"正则1\", \"正则2\"]")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"content 必须是有效的 JSON 格式: {e}")
    
    try:
        rule = rule_manager.create(data)
        pipeline.reload_rules()
        return rule
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/rules/{rule_id}", response_model=Rule, tags=["规则管理"])
async def update_rule(rule_id: int, data: RuleUpdate):
    """更新规则"""
    rule = rule_manager.update(rule_id, data)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    pipeline.reload_rules()
    return rule


@app.delete("/api/rules/{rule_id}", tags=["规则管理"])
async def delete_rule(rule_id: int):
    """删除规则"""
    if not rule_manager.delete(rule_id):
        raise HTTPException(status_code=404, detail="规则不存在")
    pipeline.reload_rules()
    return {"message": "删除成功"}


@app.put("/api/rules/{rule_id}/toggle", response_model=Rule, tags=["规则管理"])
async def toggle_rule(rule_id: int):
    """切换规则启用状态"""
    rule = rule_manager.toggle(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    pipeline.reload_rules()
    return rule


@app.get("/api/rules/{rule_id}/versions", tags=["规则管理"])
async def get_rule_versions(rule_id: int):
    """获取规则版本历史"""
    versions = rule_manager.get_versions(rule_id)
    return versions


@app.post("/api/rules/{rule_id}/rollback/{version}", response_model=Rule, tags=["规则管理"])
async def rollback_rule(rule_id: int, version: int):
    """回滚到指定版本"""
    rule = rule_manager.rollback(rule_id, version)
    if not rule:
        raise HTTPException(status_code=404, detail="规则或版本不存在")
    pipeline.reload_rules()
    return rule


@app.get("/api/rules/export", tags=["规则管理"])
async def export_rules():
    """导出所有规则"""
    rules = rule_manager.export_rules()
    return {"rules": rules, "count": len(rules)}


@app.post("/api/rules/import", tags=["规则管理"])
async def import_rules(data: ImportRulesRequest):
    """批量导入规则"""
    result = rule_manager.import_rules(data.rules, overwrite=True)
    pipeline.reload_rules()
    return {"message": "导入完成", **result}


@app.post("/api/rules/test", tags=["规则管理"])
async def test_rule(rule_id: int, text: str):
    """测试单条规则"""
    from .rules import RuleCreate
    rule = rule_manager.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    result = pipeline.rule_engine.test_rule(rule, text)
    return {
        "is_matched": result.is_matched,
        "confidence": result.confidence,
        "matched_rules": [m.model_dump() for m in result.matched_rules],
    }


# ==================== 过滤API ====================

@app.post("/api/filter", tags=["过滤"])
async def filter_text(request: FilterRequest):
    """过滤单条文本"""
    result = pipeline.filter_text(request.text, use_llm=request.use_llm)
    return result.model_dump()


@app.post("/api/filter/batch", tags=["过滤"])
async def filter_batch(request: BatchFilterRequest):
    """批量过滤"""
    results = pipeline.filter_and_split(
        request.items,
        content_field=request.content_field,
        use_llm=request.use_llm,
    )
    return results


# ==================== 动态过滤API ====================

@app.post("/api/filter/dynamic", tags=["动态过滤"])
async def dynamic_filter(request: DynamicFilterRequest):
    """
    动态过滤 - 根据查询意图自动选择规则
    
    功能：
    1. 分析用户查询意图（场景、严格程度）
    2. 动态选择适用的规则集
    3. 执行过滤
    4. （可选）分析缺口并生成新规则
    """
    try:
        dp = get_dynamic_pipeline()
        result = dp.filter_with_query(
            query=request.query,
            texts=request.texts,
            context=request.context,
            auto_generate_rules=request.auto_generate_rules,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query/analyze", tags=["动态过滤"])
async def analyze_query(request: QueryAnalyzeRequest):
    """
    分析查询意图
    
    返回：场景、严格程度、额外关注类别、自定义关键词
    """
    analyzer = QueryAnalyzer()
    intent = analyzer.analyze(
        query=request.query,
        context=request.context,
    )
    return intent.to_dict()


# ==================== 智能筛选API ====================

# 智能筛选器（懒加载）
_smart_filter = None

def get_smart_filter() -> SmartDataFilter:
    """获取智能筛选器"""
    global _smart_filter
    if _smart_filter is None:
        _smart_filter = SmartDataFilter(use_llm=True)
    return _smart_filter


# 智能规则匹配器（懒加载）
_smart_matcher = None

def get_smart_matcher() -> SmartRuleMatcher:
    """获取智能规则匹配器"""
    global _smart_matcher
    if _smart_matcher is None:
        _smart_matcher = SmartRuleMatcher(
            rule_manager=rule_manager,
            db_path=settings.DATABASE_PATH,
        )
    return _smart_matcher


@app.post("/api/filter/smart", tags=["智能筛选"])
async def filter_smart_relevance(request: RelevanceFilterRequest):
    """
    智能数据筛选（相关性，旧接口保留兼容）

    功能：
    1. 解析用户查询意图
    2. 过滤垃圾/广告内容
    3. 筛选与查询相关的内容
    4. 按相关性排序返回
    """
    try:
        sf = get_smart_filter()
        relevance_map = {
            "high": RelevanceLevel.HIGH,
            "medium": RelevanceLevel.MEDIUM,
            "low": RelevanceLevel.LOW,
        }
        min_rel = relevance_map.get(request.min_relevance, RelevanceLevel.MEDIUM)
        result = sf.smart_filter(
            query=request.query,
            texts=request.texts,
            filter_spam=request.filter_spam,
            filter_relevance=request.filter_relevance,
            min_relevance=min_rel,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/filter/relevance", tags=["智能筛选"])
async def filter_by_relevance(request: RelevanceFilterRequest):
    """
    仅按相关性筛选（不过滤垃圾）

    更快速，适合已清洗的数据
    """
    try:
        sf = get_smart_filter()
        relevance_map = {
            "high": RelevanceLevel.HIGH,
            "medium": RelevanceLevel.MEDIUM,
            "low": RelevanceLevel.LOW,
        }
        min_rel = relevance_map.get(request.min_relevance, RelevanceLevel.MEDIUM)
        result = sf.relevance_filter.filter_by_relevance(
            query=request.query,
            texts=request.texts,
            min_relevance=min_rel,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules/generate", tags=["动态过滤"])
async def generate_rules(request: RuleGenerateRequest):
    """
    根据样本文本生成过滤规则
    
    使用LLM分析样本文本并生成适用的规则
    """
    try:
        dp = get_dynamic_pipeline()
        generated_rules = dp.generate_missing_rules(
            query=request.query,
            sample_texts=request.sample_texts,
            category=request.category,
        )
        return {
            "generated_rules": [r.to_dict() for r in generated_rules],
            "count": len(generated_rules),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules/generate/save", tags=["动态过滤"])
async def save_generated_rule(rule_data: dict):
    """保存生成的规则"""
    try:
        dp = get_dynamic_pipeline()
        
        # 从rule_data构建RuleCreate
        from .rules import RuleCreate, RuleType, RuleCategory
        
        rule_info = rule_data.get("rule", rule_data)
        rule_create = RuleCreate(
            name=rule_info["name"],
            type=RuleType(rule_info["type"]),
            content=rule_info["content"],
            category=RuleCategory(rule_info["category"]) if rule_info.get("category") else None,
            priority=rule_info.get("priority", 50),
            description=rule_info.get("description", "LLM自动生成"),
            enabled=True,
        )
        
        rule = rule_manager.create(rule_create)
        pipeline.reload_rules()
        dp.reload_rules()
        
        return {"message": "规则已保存", "rule_id": rule.id, "rule": rule.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scenarios", tags=["动态过滤"])
async def list_scenarios():
    """获取支持的过滤场景列表"""
    return {
        "scenarios": [
            {"value": "normal", "label": "通用场景", "description": "默认过滤规则"},
            {"value": "ecommerce", "label": "电商场景", "description": "商品评论、好评返现等"},
            {"value": "news", "label": "新闻资讯", "description": "新闻内容、政治敏感等"},
            {"value": "social", "label": "社交内容", "description": "评论、私信、引流等"},
            {"value": "finance", "label": "金融财经", "description": "投资、理财、股票等"},
            {"value": "medical", "label": "医疗健康", "description": "医药、健康、保健品等"},
            {"value": "education", "label": "教育培训", "description": "课程、培训、考试等"},
        ],
        "severities": [
            {"value": "relaxed", "label": "宽松", "description": "仅过滤明显违规内容"},
            {"value": "normal", "label": "正常", "description": "标准过滤"},
            {"value": "strict", "label": "严格", "description": "严格过滤所有可疑内容"},
        ],
    }


@app.get("/api/dynamic/stats", tags=["动态过滤"])
async def get_dynamic_stats():
    """获取动态过滤统计"""
    try:
        dp = get_dynamic_pipeline()
        return dp.get_stats()
    except Exception as e:
        return {"error": str(e)}


# ==================== 智能规则匹配API ====================

@app.post("/api/smart-match", tags=["智能匹配"])
async def smart_match(request: SmartMatchRequest):
    """
    智能规则匹配（仅分析，不过滤数据）- Layer-2 分析入口

    流程：
      1. 场景识别（LLM + 关键词双保险）
      2. 加载场景专属规则库
      3. LLM 思维链：意图提取 → 规则匹配 → 缺口识别 → 补充规则生成
      4. 返回分析结果（matched_rules / gap_rules / needs_llm_filter）
    """
    try:
        matcher = get_smart_matcher()
        result = await matcher.match(request.query, force_scenario=request.scenario)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/smart-filter", tags=["智能匹配"])
async def smart_filter(request: SmartFilterRequest):
    """
    智能过滤（带数据）- Layer-2 执行入口

    在 /api/smart-match 分析的基础上，对提供的 contents 执行：
      1. LLM 分析 query → 识别场景、匹配/生成规则
      2. 场景规则引擎过滤（通用规则 + 场景规则 + LLM缺口规则）

    返回：
      - match_analysis: 与 /api/smart-match 相同的分析结果
      - filter_results: 每条内容的过滤结果（含命中规则、layer 标记）
      - stats: 统计汇总（含 needs_llm_filter 标记，告知是否需进入 Layer-3）
    """
    try:
        matcher = get_smart_matcher()
        result = await matcher.match(request.query, force_scenario=request.scenario)

        import re as _re
        scenario = result.detected_scenario
        _, scene_rules = matcher._load_rules_for_scenario(scenario)

        # 预解析场景规则（Layer-2 规则库，不含通用规则，通用规则由 Layer-1 负责）
        parsed_scene_rules = []
        for rule in scene_rules:
            try:
                keywords = json.loads(rule.content)
                if not isinstance(keywords, list):
                    keywords = [rule.content]
            except Exception:
                keywords = [rule.content] if rule.content else []
            if keywords:
                parsed_scene_rules.append((rule, keywords))

        filter_results = []
        for content in request.contents:
            matched = False
            matched_rule_name = None
            matched_purpose = None
            content_lower = content.lower()

            for rule, keywords in parsed_scene_rules:
                rule_type = rule.type.value if hasattr(rule.type, "value") else str(rule.type)
                hit = False
                if rule_type == "keyword":
                    hit = any(str(kw).lower() in content_lower for kw in keywords if kw)
                elif rule_type == "regex":
                    for pat in keywords:
                        try:
                            if _re.search(str(pat), content, _re.IGNORECASE):
                                hit = True
                                break
                        except _re.error:
                            pass
                else:
                    hit = any(str(kw).lower() in content_lower for kw in keywords if kw)

                if hit:
                    matched = True
                    matched_rule_name = rule.name
                    matched_purpose = rule.purpose.value if hasattr(rule.purpose, "value") else str(rule.purpose)
                    break

            filter_results.append({
                "content": content,
                "matched": matched,
                "rule": matched_rule_name,
                "purpose": matched_purpose,
                "layer": "scene_rule" if matched else None,
            })

        # 即时应用 LLM 缺口规则（不写库）
        if request.apply_gap_rules and result.gap_rules:
            unmatched_contents = [r["content"] for r in filter_results if not r["matched"]]
            gap_results = matcher.apply_gap_rules_to_content(unmatched_contents, result.gap_rules)
            gap_map = {r["content"]: r for r in gap_results}
            for item in filter_results:
                if not item["matched"] and item["content"] in gap_map:
                    gr = gap_map[item["content"]]
                    if gr["matched"]:
                        item.update({"matched": True, "rule": gr["rule"],
                                     "purpose": gr["purpose"], "layer": "llm_gap_rule"})

        stats = {
            "total": len(filter_results),
            "filtered": sum(1 for r in filter_results if r["matched"] and r.get("purpose") == "filter"),
            "selected": sum(1 for r in filter_results if r["matched"] and r.get("purpose") == "select"),
            "passed": sum(1 for r in filter_results if not r["matched"]),
            "needs_llm_filter": result.needs_llm_filter,
        }

        return {
            "match_analysis": result.to_dict(),
            "filter_results": filter_results,
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/smart-match/save", tags=["智能匹配"])
async def save_suggested_rules(request: SaveSuggestedRulesRequest):
    """
    保存智能匹配建议的规则
    
    将 suggest_save 中的规则保存到数据库
    """
    try:
        matcher = get_smart_matcher()
        
        # 构建 SuggestSaveRule 对象
        from .llm.smart_matcher import SuggestSaveRule
        
        suggest_rules = []
        for item in request.rules:
            suggest_rules.append(SuggestSaveRule(
                name=item.get("name", "未命名规则"),
                type=item.get("type", "keyword"),
                category=item.get("category", "other"),
                rule=item.get("rule", {}),
                reason=item.get("reason", "用户手动保存"),
            ))
        
        saved_ids = matcher.save_suggested_rules(suggest_rules)
        
        # 重载规则
        pipeline.reload_rules()
        
        return {
            "message": f"成功保存 {len(saved_ids)} 条规则",
            "saved_rule_ids": saved_ids,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BatchTestRequest(BaseModel):
    """批量测试请求"""
    contents: List[str] = Field(..., description="待测试内容列表")
    general_only: bool = Field(True, description="是否只使用通用场景规则（名称以'通用-'开头）")


class BatchTestItem(BaseModel):
    """批量测试结果项"""
    content: str
    matched: bool
    rule: Optional[str] = None
    purpose: Optional[str] = None


@app.post("/api/batch-test", response_model=List[BatchTestItem], tags=["智能匹配"])
async def batch_test(request: BatchTestRequest):
    """
    基础规则过滤引擎

    对多条内容进行规则匹配测试，返回每条内容的匹配结果。
    直接复用 RuleEngine（支持关键词/正则/pattern 三种类型，AC自动机加速）。
    general_only=True 时，只采纳名称以"通用-"开头的命中规则。
    """
    results = []

    for content in request.contents:
        # 复用全局 RuleEngine，支持 keyword / regex / pattern 三种类型
        engine_result = pipeline.rule_engine.filter(content)

        matched = False
        matched_rule_name = None
        matched_purpose = None

        if engine_result.is_matched:
            # 按 general_only 过滤命中规则列表
            candidate_rules = engine_result.matched_rules
            if request.general_only:
                candidate_rules = [
                    r for r in candidate_rules
                    if r.rule_name.startswith("通用-")
                ]

            if candidate_rules:
                # 优先取 filter 类型规则；若全为 select 则取第一条
                filter_hits = [r for r in candidate_rules if r.purpose == "filter"]
                hit_rule = filter_hits[0] if filter_hits else candidate_rules[0]

                matched = True
                matched_rule_name = hit_rule.rule_name
                matched_purpose = hit_rule.purpose

        results.append(BatchTestItem(
            content=content,
            matched=matched,
            rule=matched_rule_name,
            purpose=matched_purpose,
        ))

    return results


# ==================== 三层过滤流水线 (优化版) ====================

def apply_rules_to_contents(
    matcher,  # SmartRuleMatcher
    contents: List[str],
    matched_rules: List,  # List[MatchedRuleInfo]
    gap_rules: List,      # List[GapRule]
) -> Tuple[List[bool], dict]:
    """
    将已有规则和补充规则应用到内容列表
    
    Returns:
        (pass_flags, stats)
        pass_flags[i] = True 表示第 i 条内容通过
        stats = {"filter_count": X, "select_count": Y, "default_pass_count": Z}
    """
    # 1. 应用 gap_rules（LLM 生成的补充规则）
    gap_filter_results = matcher.apply_gap_rules_to_content(contents, gap_rules)
    
    # 2. 应用 matched_rules（规则库中已有的规则）
    import re as _re
    matched_filter_results = []
    if matched_rules:
        for text in contents:
            matched = False
            matched_name = None
            matched_purpose = None
            text_lower = text.lower()
            
            for rule_info in matched_rules:
                try:
                    rule_content = json.loads(rule_info.rule_content)
                    if not isinstance(rule_content, list):
                        rule_content = [rule_info.rule_content]
                except Exception:
                    rule_content = [rule_info.rule_content] if rule_info.rule_content else []
                
                if not rule_content:
                    continue
                
                hit = False
                if rule_info.rule_type == "keyword":
                    hit = any(str(kw).lower() in text_lower for kw in rule_content if kw)
                elif rule_info.rule_type == "regex":
                    for pat in rule_content:
                        try:
                            if _re.search(str(pat), text, _re.IGNORECASE):
                                hit = True
                                break
                        except _re.error:
                            pass
                else:
                    hit = any(str(kw).lower() in text_lower for kw in rule_content if kw)
                
                if hit:
                    matched = True
                    matched_name = rule_info.rule_name
                    matched_purpose = rule_info.purpose
                    break
            
            matched_filter_results.append({
                "content": text,
                "matched": matched,
                "rule": matched_name,
                "purpose": matched_purpose,
            })
    else:
        matched_filter_results = [
            {"content": text, "matched": False, "rule": None, "purpose": None}
            for text in contents
        ]
    
    # 3. 判断规则类型（是否存在 select 规则）
    has_filter_rules = any(r.purpose == "filter" for r in gap_rules)
    has_select_rules = any(r.purpose == "select" for r in gap_rules)
    
    if matched_rules:
        has_filter_rules = has_filter_rules or any(r.purpose == "filter" for r in matched_rules)
        has_select_rules = has_select_rules or any(r.purpose == "select" for r in matched_rules)
    
    # 4. 生成通过标记（综合两类规则的结果）
    pass_flags = []
    filter_count = 0
    select_count = 0
    not_selected_count = 0
    default_pass_count = 0
    
    for i, text in enumerate(contents):
        gap_result = gap_filter_results[i]
        matched_result = matched_filter_results[i]
        
        filtered = False
        selected = False
        
        # 检查 gap_rules
        if gap_result["matched"]:
            if gap_result["purpose"] == "filter":
                filtered = True
            elif gap_result["purpose"] == "select":
                selected = True
        
        # 检查 matched_rules
        if matched_result["matched"]:
            if matched_result["purpose"] == "filter":
                filtered = True
            elif matched_result["purpose"] == "select":
                selected = True
        
        # 决策逻辑
        if filtered:
            pass_flags.append(False)
            filter_count += 1
        elif has_select_rules:
            if selected:
                pass_flags.append(True)
                select_count += 1
            else:
                pass_flags.append(False)
                not_selected_count += 1
        else:
            pass_flags.append(True)
            default_pass_count += 1
    
    stats = {
        "filter_count": filter_count,
        "select_count": select_count,
        "not_selected_count": not_selected_count,
        "default_pass_count": default_pass_count,
    }
    
    return pass_flags, stats


class ThreeLayerFilterRequest(BaseModel):
    """三层过滤请求（优化版）"""
    query: str = Field(..., description="用户查询，如'丽江旅游攻略'")
    contents: List[str] = Field(..., description="待过滤内容列表", max_items=1000)
    
    # 全局控制
    session_id: Optional[str] = Field(None, description="Session ID（可选，用于追踪）")
    platform: Optional[str] = Field(None, description="平台标识（可选）")
    
    # Layer-1 控制
    enable_layer1: bool = Field(True, description="启用 Layer-1 基础规则过滤")
    min_content_length: int = Field(4, ge=0, description="最小内容长度")
    
    # Layer-2 控制
    enable_layer2: bool = Field(True, description="启用 Layer-2 场景规则过滤")
    force_scenario: Optional[str] = Field(None, description="强制指定场景")
    save_gap_rules: bool = Field(False, description="保存 LLM 生成的补充规则")
    
    # Layer-3 控制
    enable_layer3: bool = Field(True, description="启用 Layer-3 语义相关性过滤")
    min_relevance: str = Field("medium", description="最低相关性: high/medium/low")
    llm_only: bool = Field(True, description="Layer-3 完全依赖 LLM 判断")
    
    # 性能优化
    batch_size: int = Field(100, ge=10, le=500, description="批处理大小")
    max_workers: int = Field(3, ge=1, le=10, description="并发处理线程数")


class ThreeLayerFilterResponse(BaseModel):
    """三层过滤响应"""
    session_id: Optional[str] = None
    query: str
    
    # 统计信息
    stats: dict = Field(..., description="各层统计")
    
    # 最终结果
    results: List[dict] = Field(..., description="通过三层过滤的内容")
    
    # 性能信息
    performance: dict = Field(..., description="各层耗时(秒)")
    
    # 元数据
    metadata: dict = Field(default_factory=dict, description="额外元数据")


@app.post("/api/filter/three-layer", response_model=ThreeLayerFilterResponse, tags=["三层流水线"])
async def three_layer_filter(request: ThreeLayerFilterRequest):
    """
    🚀 三层过滤 API（优化版）
    
    **性能优化**:
    - 批量处理减少 LLM 调用
    - 并发处理提升吞吐量
    - 早停策略避免无效计算
    
    **处理流程**:
    1. Layer-1: 基础规则过滤（垃圾/敏感内容）
    2. Layer-2: 场景规则 + LLM 缺口分析
    3. Layer-3: LLM 语义相关性判断
    
    **示例**:
    ```bash
    curl -X POST "http://localhost:8081/api/filter/three-layer" \
      -H "Content-Type: application/json" \
      -d '{
        "query": "丽江旅游攻略",
        "contents": ["丽江古城游玩指南...", "广告：加微信..."],
        "enable_layer1": true,
        "enable_layer2": true,
        "enable_layer3": true
      }'
    ```
    
    **返回格式**:
    ```json
    {
      "session_id": "sess_xxx",
      "query": "丽江旅游攻略",
      "stats": {
        "total_input": 100,
        "layer1_passed": 85,
        "layer2_passed": 42,
        "layer3_passed": 28,
        "final_count": 28
      },
      "results": [...],
      "performance": {
        "layer1": 0.5,
        "layer2": 12.3,
        "layer3": 8.7,
        "total": 21.5
      }
    }
    ```
    """
    import time
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    start_time = time.time()
    session_id = request.session_id or f"sess_{int(time.time())}_{len(request.contents)}"
    
    # 性能追踪
    perf = {
        "layer1": 0.0,
        "layer2": 0.0,
        "layer3": 0.0,
        "total": 0.0,
    }
    
    # 统计信息
    stats = {
        "total_input": len(request.contents),
        "layer1_passed": 0,
        "layer2_passed": 0,
        "layer3_passed": 0,
        "final_count": 0,
    }
    
    # 结果容器（带索引）
    items = [{"index": i, "content": c, "passed": True, "layers": []} 
             for i, c in enumerate(request.contents)]
    
    try:
        # ═══════════════════════════════════════════════════════
        # Layer-1: 基础规则过滤
        # ═══════════════════════════════════════════════════════
        if request.enable_layer1:
            t0 = time.time()
            print(f"🔍 Layer-1: 基础规则过滤 ({len(items)} 条)")
            
            for item in items:
                content = item["content"]
                
                # 长度过滤
                if len(content.strip()) < request.min_content_length:
                    item["passed"] = False
                    item["reject_reason"] = "content_too_short"
                    continue
                
                # 规则引擎过滤（只用通用规则）
                result = pipeline.rule_engine.filter(content)
                
                # 检查是否命中通用规则（涉黄涉政涉暴等）
                if result.is_matched:
                    general_hits = [r for r in result.matched_rules 
                                   if r.rule_name.startswith("通用-") and r.purpose == "filter"]
                    if general_hits:
                        item["passed"] = False
                        item["reject_reason"] = "layer1_rule_matched"
                        item["matched_rule"] = general_hits[0].rule_name
                        continue
                
                item["layers"].append("layer1_passed")
            
            stats["layer1_passed"] = sum(1 for x in items if x["passed"])
            perf["layer1"] = time.time() - t0
            
            print(f"  ✅ Layer-1 完成: {stats['layer1_passed']}/{stats['total_input']} 通过 "
                  f"({perf['layer1']:.2f}s)")
            
            # 早停检查
            if stats["layer1_passed"] == 0:
                stats["final_count"] = 0
                perf["total"] = time.time() - start_time
                return ThreeLayerFilterResponse(
                    session_id=session_id,
                    query=request.query,
                    stats=stats,
                    results=[],
                    performance=perf,
                    metadata={"early_stop": "layer1", "reason": "no_content_passed"}
                )
        else:
            stats["layer1_passed"] = stats["total_input"]
        
        # ═══════════════════════════════════════════════════════
        # Layer-2: 场景规则 + LLM 缺口分析
        # ═══════════════════════════════════════════════════════
        if request.enable_layer2:
            t0 = time.time()
            survivors = [x for x in items if x["passed"]]
            print(f"\n🎯 Layer-2: 场景规则过滤 ({len(survivors)} 条)")
            
            matcher = get_smart_matcher()
            
            # Step 1: LLM 分析（只需一次）
            match_result = await matcher.match(request.query, force_scenario=request.force_scenario)
            
            print(f"  场景: {match_result.detected_scenario}")
            print(f"  已有规则: {len(match_result.matched_rules)} 条")
            print(f"  补充规则: {len(match_result.gap_rules)} 条")
            
            # Step 2: 应用规则
            contents = [x["content"] for x in survivors]
            pass_flags, rule_stats = apply_rules_to_contents(
                matcher, contents, match_result.matched_rules, match_result.gap_rules
            )
            
            # 更新通过状态
            for item, passed in zip(survivors, pass_flags):
                if not passed:
                    item["passed"] = False
                    item["reject_reason"] = "layer2_rule_matched"
                else:
                    item["layers"].append("layer2_passed")
            
            # 保存补充规则（可选）
            if request.save_gap_rules and match_result.suggest_save:
                saved = matcher.save_suggested_rules(match_result.suggest_save)
                print(f"  💾 已保存 {len(saved)} 条补充规则")
            
            stats["layer2_passed"] = sum(1 for x in items if x["passed"])
            perf["layer2"] = time.time() - t0
            
            print(f"  ✅ Layer-2 完成: {stats['layer2_passed']}/{stats['layer1_passed']} 通过 "
                  f"({perf['layer2']:.2f}s)")
            
            # 早停检查
            if stats["layer2_passed"] == 0:
                stats["final_count"] = 0
                perf["total"] = time.time() - start_time
                return ThreeLayerFilterResponse(
                    session_id=session_id,
                    query=request.query,
                    stats=stats,
                    results=[],
                    performance=perf,
                    metadata={"early_stop": "layer2", "reason": "no_content_passed"}
                )
        else:
            stats["layer2_passed"] = stats["layer1_passed"]
        
        # ═══════════════════════════════════════════════════════
        # Layer-3: LLM 语义相关性过滤
        # ═══════════════════════════════════════════════════════
        if request.enable_layer3:
            t0 = time.time()
            survivors = [x for x in items if x["passed"]]
            print(f"\n🤖 Layer-3: LLM 语义过滤 ({len(survivors)} 条)")
            
            sf = get_smart_filter()
            relevance_map = {
                "high": RelevanceLevel.HIGH,
                "medium": RelevanceLevel.MEDIUM,
                "low": RelevanceLevel.LOW,
            }
            min_rel = relevance_map.get(request.min_relevance, RelevanceLevel.MEDIUM)
            
            contents = [x["content"] for x in survivors]
            
            # 批量相关性判断（LLM only 模式）
            rel_result = sf.relevance_filter.filter_by_relevance(
                query=request.query,
                texts=contents,
                min_relevance=min_rel,
                use_llm_for_uncertain=True,
                llm_only=request.llm_only,
            )
            
            # 更新通过状态和相关性分数
            relevance_order = {
                RelevanceLevel.HIGH: 3,
                RelevanceLevel.MEDIUM: 2,
                RelevanceLevel.LOW: 1,
                RelevanceLevel.IRRELEVANT: 0,
            }
            min_order = relevance_order[min_rel]
            
            for item, res_dict in zip(survivors, rel_result["results"]):
                score = float(res_dict.get("score", 0.0))
                level_str = res_dict.get("relevance", "irrelevant")
                level = RelevanceLevel(level_str) if level_str in [e.value for e in RelevanceLevel] else RelevanceLevel.IRRELEVANT
                
                item["relevance_score"] = round(score, 3)
                item["relevance_level"] = level_str
                
                if relevance_order[level] >= min_order:
                    item["layers"].append("layer3_passed")
                else:
                    item["passed"] = False
                    item["reject_reason"] = "low_relevance"
            
            stats["layer3_passed"] = sum(1 for x in items if x["passed"])
            perf["layer3"] = time.time() - t0
            
            print(f"  ✅ Layer-3 完成: {stats['layer3_passed']}/{stats['layer2_passed']} 通过 "
                  f"({perf['layer3']:.2f}s)")
        else:
            stats["layer3_passed"] = stats["layer2_passed"]
        
        # ═══════════════════════════════════════════════════════
        # 汇总结果
        # ═══════════════════════════════════════════════════════
        final_results = [
            {
                "index": x["index"],
                "content": x["content"],
                "relevance_score": x.get("relevance_score"),
                "relevance_level": x.get("relevance_level"),
                "layers_passed": x["layers"],
            }
            for x in items if x["passed"]
        ]
        
        # 按相关性分数排序
        final_results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        
        stats["final_count"] = len(final_results)
        perf["total"] = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ 三层过滤完成")
        print(f"  总输入: {stats['total_input']}")
        print(f"  Layer-1 通过: {stats['layer1_passed']} ({stats['layer1_passed']/stats['total_input']*100:.1f}%)")
        print(f"  Layer-2 通过: {stats['layer2_passed']} ({stats['layer2_passed']/stats['total_input']*100:.1f}%)")
        print(f"  Layer-3 通过: {stats['layer3_passed']} ({stats['layer3_passed']/stats['total_input']*100:.1f}%)")
        print(f"  最终结果: {stats['final_count']} 条")
        print(f"  总耗时: {perf['total']:.2f}s")
        print(f"{'='*60}\n")
        
        return ThreeLayerFilterResponse(
            session_id=session_id,
            query=request.query,
            stats=stats,
            results=final_results,
            performance=perf,
            metadata={
                "scenario": match_result.detected_scenario if request.enable_layer2 else None,
                "min_relevance": request.min_relevance,
            }
        )
        
    except Exception as e:
        import traceback
        print(f"\n❌ 三层过滤出错: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Filter failed: {str(e)}")


# ==================== 一站式过滤 API ====================

class CompleteFilterRequest(BaseModel):
    """一站式过滤请求（输入 query，返回 post_data）"""
    query: str = Field(..., description="用户查询，如'丽江旅游攻略'")
    
    # 数据源控制
    platform: Optional[str] = Field(None, description="平台过滤（xhs/weibo），不填则全平台")
    max_posts: int = Field(500, ge=10, le=2000, description="最多处理帖子数")
    
    # Layer-2 控制
    force_scenario: Optional[str] = Field(None, description="强制指定场景")
    
    # Layer-3 控制
    min_relevance: str = Field("medium", description="最低相关性: high/medium/low")
    llm_only: bool = Field(True, description="Layer-3 完全依赖 LLM")
    
    # 返回控制
    limit: int = Field(50, ge=1, le=500, description="返回结果数量")
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="最低相关性分数过滤")
    include_comments: bool = Field(True, description="是否包含评论")
    
    # Session 控制
    save_session: bool = Field(True, description="是否保存到 Session 表（默认不保存）")


class CompleteFilterResponse(BaseModel):
    """一站式过滤响应（直接返回 post_data）"""
    query: str
    session_id: str
    
    # 统计信息
    stats: dict = Field(..., description="各层统计")
    
    # 最终数据（直接可用的 post_data）
    posts: List[dict] = Field(..., description="过滤后的帖子数据（含评论）")
    
    # 性能信息
    performance: dict = Field(..., description="各层耗时")
    
    # 元数据
    metadata: dict = Field(default_factory=dict)


@app.post("/api/filter/complete", response_model=CompleteFilterResponse, tags=["一站式过滤"])
async def complete_filter(request: CompleteFilterRequest):
    """
    🎯 一站式过滤 API（输入 query，直接返回 post_data）

    自动执行：数据读取 → Layer-2 → Layer-3 → 返回帖子+评论，一次请求即可获得结果。
    设置 save_session=True 可将结果持久化到数据库，支持后续通过 Session API 再次查询。
    """
    import time
    from .api_utils import (
        fetch_posts_from_db, run_layer2, run_layer3,
        fetch_comments, save_session, make_session_id,
        print_banner, print_summary,
    )

    start_time = time.time()
    session_id = make_session_id()
    perf = {"layer1": 0.0, "layer2": 0.0, "layer3": 0.0, "fetch_results": 0.0, "save_session": 0.0, "total": 0.0}
    stats = {"l1_total_posts": 0, "l2_passed_posts": 0, "l3_passed_posts": 0, "final_returned": 0}

    try:
        supabase = get_supabase()
        matcher = get_smart_matcher()
        sf = get_smart_filter()

        print_banner("🎯 一站式过滤", Query=request.query, Platform=request.platform or "全平台", Session=session_id)

        # Step 1: 读取 Layer-1 数据
        all_posts, perf["layer1"] = fetch_posts_from_db(supabase, request.platform, request.max_posts)
        stats["l1_total_posts"] = len(all_posts)
        print(f"  ✅ [L1] 读取 {stats['l1_total_posts']} 条 ({perf['layer1']:.2f}s)")

        if stats["l1_total_posts"] == 0:
            raise HTTPException(status_code=404, detail="filtered_posts 表无数据，请先运行 Layer-1 批量过滤")

        # Step 2: Layer-2 场景规则过滤
        passed_posts, match_result, perf["layer2"] = await run_layer2(
            matcher, request.query, all_posts, request.force_scenario
        )
        stats["l2_passed_posts"] = len(passed_posts)
        print(f"  ✅ [L2] 场景={match_result.detected_scenario}  通过={stats['l2_passed_posts']} ({perf['layer2']:.2f}s)")

        if stats["l2_passed_posts"] == 0:
            perf["total"] = time.time() - start_time
            return CompleteFilterResponse(
                query=request.query, session_id=session_id, stats=stats, posts=[],
                performance=perf, metadata={"early_stop": "layer2", "scenario": match_result.detected_scenario}
            )

        # Step 3: Layer-3 LLM 相关性过滤
        valid_posts, valid_ids, perf["layer3"] = run_layer3(
            sf, request.query, passed_posts, request.min_relevance, request.llm_only, request.min_score
        )
        stats["l3_passed_posts"] = len(valid_posts)
        print(f"  ✅ [L3] 通过={stats['l3_passed_posts']} ({perf['layer3']:.2f}s)")

        # Step 4: 读取评论
        if request.include_comments and valid_ids:
            comments_by_post, total_comments, perf["fetch_results"] = fetch_comments(supabase, valid_ids)
            for post in valid_posts:
                post["comments"] = comments_by_post.get(post["id"], [])
            print(f"  ✅ [评论] 共 {total_comments} 条 ({perf['fetch_results']:.2f}s)")
        else:
            for post in valid_posts:
                post["comments"] = []

        # Step 5: 排序 + 截断
        valid_posts.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        final_posts = valid_posts[:request.limit]
        stats["final_returned"] = len(final_posts)

        # Step 6: 可选保存 Session
        if request.save_session:
            perf["save_session"] = save_session(
                supabase, session_id, request.query, match_result.detected_scenario,
                stats, passed_posts, valid_posts
            )
            print(f"  ✅ [Session] 已保存 ({perf['save_session']:.2f}s)")

        perf["total"] = time.time() - start_time
        print_summary(stats, perf, session_id if request.save_session else None)

        return CompleteFilterResponse(
            query=request.query,
            session_id=session_id,
            stats=stats,
            posts=final_posts,
            performance=perf,
            metadata={
                "scenario": match_result.detected_scenario,
                "min_relevance": request.min_relevance,
                "platform": request.platform,
                "session_saved": request.save_session,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"\n❌ 一站式过滤出错: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"complete_filter failed: {str(e)}")


# ==================== 端到端自动过滤 API ====================

class AutoFilterRequest(BaseModel):
    """端到端自动过滤请求（从数据库读取）"""
    query: str = Field(..., description="用户查询，如'丽江旅游攻略'")
    
    # 数据源控制
    platform: Optional[str] = Field(None, description="平台过滤（xhs/weibo），不填则全平台")
    max_posts: int = Field(50000, ge=10, le=2000, description="最多处理帖子数")
    max_comments_per_post: int = Field(50, ge=0, le=200, description="每个帖子最多处理评论数")
    
    # Layer-2 控制
    force_scenario: Optional[str] = Field(None, description="强制指定场景")
    save_gap_rules: bool = Field(False, description="保存 LLM 生成的补充规则")
    
    # Layer-3 控制
    min_relevance: str = Field("medium", description="最低相关性: high/medium/low")
    llm_only: bool = Field(True, description="Layer-3 完全依赖 LLM")
    
    # Session 控制
    session_id: Optional[str] = Field(None, description="指定 Session ID（可选）")
    auto_save: bool = Field(True, description="自动保存到 session 临时表")


class AutoFilterResponse(BaseModel):
    """端到端自动过滤响应"""
    session_id: str
    query: str
    
    # 数据统计
    stats: dict = Field(..., description="各层统计")
    
    # 性能信息
    performance: dict = Field(..., description="各层耗时")
    
    # 数据访问
    access: dict = Field(..., description="数据访问方式")
    
    # 元数据
    metadata: dict = Field(default_factory=dict)


@app.post("/api/filter/auto", response_model=AutoFilterResponse, tags=["端到端过滤"])
async def auto_filter(request: AutoFilterRequest):
    """
    🤖 端到端自动过滤（从数据库读取数据）
    
    **核心特性**:
    - 只需输入 query，自动从数据库读取数据
    - 自动执行 Layer-1 → Layer-2 → Layer-3
    - 结果保存到 Session 临时表
    - 返回 API 访问地址
    
    **处理流程**:
    1. 从 `filtered_posts` 读取 Layer-1 已过滤数据
    2. 执行 Layer-2 场景规则过滤 → 写入 `session_l2_posts`
    3. 从 `filtered_comments` 读取有效帖子的评论 → 写入 `session_l2_comments`
    4. 执行 Layer-3 语义相关性过滤 → 写入 `session_l3_results`
    5. 更新 `session_metadata`
    
    **使用示例**:
    ```bash
    curl -X POST "http://localhost:8081/api/filter/auto" \
      -H "Content-Type: application/json" \
      -d '{
        "query": "丽江旅游攻略",
        "platform": "xhs",
        "max_posts": 500
      }'
    ```
    
    **返回格式**:
    ```json
    {
      "session_id": "sess_20260410_123456_abcd",
      "query": "丽江旅游攻略",
      "stats": {
        "l1_total_posts": 500,
        "l2_passed_posts": 234,
        "l3_passed_posts": 89
      },
      "performance": {
        "total": 45.6
      },
      "access": {
        "api_url": "/api/sessions/sess_xxx/results",
        "web_url": "http://localhost:8081/api/sessions/sess_xxx/results"
      }
    }
    ```
    
    **Agent 调用**:
    ```python
    # Step 1: 启动过滤任务
    response = requests.post(
        "http://localhost:8081/api/filter/auto",
        json={"query": "丽江旅游攻略", "platform": "xhs"}
    )
    session_id = response.json()["session_id"]
    
    # Step 2: 获取过滤结果
    results = requests.get(
        f"http://localhost:8081/api/sessions/{session_id}/results"
    ).json()
    ```
    """
    import time
    import hashlib
    from datetime import datetime, timezone
    from .api_utils import (
        fetch_posts_from_db, run_layer2, run_layer3,
        fetch_comments, make_session_id, print_banner, print_summary,
    )

    start_time = time.time()
    session_id = request.session_id or make_session_id()
    perf = {"layer1": 0.0, "layer2": 0.0, "layer3": 0.0, "total": 0.0}
    stats = {
        "l1_total_posts": 0,
        "l1_total_comments": 0,
        "l2_passed_posts": 0,
        "l2_passed_comments": 0,
        "l3_passed_posts": 0,
    }

    try:
        supabase = get_supabase()
        matcher = get_smart_matcher()
        sf = get_smart_filter()

        print_banner("🤖 端到端自动过滤",
                     Session=session_id, Query=request.query,
                     Platform=request.platform or "全平台", MaxPosts=request.max_posts)

        # ── Step 1: 读取 Layer-1 数据 ────────────────────────────────
        print("📖 Step 1: 读取 Layer-1 已过滤帖子...")
        all_posts, perf["layer1"] = fetch_posts_from_db(supabase, request.platform, request.max_posts)
        stats["l1_total_posts"] = len(all_posts)
        print(f"  ✅ 读取 {stats['l1_total_posts']} 条帖子 ({perf['layer1']:.2f}s)\n")

        if not all_posts:
            raise HTTPException(status_code=404, detail="filtered_posts 表无数据，请先执行 Layer-1 过滤")

        # ── Step 2: Layer-2 场景规则过滤 ────────────────────────────
        print("🎯 Step 2: Layer-2 场景规则过滤...")
        passed_posts, match_result, perf["layer2"] = await run_layer2(
            matcher, request.query, all_posts, request.force_scenario
        )
        stats["l2_passed_posts"] = len(passed_posts)

        if request.save_gap_rules and match_result.suggest_save:
            matcher.save_suggested_rules(match_result.suggest_save)

        print(f"  场景: {match_result.detected_scenario} | 已有规则: {len(match_result.matched_rules)} | "
              f"补充规则: {len(match_result.gap_rules)}")
        print(f"  ✅ Layer-2 完成: {stats['l2_passed_posts']}/{stats['l1_total_posts']} 通过 "
              f"({perf['layer2']:.2f}s)\n")

        # 写入 session_l2_posts（含 hashlib 唯一 ID）
        if request.auto_save and passed_posts:
            all_rule_names = (
                [r.rule_name for r in match_result.matched_rules]
                + [g.name for g in match_result.gap_rules]
            )
            rows = []
            for post in passed_posts:
                oid = str(post.get("id", ""))
                uid = f"{hashlib.md5(f'{session_id}_{oid}'.encode()).hexdigest()[:16]}_{oid[-8:]}"
                rows.append({
                    "id": uid, "session_id": session_id,
                    "platform": post.get("platform", "xhs"),
                    "type": post.get("type"), "url": post.get("url"),
                    "title": post.get("title"), "content": post.get("content"),
                    "publish_time": post.get("publish_time"),
                    "author_id": post.get("author_id"),
                    "author_nickname": post.get("author_nickname"),
                    "metrics_likes": post.get("metrics_likes", 0),
                    "metrics_comments": post.get("metrics_comments", 0),
                    "tags": post.get("tags"),
                    "scene_matched_rules": json.dumps(all_rule_names, ensure_ascii=False),
                })
            print(f"💾 写入 session_l2_posts ({len(rows)} 条)...")
            for i in range(0, len(rows), 50):
                supabase.table("session_l2_posts").insert(rows[i:i + 50]).execute()
            print(f"  ✅ 已写入\n")

        if stats["l2_passed_posts"] == 0:
            if request.auto_save:
                supabase.table("session_metadata").insert({
                    "session_id": session_id, "query_text": request.query,
                    **{k: stats[k] for k in stats}, "status": "completed",
                }).execute()
            perf["total"] = time.time() - start_time
            return AutoFilterResponse(
                session_id=session_id, query=request.query,
                stats=stats, performance=perf,
                access={"api_url": f"/api/sessions/{session_id}/results",
                        "message": "No posts passed Layer-2"},
                metadata={"early_stop": "layer2", "scenario": match_result.detected_scenario}
            )

        # ── Step 3: 读取评论 ─────────────────────────────────────────
        print("💬 Step 3: 读取有效帖子的评论...")
        valid_post_ids = [p["id"] for p in passed_posts]
        comments_by_post_raw, total_comments, _ = fetch_comments(supabase, valid_post_ids)
        all_comments = [c for comments in comments_by_post_raw.values() for c in comments]
        stats["l1_total_comments"] = total_comments
        print(f"  ✅ 读取 {total_comments} 条评论\n")

        # ── Step 4: Layer-2 过滤评论 ─────────────────────────────────
        passed_comments: list = []
        if all_comments:
            print("🎯 Step 4: Layer-2 过滤评论（复用规则）...")
            comment_contents = [c.get("content", "") for c in all_comments]
            comment_pass_flags, _ = apply_rules_to_contents(
                matcher, comment_contents, match_result.matched_rules, match_result.gap_rules
            )
            passed_comments = [c for c, flag in zip(all_comments, comment_pass_flags) if flag]
            stats["l2_passed_comments"] = len(passed_comments)
            print(f"  ✅ 评论通过: {stats['l2_passed_comments']}/{total_comments}\n")

            if request.auto_save and passed_comments:
                rows = []
                for comment in passed_comments:
                    oid = str(comment.get("id", ""))
                    uid = f"{hashlib.md5(f'{session_id}_{oid}'.encode()).hexdigest()[:16]}_{oid[-8:]}"
                    rows.append({
                        "id": uid, "session_id": session_id,
                        "content_id": comment.get("content_id"),
                        "platform": comment.get("platform", "xhs"),
                        "content": comment.get("content"),
                        "publish_time": comment.get("publish_time"),
                        "author_id": comment.get("author_id"),
                        "author_nickname": comment.get("author_nickname"),
                        "metrics_likes": comment.get("metrics_likes", 0),
                        "scene_matched_rules": json.dumps(all_rule_names, ensure_ascii=False),
                    })
                print(f"💾 写入 session_l2_comments ({len(rows)} 条)...")
                for i in range(0, len(rows), 50):
                    supabase.table("session_l2_comments").insert(rows[i:i + 50]).execute()
                print("  ✅ 已写入\n")

        # ── Step 5: Layer-3 语义相关性过滤 ───────────────────────────
        print("🤖 Step 5: Layer-3 LLM 语义过滤...")
        valid_posts, valid_ids, perf["layer3"] = run_layer3(
            sf, request.query, passed_posts, request.min_relevance, request.llm_only
        )
        stats["l3_passed_posts"] = len(valid_posts)
        print(f"  ✅ Layer-3 完成: {stats['l3_passed_posts']}/{stats['l2_passed_posts']} 通过 "
              f"({perf['layer3']:.2f}s)\n")

        # ── Step 6: 写入 session_l3_results ──────────────────────────
        if request.auto_save and valid_posts:
            # 按 post_id 重建评论分组
            comments_by_post: dict = {}
            for comment in passed_comments:
                cid = comment.get("content_id")
                if cid in valid_ids:
                    comments_by_post.setdefault(cid, []).append(comment)

            rows = [{
                "session_id": session_id,
                "post_id": p["id"],
                "post_data": p,
                "comments": comments_by_post.get(p["id"], []),
                "comment_count": len(comments_by_post.get(p["id"], [])),
                "query_text": request.query,
            } for p in valid_posts]

            print(f"💾 写入 session_l3_results ({len(rows)} 条)...")
            for i in range(0, len(rows), 50):
                supabase.table("session_l3_results").upsert(rows[i:i + 50]).execute()
            print("  ✅ 已写入\n")

        # ── Step 7: 写入 session_metadata ────────────────────────────
        if request.auto_save:
            supabase.table("session_metadata").insert({
                "session_id": session_id, "query_text": request.query,
                "l1_total_posts": stats["l1_total_posts"],
                "l1_total_comments": stats["l1_total_comments"],
                "l2_passed_posts": stats["l2_passed_posts"],
                "l2_passed_comments": stats["l2_passed_comments"],
                "l3_passed_posts": stats["l3_passed_posts"],
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).execute()

        perf["total"] = time.time() - start_time
        print_summary(stats, perf, session_id)

        return AutoFilterResponse(
            session_id=session_id,
            query=request.query,
            stats=stats,
            performance=perf,
            access={
                "api_url": f"/api/sessions/{session_id}/results",
                "web_url": f"http://localhost:8081/api/sessions/{session_id}/results",
                "metadata_url": f"/api/sessions/{session_id}/metadata",
            },
            metadata={
                "scenario": match_result.detected_scenario,
                "min_relevance": request.min_relevance,
                "platform": request.platform,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"\n❌ 自动过滤出错: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Auto filter failed: {str(e)}")


# ==================== 三层过滤流水线 (原版，保留兼容) ====================

@app.post("/api/pipeline/run", tags=["三层流水线"])
async def run_pipeline(request: PipelineRequest):
    """
    完整三层过滤流水线

    Layer-1  基础规则过滤（涉黄/涉政/涉暴，通用规则，AC自动机）
      ↓  剩余未被过滤的内容
    Layer-2  场景规则 + LLM缺口分析
             a. LLM识别场景（电商/社交/财经...）
             b. 加载场景专属规则，逐条匹配内容
             c. LLM思维链分析缺口，生成补充规则并即时应用
      ↓  剩余未命中的内容
    Layer-3  LLM语义相关性筛选
             a. 解析 query 意图（核心实体 + 用途）
             b. 对每条内容打相关性分数
             c. 按 min_relevance 阈值保留相关内容

    返回：
      - layer1 / layer2 / layer3 各层详细结果
      - final_results: 最终保留的内容列表
      - stats: 各层过滤统计
    """
    try:
        results_layer1 = []  # (content, filtered, rule, purpose)
        results_layer2 = []
        results_layer3 = []

        import re as _re

        # ── Layer-1：基础规则过滤 ──────────────────────────────────
        layer1_detail = []
        survivors_after_l1 = []

        if request.enable_base_filter:
            for content in request.contents:
                engine_result = pipeline.rule_engine.filter(content)
                filtered = False
                hit_rule = None
                if engine_result.is_matched:
                    general_hits = [r for r in engine_result.matched_rules
                                    if r.rule_name.startswith("通用-") and r.purpose == "filter"]
                    if general_hits:
                        filtered = True
                        hit_rule = general_hits[0].rule_name

                layer1_detail.append({
                    "content": content,
                    "filtered": filtered,
                    "rule": hit_rule,
                    "layer": "base_rule",
                })
                if not filtered:
                    survivors_after_l1.append(content)
        else:
            survivors_after_l1 = list(request.contents)
            layer1_detail = [{"content": c, "filtered": False, "rule": None, "layer": "skipped"}
                             for c in request.contents]

        # ── Layer-2：场景规则 + LLM缺口分析 ──────────────────────
        layer2_detail = []
        match_analysis = None
        survivors_after_l2 = []

        if request.enable_scene_filter and survivors_after_l1:
            matcher = get_smart_matcher()
            match_result = await matcher.match(request.query, force_scenario=request.scenario)
            match_analysis = match_result.to_dict()

            scenario = match_result.detected_scenario
            _, scene_rules = matcher._load_rules_for_scenario(scenario)

            parsed_scene_rules = []
            for rule in scene_rules:
                try:
                    keywords = json.loads(rule.content)
                    if not isinstance(keywords, list):
                        keywords = [rule.content]
                except Exception:
                    keywords = [rule.content] if rule.content else []
                if keywords:
                    parsed_scene_rules.append((rule, keywords))

            for content in survivors_after_l1:
                matched = False
                matched_rule_name = None
                matched_purpose = None
                content_lower = content.lower()

                for rule, keywords in parsed_scene_rules:
                    rule_type = rule.type.value if hasattr(rule.type, "value") else str(rule.type)
                    hit = False
                    if rule_type == "keyword":
                        hit = any(str(kw).lower() in content_lower for kw in keywords if kw)
                    elif rule_type == "regex":
                        for pat in keywords:
                            try:
                                if _re.search(str(pat), content, _re.IGNORECASE):
                                    hit = True
                                    break
                            except _re.error:
                                pass
                    else:
                        hit = any(str(kw).lower() in content_lower for kw in keywords if kw)

                    if hit:
                        matched = True
                        matched_rule_name = rule.name
                        matched_purpose = rule.purpose.value if hasattr(rule.purpose, "value") else str(rule.purpose)
                        break

                layer2_detail.append({
                    "content": content,
                    "matched": matched,
                    "rule": matched_rule_name,
                    "purpose": matched_purpose,
                    "layer": "scene_rule" if matched else None,
                })

            # LLM 缺口规则即时应用
            if request.apply_gap_rules and match_result.gap_rules:
                unmatched = [r["content"] for r in layer2_detail if not r["matched"]]
                gap_results = matcher.apply_gap_rules_to_content(unmatched, match_result.gap_rules)
                gap_map = {r["content"]: r for r in gap_results}
                for item in layer2_detail:
                    if not item["matched"] and item["content"] in gap_map:
                        gr = gap_map[item["content"]]
                        if gr["matched"]:
                            item.update({"matched": True, "rule": gr["rule"],
                                         "purpose": gr["purpose"], "layer": "llm_gap_rule"})

            # filter 目的的命中内容被过滤掉，select/未命中的进入下一层
            for item in layer2_detail:
                if not item["matched"] or item.get("purpose") == "select":
                    survivors_after_l2.append(item["content"])
        else:
            survivors_after_l2 = list(survivors_after_l1)
            layer2_detail = [{"content": c, "matched": False, "rule": None,
                               "purpose": None, "layer": "skipped"}
                             for c in survivors_after_l1]

        # ── Layer-3：LLM 语义相关性筛选 ──────────────────────────
        layer3_detail = []
        final_contents = []

        if request.enable_relevance_filter and survivors_after_l2:
            sf = get_smart_filter()
            relevance_map = {
                "high": RelevanceLevel.HIGH,
                "medium": RelevanceLevel.MEDIUM,
                "low": RelevanceLevel.LOW,
            }
            min_rel = relevance_map.get(request.min_relevance, RelevanceLevel.MEDIUM)
            rel_result = sf.relevance_filter.filter_by_relevance(
                query=request.query,
                texts=survivors_after_l2,
                min_relevance=min_rel,
            )
            # 统一处理返回格式（list 或 dict）
            if isinstance(rel_result, dict):
                rel_items = rel_result.get("results", rel_result.get("items", []))
            else:
                rel_items = rel_result

            for item in rel_items:
                content = item.get("content", "") if isinstance(item, dict) else str(item)
                relevance = item.get("relevance", "medium") if isinstance(item, dict) else "medium"
                score = item.get("score", 0.5) if isinstance(item, dict) else 0.5
                kept = relevance not in ("irrelevant",) and score >= 0.3
                layer3_detail.append({
                    "content": content,
                    "relevance": relevance,
                    "score": score,
                    "kept": kept,
                    "layer": "llm_relevance",
                })
                if kept:
                    final_contents.append(content)
        else:
            final_contents = list(survivors_after_l2)
            layer3_detail = [{"content": c, "relevance": "unknown", "score": 1.0,
                               "kept": True, "layer": "skipped"}
                             for c in survivors_after_l2]

        # ── 统计 ──────────────────────────────────────────────────
        stats = {
            "total_input": len(request.contents),
            "layer1_filtered": sum(1 for r in layer1_detail if r.get("filtered")),
            "layer1_passed": len(survivors_after_l1),
            "layer2_filtered": sum(1 for r in layer2_detail
                                   if r.get("matched") and r.get("purpose") == "filter"),
            "layer2_selected": sum(1 for r in layer2_detail
                                   if r.get("matched") and r.get("purpose") == "select"),
            "layer2_passed": len(survivors_after_l2),
            "layer3_kept": len(final_contents),
            "layer3_dropped": len(survivors_after_l2) - len(final_contents),
            "final_count": len(final_contents),
        }

        return {
            "query": request.query,
            "detected_scenario": match_analysis.get("detected_scenario") if match_analysis else None,
            "stats": stats,
            "layer1_results": layer1_detail,
            "layer2_results": layer2_detail,
            "layer2_match_analysis": match_analysis,
            "layer3_results": layer3_detail,
            "final_results": final_contents,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", tags=["系统"])
async def get_system_stats():
    """获取系统统计"""
    return pipeline.get_stats()


@app.post("/api/cache/clear", tags=["系统"])
async def clear_cache():
    """清空缓存"""
    pipeline.clear_cache()
    return {"message": "缓存已清空"}


@app.post("/api/rules/reload", tags=["系统"])
async def reload_rules():
    """重新加载规则"""
    pipeline.reload_rules()
    return {"message": "规则已重新加载"}


# ==================== 前端页面 ====================

@app.get("/", response_class=HTMLResponse, tags=["前端"])
async def index():
    """管理界面"""
    html_path = Path(__file__).parent / "web" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    
    # 返回简单的内嵌页面
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>过滤引擎管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; margin-bottom: 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin-right: 8px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-secondary { background: #e2e3e5; color: #383d41; }
        textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        #result { margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 过滤引擎管理</h1>
        
        <div class="card">
            <h3>快速测试</h3>
            <textarea id="testText" rows="3" placeholder="输入要测试的文本..."></textarea>
            <div style="margin-top: 10px;">
                <button class="btn btn-primary" onclick="testFilter()">规则过滤</button>
                <button class="btn btn-success" onclick="testFilter(true)">规则+LLM过滤</button>
            </div>
            <pre id="result"></pre>
        </div>
        
        <div class="card">
            <h3>规则列表 <button class="btn btn-primary" onclick="loadRules()">刷新</button></h3>
            <table>
                <thead>
                    <tr><th>ID</th><th>名称</th><th>类型</th><th>分类</th><th>状态</th><th>操作</th></tr>
                </thead>
                <tbody id="rulesTable"></tbody>
            </table>
        </div>
    </div>
    
    <script>
        async function loadRules() {
            const res = await fetch('/api/rules');
            const rules = await res.json();
            const tbody = document.getElementById('rulesTable');
            tbody.innerHTML = rules.map(r => `
                <tr>
                    <td>${r.id}</td>
                    <td>${r.name}</td>
                    <td>${r.type}</td>
                    <td>${r.category || '-'}</td>
                    <td><span class="badge ${r.enabled ? 'badge-success' : 'badge-secondary'}">${r.enabled ? '启用' : '禁用'}</span></td>
                    <td>
                        <button class="btn btn-primary" onclick="toggleRule(${r.id})">切换</button>
                        <button class="btn btn-danger" onclick="deleteRule(${r.id})">删除</button>
                    </td>
                </tr>
            `).join('');
        }
        
        async function testFilter(useLlm = false) {
            const text = document.getElementById('testText').value;
            if (!text) return alert('请输入文本');
            
            const res = await fetch('/api/filter', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text, use_llm: useLlm})
            });
            const result = await res.json();
            document.getElementById('result').textContent = JSON.stringify(result, null, 2);
        }
        
        async function toggleRule(id) {
            await fetch(`/api/rules/${id}/toggle`, {method: 'PUT'});
            loadRules();
        }
        
        async function deleteRule(id) {
            if (!confirm('确定删除?')) return;
            await fetch(`/api/rules/${id}`, {method: 'DELETE'});
            loadRules();
        }
        
        loadRules();
    </script>
</body>
</html>
    """)


# ==================== Session 数据查询接口 ====================

class SessionMetadata(BaseModel):
    """Session 元数据"""
    session_id: str
    query_text: str
    l1_total_posts: int
    l1_total_comments: int
    l2_passed_posts: int
    l2_passed_comments: int
    l3_passed_posts: int
    status: str
    created_at: str
    completed_at: Optional[str] = None


class SessionPostData(BaseModel):
    """Session 帖子数据（简化版）"""
    post_id: str
    title: Optional[str] = None
    content: str
    platform: str
    author_nickname: Optional[str] = None
    publish_time: Optional[str] = None
    relevance_score: Optional[float] = None
    relevance_level: Optional[str] = None
    metrics_likes: Optional[int] = 0
    metrics_comments: Optional[int] = 0
    url: Optional[str] = None
    tags: Optional[List[str]] = None


class SessionResult(BaseModel):
    """完整 Session 结果（包含帖子和评论）"""
    post: SessionPostData
    comments: List[dict]
    comment_count: int


class SessionResponse(BaseModel):
    """Session 查询响应"""
    session_id: str
    query_text: str
    total_results: int
    results: List[SessionResult]
    metadata: SessionMetadata


# Supabase 配置
SUPABASE_URL = "https://rynxtsbrwvexytmztcyh.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ5bnh0c2Jyd3ZleHl0bXp0Y3loIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3Njc4NTA5ODUsImV4cCI6MjA4MzQyNjk4NX0"
    ".0AGziOeTUQjv1cpaCfNCBST3xz97VxkMs_ggzaxthgo"
)

try:
    from supabase import create_client, Client
    _supabase_client: Optional[Client] = None
    
    def get_supabase() -> Client:
        global _supabase_client
        if _supabase_client is None:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _supabase_client
except ImportError:
    def get_supabase():
        raise HTTPException(status_code=500, detail="Supabase client not installed. Run: pip install supabase")


@app.get("/api/sessions/{session_id}/metadata", response_model=SessionMetadata, tags=["Session Data"])
async def get_session_metadata(session_id: str):
    """
    获取 Session 元数据
    
    **用途**: 查看过滤任务的统计信息
    
    **示例**:
    ```
    GET /api/sessions/sess_abc123/metadata
    ```
    """
    try:
        supabase = get_supabase()
        resp = supabase.table("session_metadata").select("*").eq("session_id", session_id).execute()
        
        if not resp.data or len(resp.data) == 0:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        return resp.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/sessions/{session_id}/results", response_model=SessionResponse, tags=["Session Data"])
async def get_session_results(
    session_id: str,
    limit: int = Query(100, ge=1, le=1000, description="返回结果数量限制"),
    offset: int = Query(0, ge=0, description="偏移量（分页）"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="最低相关性分数过滤"),
):
    """
    获取 Session 的 Layer-3 过滤结果（帖子+评论）
    
    **用途**: Agent 获取最终过滤好的数据
    
    **参数**:
    - `session_id`: Session ID（由过滤脚本生成）
    - `limit`: 返回结果数量（默认100，最大1000）
    - `offset`: 分页偏移量（默认0）
    - `min_score`: 最低相关性分数（可选，0.0-1.0）
    
    **示例**:
    ```
    GET /api/sessions/sess_abc123/results?limit=50&min_score=0.7
    ```
    
    **返回格式**:
    ```json
    {
        "session_id": "sess_abc123",
        "query_text": "丽江旅游景点推荐",
        "total_results": 45,
        "results": [
            {
                "post": {
                    "post_id": "xxx",
                    "title": "丽江古城深度游攻略",
                    "content": "...",
                    "relevance_score": 0.92,
                    "relevance_level": "high",
                    ...
                },
                "comments": [{...}, {...}],
                "comment_count": 15
            }
        ],
        "metadata": {...}
    }
    ```
    """
    try:
        supabase = get_supabase()
        
        # 1. 获取元数据
        meta_resp = supabase.table("session_metadata").select("*").eq("session_id", session_id).execute()
        if not meta_resp.data or len(meta_resp.data) == 0:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        metadata = meta_resp.data[0]
        
        # 2. 查询 Layer-3 结果（不使用数据库排序，改为 Python 排序）
        # 注意：由于 Supabase 不支持 JSON 字段的类型转换排序，我们在 Python 端处理
        
        # 先获取所有数据（如果数据量大，可以考虑增加 limit 参数或分批获取）
        query = supabase.table("session_l3_results") \
            .select("*") \
            .eq("session_id", session_id)
        
        resp = query.execute()
        all_results = resp.data or []
        
        # 3. 在 Python 中过滤和排序
        # 过滤低分结果（可选）
        if min_score is not None:
            all_results = [
                r for r in all_results
                if r.get("post_data", {}).get("relevance_score", 0.0) >= min_score
            ]
        
        # 按相关性分数排序（降序）
        all_results.sort(
            key=lambda x: x.get("post_data", {}).get("relevance_score", 0.0),
            reverse=True
        )
        
        # 应用分页
        raw_results = all_results[offset:offset + limit]
        
        # 4. 格式化返回数据
        results = []
        for item in raw_results:
            post_data = item.get("post_data", {})
            
            # 构建 SessionPostData
            post = SessionPostData(
                post_id=item["post_id"],
                title=post_data.get("title"),
                content=post_data.get("content", ""),
                platform=post_data.get("platform", "xhs"),
                author_nickname=post_data.get("author_nickname"),
                publish_time=post_data.get("publish_time"),
                relevance_score=post_data.get("relevance_score"),
                relevance_level=post_data.get("relevance_level"),
                metrics_likes=post_data.get("metrics_likes", 0),
                metrics_comments=post_data.get("metrics_comments", 0),
                url=post_data.get("url"),
                tags=post_data.get("tags"),
            )
            
            results.append(SessionResult(
                post=post,
                comments=item.get("comments", []),
                comment_count=item.get("comment_count", 0),
            ))
        
        return SessionResponse(
            session_id=session_id,
            query_text=metadata.get("query_text", ""),
            total_results=len(results),
            results=results,
            metadata=SessionMetadata(**metadata),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/sessions", tags=["Session Data"])
async def list_sessions(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    status: Optional[str] = Query(None, description="过滤状态: completed/processing/failed"),
):
    """
    列出所有 Session
    
    **用途**: 查看所有过滤任务
    
    **示例**:
    ```
    GET /api/sessions?limit=10&status=completed
    ```
    """
    try:
        supabase = get_supabase()
        
        query = supabase.table("session_metadata").select("*").limit(limit)
        
        if status:
            query = query.eq("status", status)
        
        query = query.order("created_at", desc=True)
        
        resp = query.execute()
        return {
            "total": len(resp.data or []),
            "sessions": resp.data or [],
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.delete("/api/sessions/{session_id}", tags=["Session Data"])
async def delete_session(session_id: str):
    """
    删除 Session 及其所有数据
    
    **警告**: 此操作不可逆！
    
    **示例**:
    ```
    DELETE /api/sessions/sess_abc123
    ```
    """
    try:
        supabase = get_supabase()
        
        # 删除 L2 数据
        supabase.table("session_l2_posts").delete().eq("session_id", session_id).execute()
        supabase.table("session_l2_comments").delete().eq("session_id", session_id).execute()
        
        # 删除 L3 数据
        supabase.table("session_l3_results").delete().eq("session_id", session_id).execute()
        
        # 删除元数据
        supabase.table("session_metadata").delete().eq("session_id", session_id).execute()
        
        return {"message": f"Session '{session_id}' deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


# ==================== 主入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
