# SELECT 规则逻辑错误修复文档

## 问题发现

**时间**: 2026年4月8日  
**发现者**: 用户  
**症状**: Layer-2 SmartRuleMatcher 生成 select 规则后，通过率仍高达 98%+，与预期严重不符

### 问题描述

用户 Query: `"丽江便宜的性价比高的民宿有哪些"`

LLM 生成的 select 规则:
```
旅游-性价比-民宿关键词 (select) - 5 个关键词: ['性价比', '便宜', '经济型', '实惠', '高性价比']
```

**用户预期**:
- ✅ 包含这些关键词的帖子 → 保留
- ❌ 不包含这些关键词的帖子 → **应该被过滤掉**
- 预期通过率: ~5-10% (1万条中约 50-100 条符合要求)

**实际结果**:
- ✅ 包含关键词的帖子 → 保留 (约 2%)
- ✅ 不包含关键词的帖子 → **也被保留** (约 96%)
- 实际通过率: **98%+**

---

## 根本原因分析

### 1. Select 规则语义

根据 `filter_engine/llm/prompts_smart.py` 中的定义:

```python
## 规则用途说明
- **filter（过滤删除）**：命中即删除。用于去除不想要的内容，如广告、垃圾、敏感词
- **select（筛选保留）**：命中即保留。用于保留想要的内容，如特定主题、质量标准
```

**Select 规则的正确语义**:
- 当存在 select 规则时，**只有命中 select 规则的内容才能通过**
- 未命中 select 规则的内容应该被**拦截**
- 这是一种**白名单机制**

### 2. 错误的代码逻辑

**原始代码** (`batch_scene_filter_smart.py` 第 395-438 行):

```python
# 决策逻辑（错误）
if filtered:
    pass_flags.append(False)  # 拦截
    filter_count += 1
elif selected:
    pass_flags.append(True)   # 保留
    select_count += 1
else:
    # 默认通过（保守策略）← 问题所在！
    pass_flags.append(True)
    default_pass_count += 1
```

**问题分析**:

```
场景 1: 存在 select 规则，某条内容不包含关键词
  filtered = False  (没有 filter 规则)
  selected = False  (未命中 select 规则)
  → 走到 else 分支 → pass_flags.append(True)  ← 错误！应该拦截
```

这导致:
- 命中 select 规则: 2% → 保留 ✅
- 未命中 select 规则: 98% → **错误保留** ❌

---

## 修复方案

### 1. 正确的决策逻辑

```python
# 收集规则类型统计
has_filter_rules = any(r.purpose == "filter" for r in matched_rules) or \
                   any(r.purpose == "filter" for r in gap_rules)
has_select_rules = any(r.purpose == "select" for r in matched_rules) or \
                   any(r.purpose == "select" for r in gap_rules)

for i, text in enumerate(contents):
    gap_result = gap_filter_results[i]
    matched_result = matched_filter_results[i]
    
    filtered = False
    selected = False
    
    # 检查是否命中 filter 规则
    if gap_result["matched"] and gap_result["purpose"] == "filter":
        filtered = True
    if matched_result["matched"] and matched_result["purpose"] == "filter":
        filtered = True
    
    # 检查是否命中 select 规则
    if gap_result["matched"] and gap_result["purpose"] == "select":
        selected = True
    if matched_result["matched"] and matched_result["purpose"] == "select":
        selected = True
    
    # 决策逻辑（修正）
    if filtered:
        # 命中 filter 规则 → 拦截
        pass_flags.append(False)
        filter_count += 1
    elif has_select_rules:
        # ⭐ 关键修改：如果存在 select 规则，必须命中才能通过
        if selected:
            pass_flags.append(True)
            select_count += 1
        else:
            pass_flags.append(False)  # 未命中 select → 拦截
            not_selected_count += 1
    else:
        # 没有任何规则 → 默认通过（保守策略）
        pass_flags.append(True)
        default_pass_count += 1
```

### 2. 决策树对比

#### 修复前（错误逻辑）

```
├─ filtered == True  → 拦截 ✅
├─ selected == True  → 保留 ✅
└─ else (filtered == False && selected == False)
   └─ 默认通过 ❌ (这里是问题！)
```

#### 修复后（正确逻辑）

```
├─ filtered == True  → 拦截 ✅
├─ has_select_rules == True
│  ├─ selected == True   → 保留 ✅
│  └─ selected == False  → 拦截 ✅ (新增逻辑)
└─ has_select_rules == False
   └─ 默认通过 ✅ (保守策略，仅在无任何规则时)
```

---

## 代码修改

### 文件: `scripts/batch_scene_filter_smart.py`

#### 修改 1: `apply_rules_to_contents()` 函数

**位置**: 第 395-446 行

**关键变更**:
1. 新增 `has_filter_rules` 和 `has_select_rules` 标志判断
2. 新增 `not_selected_count` 统计项
3. 修改决策树：`elif has_select_rules` 分支区分命中/未命中

#### 修改 2: 调试输出

**位置**: 第 517 行

**变更**:
```python
# 新增输出项
print(f"   - 未命中 select 规则（被拦截）: {stats.get('not_selected_count', 0)} 条")
```

---

## 预期效果

### 修复前（错误）

