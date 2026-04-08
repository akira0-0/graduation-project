# 三层过滤快速参考卡

## 一、快速开始

```bash
# 1. 初始化数据库（在 Supabase SQL Editor 手动执行）
database/schema_filtered.sql
database/migrate_add_data_type.sql
database/schema_session.sql

# 2. Layer-1: 全量过滤
uv run python scripts/batch_filter.py --data-type all

# 3. Layer-2: 智能场景过滤（推荐，使用 LLM 思维链分析）
uv run python scripts/batch_scene_filter_smart.py --query "丽江旅游攻略"
# 输出: session_id : a1b2c3d4-e5f6-7890-abcd-1234567890ab

# 3备选. Layer-2: 基础场景过滤（关键词匹配，快速但不智能）
uv run python scripts/batch_scene_filter.py --query "丽江旅游攻略"
# 输出: session_id : sess_20260408_160000_xyz

# 4. Layer-3: 语义过滤
uv run python scripts/batch_llm_filter.py \
  --session-id a1b2c3d4-e5f6-7890-abcd-1234567890ab \
  --query "丽江有什么好玩的景点"
```

---

## 二、命令速查

### Layer-1 (`batch_filter.py`)
```bash
# 基础用法
uv run python scripts/batch_filter.py --data-type all

# 常用参数
--data-type posts|comments|all    # 数据类型
--platform xhs|weibo              # 平台过滤
--min-content-len 10              # 最短内容长度
--threshold 0.7                   # spam 阈值
--dry-run                         # 试运行
```

### Layer-2 智能版 (`batch_scene_filter_smart.py`) 🌟 推荐
```bash
# 基础用法（推荐先 dry-run）
uv run python scripts/batch_scene_filter_smart.py \
  --query "过滤电商平台的广告评论" \
  --dry-run

# 正式运行
uv run python scripts/batch_scene_filter_smart.py \
  --query "过滤电商平台的广告评论"

# 常用参数
--query "查询描述"                       # 必需
--platform xhs|weibo                   # 平台
--force-scenario ecommerce|social|...  # 强制场景
--page-size 200                        # 分页大小
--write-batch-size 50                  # 批量写入（网络慢时减小）
--filter-comments-mode all|valid-posts-only
--save-gap-rules                       # 保存 LLM 生成的规则
--dry-run                              # 试运行

# 典型场景
# 电商广告过滤
uv run python scripts/batch_scene_filter_smart.py \
  --query "过滤电商平台的广告、刷单、引流评论" \
  --platform xhs \
  --save-gap-rules

# 社交高质量筛选
uv run python scripts/batch_scene_filter_smart.py \
  --query "保留真实用户的高质量评论，去掉营销号" \
  --force-scenario social \
  --filter-comments-mode valid-posts-only

# 大数据集快速处理
uv run python scripts/batch_scene_filter_smart.py \
  --query "过滤垃圾内容" \
  --page-size 500 \
  --write-batch-size 100
```

### Layer-2 基础版 (`batch_scene_filter.py`)
```bash
# 基础用法
uv run python scripts/batch_scene_filter.py --query "你的查询"

# 常用参数
--query "查询描述"                 # 必需
--severity relaxed|normal|strict  # 严格度
--platform xhs|weibo              # 平台
--filter-comments-mode all|valid-posts-only
--no-llm                          # 禁用LLM
--no-generate-rules               # 禁止生成规则
--dry-run                         # 试运行
```

### Layer-3 (`batch_llm_filter.py`)
```bash
# 基础用法
uv run python scripts/batch_llm_filter.py \
  --session-id sess_xxx \
  --query "你的语义查询"

# 常用参数
--session-id sess_xxx             # 必需
--query "语义查询"                # 必需
--min-relevance high|medium|low   # 最低相关性
--no-llm                          # 纯关键词
--dry-run                         # 试运行
```

---

## 三、数据表关系

