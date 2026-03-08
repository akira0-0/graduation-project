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


class SmartFilterRequest(BaseModel):
    """智能筛选请求"""
    query: str = Field(..., description="用户查询，如'丽江有什么好玩的'")
    texts: List[str] = Field(..., description="待筛选文本列表")
    filter_spam: bool = Field(True, description="是否过滤垃圾广告")
    filter_relevance: bool = Field(True, description="是否筛选相关性")
    min_relevance: str = Field("medium", description="最低相关性: high/medium/low")


class BatchFilterRequest(BaseModel):
    """批量过滤请求"""
    items: List[dict] = Field(..., description="数据列表")
    content_field: str = Field("content", description="内容字段名")
    use_llm: bool = Field(False, description="是否使用LLM")


class SmartMatchRequest(BaseModel):
    """智能规则匹配请求"""
    query: str = Field(..., description="用户自然语言查询，如'帮我找便宜的丽江民宿，别看广告'")


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
async def smart_filter(request: SmartFilterRequest):
    """
    智能数据筛选
    
    功能：
    1. 解析用户查询意图（如"丽江有什么好玩的" → 核心实体:丽江, 意图:旅游）
    2. 过滤垃圾/广告内容
    3. 筛选与查询相关的内容
    4. 按相关性排序返回
    
    适用场景：
    - 从海量数据中筛选特定主题的内容
    - 用户搜索查询
    - 数据清洗和分类
    """
    try:
        sf = get_smart_filter()
        
        # 转换相关性级别
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
async def filter_by_relevance(request: SmartFilterRequest):
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
    智能规则匹配 - LLM驱动的规则理解与生成
    
    功能：
    1. 解析用户自然语言查询，提取所有约束条件
    2. 匹配现有规则库中的适用规则
    3. 分析规则缺口，识别缺失的规则
    4. 自动生成缺失规则
    5. 组合最终过滤规则
    6. 建议保存有价值的新规则
    
    示例输入：
    - "帮我找便宜的丽江民宿，别看广告"
    - "过滤掉所有推广内容，只保留高赞评论"
    - "筛选最近一周的美食推荐"
    
    返回：
    - thought_trace: 思维链追踪（CoT）
    - matched_rules: 匹配到的现有规则
    - generated_rules: 生成的新规则
    - final_rule: 组合后的最终规则
    - suggest_save: 建议保存的规则
    """
    try:
        matcher = get_smart_matcher()
        result = await matcher.match(request.query)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/smart-match/sync", tags=["智能匹配"])
async def smart_match_sync(request: SmartMatchRequest):
    """
    智能规则匹配（同步版本）
    
    与 /api/smart-match 相同功能，但使用同步LLM调用
    """
    try:
        matcher = get_smart_matcher()
        result = matcher.match_sync(request.query)
        return result.to_dict()
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


class BatchTestItem(BaseModel):
    """批量测试结果项"""
    content: str
    matched: bool
    rule: Optional[str] = None
    purpose: Optional[str] = None


@app.post("/api/batch-test", response_model=List[BatchTestItem], tags=["智能匹配"])
async def batch_test(request: BatchTestRequest):
    """
    批量测试内容匹配
    
    对多条内容进行规则匹配测试，返回每条内容的匹配结果
    """
    results = []
    all_rules = rule_manager.list(enabled_only=True)
    
    for content in request.contents:
        matched = False
        matched_rule = None
        matched_purpose = None
        
        # 遍历所有规则进行匹配
        for rule in all_rules:
            import re
            pattern = rule.pattern if hasattr(rule, 'pattern') else rule.get('pattern', '')
            if not pattern:
                continue
            
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    matched = True
                    matched_rule = rule.name if hasattr(rule, 'name') else rule.get('name', '未知规则')
                    matched_purpose = rule.purpose if hasattr(rule, 'purpose') else rule.get('purpose', 'filter')
                    break
            except re.error:
                # 如果正则无效，尝试简单的字符串包含
                if pattern.lower() in content.lower():
                    matched = True
                    matched_rule = rule.name if hasattr(rule, 'name') else rule.get('name', '未知规则')
                    matched_purpose = rule.purpose if hasattr(rule, 'purpose') else rule.get('purpose', 'filter')
                    break
        
        results.append(BatchTestItem(
            content=content,
            matched=matched,
            rule=matched_rule,
            purpose=matched_purpose
        ))
    
    return results


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