```
Query: "丽江便宜的性价比高的民宿有哪些"
规则: 旅游-性价比-民宿关键词 (select) - ['性价比', '便宜', '经济型', '实惠', '高性价比']

结果:
✅ 通过: 9800 / 10000 (98.0%)
   - 被 filter 规则拦截: 0 条
   - 被 select 规则保留: 200 条
   - 无规则命中（默认通过）: 9800 条  ← 错误！
```

### 修复后（正确）

```
Query: "丽江便宜的性价比高的民宿有哪些"
规则: 旅游-性价比-民宿关键词 (select) - ['性价比', '便宜', '经济型', '实惠', '高性价比']

结果:
✅ 通过: 200 / 10000 (2.0%)
   - 被 filter 规则拦截: 0 条
   - 被 select 规则保留: 200 条
   - 未命中 select 规则（被拦截）: 9800 条  ← 修复！
   - 无规则命中（默认通过）: 0 条
```

---

## 影响范围

### 1. 受影响的场景

**所有使用 select 规则的 Query 都受影响**，包括但不限于:

- ✅ "找**性价比高**的民宿" → select 规则
- ✅ "只看**好评多**的餐厅" → select 规则
- ✅ "筛选**有图片**的帖子" → select 规则
- ✅ "要**1000元以下**的酒店" → select 规则

### 2. 不受影响的场景

- ❌ "过滤广告" → filter 规则（逻辑一直正确）
- ❌ "删除敏感内容" → filter 规则（逻辑一直正确）

### 3. 历史数据

**如果之前运行过使用 select 规则的任务**:
- 数据质量: **严重不达标**（98% 不相关内容被错误保留）
- 建议操作: **重新运行 Layer-2 过滤**

---

## 测试验证

### 测试用例 1: 纯 select 规则

```python
Query: "找性价比高的民宿"
规则:
  - 旅游-性价比-民宿关键词 (select) - ['性价比', '便宜', '实惠']

测试数据:
  - "这家民宿性价比超高！" → 应保留 ✅
  - "丽江古城民宿推荐" → 应拦截 ❌
  - "超级便宜的客栈" → 应保留 ✅
  - "五星级酒店" → 应拦截 ❌

预期通过率: 50% (2/4)
```

### 测试用例 2: filter + select 混合

```python
Query: "找不发广告的性价比高的民宿"
规则:
  - 电商-引流-私信加V (filter) - ['加V', '私信']
  - 旅游-性价比-民宿关键词 (select) - ['性价比', '便宜']

测试数据:
  - "性价比高的民宿，私信我" → 应拦截 (filter 优先) ❌
  - "性价比超高！推荐" → 应保留 ✅
  - "丽江民宿推荐" → 应拦截 (未命中 select) ❌
  - "便宜的客栈，加V咨询" → 应拦截 (filter 优先) ❌

预期通过率: 25% (1/4)
```

### 测试用例 3: 无规则

```python
Query: "" (空或无效)
规则: 无

测试数据:
  - "任意内容 1" → 应保留 ✅
  - "任意内容 2" → 应保留 ✅

预期通过率: 100% (默认保守策略)
```

---

## 相关文档

1. **规则语义定义**: `filter_engine/llm/prompts_smart.py` 第 44-46 行
2. **RulePurpose 枚举**: `filter_engine/rules/models.py` 第 19-22 行
3. **前序 Bug 修复**: `docs/LAYER2_SMART_CRITICAL_BUG_FIX.md`

---

## 经验教训

### 1. 默认行为的危险性

```python
# 危险的代码模式
if condition_A:
    handle_A()
elif condition_B:
    handle_B()
else:
    default_pass()  # ⚠️ 危险！可能掩盖逻辑错误
```

**改进**:
- 明确列举所有分支条件
- `else` 只用于真正的"其他情况"，不是"未知情况"
- 使用警告/日志记录非预期路径

### 2. 规则语义的歧义性

**Select 规则的语义可能被理解为**:
- ❌ 理解 1: "命中则保留，未命中不管"（保守）
- ✅ 理解 2: "命中则保留，未命中拦截"（严格，正确）

**解决方案**:
- 文档明确说明语义（已有，但需强化）
- 添加单元测试覆盖边界情况
- 代码注释清晰标注决策逻辑

### 3. 测试覆盖不足

**缺失的测试**:
- [ ] Select 规则未命中场景
- [ ] Filter + Select 混合场景
- [ ] 高通过率异常检测

**后续改进**:
- 添加 `tests/test_select_rule_logic.py`
- 集成到 CI/CD pipeline

---

## 总结

| 项目 | 内容 |
|------|------|
| **Bug 类型** | 逻辑错误（条件判断缺失） |
| **严重程度** | ⭐⭐⭐⭐⭐ 严重（完全改变规则语义） |
| **影响范围** | 所有使用 select 规则的场景 |
| **修复难度** | ⭐⭐ 简单（单点修改，逻辑清晰） |
| **测试覆盖** | ⚠️ 需补充单元测试 |
| **文档更新** | ✅ 已完成（本文档） |

---

**修复日期**: 2026年4月8日  
**修复版本**: v2.1.0  
**修复作者**: GitHub Copilot  
**审核状态**: ⏳ 待用户测试验证
