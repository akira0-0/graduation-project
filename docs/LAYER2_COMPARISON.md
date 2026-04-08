# Layer-2 两种实现对比

## 概述

项目中有两种 Layer-2 实现方案，适用于不同场景：

| 方案 | 脚本 | 核心引擎 | 场景识别 | 规则补充 | 适用场景 |
|------|------|---------|---------|---------|---------|
| **方案 A** | `batch_scene_filter.py` | `DynamicFilterPipeline` | 关键词匹配 | ❌ 否 | 快速过滤，已知场景 |
| **方案 B** | `batch_scene_filter_smart.py` | `SmartRuleMatcher` | **LLM 思维链** | ✅ 是 | 复杂语义，未知场景 |

---

## 方案 A：`DynamicFilterPipeline`（快速规则模式）

### 工作流程
```
用户 query → QueryAnalyzer
              ├─ 关键词扫描 → 场景识别
              ├─ 严格度检测
              └─ RuleSelector → 选择场景规则
                                  ↓
                              RuleEngine 执行过滤
```

### 核心代码
```python
# 场景识别：纯关键词匹配
SCENARIO_KEYWORDS = {
    "ecommerce": ["商品", "购物", "电商", ...],
    "social": ["评论", "帖子", "动态", ...],
}

def _detect_scenario(query):
    for scenario, keywords in SCENARIO_KEYWORDS.items():
        for kw in keywords:
            if kw in query:
                scores[scenario] += 1
    return max(scores, key=scores.get)

# 规则选择：加载场景前缀规则
RuleSelector.select(intent) → 返回 "电商-" / "社交-" 前缀规则

# 过滤执行：AC自动机
RuleEngine.filter(texts) → 布尔命中结果
```

### 特点
- ✅ **快速**：无 LLM 调用，纯规则引擎（AC自动机 O(n+m)）
- ✅ **确定性**：同样输入必定同样输出
- ✅ **成本低**：无 API 调用费用
- ❌ **无规则补充**：只能用现有规则
- ❌ **场景识别简单**：关键词匹配，语义复杂时不准
- ❌ **无置信度**：布尔命中，无法量化

### 适用场景
- 已知场景（如"电商广告"、"社交营销"）
- 规则库已完善
- 需要快速批量处理
- 成本敏感

---

## 方案 B：`SmartRuleMatcher`（LLM 思维链模式）

### 工作流程
```
用户 query → SmartRuleMatcher
              ├─ LLM 场景识别（语义理解）
              ├─ 加载场景专属规则库
              └─ LLM 思维链分析（4步推理）
                  ├─ Step 1: 意图提取（filter/select 约束）
                  ├─ Step 2: 规则匹配（语义相关性判断）
                  ├─ Step 3: 缺口分析（未覆盖的需求）
                  └─ Step 4: 补充规则生成（关键词/正则）
                      ↓
                  matched_rules + gap_rules → 动态组合
                      ↓
                  apply_gap_rules_to_content() → 执行过滤
```

### 核心代码
```python
# 场景识别：LLM 语义理解
async def detect_scenario_llm(query: str) -> str:
    prompt = SCENARIO_DETECT_PROMPT.replace("{{query}}", query)
    response = await llm_client.chat([{"role": "user", "content": prompt}])
    return response.content.strip()  # ecommerce / social / ...

# LLM 思维链分析
async def match(query: str) -> SmartMatchResult:
    scenario = await detect_scenario_llm(query)
    base_rules, scene_rules = _load_rules_for_scenario(scenario)
    
    # 构建提示词（含规则库 + 思维链模板）
    prompt = build_smart_match_prompt(query, scenario, scene_rules)
    messages = [
        {"role": "system", "content": SMART_MATCH_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    
    # LLM 返回结构化结果
    response = await llm_client.chat(messages)
    return parse_llm_response(response)  # SmartMatchResult
    
# 返回结果
SmartMatchResult:
    - matched_rules: List[MatchedRuleInfo]    # 规则库已有
    - gap_rules: List[GapRule]                 # LLM 即时生成
    - needs_llm_filter: bool                   # 是否需要 Layer-3
    - thought_trace: ThoughtTrace              # 思维链记录
```

### LLM 思维链示例
```json
{
  "thought_trace": {
    "step_1_extraction": [
      "约束1：去掉广告内容 (purpose: filter)",
      "约束2：保留高质量评论 (purpose: select)"
    ],
    "step_2_match": [
      "规则 社交-引流-营销推广 [ID:50] content_keywords含['推广','引流']，覆盖约束1"
    ],
    "step_3_gap_analysis": [
      "缺口a：'高质量评论' 无对应 select 规则 → 需生成",
      "缺口b：语义模糊的隐式广告 → needs_llm_semantic=true"
    ],
    "step_4_generation": [
      "生成规则：社交-质量-高质量评论词 (select, keyword)"
    ]
  },
  "matched_rules": [
    {"rule_id": 50, "rule_name": "社交-引流-营销推广"}
  ],
  "gap_rules": [
    {
      "name": "社交-质量-高质量评论词",
      "type": "keyword",
      "content": ["写得很好", "非常有用", "干货满满"],
      "purpose": "select"
    }
  ],
  "needs_llm_filter": true,
  "llm_filter_reason": "存在语义模糊的隐式广告"
}
```

