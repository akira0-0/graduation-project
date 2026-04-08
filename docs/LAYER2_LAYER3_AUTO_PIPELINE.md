# Layer-2 自动衔接 Layer-3 功能文档

## 功能概述

**更新时间**: 2026年4月8日  
**功能**: Layer-2 完成后自动执行 Layer-3 语义相关性过滤

**优势**:
- ✅ 一键完成完整过滤流程（Layer-2 + Layer-3）
- ✅ 无需手动复制 session_id
- ✅ 自动传递 query 参数
- ✅ 可选跳过 Layer-3（灵活控制）

---

## 使用方法

### 1. 默认模式（自动执行 Layer-3）

```bash
# 一键完成 Layer-2 + Layer-3 过滤
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江有什么好玩的"
```

**执行流程**:
```
Layer-1 (已完成) → filtered_posts / filtered_comments
    ↓
Layer-2 (SmartRuleMatcher) → session_l2_posts / session_l2_comments
    ↓ (自动衔接)
Layer-3 (RelevanceFilter) → session_l3_results
    ↓
完成！
```

### 2. 跳过 Layer-3（仅执行 Layer-2）

```bash
# 仅执行 Layer-2，稍后手动运行 Layer-3
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江有什么好玩的" \
  --skip-layer3
```

**适用场景**:
- 需要先检查 Layer-2 结果
- 想要调整 Layer-3 参数后再运行
- 调试 Layer-2 逻辑

### 3. 自定义 Layer-3 参数

```bash
# 自定义相关性阈值
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江有什么好玩的" \
  --min-relevance high

# 禁用 Layer-3 的 LLM（仅关键词匹配，快速模式）
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江有什么好玩的" \
  --no-llm-layer3
```

---

## 新增参数

### `--skip-layer3`

**类型**: `action="store_true"`  
**默认值**: `False` (自动执行 Layer-3)  
**说明**: 跳过 Layer-3 语义过滤，仅执行 Layer-2

**示例**:
```bash
# 仅执行 Layer-2
uv run python scripts/batch_scene_filter_smart.py \
  --query "xxx" \
  --skip-layer3
```

### `--min-relevance`

**类型**: `str`  
**可选值**: `high` / `medium` / `low`  
**默认值**: `medium`  
**说明**: Layer-3 最低相关性要求

**级别说明**:
- `high`: 仅保留高度相关的内容（通过率 ~5-15%）
- `medium`: 中等相关以上（通过率 ~20-40%）
- `low`: 低相关以上（通过率 ~50-70%）

**示例**:
```bash
# 严格模式：仅保留高度相关
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江旅游攻略" \
  --min-relevance high

# 宽松模式：保留低相关以上
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江旅游攻略" \
  --min-relevance low
```

### `--no-llm-layer3`

**类型**: `action="store_true"`  
**默认值**: `False` (使用 LLM)  
**说明**: Layer-3 禁用 LLM，仅使用关键词匹配判断相关性

**优势**:
- ✅ 速度快（无 LLM 调用）
- ✅ 成本低（不消耗 API 配额）
- ⚠️ 准确率略低（70-80% vs 90-95%）

**示例**:
```bash
# 快速模式（纯关键词匹配）
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江旅游" \
  --no-llm-layer3
```

---

## 执行流程详解

### 完整流程

```
1. Layer-2 场景规则过滤
   ├─ LLM 思维链分析
   ├─ 场景识别
   ├─ 规则匹配 + 生成
   ├─ 应用规则到帖子/评论
   └─ 写入 session_l2_posts / session_l2_comments

2. 自动检查是否执行 Layer-3
   ├─ 检查 --skip-layer3 参数
   ├─ 检查 --dry-run 参数
   └─ 决定是否继续

3. Layer-3 语义相关性过滤
   ├─ 读取 session_l2_posts
   ├─ 关键词匹配评分 (0-1.0)
   ├─ 中间地带调用 LLM
   ├─ 筛选相关帖子
   ├─ 读取相关帖子的评论
   └─ 写入 session_l3_results

4. 更新元数据
   └─ session_metadata (l2/l3 统计)
```

### 输出示例

