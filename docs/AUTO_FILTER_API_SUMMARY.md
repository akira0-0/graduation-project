# 端到端自动过滤 API 完成总结

## ✅ 已完成功能

### 🎯 核心需求

**用户需求**：只输入 `query`，不手动传入 `contents`，自动从数据库读取并执行 Layer-2 和 Layer-3 过滤。

**解决方案**：创建端到端自动过滤 API `/api/filter/auto`

---

## 📦 实现内容

### 1. 新 API 接口

**文件**：`filter_engine/api.py`

**接口路径**：`POST /api/filter/auto`

**核心特性**：
- ✅ **只需输入 query** - 无需手动传入 contents 数组
- ✅ **自动从数据库读取** - 从 `filtered_posts` / `filtered_comments` 读取 Layer-1 数据
- ✅ **自动执行三层过滤**：
  - Layer-1：从数据库读取已过滤数据
  - Layer-2：场景规则 + LLM 缺口分析
  - Layer-3：LLM 语义相关性判断
- ✅ **自动保存结果** - 写入 Session 临时表（session_l2_*, session_l3_results）
- ✅ **返回 API 访问地址** - 通过 Session API 获取结果

---

### 2. 测试脚本

**文件**：`scripts/test_auto_filter_api.py`

**功能**：
- ✅ 标准功能测试
- ✅ 最简请求测试（只输入 query）
- ✅ Query 对比测试（不同场景）
- ✅ 自动获取结果验证

**使用方法**：
```bash
uv run python scripts/test_auto_filter_api.py
```

---

### 3. 使用文档

**文件**：`docs/AUTO_FILTER_API_GUIDE.md`

**内容**：
- 快速开始（最简示例）
- API 参数详解
- 5 种典型使用场景
- 完整工作流程图
- 与手动传入对比
- 性能优化建议
- 常见问题解答
- 最佳实践
- 迁移指南

---

## 🚀 使用示例

### 最简请求（推荐）

```python
import requests

# 只需输入 query，一行代码启动过滤
response = requests.post(
    "http://localhost:8081/api/filter/auto",
    json={"query": "丽江旅游攻略"}
)

result = response.json()
session_id = result["session_id"]

print(f"✅ 过滤完成")
print(f"  L1 总帖子: {result['stats']['l1_total_posts']}")
print(f"  L3 通过: {result['stats']['l3_passed_posts']}")
print(f"  API 访问: {result['access']['web_url']}")

# 获取过滤结果
results = requests.get(
    f"http://localhost:8081/api/sessions/{session_id}/results"
).json()
```

---

### 完整配置示例

```python
response = requests.post(
    "http://localhost:8081/api/filter/auto",
    json={
        # 必填参数
        "query": "丽江旅游攻略",
        
        # 数据源控制
        "platform": "xhs",           # 只处理小红书
        "max_posts": 500,            # 最多 500 条帖子
        "max_comments_per_post": 50, # 每帖最多 50 条评论
        
        # Layer-2 控制
        "force_scenario": None,      # 自动识别场景
        "save_gap_rules": False,     # 不保存补充规则
        
        # Layer-3 控制
        "min_relevance": "medium",   # 中等相关性
        "llm_only": True,            # 完全依赖 LLM
        
        # Session 控制
        "auto_save": True,           # 自动保存到数据库
    }
)
```

---

## 📊 工作流程

```
┌─────────────────────────────────────────────────────────┐
│                    用户输入 query                        │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Step 1: 从 filtered_posts 读取 Layer-1 已过滤数据      │
│  - 支持平台过滤（platform）                              │
│  - 支持数量限制（max_posts）                             │
│  - 分页读取避免超时                                      │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Step 2: Layer-2 场景规则过滤（帖子）                    │
│  - LLM 场景识别                                          │
│  - 匹配已有规则                                          │
│  - LLM 生成补充规则                                      │
│  - 应用规则过滤                                          │
│  → 写入 session_l2_posts                                │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Step 3: 读取有效帖子的评论                              │
│  - 从 filtered_comments 按 content_id 查询              │
│  - 只读取 Layer-2 通过帖子的评论                         │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Step 4: Layer-2 过滤评论（复用规则）                    │
│  - 使用相同的场景规则                                    │
│  - 无需再次调用 LLM                                      │
│  → 写入 session_l2_comments                             │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Step 5: Layer-3 LLM 语义相关性过滤                      │
│  - 批量判断帖子相关性                                    │
│  - 打分 + 分级（high/medium/low）                        │
│  - 按 min_relevance 过滤                                │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Step 6: 构建帖子+评论嵌套结构                          │
│  - 按 content_id 分组评论                               │
│  - 组合为 {post: {...}, comments: [...]}                │
│  → 写入 session_l3_results                              │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Step 7: 更新 session_metadata                          │
│  - 记录统计信息（L1/L2/L3 通过数）                       │
│  - 记录 query_text、场景、状态                          │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  返回响应                                                │
│  - session_id                                           │
│  - stats（各层统计）                                     │
│  - performance（各层耗时）                               │
│  - access（API 访问地址）                                │
│  - metadata（场景、相关性等）                            │
└─────────────────────────────────────────────────────────┘
```