### 特点
- ✅ **智能**：LLM 语义理解，复杂场景识别准确
- ✅ **动态规则补充**：自动生成缺口规则，无需手动维护
- ✅ **思维链可解释**：每步推理清晰可见
- ✅ **Layer-3 标记**：自动判断是否需要语义过滤
- ❌ **慢**：每次需调用 LLM（~2-5秒）
- ❌ **成本高**：API 调用费用
- ❌ **非确定性**：同样输入可能不同输出（temperature > 0）

### 适用场景
- 未知场景（如"健康养生但不要医疗广告"）
- 规则库不完善
- 需要语义理解
- 对准确度要求高
- 可接受延迟和成本

---

## 核心差异对比

### 1. 场景识别

| 方案 | 方法 | 代码 | 准确度 |
|------|------|------|--------|
| **A** | 关键词匹配 | `if "电商" in query: return "ecommerce"` | 简单场景准确 |
| **B** | LLM 语义理解 | `llm.chat("从7个场景中选择...")` | 复杂场景准确 |

**示例**：
- Query: "健康养生但不要医疗广告"
  - 方案 A: `medical`（❌ 错误，匹配到"健康"关键词）
  - 方案 B: `social`（✅ 正确，理解是"去除广告"场景）

---

### 2. 规则选择

| 方案 | 方法 | 代码 |
|------|------|------|
| **A** | 固定前缀 | `RuleSelector.select("电商") → 加载 "电商-" 前缀规则` |
| **B** | 语义匹配 | `LLM 逐条分析 content_keywords 与 query 的语义相关性` |

**示例**：
- Query: "去掉软广和植入"
  - 方案 A: 只匹配 `"广告"` 关键词的规则
  - 方案 B: LLM 识别"软广"="隐式营销"，匹配相关规则

---

### 3. 规则补充

| 方案 | 是否生成 | 生成方式 |
|------|---------|---------|
| **A** | ❌ 否 | 无 |
| **B** | ✅ 是 | LLM 分析缺口 → 生成关键词/正则 |

**示例**：
- Query: "去掉'打卡领红包'这种营销内容"
  - 方案 A: 规则库若无"打卡"关键词，则无法过滤
  - 方案 B: LLM 生成补充规则：
    ```json
    {
      "name": "社交-营销-打卡活动",
      "content": ["打卡", "领红包", "签到", "集卡"],
      "purpose": "filter"
    }
    ```

---

### 4. 性能与成本

| 指标 | 方案 A | 方案 B |
|------|--------|--------|
| **速度** | ~100ms（纯规则） | ~2-5s（含 LLM 调用） |
| **吞吐** | ~10000条/秒 | ~200条/秒（受 LLM 限制） |
| **成本** | $0 | ~$0.001/次（GPT-3.5） |
| **确定性** | 100%（同输入同输出） | ~80%（temperature=0.1 时） |

---

## 推荐使用策略

### 混合模式（最佳实践）

```
用户 query → 关键词快速检测
              ├─ 明确场景（如"电商广告"） → 方案 A（DynamicFilterPipeline）
              └─ 复杂语义（如"健康但不要广告"） → 方案 B（SmartRuleMatcher）
```

### 实现建议

1. **首次过滤**：用方案 B，保存生成的 gap_rules
2. **后续过滤**：将 gap_rules 保存到数据库 → 用方案 A（已有规则）
3. **定期优化**：用方案 B 重新分析，更新规则库

---

## 代码示例

### 方案 A 使用
```python
# scripts/batch_scene_filter.py
from filter_engine.core.dynamic_pipeline import DynamicFilterPipeline

pipeline = DynamicFilterPipeline(use_llm=False)  # 纯规则
results = pipeline.filter_with_query(
    query="过滤电商平台的广告评论",
    texts=["商品不错", "加微信xxx", "质量很好"],
)
# results[1].is_spam = True（规则命中"微信"）
```

### 方案 B 使用
```python
# scripts/batch_scene_filter_smart.py
from filter_engine.llm.smart_matcher import SmartRuleMatcher

matcher = SmartRuleMatcher()
result = await matcher.match("过滤健康养生的软广植入")

print(result.detected_scenario)  # "social"
print(result.matched_rules)      # [已有规则列表]
print(result.gap_rules)          # [LLM 生成的补充规则]

# 应用规则
filter_results = matcher.apply_gap_rules_to_content(
    contents=["今天打卡第7天，领到了红包"],
    gap_rules=result.gap_rules,
)
# filter_results[0]["matched"] = True（gap_rules 命中"打卡"）

# 可选：保存补充规则
matcher.save_suggested_rules(result.suggest_save)
```

---

## 总结

- **方案 A**：适合规则库完善、场景明确、追求性能的场景
- **方案 B**：适合规则库不足、语义复杂、追求准确度的场景
- **最佳实践**：用方案 B 生成规则 → 保存到库 → 后续用方案 A 执行

两种方案互补，根据实际需求选择！🎯