```
================================================================================
🚀 Layer-2 智能场景批量过滤 (SmartRuleMatcher)
================================================================================
🔍 Query: 丽江有什么好玩的
📱 Platform: 全平台
🎯 Force Scenario: 自动识别
📦 批量写入大小: 50 条/批
💾 保存补充规则: 否
💬 评论过滤模式: valid-posts-only
🧪 Dry-run: 否

🆔 Session ID: b78b232c-0f81-4663-ac72-2794ac6d1342

... (Layer-2 执行过程)

================================================================================
✅ Layer-2 过滤完成！
================================================================================
🆔 Session ID: b78b232c-0f81-4663-ac72-2794ac6d1342

================================================================================
🚀 自动启动 Layer-3 语义相关性过滤
================================================================================
📊 Layer-3 参数:
   - Query: 丽江有什么好玩的
   - 最低相关性: medium
   - 使用 LLM: True

────────────────────────────────────────────────────────────────
📝 Step 1: 读取 Layer-2 通过的帖子
────────────────────────────────────────────────────────────────
✅ 读取到 500 条帖子

────────────────────────────────────────────────────────────────
🧠 Step 2: 相关性判断（关键词 + LLM）
────────────────────────────────────────────────────────────────
✅ 帖子过滤完成: 500 → 150 条通过 (30.0%)
   - 耗时: 12.3s

────────────────────────────────────────────────────────────────
💬 Step 3: 读取有效帖子的评论
────────────────────────────────────────────────────────────────
✅ 读取到 1200 条评论（来自 150 个有效帖子）
✅ 构建 150 个帖子+评论嵌套结果

────────────────────────────────────────────────────────────────
💾 Step 4: 写入 session_l3_results
────────────────────────────────────────────────────────────────
  ✅ 已写入 50/150 条...
  ✅ 已写入 100/150 条...
  ✅ 已写入 150/150 条...
✅ 写入完成: 150 条记录

============================================================
✅ Layer-3 语义过滤完成
============================================================
   - 帖子: 500 → 150 条通过 (30.0%)
   - 评论: 1200 条（来自有效帖子）
   - 总耗时: 15.7s
   - 数据已写入 session_l3_results

📊 查询结果:
   SELECT * FROM session_l2_posts WHERE session_id = 'b78b232c...';
   SELECT * FROM session_l2_comments WHERE session_id = 'b78b232c...';
   SELECT * FROM session_l3_results WHERE session_id = 'b78b232c...';
   SELECT * FROM session_metadata WHERE session_id = 'b78b232c...';
```

---

## 参数对比

### Layer-2 + Layer-3 完整参数

```bash
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江有什么好玩的" \           # 必填：查询描述
  --platform xhs \                        # 可选：平台过滤
  --force-scenario travel \               # 可选：强制场景
  --page-size 200 \                       # 可选：分页大小
  --write-batch-size 50 \                 # 可选：写入批次
  --save-gap-rules \                      # 可选：保存补充规则
  --filter-comments-mode valid-posts-only \  # 可选：评论过滤模式
  --skip-layer3 \                         # 可选：跳过 Layer-3
  --min-relevance medium \                # 可选：Layer-3 相关性阈值
  --no-llm-layer3 \                       # 可选：Layer-3 禁用 LLM
  --dry-run                               # 可选：试运行
```

### 与独立运行 Layer-3 的对比

| 方式 | 命令数 | session_id 处理 | query 传递 | 推荐场景 |
|------|--------|----------------|-----------|---------|
| **自动衔接** | 1 条 | 自动 | 自动 | 常规使用 ✅ |
| **手动运行** | 2 条 | 需复制 | 需重复输入 | 调试/定制 |

**自动衔接**:
```bash
# 一条命令完成
uv run python scripts/batch_scene_filter_smart.py --query "xxx"
```

**手动运行**:
```bash
# Step 1: 执行 Layer-2
uv run python scripts/batch_scene_filter_smart.py --query "xxx" --skip-layer3
# 输出: Session ID: abc-123

# Step 2: 手动复制 session_id，执行 Layer-3
uv run python scripts/batch_llm_filter.py --session-id abc-123 --query "xxx"
```

---

## 使用场景示例

### 场景 1: 日常使用（推荐）

```bash
# 完整过滤流程，默认参数
uv run python scripts/batch_scene_filter_smart.py \
  --query "丽江有什么好玩的"
```

**适用**: 
- 日常数据处理
- 不需要中间检查
- 使用默认相关性阈值（medium）

### 场景 2: 高质量筛选

```bash
# 严格相关性要求
uv run python scripts/batch_scene_filter_smart.py \
  --query "成都美食推荐" \
  --min-relevance high
```

**适用**:
- 需要高质量结果
- 宁缺毋滥
- 预期通过率 5-15%

### 场景 3: 快速测试

```bash
# 禁用 Layer-3 的 LLM（快速模式）
uv run python scripts/batch_scene_filter_smart.py \
  --query "北京景点" \
  --no-llm-layer3
```

