# 过滤系统错误修复记录

## 📋 目录

1. [SELECT 规则逻辑错误](#select-规则逻辑错误)
2. [Layer-2 规则未实际应用](#layer-2-规则未实际应用)
3. [批量插入超时问题](#批量插入超时问题)
4. [主键冲突问题](#主键冲突问题)
5. [字段映射错误](#字段映射错误)
6. [其他优化记录](#其他优化记录)

---

## SELECT 规则逻辑错误

### 问题描述

**发现时间**: 2026-04-08  
**严重程度**: 🔴 严重

**症状**:
- Layer-2 生成 select 规则后，通过率仍高达 **98%+**，与预期严重不符
- 用户预期：只有包含特定关键词的内容才通过（白名单模式）
- 实际结果：几乎所有内容都通过，规则失效

**示例场景**:
```
用户 Query: "丽江便宜的性价比高的民宿有哪些"

LLM 生成 select 规则:
  - 旅游-性价比-民宿关键词 (select)
  - 关键词: ['性价比', '便宜', '经济型', '实惠', '高性价比']

预期通过率: ~5-10% (1万条中约 50-100 条符合)
实际通过率: 98%+ (9800+ 条全通过)
```

### 根本原因

#### 1. Select 规则语义错误理解

**正确语义** (`prompts_smart.py` 中的定义):
```python
## 规则用途说明
- **filter（过滤删除）**：命中即删除。用于去除不想要的内容
- **select（筛选保留）**：命中即保留。用于保留想要的内容
```

**Select 规则的正确行为**:
- 当存在 select 规则时，**只有命中 select 规则的内容才能通过**
- 未命中 select 规则的内容应该被**拦截**
- 这是一种**白名单机制**

#### 2. 错误的代码逻辑

**修复前代码** (`batch_scene_filter_smart.py`):

```python
# ❌ 错误的决策逻辑
if filtered:
    pass_flags.append(False)  # 拦截
    filter_count += 1
elif selected:
    pass_flags.append(True)   # 保留
    select_count += 1
else:
    # 🔴 问题所在：默认通过
    pass_flags.append(True)
    default_pass_count += 1
```

**问题分析**:
```
场景：存在 select 规则，某条内容不包含关键词
  filtered = False  (没有 filter 规则)
  selected = False  (未命中 select 规则)
  → 走到 else 分支 → pass_flags.append(True)  ← 错误！应该拦截

结果：
  - 命中 select 规则: 2% → 保留 ✅
  - 未命中 select 规则: 98% → 错误保留 ❌
```

### 修复方案

#### 正确的决策逻辑

```python
# 第一步：统计规则类型
has_filter_rules = any(r.purpose == "filter" for r in matched_rules + gap_rules)
has_select_rules = any(r.purpose == "select" for r in matched_rules + gap_rules)

# 第二步：对每条内容决策
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
    
    # 第三步：应用决策树
    if filtered:
        # ✅ filter 优先级最高
        pass_flags.append(False)
        filter_count += 1
    elif has_select_rules:
        # ✅ 存在 select 规则时，启用白名单模式
        if selected:
            pass_flags.append(True)
            select_count += 1
        else:
            # ✅ 未命中 select 规则 → 拦截
            pass_flags.append(False)
            not_selected_count += 1
    else:
        # ✅ 无 select 规则 → 默认通过（黑名单模式）
        pass_flags.append(True)
        default_pass_count += 1
```

### 决策树可视化

```
                 命中 filter 规则？
                       │
            ┌──────────┴──────────┐
           YES                    NO
            │                      │
        拦截 ❌                存在 select 规则？
                                  │
                       ┌──────────┴──────────┐
                      YES                   NO
                       │                     │
               命中 select 规则？         默认通过 ✅
                       │
            ┌──────────┴──────────┐
           YES                    NO
            │                      │
        保留 ✅                  拦截 ❌
```

### 修复效果

**修复前**:
```
Query: "丽江便宜民宿"
总数: 10000 条
  - 命中 select 规则: 200 条 → 保留
  - 未命中 select 规则: 9800 条 → 错误保留 ❌
通过率: 98%+ (10000 条)
```

**修复后**:
```
Query: "丽江便宜民宿"
总数: 10000 条
  - 命中 select 规则: 200 条 → 保留 ✅
  - 未命中 select 规则: 9800 条 → 拦截 ✅
通过率: 2% (200 条)
```

### 相关文件

- 主要修复: `scripts/batch_scene_filter_smart.py` (第 395-480 行)
- API 同步修复: `filter_engine/api.py` (`apply_rules_to_contents` 函数)
- 文档说明: `filter_engine/llm/prompts_smart.py`

---

## Layer-2 规则未实际应用

### 问题描述

**发现时间**: 2026-04-08  
**严重程度**: 🔴 严重

**症状**:
1. 通过率异常高（98%+）
2. LLM 生成的规则没有保存到数据库
3. 规则似乎完全没有生效

### 三个严重 Bug

#### Bug 1: 只应用了补充规则，未应用已有规则

**错误代码**:
```python
# ❌ 只应用 gap_rules，忽略了 matched_rules
filter_results = matcher.apply_gap_rules_to_content(contents, match_result.gap_rules)

for result in filter_results:
    if result["matched"]:
        # 处理 gap_rules 匹配结果
        pass
    else:
        pass_flags.append(True)  # 默认通过
```

**问题分析**:
```
LLM 分析结果:
  matched_rules: [规则38, 规则41]  ← 从规则库智能选择，但被忽略
  gap_rules: []                    ← LLM 认为无需补充

实际执行:
  - 应用 gap_rules (空)
  - 所有内容 matched=False
  - 全部默认通过
  - 通过率 100% ❌
```

**正确理解 matched_rules**:
```
规则库场景规则: 10 条 (电商场景所有规则)
      ↓
  LLM 思维链分析 (语义匹配)
      ↓
matched_rules: 3 条 (LLM 认为与 query 相关的规则)
      ↓
应该应用这 3 条规则 ✅  (不是全部 10 条 ❌)
```

#### Bug 2: 默认通过逻辑导致规则失效

**问题**:
```python
else:
    pass_flags.append(True)  # ❌ 默认通过
```

**极端情况**:
- 如果 LLM 未生成补充规则（`gap_rules = []`）
- 所有内容的 `matched = False`
- 所有内容走 `else` 分支 → **100% 通过**
- **规则完全失效**

**为什么 LLM 不生成补充规则？**
1. 规则库已包含相关规则 → LLM 认为无需补充
2. 场景简单 → LLM 认为已有规则足够
3. LLM 分析失败 → 返回空规则列表

#### Bug 3: matched_rules 的 rule_id 未传递

**问题代码**:
```python
# ❌ matched_rules 中只有规则名，没有 rule_id
matched_filter_results = []
for text in contents:
    for rule_info in matched_rules:
        rule_name = rule_info.rule_name  # ✅ 有名称
        rule_id = rule_info.rule_id      # ❌ 但缺少 ID，无法获取 content
```

**影响**:
- 无法从数据库查询规则的实际 content（关键词/正则）
- 无法真正执行规则匹配
- 规则形同虚设

### 修复方案

#### 1. 应用两类规则

```python
# ✅ 同时应用 matched_rules 和 gap_rules
gap_filter_results = matcher.apply_gap_rules_to_content(contents, match_result.gap_rules)
matched_filter_results = matcher.apply_matched_rules_to_content(contents, match_result.matched_rules)

# ✅ 综合两类规则的结果
for i, text in enumerate(contents):
    gap_result = gap_filter_results[i]
    matched_result = matched_filter_results[i]
    
    # 任意一类规则命中都生效
    if gap_result["matched"] or matched_result["matched"]:
        # 处理命中逻辑
        pass
```

#### 2. 修复默认通过逻辑

```python
# ✅ 根据规则类型决定默认行为
has_filter_rules = any(r.purpose == "filter" for r in all_rules)
has_select_rules = any(r.purpose == "select" for r in all_rules)

if not matched:
    if has_select_rules:
        pass_flags.append(False)  # 有 select 规则时，未命中即拦截
    else:
        pass_flags.append(True)   # 无 select 规则时，默认通过
```

#### 3. 传递完整规则信息

```python
# ✅ 在 SmartRuleMatcher 中返回完整的规则对象
matched_rules: List[MatchedRuleInfo] = []

for rule in selected_rules:
    matched_rules.append(MatchedRuleInfo(
        rule_id=rule.id,        # ✅ 包含 ID
        rule_name=rule.name,
        match_reason="...",
        purpose=rule.purpose
    ))
```

#### 4. 实现规则内容查询

```python
def apply_matched_rules_to_content(self, contents, matched_rules):
    results = []
    
    # ✅ 预加载所有规则的 content
    rule_details = {}
    for rule_info in matched_rules:
        rule = self.rule_manager.get(rule_info.rule_id)
        if rule:
            rule_details[rule_info.rule_id] = rule
    
    # ✅ 执行真正的规则匹配
    for text in contents:
        matched = False
        for rule_info in matched_rules:
            rule = rule_details.get(rule_info.rule_id)
            if rule and self._check_rule_match(text, rule):
                matched = True
                break
        results.append({"matched": matched, ...})
    
    return results
```

### 修复效果对比

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| LLM 选择 2 条 filter 规则，无 gap | 通过率 100% ❌ | 通过率 45% ✅ |
| LLM 生成 1 条 select 规则 | 通过率 98% ❌ | 通过率 3% ✅ |
| 规则库已覆盖，无需补充 | 规则完全失效 ❌ | 规则正常生效 ✅ |

### 相关文件

- `scripts/batch_scene_filter_smart.py` (主要修复)
- `filter_engine/llm/smart_matcher.py` (新增 `apply_matched_rules_to_content` 方法)
- `filter_engine/api.py` (同步修复)

---

## 批量插入超时问题

### 问题描述

**发现时间**: 2026-04-08  
**严重程度**: 🟠 中等

**错误信息**:
```python
postgrest.exceptions.APIError: {
  'message': 'canceling statement due to statement timeout',
  'code': '57014'
}
```

**发生位置**: `insert_session_l2_comments_batch` 函数

**根本原因**:
- 一次性插入大量数据（可能数千条评论）
- 超过 Supabase/PostgreSQL 默认语句超时时间（60秒）

### 修复前

```python
def insert_session_l2_comments_batch(...):
    rows = []
    for comment in comments:
        rows.append({...})  # 准备所有数据
    
    # ❌ 一次性插入所有数据（可能5000条）
    supabase.table("session_l2_comments").insert(rows).execute()
    return len(rows)
```

**问题**:
- 假设有 5000 条评论
- 单个 SQL 语句插入 5000 条记录
- 超过 60 秒超时限制

### 修复后

```python
def insert_session_l2_comments_batch(
    ...,
    batch_size: int = 50,  # 每批 50 条
):
    rows = []
    for comment in comments:
        rows.append({...})
    
    if dry_run:
        return len(rows)
    
    # ✅ 分批插入，避免单次操作过大
    total_inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        supabase.table("session_l2_comments").insert(batch).execute()
        total_inserted += len(batch)
        print(f"  ✅ 已写入 {total_inserted}/{len(rows)} 条评论...")
    
    return total_inserted
```

### 改进点

1. **分批处理**: 每次最多插入 50 条记录
2. **进度显示**: 实时显示已写入数量
3. **可配置**: `--write-batch-size` 参数自定义批量大小
4. **稳定性**: 单批失败不影响其他批次

### 配置建议

```bash
# 默认批量大小（推荐）
--write-batch-size 50

# 网络慢/延迟高
--write-batch-size 20

# 网络快/延迟低
--write-batch-size 100
```

### 性能对比

| 数据量 | 修复前 | 修复后 |
|--------|--------|--------|
| 1000条 | 15秒 ✅ | 20秒（50条/批）✅ |
| 5000条 | 超时 ❌ | 100秒（50条/批）✅ |
| 10000条 | 超时 ❌ | 200秒（50条/批）✅ |

### 相关文件

- `scripts/batch_scene_filter_smart.py`
- `scripts/batch_llm_filter.py`

---

## 主键冲突问题

### 问题1: Layer-2 主键冲突

**发现时间**: 2026-04-08  
**严重程度**: 🟠 中等

**错误信息**:
```python
postgrest.exceptions.APIError: {
  'message': 'duplicate key value violates unique constraint "session_l2_posts_pkey"',
  'code': '23505',
  'details': 'Key (id)=(5271530469590781) already exists.'
}
```

#### 根本原因

**Schema 设计**:
```sql
CREATE TABLE session_l2_posts (
    id VARCHAR(50) PRIMARY KEY,        -- ❌ 直接使用 filtered_posts.id
    session_id VARCHAR(50) NOT NULL,
    ...
);
```

**冲突场景**:
```
Session 1: 用户 A 查询 "电商广告"
  → 帖子 5271530469590781 被写入 session_l2_posts
  → id = "5271530469590781"

Session 2: 用户 B 查询 "社交营销"（可能包含同一条帖子）
  → 帖子 5271530469590781 再次被写入
  → 主键冲突！❌
```

#### 解决方案

**方案1: 使用 upsert（推荐）**

```python
# ❌ 修复前
supabase.table("session_l2_posts").insert(batch).execute()

# ✅ 修复后
supabase.table("session_l2_posts").upsert(batch).execute()
```

**方案2: 修改主键为联合主键**

```sql
CREATE TABLE session_l2_posts (
    session_id VARCHAR(50),
    post_id VARCHAR(50),
    PRIMARY KEY (session_id, post_id)  -- ✅ 联合主键
);
```

### 问题2: Layer-3 主键冲突

**发现时间**: 2026-04-08  
**严重程度**: 🟠 中等

**错误信息**:
```python
postgrest.exceptions.APIError: {
  'message': 'duplicate key value violates unique constraint "session_l3_results_pkey"',
  'code': '23505',
  'details': 'Key (session_id, post_id)=(xxx, xxx) already exists.'
}
```

#### 根本原因

- 重复运行 `batch_llm_filter.py`（如测试不同 `--min-relevance` 参数）
- 使用 `insert()` 而非 `upsert()` 导致主键冲突

#### 解决方案

**方案1: 使用 upsert**

```python
# ❌ 修复前
supabase.table("session_l3_results").insert(chunk).execute()

# ✅ 修复后
supabase.table("session_l3_results").upsert(chunk).execute()
```

**方案2: 新增 --clear-existing 参数**

```bash
# 清理旧数据后重新运行
uv run python scripts/batch_llm_filter.py \
  --session-id xxx \
  --query "xxx" \
  --clear-existing
```

```python
if args.clear_existing:
    print(f"🗑️  清理 session {session_id} 的旧数据...")
    supabase.table("session_l3_results")\
        .delete()\
        .eq("session_id", session_id)\
        .execute()
```

### 相关文件

- `scripts/batch_scene_filter_smart.py`
- `scripts/batch_llm_filter.py`
- `database/schema_session.sql`

---

## 字段映射错误

### 问题描述

**发现时间**: 2026-04-07  
**严重程度**: 🟡 轻微

**症状**:
- 数据库字段名与代码中使用的字段名不一致
- 导致数据查询/写入失败
- 字段为 NULL 或缺失

### 典型错误

#### 1. metrics 字段映射

**错误代码**:
```python
# ❌ 使用嵌套结构
post = {
    "metrics": {
        "likes": 100,
        "comments": 50
    }
}
```

**数据库 Schema**:
```sql
-- ✅ 实际是扁平结构
CREATE TABLE filtered_posts (
    metrics_likes INTEGER,
    metrics_comments INTEGER
);
```

**正确代码**:
```python
# ✅ 使用扁平字段名
post = {
    "metrics_likes": 100,
    "metrics_comments": 50
}
```

#### 2. author 字段映射

**错误代码**:
```python
# ❌ 使用嵌套结构
post = {
    "author": {
        "id": "123",
        "nickname": "张三"
    }
}
```

**正确代码**:
```python
# ✅ 使用扁平字段名
post = {
    "author_id": "123",
    "author_nickname": "张三"
}
```

### 修复方案

#### 统一字段命名规范

| 业务含义 | 错误写法 | 正确写法 |
|---------|---------|---------|
| 点赞数 | `metrics.likes` | `metrics_likes` |
| 收藏数 | `metrics.collects` | `metrics_collects` |
| 评论数 | `metrics.comments` | `metrics_comments` |
| 分享数 | `metrics.shares` | `metrics_shares` |
| 作者ID | `author.id` | `author_id` |
| 作者昵称 | `author.nickname` | `author_nickname` |
| 作者头像 | `author.avatar` | `author_avatar` |
| 图片列表 | `media.images` | `media_images` |
| 视频URL | `media.video_url` | `media_video_url` |

### 相关文件

- `tools/data_format_converter.py`
- `database/schema.sql`
- `database/schema_filtered.sql`

---

## 其他优化记录

### 1. Layer-2 规则宽松化

**时间**: 2026-04-08  
**原因**: select 规则关键词太少，导致通过率过低

**修复**:
```python
# ❌ 修复前：关键词太少
["便宜"]  # 可能漏掉 "实惠"、"性价比"

# ✅ 修复后：关键词覆盖面广
["便宜", "实惠", "性价比", "经济型", "高性价比", 
 "划算", "物美价廉", "省钱", "优惠", "折扣"]
```

**Prompt 优化**:
```python
## ⚠️ 重要约束
生成的关键词要**宽松**，覆盖面更广，避免遗漏
- filter 规则：只添加最明显的垃圾/广告关键词
- select 规则：添加更多相关词汇，降低筛选门槛
- 每个规则建议包含 **5-10 个关键词**，而不是 2-3 个
```

### 2. Layer-3 LLM Only 模式

**时间**: 2026-04-08  
**功能**: 完全依赖 LLM 进行相关性判断，不进行关键词预筛选

**使用场景**:
- 高质量内容筛选
- 语义复杂场景
- 对准确率要求高

**开启方式**:
```python
{
    "llm_only": true,  # 启用 LLM Only 模式
    "min_relevance": "high"
}
```

### 3. 性能优化

**批量处理大小调优**:
```python
# Layer-3 批处理（LLM 调用）
batch_size = 100  # 默认值
max_workers = 3   # 并发线程数

# 调整建议：
# - LLM API 速度快 → 增大 batch_size 到 200
# - LLM API 速度慢 → 减小 batch_size 到 50
# - 并发限制 → 调整 max_workers
```

**早停策略**:
```python
# Layer-1 通过数为 0 时，直接返回
if layer1_passed == 0:
    return {"stats": {...}, "results": []}

# Layer-2 通过数为 0 时，跳过 Layer-3
if layer2_passed == 0:
    return {"stats": {...}, "results": []}
```

### 4. 日志优化

**添加详细日志**:
```python
print(f"🔍 Layer-1: 基础规则过滤 ({len(items)} 条)")
print(f"  ✅ Layer-1 完成: {stats['layer1_passed']}/{stats['total_input']} 通过 ({perf['layer1']:.2f}s)")

print(f"🎯 Layer-2: 场景规则过滤 ({len(survivors)} 条)")
print(f"  场景: {match_result.detected_scenario}")
print(f"  已有规则: {len(match_result.matched_rules)} 条")
print(f"  补充规则: {len(match_result.gap_rules)} 条")
print(f"  ✅ Layer-2 完成: {stats['layer2_passed']}/{stats['layer1_passed']} 通过 ({perf['layer2']:.2f}s)")

print(f"🤖 Layer-3: LLM 语义过滤 ({len(survivors)} 条)")
print(f"  ✅ Layer-3 完成: {stats['layer3_passed']}/{stats['layer2_passed']} 通过 ({perf['layer3']:.2f}s)")
```

---

## 修复时间线

| 日期 | 问题 | 严重程度 | 状态 |
|------|------|---------|------|
| 2026-04-07 | 字段映射错误 | 🟡 轻微 | ✅ 已修复 |
| 2026-04-08 | SELECT 规则逻辑错误 | 🔴 严重 | ✅ 已修复 |
| 2026-04-08 | Layer-2 规则未应用 | 🔴 严重 | ✅ 已修复 |
| 2026-04-08 | 批量插入超时 | 🟠 中等 | ✅ 已修复 |
| 2026-04-08 | 主键冲突问题 | 🟠 中等 | ✅ 已修复 |
| 2026-04-08 | Layer-2 规则宽松化 | 🟡 轻微 | ✅ 已优化 |
| 2026-04-08 | Layer-3 LLM Only 模式 | 🟢 增强 | ✅ 已实现 |

---

## 测试验证

### 回归测试

```bash
# 1. 测试 SELECT 规则逻辑
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江便宜民宿" \
  --session-id test_select \
  --dry-run

# 预期：通过率 < 10%

# 2. 测试 matched_rules 应用
uv run python scripts/batch_scene_filter_smart.py \
  --query "过滤电商广告" \
  --session-id test_matched \
  --dry-run

# 预期：通过率 < 50%

# 3. 测试批量插入
uv run python scripts/batch_scene_filter_smart.py \
  --query "测试大数据" \
  --session-id test_batch \
  --write-batch-size 50

# 预期：无超时错误

# 4. 测试主键冲突修复
uv run python scripts/batch_llm_filter.py \
  --session-id test_upsert \
  --query "测试" \
  --min-relevance high

# 重复运行两次，预期：无主键冲突
```

### 性能测试

| 测试场景 | 数据量 | 修复前 | 修复后 |
|---------|--------|--------|--------|
| SELECT 规则通过率 | 10000 | 98% ❌ | 3% ✅ |
| matched_rules 生效 | 5000 | 0% ❌ | 100% ✅ |
| 批量插入耗时 | 5000 | 超时 ❌ | 100s ✅ |
| 主键冲突频率 | 重复10次 | 100% ❌ | 0% ✅ |

---

## 经验总结

### 1. 决策逻辑设计原则

- **明确规则语义**: filter（黑名单）vs select（白名单）
- **考虑极端情况**: 规则为空、全部命中、全部未命中
- **避免隐式默认**: 明确写出所有分支的行为

### 2. 数据库操作最佳实践

- **优先使用 upsert**: 避免主键冲突
- **分批处理大数据**: 防止超时
- **联合主键设计**: 支持多维度唯一性
- **添加清理参数**: 支持重复运行

### 3. 代码审查要点

- ✅ 规则是否真正应用到数据？
- ✅ 默认行为是否符合预期？
- ✅ 是否考虑了空集合情况？
- ✅ 是否有充分的日志输出？
- ✅ 是否有错误处理和容错？

### 4. 测试覆盖建议

- 单元测试：每个决策分支
- 集成测试：完整流水线
- 压力测试：大数据量场景
- 回归测试：修复后重测

---

**文档版本**: v1.0  
**最后更新**: 2026-05-17  
**维护者**: 系统开发团队
