# -*- coding: utf-8 -*-
"""过滤引擎 API - FastAPI"""
import json
from typing import List, Optional
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


# ==================== 三层过滤流水线 ====================

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


# ==================== 主入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
