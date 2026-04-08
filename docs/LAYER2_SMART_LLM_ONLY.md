# Layer-2 Smart 版场景识别优化：移除关键词匹配，纯 LLM 分析

## 📅 修改日期
2026-04-08

---

## 🎯 问题描述

### 原始问题
用户 query: **"丽江便宜的性价比高的民宿有哪些"**

**预期场景**: `travel` (旅游)  
**实际场景**: `ecommerce` (电商)  ❌

### 根本原因
SmartRuleMatcher 的场景识别采用了 **两阶段策略**：

```python
async def detect_scenario_llm(self, query: str) -> str:
    # 第一阶段：关键词快速匹配
    fast_result = self.detect_scenario(query)  # 关键词匹配
    if fast_result != "normal":
        return fast_result  # 直接返回，不调用 LLM ❌
    
    # 第二阶段：LLM 语义识别（仅当关键词无法匹配时）
    prompt = SCENARIO_DETECT_PROMPT.replace("{{query}}", query)
    response = await self.llm_client.chat(messages=messages, ...)
    return response.content.strip().lower()
```

**问题关键词对照**:
```python
SCENARIO_DETECT_KEYWORDS = {
    "ecommerce": ["电商", "购物", "商品", "价格", "优惠", ...],
    "travel": ["旅游", "景点", "攻略", "民宿", "酒店", ...],
}
```

用户 query: "丽江**便宜**的**性价比**高的**民宿**有哪些"
- ✅ 包含 `"民宿"` → 触发 `travel` 场景（+1分）
- ✅ 包含 `"便宜"`、`"性价比"` → 误触发 `ecommerce` 场景（+2分，因为原代码还包含 "价格"、"优惠" 等泛化词）

**结果**: `ecommerce` 分数 > `travel` 分数 → **误判为电商** → 直接返回，**未调用 LLM**

---

## ✅ 解决方案

### 修改策略
**完全移除关键词匹配**，改为 **纯 LLM 语义识别**

### 代码变更

#### 1. 移除关键词字典 (`smart_matcher.py`)
```python
# ❌ 删除
SCENARIO_DETECT_KEYWORDS: Dict[str, List[str]] = {
    "ecommerce": ["电商", "购物", ...],
    "travel": ["旅游", "景点", ...],
    ...
}
```

#### 2. 移除关键词匹配方法 (`smart_matcher.py`)
```python
# ❌ 删除整个方法
def detect_scenario(self, query: str) -> str:
    """规则快速检测场景（无需 LLM）"""
    query_lower = query.lower()
    scores: Dict[str, int] = {s: 0 for s in SCENARIO_DETECT_KEYWORDS}
    for scenario, keywords in SCENARIO_DETECT_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                scores[scenario] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "normal"
```

#### 3. 简化场景识别逻辑 (`smart_matcher.py`)
```python
# ✅ 修改后（纯 LLM）
async def detect_scenario_llm(self, query: str) -> str:
    """
    使用 LLM 进行场景识别（语义理解，准确率高）
    返回标准英文场景名：normal/ecommerce/travel/news/social/finance/medical/education
    """
    from .prompts_smart import SCENARIO_DETECT_PROMPT
    prompt = SCENARIO_DETECT_PROMPT.replace("{{query}}", query)
    messages = [{"role": "user", "content": prompt}]
    try:
        response = await self.llm_client.chat(messages=messages, temperature=0.0, max_tokens=10)
        scenario = response.content.strip().lower()
        valid = {"normal", "ecommerce", "travel", "news", "social", "finance", "medical", "education"}
        return scenario if scenario in valid else "normal"
    except Exception as e:
        print(f"⚠️  LLM场景识别失败，使用默认场景 normal: {e}")
        return "normal"
```

#### 4. 添加 `travel` 场景支持

**`SCENARIO_PREFIX_MAP` 更新**:
```python
SCENARIO_PREFIX_MAP: Dict[str, str] = {
    "ecommerce": "电商-",
    "travel":    "旅游-",  # ✅ 新增
    "news":      "新闻-",
    "social":    "社交-",
    "finance":   "财经-",
    "medical":   "医疗-",
    "education": "教育-",
    "normal":    "",
}
```

**`SCENARIO_DETECT_PROMPT` 更新** (`prompts_smart.py`):
```python
SCENARIO_DETECT_PROMPT = (
  "你是一个文本分类器。请从下列标签中选择一个最贴切的返回，严禁输出任何解释文字：\n"
  "- ecommerce: 电商、商品、购物、物流、客服投诉\n"
  "- travel: 旅游、景点、攻略、民宿、酒店、住宿\n"  # ✅ 新增
  "- news: 时政、社会新闻、媒体报道\n"
  "- social: 社交平台动态、用户评论、粉丝互动\n"
  "- finance: 股票、理财、银行、经济分析\n"
  "- medical: 疾病、药物、医生咨询、健康建议\n"
  "- education: 学习、考试、课程、学术资料\n"
  "- normal: 无法归类的日常对话或通用内容\n\n"
  "内容：{{query}}"
)
```

**`SCENARIO_NAMES` 更新** (`prompts_smart.py`):
```python
SCENARIO_NAMES = {
    "normal":     "通用",
    "ecommerce":  "电商",
    "travel":     "旅游",  # ✅ 新增
    "news":       "新闻",
    "social":     "社交",
    "finance":    "财经",
    "medical":    "医疗",
    "education":  "教育",
}
```

