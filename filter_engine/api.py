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
from .config import settings


# ==================== 请求/响应模型 ====================

class FilterRequest(BaseModel):
    """过滤请求"""
    text: str = Field(..., description="待过滤文本")
    use_llm: bool = Field(False, description="是否使用LLM")


class BatchFilterRequest(BaseModel):
    """批量过滤请求"""
    items: List[dict] = Field(..., description="数据列表")
    content_field: str = Field("content", description="内容字段名")
    use_llm: bool = Field(False, description="是否使用LLM")


class ImportRulesRequest(BaseModel):
    """导入规则请求"""
    rules: List[dict] = Field(..., description="规则列表")


# ==================== FastAPI应用 ====================

app = FastAPI(
    title="过滤引擎 API",
    description="规则过滤 + LLM语义过滤",
    version="2.0.0",
)

# 全局实例
rule_manager = RuleManager(settings.DATABASE_PATH)
pipeline = FilterPipeline(use_llm=False)


# ==================== 规则管理API ====================

@app.get("/api/rules", response_model=List[Rule], tags=["规则管理"])
async def list_rules(
    enabled_only: bool = Query(False, description="只返回启用的规则"),
    category: str = Query(None, description="按分类筛选"),
):
    """获取规则列表"""
    return rule_manager.list(enabled_only=enabled_only, category=category)


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
    count = rule_manager.import_rules(data.rules)
    pipeline.reload_rules()
    return {"message": f"成功导入 {count} 条规则", "count": count}


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