---

## 🆚 与其他接口对比

| 特性 | `/api/filter/auto` | `/api/filter/three-layer` | 脚本方式 |
|------|-------------------|--------------------------|---------|
| **输入复杂度** | ⭐ 只需 query | ⭐⭐ 需要 query + contents | ⭐⭐⭐ 多个命令 |
| **数据源** | 自动从数据库读取 | 手动传入数组 | 手动指定文件 |
| **数据量限制** | 2000 条 | 1000 条 | 无限制 |
| **Session 保存** | ✅ 自动 | ❌ 不保存 | ✅ 手动 |
| **评论关联** | ✅ 自动 | ❌ 需手动 | ✅ 自动 |
| **跨网络访问** | ✅ | ✅ | ❌ |
| **适用场景** | **生产环境** | 测试/小批量 | 离线处理 |

**推荐使用场景**：
- 🏆 **生产环境** → `/api/filter/auto`
- 🧪 **快速测试** → `/api/filter/three-layer`
- 📦 **离线批处理** → 脚本方式

---

## ⚡ 性能特点

### 1. 自动批量读取

```python
# 分页读取避免超时
while len(all_posts) < max_posts:
    resp = query_builder.range(offset, offset + 1000 - 1).execute()
    # ...
```

### 2. 规则复用

```python
# Layer-2 评论过滤复用帖子的规则，无需再次调用 LLM
comment_pass_flags, _ = apply_rules_to_contents(
    matcher, comment_contents,
    match_result.matched_rules,  # 复用
    match_result.gap_rules        # 复用
)
```

### 3. 早停优化

```python
# Layer-2 无通过内容时直接返回
if stats["l2_passed_posts"] == 0:
    return AutoFilterResponse(
        metadata={"early_stop": "layer2"}
    )
```

---

## 📝 请求参数速查

### 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | string | 用户查询（唯一必填） |

### 常用可选参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `platform` | `null` | 平台过滤（xhs/weibo） |
| `max_posts` | `500` | 最多处理帖子数 |
| `min_relevance` | `"medium"` | 最低相关性（high/medium/low） |
| `llm_only` | `true` | Layer-3 是否完全依赖 LLM |

### 高级参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_comments_per_post` | `50` | 每个帖子最多处理评论数 |
| `force_scenario` | `null` | 强制指定场景 |
| `save_gap_rules` | `false` | 保存 LLM 生成的规则 |
| `session_id` | 自动生成 | 自定义 Session ID |
| `auto_save` | `true` | 自动保存到数据库 |

---

## 🎯 典型用例

### 用例 1: Agent 集成

```python
class ContentAnalysisAgent:
    """内容分析 Agent"""
    
    def analyze_topic(self, topic: str):
        # Step 1: 启动过滤
        response = requests.post(
            "http://api.example.com/api/filter/auto",
            json={"query": topic, "platform": "xhs"}
        )
        
        session_id = response.json()["session_id"]
        
        # Step 2: 获取结果
        results = requests.get(
            f"http://api.example.com/api/sessions/{session_id}/results"
        ).json()
        
        # Step 3: 分析数据
        high_quality = [
            r for r in results["results"]
            if r["post"]["relevance_score"] >= 0.8
        ]
        
        return {
            "topic": topic,
            "total_found": results["total_results"],
            "high_quality_count": len(high_quality),
            "data": high_quality
        }

# 使用
agent = ContentAnalysisAgent()
result = agent.analyze_topic("丽江旅游攻略")
```

---

### 用例 2: 定时任务

