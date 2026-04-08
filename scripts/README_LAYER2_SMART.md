# Layer-2 智能场景过滤脚本使用指南

## 快速开始

### 基础用法

```bash
# 从项目根目录运行
cd e:\xhs-crawler

# 标准模式（自动 LLM 场景识别 + 规则补充）
uv run python scripts/batch_scene_filter_smart.py \
    --query "过滤电商平台的广告评论"

# Dry-run 测试（不写数据库）
uv run python scripts/batch_scene_filter_smart.py \
    --query "过滤旅游攻略中的营销推广" \
    --dry-run
```

---

## 核心参数

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--query` | 过滤意图描述（LLM 分析用） | `"过滤电商广告和刷单评论"` |

### 可选参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--platform` | 全平台 | 指定平台：`xhs` / `weibo` |
| `--force-scenario` | 自动识别 | 强制场景：`ecommerce` / `social` / `news` 等 |
| `--page-size` | 200 | 分页大小 |
| `--save-gap-rules` | False | 将 LLM 生成的补充规则保存到数据库 |
| `--filter-comments-mode` | `all` | 评论过滤模式：`all` / `valid-posts-only` |
| `--dry-run` | False | 试运行（不写数据库） |

---

## 使用场景

### 场景 1：电商平台广告过滤

```bash
uv run python scripts/batch_scene_filter_smart.py \
    --query "过滤电商平台的广告、刷单、引流评论" \
    --platform xhs \
    --save-gap-rules  # 保存 LLM 生成的规则
```

**预期效果**：
- LLM 识别场景为 `ecommerce`
- 匹配规则：`电商-广告-引流词`、`电商-刷单-异常行为`
- 可能生成补充规则：`电商-营销-软广植入`（如规则库缺失）

---

### 场景 2：社交平台高质量内容筛选

```bash
uv run python scripts/batch_scene_filter_smart.py \
    --query "保留真实用户的高质量评论，去掉营销号和水军" \
    --force-scenario social \
    --filter-comments-mode valid-posts-only  # 仅过滤有效帖子的评论
```

**预期效果**：
- LLM 生成 `select` 规则（保留高质量词）
- LLM 生成 `filter` 规则（拦截营销词）
- 联动过滤：只处理 Layer-2 通过的帖子的评论

---

### 场景 3：语义复杂场景（健康养生去广告）

```bash
uv run python scripts/batch_scene_filter_smart.py \
    --query "健康养生内容，但要去掉医疗广告和产品推销" \
    --dry-run  # 先测试不写库
```

**预期效果**：
- LLM 识别这是 `social` 场景（而非 `medical`）
- 生成补充规则：`社交-广告-健康产品推销`
- 标记 `needs_llm_filter=true`（建议执行 Layer-3）

---

### 场景 4：批量处理全平台数据

```bash
# 不指定 --platform，处理所有平台
uv run python scripts/batch_scene_filter_smart.py \
    --query "过滤所有平台的广告和垃圾评论" \
    --page-size 500  # 大批量处理
```

---

## 输出示例

### 成功运行输出

```
================================================================================
🚀 Layer-2 智能场景批量过滤 (SmartRuleMatcher)
================================================================================
🔍 Query: 过滤电商平台的广告评论
📱 Platform: xhs
🎯 Force Scenario: 自动识别
💾 保存补充规则: 是
💬 评论过滤模式: all
🧪 Dry-run: 否

🆔 Session ID: 123e4567-e89b-12d3-a456-426614174000

================================================================================
📝 STEP 1: 处理帖子 (filtered_posts → session_l2_posts)
================================================================================
📊 从 Layer-1 读取帖子: 1234 条

============================================================
🧠 LLM 思维链分析 - 帖子
============================================================

✅ 场景识别: ecommerce (电商)
📋 匹配已有规则: 2 条
   - [ID:30] 电商-广告-引流词 (filter)
   - [ID:31] 电商-刷单-异常行为 (filter)
🔧 LLM 生成补充规则: 1 条
   - 电商-营销-软广植入 (filter) - 8 个关键词
🎯 需要 Layer-3 语义过滤: true
   原因: 存在隐式营销内容，规则引擎难以识别

📊 应用规则到 1234 条帖子...
✅ 通过: 856 / 1234 (69.4%)

✅ Layer-2 帖子通过: 856 / 1234

================================================================================
💬 STEP 2: 处理评论 (filtered_comments → session_l2_comments)
================================================================================
🌐 全量模式: 过滤所有 Layer-1 通过的评论
📊 待过滤评论: 5678 条

============================================================
🧠 LLM 思维链分析 - 评论
============================================================

✅ 场景识别: ecommerce (电商)
📋 匹配已有规则: 2 条
🔧 LLM 生成补充规则: 1 条
🎯 需要 Layer-3 语义过滤: true

📊 应用规则到 5678 条评论...
✅ 通过: 3421 / 5678 (60.3%)

✅ Layer-2 评论通过: 3421 / 5678

================================================================================
💾 STEP 3: 保存补充规则到数据库
================================================================================
✅ 成功保存 1 条规则: [125]

================================================================================
✅ Layer-2 过滤完成！
================================================================================
🆔 Session ID: 123e4567-e89b-12d3-a456-426614174000

📌 下一步: 执行 Layer-3 语义过滤
   uv run python scripts/batch_llm_filter.py --session-id 123e4567-e89b-12d3-a456-426614174000 --query "过滤电商平台的广告评论"

📊 查询结果:
   SELECT * FROM session_l2_posts WHERE session_id = '123e4567-e89b-12d3-a456-426614174000';
   SELECT * FROM session_l2_comments WHERE session_id = '123e4567-e89b-12d3-a456-426614174000';
   SELECT * FROM session_metadata WHERE session_id = '123e4567-e89b-12d3-a456-426614174000';
```