```
原始数据
├── posts
└── comments
    ↓ Layer-1
持久化
├── filtered_posts
└── filtered_comments
    ↓ Layer-2 (按 session_id)
Session临时
├── session_l2_posts
└── session_l2_comments
    ↓ Layer-3
最终结果
└── session_l3_results (帖子+评论嵌套JSON)
```

---

## 四、场景示例

### 场景1: 旅游攻略筛选（智能版）
```bash
# Layer-2 智能场景识别
uv run python scripts/batch_scene_filter_smart.py \
  --query "云南旅游攻略，要去大理和丽江" \
  --platform xhs \
  --save-gap-rules

# Layer-3 语义相关性
uv run python scripts/batch_llm_filter.py \
  --session-id a1b2c3d4-... \
  --query "大理丽江有什么好玩的景点" \
  --min-relevance medium
```

### 场景2: 电商广告过滤（智能版）
```bash
# Layer-2 自动识别电商场景
uv run python scripts/batch_scene_filter_smart.py \
  --query "过滤电商评论中的广告、刷单、引流" \
  --filter-comments-mode valid-posts-only \
  --save-gap-rules

# Layer-3 语义相关性（可选）
uv run python scripts/batch_llm_filter.py \
  --session-id a1b2c3d4-... \
  --query "真实用户评价" \
  --min-relevance high
```

### 场景3: 美食推荐（基础版，快速）
```bash
# Layer-2 关键词匹配
uv run python scripts/batch_scene_filter.py \
  --query "成都美食推荐" \
  --severity normal

# Layer-3 纯关键词（无 LLM，快速）
uv run python scripts/batch_llm_filter.py \
  --session-id sess_xxx \
  --query "成都有什么特色小吃和火锅店" \
  --no-llm
```

---

## 五、Layer-2 版本对比

| 特性 | Smart 版（智能） | 基础版（快速） |
|------|------------------|----------------|
| **场景识别** | LLM 语义理解 | 关键词匹配 |
| **思维链分析** | ✅ 4 步推理 | ❌ 无 |
| **规则匹配** | 语义相关性 | 关键词包含 |
| **缺口补充** | ✅ LLM 生成 | ❌ 无 |
| **准确率** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **速度** | 中等（需 LLM） | 快速 |
| **适用场景** | 复杂意图、新场景 | 已知场景、速度优先 |
| **推荐程度** | 🌟 强烈推荐 | 适合简单任务 |

**选择建议**:
- ✅ 用 Smart 版：复杂查询、需要高准确率、新场景探索
- ✅ 用基础版：简单关键词、速度要求高、规则已完善

---

## 六、SQL 查询示例

### 查看 Session 列表
```sql
SELECT session_id, query_text, 
       l2_passed_posts, l2_passed_comments, l3_passed_posts,
       status, created_at
FROM session_metadata
ORDER BY created_at DESC
LIMIT 10;
```

### 查看最终结果
```sql
-- 查看帖子+评论数量
SELECT session_id, COUNT(*) AS post_count, SUM(comment_count) AS total_comments
FROM session_l3_results
WHERE session_id = 'sess_xxx'
GROUP BY session_id;

-- 提取高相关性帖子
SELECT 
  post_data->>'title' AS title,
  post_data->>'relevance_score' AS score,
  comment_count
FROM session_l3_results
WHERE session_id = 'sess_xxx'
  AND (post_data->>'relevance_score')::numeric > 0.8
ORDER BY (post_data->>'relevance_score')::numeric DESC;
```

### 清理过期数据
```sql
-- 清理 2 小时前的 session
SELECT * FROM cleanup_expired_sessions(2);

-- 手动删除特定 session
DELETE FROM session_l2_posts WHERE session_id = 'sess_xxx';
DELETE FROM session_l2_comments WHERE session_id = 'sess_xxx';
DELETE FROM session_l3_results WHERE session_id = 'sess_xxx';
DELETE FROM session_metadata WHERE session_id = 'sess_xxx';
```

---

## 六、故障排查

### Layer-1 相关问题

#### 问题1: `filtered_posts` 表不存在
```bash
# 在 Supabase SQL Editor 执行
database/schema_filtered.sql
```