**适用**:
- 快速预览结果
- 节省 API 调用
- 准确率要求不高

### 场景 4: 调试模式

```bash
# 先执行 Layer-2，检查后再手动运行 Layer-3
uv run python scripts/batch_scene_filter_smart.py \
  --query "西安旅游" \
  --skip-layer3
```

**适用**:
- 调试 Layer-2 逻辑
- 需要检查中间结果
- 想自定义 Layer-3 参数

### 场景 5: Dry-run 测试

```bash
# 不写数据库，仅查看流程
uv run python scripts/batch_scene_filter_smart.py \
  --query "上海美食" \
  --dry-run
```

**适用**:
- 测试流程
- 查看规则匹配情况
- 估算通过率

---

## 技术实现

### 核心函数: `run_layer3_filter()`

**位置**: `scripts/batch_scene_filter_smart.py` 第 774-920 行

**功能**: 在 Layer-2 完成后自动执行 Layer-3 过滤

**流程**:
1. 读取 `session_l2_posts` 表
2. 使用 `RelevanceFilter` 判断相关性
3. 筛选符合阈值的帖子
4. 读取相关帖子的评论
5. 构建帖子+评论嵌套结构
6. 写入 `session_l3_results` 表
7. 更新 `session_metadata`

**特点**:
- ✅ 异步执行（`async def`）
- ✅ 分批处理（避免内存溢出）
- ✅ UPSERT 写入（避免主键冲突）
- ✅ 详细进度输出

---

## 注意事项

### 1. 内存使用

- Layer-3 会一次性读取所有 Layer-2 通过的帖子到内存
- 如果 Layer-2 通过数量很大（>10000），建议：
  - 使用 `--min-relevance high` 提前筛选
  - 或先 `--skip-layer3`，手动分批运行

### 2. LLM 调用限制

- Layer-3 对中间地带帖子会调用 LLM
- 如果帖子数量很多，可能触发 API 限流
- 解决方案：
  - 使用 `--no-llm-layer3` 禁用 LLM
  - 或调整 `--min-relevance` 减少需要判断的帖子

### 3. 执行时间

**估算公式**:
```
总时间 ≈ Layer-2 时间 + Layer-3 时间

Layer-2 ≈ 10-30s (取决于 LLM 响应速度)
Layer-3 ≈ 帖子数 × 0.05s + LLM调用数 × 2s

示例:
- 500 条帖子，150 条中间地带需要 LLM
- Layer-2: 15s
- Layer-3: 500×0.05 + 150×2 = 325s ≈ 5.4分钟
- 总计: ~6分钟
```

---

## 常见问题

### Q1: 如何只运行 Layer-3？

**A**: 使用独立的 `batch_llm_filter.py` 脚本：

```bash
uv run python scripts/batch_llm_filter.py \
  --session-id <session_id> \
  --query "xxx"
```

### Q2: 如何修改已完成的 Layer-2 结果的相关性阈值？

**A**: 重新运行 Layer-3，会自动 UPSERT：

```bash
# 第一次：medium
uv run python scripts/batch_scene_filter_smart.py --query "xxx" --min-relevance medium

# 想改成 high，重新运行（会覆盖）
uv run python scripts/batch_llm_filter.py \
  --session-id <上次的session_id> \
  --query "xxx" \
  --min-relevance high \
  --clear-existing
```

### Q3: 自动衔接会增加多少时间？

**A**: 
- Layer-3 时间 = 帖子数 × 0.05s + LLM调用数 × 2s
- 示例：500 条帖子，约 30s - 5分钟（取决于 LLM 调用数）

### Q4: 可以中途取消吗？

**A**: 
- 可以 Ctrl+C 中断
- Layer-2 已完成的数据不会丢失
- 可以稍后手动运行 Layer-3

---

## 总结

| 特性 | 说明 |
|------|------|
| **自动化** | 一键完成 Layer-2 + Layer-3 |
| **灵活性** | 可选跳过 Layer-3 |
| **可定制** | 支持自定义相关性阈值 |
| **幂等性** | 使用 UPSERT，可重复运行 |
| **性能** | 支持快速模式（禁用 LLM） |

**推荐使用方式**:
```bash
# 日常使用（推荐）
uv run python scripts/batch_scene_filter_smart.py --query "xxx"

# 高质量筛选
uv run python scripts/batch_scene_filter_smart.py --query "xxx" --min-relevance high

# 快速测试
uv run python scripts/batch_scene_filter_smart.py --query "xxx" --no-llm-layer3
```

---

**更新日期**: 2026年4月8日  
**版本**: v1.0  
**状态**: ✅ 已实现并测试