---

## 常见问题

### Q1: 为什么需要 `--save-gap-rules`？

**A**: 
- LLM 生成的补充规则默认**只在本次 session 生效**（临时规则）
- 加上 `--save-gap-rules` 后，规则会**永久保存到数据库**
- 下次运行时，已保存的规则会自动匹配，无需重复生成

**建议**：
- 首次运行新场景时加上此参数
- 规则库完善后可去掉（节省 LLM 调用）

---

### Q2: `--filter-comments-mode` 两种模式区别？

| 模式 | 处理范围 | 适用场景 |
|------|---------|---------|
| `all` | 所有 Layer-1 通过的评论 | 评论质量过滤（不关联帖子） |
| `valid-posts-only` | 仅 Layer-2 通过的帖子的评论 | 联动过滤（帖子+评论一致性） |

**示例**：
```bash
# 场景：只要高质量帖子 + 其评论
uv run python scripts/batch_scene_filter_smart.py \
    --query "保留高质量旅游攻略" \
    --filter-comments-mode valid-posts-only  # 低质帖子的评论直接丢弃
```

---

### Q3: 如何查看 LLM 思维链详情？

**A**: 脚本会自动打印思维链步骤：

```
🧠 LLM 思维链分析 - 帖子
✅ 场景识别: ecommerce
📋 匹配已有规则: 2 条
   - [ID:30] 电商-广告-引流词
🔧 LLM 生成补充规则: 1 条
   - 电商-营销-软广植入 - 8 个关键词
```

如需完整 JSON，可修改代码添加：
```python
print(json.dumps(match_result.to_dict(), indent=2, ensure_ascii=False))
```

---

### Q4: 为什么有时候 `needs_llm_filter=true`？

**A**: LLM 检测到以下情况时会标记：

1. **语义模糊**：规则引擎无法准确判断（如"软广植入"）
2. **上下文相关**：需要理解上下文才能判断
3. **规则缺口**：部分约束无法用关键词表达

**建议**：收到此标记后执行 Layer-3 语义过滤：
```bash
uv run python scripts/batch_llm_filter.py \
    --session-id <SESSION_ID> \
    --query "..."
```

---

### Q5: Dry-run 模式有什么用？

**A**: 
- 不写入数据库，只输出统计
- 用于测试 query 效果
- 查看会生成哪些补充规则

```bash
# 测试 query
uv run python scripts/batch_scene_filter_smart.py \
    --query "你的复杂 query" \
    --dry-run

# 满意后正式运行
uv run python scripts/batch_scene_filter_smart.py \
    --query "你的复杂 query" \
    --save-gap-rules
```

---

## 性能优化建议

### 1. 批量处理大数据集

```bash
# 增大 page-size（减少数据库查询次数）
uv run python scripts/batch_scene_filter_smart.py \
    --query "..." \
    --page-size 1000
```

### 2. 跳过 LLM 场景识别（已知场景）

```bash
# 强制指定场景，节省 1 次 LLM 调用
uv run python scripts/batch_scene_filter_smart.py \
    --query "..." \
    --force-scenario ecommerce
```

### 3. 只处理单平台

```bash
# 减少数据量
uv run python scripts/batch_scene_filter_smart.py \
    --query "..." \
    --platform xhs
```

---

## 完整三层流程

### Step 1: Layer-1 通用规则过滤

```bash
# 假设已执行（数据在 filtered_posts/comments）
uv run python scripts/batch_filter.py
```

### Step 2: Layer-2 场景规则过滤（本脚本）

```bash
uv run python scripts/batch_scene_filter_smart.py \
    --query "过滤电商广告" \
    --save-gap-rules

# 输出 Session ID: abc-123-def
```

### Step 3: Layer-3 语义相关性过滤

```bash
uv run python scripts/batch_llm_filter.py \
    --session-id abc-123-def \
    --query "过滤电商广告" \
    --min-relevance medium
```

### Step 4: 查询最终结果

```sql
-- 最终通过的帖子+评论（嵌套JSON）
SELECT * FROM session_l3_results 
WHERE session_id = 'abc-123-def';

-- 统计信息
SELECT * FROM session_metadata 
WHERE session_id = 'abc-123-def';
```

---

## 故障排查

### 错误 1: `ModuleNotFoundError: No module named 'filter_engine'`

**解决**：确保从项目根目录运行
```bash
cd e:\xhs-crawler
uv run python scripts/batch_scene_filter_smart.py --query "..."
```

### 错误 2: `LLM API 调用失败`

**解决**：检查环境变量
```bash
# 设置 API Key（PowerShell）
$env:OPENAI_API_KEY="sk-..."
$env:QWEN_API_KEY="sk-..."

# 或在 .env 文件中配置
```

### 错误 3: `Supabase 连接超时`

**解决**：检查网络 + API Key
```python
# 确认 SUPABASE_URL 和 SUPABASE_KEY 正确
```

---

## 下一步

- 查看 [LAYER2_COMPARISON.md](../docs/LAYER2_COMPARISON.md) 了解两种 Layer-2 方案对比
- 查看 [FILTER_WORKFLOW.md](../docs/FILTER_WORKFLOW.md) 了解完整三层架构
- 执行 Layer-3: `uv run python scripts/batch_llm_filter.py --help`