#### 问题2: `data_type column not found`
```bash
# 在 Supabase SQL Editor 执行
database/migrate_add_data_type.sql
```

### Layer-2 Smart 版相关问题

#### 问题3: 字段映射错误
```
Could not find the 'author' column of 'session_l2_posts'
```
**已修复**: Smart 版已完全对齐 `schema_session.sql`

#### 问题4: 批量插入超时
```
canceling statement due to statement timeout
```
**解决**: 减小批量大小
```bash
--write-batch-size 20
```

#### 问题5: 主键冲突
```
duplicate key value violates unique constraint
```
**已修复**: Smart 版使用 MD5 哈希生成唯一 ID

#### 问题6: ID 长度超限
```
value too long for type character varying(50)
```
**已修复**: Smart 版哈希缩短到 25 字符

### Layer-3 相关问题

#### 问题7: Session 数据为空
```bash
# 检查 Layer-2 是否成功执行
SELECT * FROM session_metadata WHERE session_id = 'a1b2c3d4-...';

# 检查 Layer-1 数据
SELECT COUNT(*) FROM filtered_posts;
```

#### 问题8: LLM 调用失败
```bash
# 检查环境变量
echo %FILTER_LLM_API_KEY%  # Windows CMD
# 或 PowerShell: $env:FILTER_LLM_API_KEY

# 或使用 --no-llm 纯关键词模式
--no-llm
```

**完整修复文档**:
- `docs/FIELD_MAPPING_FIX.md`
- `docs/BATCH_INSERT_TIMEOUT_FIX.md`
- `docs/PRIMARY_KEY_CONFLICT_FIX.md`

---

## 七、性能建议

| 场景 | 推荐脚本 | 建议参数 | 预期速度 |
|------|---------|---------|---------|
| 快速测试 | 基础版 | `--no-llm --dry-run` | 极快 ⚡ |
| 复杂查询 | **Smart 版** 🌟 | `--save-gap-rules` | 中等 |
| 大数据量 | Smart 版 | `--page-size 500 --write-batch-size 100` | 较快 |
| 网络慢 | Smart 版 | `--write-batch-size 20` | 稳定 |
| 已知场景 | 基础版 | `--severity normal` | 快速 |
| 高精度需求 | Smart 版 | `--force-scenario xxx --min-relevance high` | 较慢但准确 |

---

## 八、关键概念

| 术语 | 说明 |
|------|------|
| **Session** | 一次完整的 Layer-2/3 查询流程，由唯一 `session_id` 标识 |
| **场景识别** | QueryAnalyzer 根据 query 自动识别场景 (电商/旅游/美食等) |
| **规则选择** | RuleSelector 根据场景动态选择适用的规则集合 |
| **相关性分数** | `relevance_score` (0~1)，只有 Layer-3 输出，表示语义相似度 |
| **TTL** | Session 表数据默认 2 小时过期，需定期清理 |

---

## 九、进阶用法

### 自定义规则（在 filter_engine 中）
```python
# 添加新规则到 SQLite rules.db
from filter_engine.rules import RuleManager

manager = RuleManager("filter_engine/data/rules.db")
manager.create({
    "name": "旅游-景点推荐",
    "type": "keyword",
    "content": '["景点", "攻略", "打卡"]',
    "category": "select",
    "purpose": "select",  # select=保留, filter=过滤
    "priority": 70,
})
```

### 批量测试多个 query
```bash
# 创建查询列表文件 queries.txt
丽江旅游攻略
成都美食推荐
北京景点大全

# 循环执行
while read query; do
  echo "Processing: $query"
  uv run python scripts/batch_scene_filter.py --query "$query"
done < queries.txt
```

---

## 十、联系与文档

- **完整文档**: `docs/FILTER_WORKFLOW.md`
- **数据格式**: `docs/DATA_FORMAT_STANDARD.md`
- **使用指南**: `docs/使用指南.md`
- **Filter Engine**: `filter_engine/README.md`