---

## 📊 效果对比

### 修改前（关键词 + LLM 混合）
```
Query: "丽江便宜的性价比高的民宿有哪些"

[1] 关键词匹配:
    - "民宿" → travel (+1)
    - "便宜"、"性价比" → ecommerce (+2)
    结果: ecommerce 获胜

[2] 返回 ecommerce，跳过 LLM 调用 ❌

[3] 加载电商规则库:
    ✅ 匹配已有规则: 4 条
       - [ID:38] 电商-引流-私信加V (filter)
       - [ID:41] 电商-违规-广告法禁词 (filter)
       - [ID:43] 电商-种草-真实评测词 (select)
       - [ID:44] 电商-种草-购买体验词 (select)
    ❌ LLM 生成补充规则: 0 条（误判场景，规则不相关）
```

### 修改后（纯 LLM）
```
Query: "丽江便宜的性价比高的民宿有哪些"

[1] 调用 LLM 场景识别:
    Prompt: "...请从下列标签中选择一个最贴切的返回..."
    Response: "travel" ✅

[2] 加载旅游规则库:
    ✅ 匹配已有规则: X 条（旅游场景相关）
    ✅ LLM 生成补充规则: Y 条
       - 旅游-住宿-性价比筛选 (select)
       - 旅游-民宿-价格区间 (select)
       ...
```

---

## 🎯 优势分析

### ✅ 准确性提升
- **语义理解**: LLM 理解 "民宿" 的语义优先级高于 "便宜"
- **上下文感知**: 识别 "丽江" + "民宿" 组合 → 明确旅游场景
- **避免误判**: 不会因为泛化词（价格、优惠）误判

### ✅ 场景扩展性
- 新增场景只需修改 prompt，无需维护关键词列表
- 支持更复杂的场景（如 "丽江亲子游民宿推荐"）

### ⚠️ 成本增加
- **每次 query 都调用 LLM**（场景识别 + 规则匹配 = 2次调用）
- **建议**: 
  - 使用便宜模型（如 qwen-turbo）进行场景识别
  - 场景识别 max_tokens=10（仅返回场景名）

---

## 🛠️ 使用建议

### 1. 性能优化
如担心 LLM 调用成本，可以：
- 使用 `--force-scenario travel` 跳过场景识别
- 缓存 query → scenario 映射（相同 query 重复使用）

```bash
# 已知是旅游场景，跳过识别
uv run python scripts/batch_scene_filter_smart.py \
    --query "丽江便宜的民宿" \
    --force-scenario travel  # 强制指定场景
```

### 2. 创建旅游规则
在 `filter_engine` 中添加旅游场景规则：

```python
from filter_engine.rules import RuleManager

manager = RuleManager("filter_engine/data/rules.db")

# 旅游-住宿-性价比
manager.create({
    "name": "旅游-住宿-性价比筛选",
    "type": "keyword",
    "content": '["性价比", "便宜", "实惠", "经济型", "青旅", "客栈"]',
    "category": "select",
    "purpose": "select",  # 保留这些内容
    "priority": 70,
})

# 旅游-广告-引流
manager.create({
    "name": "旅游-广告-引流词",
    "type": "keyword",
    "content": '["加微信", "私聊", "扫码", "优惠券", "代订", "代购"]',
    "category": "ad",
    "purpose": "filter",  # 过滤广告
    "priority": 80,
})
```

---

## 📝 完整修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `filter_engine/llm/smart_matcher.py` | ✅ 移除 `SCENARIO_DETECT_KEYWORDS` |
|  | ✅ 移除 `detect_scenario()` 方法 |
|  | ✅ 简化 `detect_scenario_llm()` 为纯 LLM |
|  | ✅ 添加 `"travel": "旅游-"` 到 `SCENARIO_PREFIX_MAP` |
| `filter_engine/llm/prompts_smart.py` | ✅ 添加 `travel` 场景到 `SCENARIO_DETECT_PROMPT` |
|  | ✅ 添加 `"travel": "旅游"` 到 `SCENARIO_NAMES` |

---

## 🧪 测试用例

```bash
# 测试 1: 旅游场景
uv run python scripts/batch_scene_filter_smart.py \
    --query "丽江便宜的性价比高的民宿有哪些" \
    --dry-run

# 预期输出:
# ✅ 场景识别: travel (旅游)

# 测试 2: 电商场景（对照）
uv run python scripts/batch_scene_filter_smart.py \
    --query "淘宝上哪家店铺的手机壳性价比高" \
    --dry-run

# 预期输出:
# ✅ 场景识别: ecommerce (电商)

# 测试 3: 模糊场景（LLM 语义理解）
uv run python scripts/batch_scene_filter_smart.py \
    --query "推荐几家靠谱的川菜馆" \
    --dry-run

# 预期输出:
# ✅ 场景识别: normal 或 social (取决于 LLM 理解)
```

---

## 📚 相关文档
- `docs/LAYER2_COMPARISON.md` - Layer-2 两个版本对比
- `docs/FILTER_WORKFLOW.md` - 完整三层过滤流程
- `scripts/README_LAYER2_SMART.md` - Smart 版使用指南

---

**最后更新**: 2026-04-08  
**修改原因**: 修复场景误判问题，提升语义理解准确性  
**影响范围**: SmartRuleMatcher 场景识别逻辑