```python
import schedule
import requests

def daily_filter_task():
    """每日自动过滤任务"""
    topics = ["热门旅游地", "美食推荐", "科技新闻"]
    
    for topic in topics:
        response = requests.post(
            "http://localhost:8081/api/filter/auto",
            json={
                "query": topic,
                "max_posts": 1000,
                "min_relevance": "high"
            }
        )
        
        session_id = response.json()["session_id"]
        print(f"✅ {topic} 过滤完成: {session_id}")

# 每天凌晨 2 点执行
schedule.every().day.at("02:00").do(daily_filter_task)
```

---

### 用例 3: 多平台对比

```python
def compare_platforms(query: str):
    """对比不同平台的内容"""
    platforms = ["xhs", "weibo"]
    results = {}
    
    for platform in platforms:
        response = requests.post(
            "http://localhost:8081/api/filter/auto",
            json={
                "query": query,
                "platform": platform,
                "max_posts": 300
            }
        )
        
        data = response.json()
        results[platform] = {
            "total": data["stats"]["l1_total_posts"],
            "passed": data["stats"]["l3_passed_posts"],
            "session_id": data["session_id"]
        }
    
    return results

# 使用
comparison = compare_platforms("丽江旅游")
print(f"小红书: {comparison['xhs']['passed']}/{comparison['xhs']['total']}")
print(f"微博: {comparison['weibo']['passed']}/{comparison['weibo']['total']}")
```

---

## 📁 文件清单

### 核心代码
- ✅ `filter_engine/api.py` - 新增 `/api/filter/auto` 接口

### 测试脚本
- ✅ `scripts/test_auto_filter_api.py` - 完整测试脚本

### 文档
- ✅ `docs/AUTO_FILTER_API_GUIDE.md` - 使用指南（350+ 行）
- ✅ `docs/AUTO_FILTER_API_SUMMARY.md` - 本总结文档

---

## 🔄 迁移路径

### 从脚本迁移

**旧方式**：
```bash
# 步骤繁琐，需要手动管理 Session ID
uv run python scripts/batch_scene_filter_smart.py --query "丽江旅游"
# 记录 Session ID
uv run python scripts/batch_llm_filter.py --session-id sess_xxx --query "丽江旅游"
```

**新方式**：
```python
# 一个请求搞定
requests.post("/api/filter/auto", json={"query": "丽江旅游"})
```

**优势**：
- ✅ 无需手动管理 Session ID
- ✅ 无需多步骤调用
- ✅ 跨网络访问
- ✅ 自动保存结果

---

## 🐛 故障排查

### 问题 1: 404 错误

**错误信息**：
```json
{
  "detail": "No posts found in filtered_posts table. Please run Layer-1 filter first."
}
```

**解决方案**：
```bash
# 先运行 Layer-1 过滤
uv run python scripts/batch_filter.py --data-type posts
```

---

### 问题 2: 结果为 0

**可能原因**：
- Query 与数据库内容不匹配
- 相关性阈值太高

**解决方案**：
```python
# 降低相关性要求
{"query": "...", "min_relevance": "low"}

# 检查元数据
metadata = requests.get(f"/api/sessions/{session_id}/metadata").json()
print(f"L1 总数: {metadata['l1_total_posts']}")
print(f"L2 通过: {metadata['l2_passed_posts']}")
```

---

### 问题 3: 超时

**解决方案**：
```python
# 减少数据量
{"query": "...", "max_posts": 200}

# 使用混合模式（减少 LLM 调用）
{"query": "...", "llm_only": False}
```

---

## 🎓 最佳实践总结

1. **生产环境**：使用默认配置，只调整 `query` 和 `platform`
2. **测试环境**：减小 `max_posts`，使用 `llm_only: false`
3. **高质量内容**：`min_relevance: "high"` + `llm_only: true`
4. **快速原型**：只输入 `query`，其他全用默认值
5. **监控优化**：关注 `performance` 字段，识别瓶颈

---

## 📞 技术支持

- **API 文档**: http://localhost:8081/docs
- **完整指南**: `docs/AUTO_FILTER_API_GUIDE.md`
- **测试脚本**: `scripts/test_auto_filter_api.py`
- **Session API**: `docs/SESSION_API_GUIDE.md`

---

**封装完成时间**：2026年4月10日  
**API 版本**：v2.1.0  
**维护状态**：✅ 已完成并测试  
**推荐等级**：⭐⭐⭐⭐⭐
