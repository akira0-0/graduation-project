# 信息过滤智能体接口文档

## 一、概述

**模块路径**: `workflow_engine/src/agents/filter_agent.py`

**类名**: `FilterAgent`

**功能描述**: 信息过滤智能体，支持多种过滤策略（关键词过滤、质量评分、去重、时间范围等），集成数据存储服务，支持从数据库读取和保存过滤结果。

---

## 二、初始化接口

### `__init__`

```python
def __init__(self, workflow_id: str, auto_save: bool = True)
```

**参数说明**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `workflow_id` | `str` | 是 | - | 工作流 ID，用于数据库关联和审计 |
| `auto_save` | `bool` | 否 | `True` | 是否自动保存过滤结果到数据库 |

**示例**:
```python
# 初始化智能体（自动保存到数据库）
agent = FilterAgent(workflow_id="wf_12345")

# 初始化智能体（不自动保存）
agent = FilterAgent(workflow_id="wf_12345", auto_save=False)
```

---

## 三、核心方法

### 3.1 `filter_data` - 过滤数据（主方法）

```python
def filter_data(
    self,
    data: List[Dict[str, Any]],
    filter_criteria: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**功能**: 对数据列表执行多维度过滤

#### 输入参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `data` | `List[Dict[str, Any]]` | 是 | 待过滤的数据列表 |
| `filter_criteria` | `Dict[str, Any]` | 否 | 过滤条件配置 |

#### `filter_criteria` 过滤条件结构

```json
{
    "keywords": ["关键词1", "关键词2"],
    "exclude_keywords": ["排除词1", "排除词2"],
    "min_length": 10,
    "max_length": 10000,
    "min_confidence": 0.5,
    "exclude_duplicates": true,
    "time_range": {
        "start": "2026-01-01T00:00:00",
        "end": "2026-12-31T23:59:59"
    },
    "sort_by": "timestamp",
    "sort_reverse": true,
    "limit": 100,
    "quality_threshold": 0.5
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keywords` | `List[str]` | `[]` | 必须包含的关键词列表（OR 关系，匹配任一即保留） |
| `exclude_keywords` | `List[str]` | `[]` | 需要排除的关键词列表（包含任一则过滤） |
| `min_length` | `int` | `0` | 最小内容长度 |
| `max_length` | `int` | `∞` | 最大内容长度 |
| `min_confidence` | `float` | `0.0` | 最小置信度阈值 (0.0-1.0) |
| `exclude_duplicates` | `bool` | `True` | 是否去重（基于 content 字段 MD5） |
| `time_range` | `Dict` | `{}` | 时间范围过滤 |
| `time_range.start` | `str` | - | 开始时间 (ISO 格式) |
| `time_range.end` | `str` | - | 结束时间 (ISO 格式) |
| `sort_by` | `str` | `"timestamp"` | 排序字段 |
| `sort_reverse` | `bool` | `True` | 是否倒序排序 |
| `limit` | `int` | `None` | 结果数量限制 |
| `quality_threshold` | `float` | `0.0` | 质量评分阈值 (0.0-1.0) |

#### 返回值结构

```json
{
    "filtered_data": [...],
    "filtered_count": 45,
    "original_count": 100,
    "filter_criteria": {...},
    "filter_stats": {
        "original_count": 100,
        "filter_steps": [
            {
                "step": "deduplicate",
                "input_count": 100,
                "output_count": 85,
                "removed_count": 15
            },
            {
                "step": "keyword_filter",
                "input_count": 85,
                "output_count": 60,
                "matched_keywords": {"关键词": 30, "匹配数": 25},
                "excluded_count": 10
            },
            {
                "step": "length_filter",
                "input_count": 60,
                "output_count": 55,
                "too_short": 3,
                "too_long": 2
            },
            {
                "step": "time_filter",
                "input_count": 55,
                "output_count": 50,
                "out_of_range": 5
            },
            {
                "step": "confidence_filter",
                "input_count": 50,
                "output_count": 48,
                "below_threshold": 2
            },
            {
                "step": "quality_filter",
                "input_count": 48,
                "output_count": 45,
                "low_quality": 3
            },
            {
                "step": "limit",
                "input_count": 45,
                "output_count": 45,
                "removed_count": 0
            }
        ]
    },
    "extra_data": {
        "workflow_id": "wf_12345",
        "filtered_at": "2026-04-07T10:30:00",
        "status": "success"
    }
}
```

#### 返回字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `filtered_data` | `List[Dict]` | 过滤后的数据列表 |
| `filtered_count` | `int` | 过滤后数据数量 |
| `original_count` | `int` | 原始数据数量 |
| `filter_criteria` | `Dict` | 实际使用的过滤条件 |
| `filter_stats` | `Dict` | 过滤统计信息 |
| `extra_data` | `Dict` | 附加元数据 |

---

### 3.2 `filter_from_database` - 从数据库读取并过滤

```python
def filter_from_database(
    self,
    filter_criteria: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
    limit: int = 1000
) -> Dict[str, Any]
```

**功能**: 从数据库读取数据并执行过滤

**参数说明**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `filter_criteria` | `Dict` | 否 | `None` | 过滤条件（同 `filter_data`） |
| `source` | `str` | 否 | `None` | 数据来源筛选 |
| `limit` | `int` | 否 | `1000` | 从数据库读取的最大数量 |

**返回值**: 与 `filter_data` 相同

---

### 3.3 `add_filter_rule` - 添加过滤规则

```python
def add_filter_rule(
    self,
    rule_id: str,
    rule_definition: Dict[str, Any]
) -> None
```

**参数说明**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `rule_id` | `str` | 规则唯一标识 |
| `rule_definition` | `Dict` | 规则定义 |

**规则定义格式**:
```json
{
    "rule_id": "custom_rule_1",
    "description": "自定义规则描述",
    "field": "content",
    "condition": "length >= 50",
    "action": "filter"
}
```

---

### 3.4 `get_filter_rules` - 获取过滤规则

```python
def get_filter_rules(self) -> List[Dict[str, Any]]
```

**返回值**: 规则列表

```json
[
    {
        "rule_id": "min_length",
        "description": "最小内容长度规则",
        "field": "content",
        "condition": "length >= 10",
        "action": "filter"
    }
]
```

---

### 3.5 `remove_filter_rule` - 删除过滤规则

```python
def remove_filter_rule(self, rule_id: str) -> bool
```

**返回值**: `True` 删除成功，`False` 规则不存在

---

### 3.6 `get_stored_results` - 获取已存储的过滤结果

```python
def get_stored_results(self, limit: int = 100) -> List[Dict[str, Any]]
```

**参数说明**:

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `limit` | `int` | `100` | 返回的最大数量 |

**返回值**: 过滤结果列表

---

### 3.7 `close` - 关闭数据库连接

```python
def close(self) -> None
```

**功能**: 释放资源，关闭数据库连接

---

## 四、输入数据格式（过滤前）

### 数据结构

```python
data: List[Dict[str, Any]]  # 数据列表，每个元素是一条数据项
```

### 完整数据项格式

```json
[
    {
        "content": "这是一条示例内容文本，用于演示过滤功能。内容应该足够长以通过最小长度检查。",
        "title": "示例标题",
        "source": "微博",
        "timestamp": "2026-04-07T10:30:00",
        "confidence": 0.85,
        "sentiment": "positive",
        "sentiment_score": 0.92,
        "url": "https://example.com/post/123",
        "author": "用户A",
        "metadata": {
            "author": "用户A",
            "likes": 150,
            "shares": 30,
            "comments": 45,
            "verified": true
        }
    },
    {
        "content": "另一条数据内容",
        "title": "另一条标题",
        "source": "知乎",
        "timestamp": "2026-04-07T11:00:00",
        "confidence": 0.75
    }
]
```

### 字段说明

| 字段 | 类型 | 必填 | 用途 |
|------|------|------|------|
| `content` | `str` | **是** | 核心文本内容，用于关键词匹配、去重、长度检查、质量评分 |
| `title` | `str` | 否 | 标题，影响质量评分（+0.1） |
| `source` | `str` | 否 | 数据来源，影响质量评分（+0.1） |
| `timestamp` | `str` | 否 | 时间戳（ISO格式），用于时间范围过滤和排序，影响质量评分（+0.1） |
| `confidence` | `float` | 否 | 置信度（0.0-1.0），用于置信度过滤 |
| `sentiment` | `str` | 否 | 情感标签（如 positive/negative/neutral），影响质量评分（+0.1） |
| `sentiment_score` | `float` | 否 | 情感分数（0.0-1.0），影响质量评分（+0.1） |
| `url` | `str` | 否 | 来源链接 |
| `author` | `str` | 否 | 作者 |
| `metadata` | `Dict` | 否 | 元数据对象，影响质量评分 |

### metadata 子字段说明

| 字段 | 类型 | 用途 |
|------|------|------|
| `author` | `str` | 作者，影响质量评分（+0.1） |
| `likes` | `int` | 点赞数，影响质量评分（+0.1） |
| `shares` | `int` | 分享数，影响质量评分（+0.1） |
| `comments` | `int` | 评论数，影响质量评分（+0.1） |

### 最简数据格式

```json
[
    {"content": "只有内容的简单数据"},
    {"content": "另一条简单数据"}
]
```

---

## 五、输出数据格式（过滤后）

### 数据结构

```python
result: Dict[str, Any]  # 返回结果对象
result["filtered_data"]: List[Dict[str, Any]]  # 过滤后的数据列表
```

### 完整返回结果格式

```json
{
    "filtered_data": [
        {
            "content": "这是一条示例内容文本，用于演示过滤功能。内容应该足够长以通过最小长度检查。",
            "title": "示例标题",
            "source": "微博",
            "timestamp": "2026-04-07T10:30:00",
            "confidence": 0.85,
            "sentiment": "positive",
            "sentiment_score": 0.92,
            "url": "https://example.com/post/123",
            "author": "用户A",
            "metadata": {
                "author": "用户A",
                "likes": 150,
                "shares": 30,
                "comments": 45,
                "verified": true
            },
            "quality_score": 0.9
        }
    ],
    "filtered_count": 1,
    "original_count": 2,
    "filter_criteria": {
        "keywords": [],
        "exclude_keywords": ["广告"],
        "min_length": 0,
        "max_length": 10000,
        "min_confidence": 0.5,
        "exclude_duplicates": true,
        "time_range": {},
        "sort_by": "timestamp",
        "sort_reverse": true,
        "limit": 100,
        "quality_threshold": 0.0
    },
    "filter_stats": {
        "original_count": 2,
        "filter_steps": [
            {
                "step": "deduplicate",
                "input_count": 2,
                "output_count": 2,
                "removed_count": 0
            },
            {
                "step": "keyword_filter",
                "input_count": 2,
                "output_count": 1,
                "matched_keywords": {},
                "excluded_count": 1
            },
            {
                "step": "confidence_filter",
                "input_count": 1,
                "output_count": 1,
                "below_threshold": 0
            }
        ]
    },
    "extra_data": {
        "workflow_id": "wf_12345",
        "filtered_at": "2026-04-07T12:00:00",
        "status": "success"
    }
}
```

### 返回字段详解

| 字段 | 类型 | 说明 |
|------|------|------|
| `filtered_data` | `List[Dict]` | 过滤后的数据列表（保留原始字段 + 可能新增 `quality_score`） |
| `filtered_count` | `int` | 过滤后数据条数 |
| `original_count` | `int` | 原始数据条数 |
| `filter_criteria` | `Dict` | 实际应用的过滤条件 |
| `filter_stats` | `Dict` | 过滤统计详情 |
| `extra_data` | `Dict` | 附加元数据 |

### filtered_data 中数据项的变化

过滤后的数据项会**保留所有原始字段**，仅在启用质量评分过滤时新增：

```json
{
    "quality_score": 0.9  // 当设置 quality_threshold > 0 时新增
}
```

---

## 六、过滤前后对比示例

### 过滤前（输入）

```json
[
    {
        "content": "今天天气真好，适合出门散步",
        "title": "美好的一天",
        "timestamp": "2026-04-07T08:00:00",
        "confidence": 0.9
    },
    {
        "content": "广告推广信息",
        "title": "促销活动",
        "timestamp": "2026-04-07T09:00:00",
        "confidence": 0.8
    },
    {
        "content": "短",
        "timestamp": "2026-04-07T10:00:00",
        "confidence": 0.6
    },
    {
        "content": "今天天气真好，适合出门散步",
        "title": "重复内容",
        "timestamp": "2026-04-07T11:00:00",
        "confidence": 0.7
    }
]
```

### 过滤条件

```json
{
    "exclude_keywords": ["广告", "推广"],
    "min_length": 5,
    "exclude_duplicates": true,
    "min_confidence": 0.7,
    "sort_by": "timestamp"
}
```

### 过滤后（输出）

```json
{
    "filtered_data": [
        {
            "content": "今天天气真好，适合出门散步",
            "title": "美好的一天",
            "timestamp": "2026-04-07T08:00:00",
            "confidence": 0.9
        }
    ],
    "filtered_count": 1,
    "original_count": 4,
    "filter_criteria": {
        "exclude_keywords": ["广告", "推广"],
        "min_length": 5,
        "exclude_duplicates": true,
        "min_confidence": 0.7,
        "sort_by": "timestamp"
    },
    "filter_stats": {
        "original_count": 4,
        "filter_steps": [
            {"step": "deduplicate", "input_count": 4, "output_count": 3, "removed_count": 1},
            {"step": "keyword_filter", "input_count": 3, "output_count": 2, "excluded_count": 1},
            {"step": "length_filter", "input_count": 2, "output_count": 2, "too_short": 0, "too_long": 0},
            {"step": "confidence_filter", "input_count": 2, "output_count": 1, "below_threshold": 1}
        ]
    },
    "extra_data": {
        "workflow_id": "wf_12345",
        "filtered_at": "2026-04-07T12:00:00",
        "status": "success"
    }
}
```

### 过滤过程说明

| 步骤 | 输入 | 输出 | 被过滤原因 |
|------|------|------|------------|
| 原始数据 | 4条 | - | - |
| 去重 | 4条 | 3条 | 第4条与第1条内容重复 |
| 关键词过滤 | 3条 | 2条 | 第2条包含"广告推广" |
| 长度过滤 | 2条 | 2条 | 无 |
| 置信度过滤 | 2条 | 1条 | 第3条 confidence=0.6 < 0.7 |

---

## 七、字段在过滤中的作用

| 过滤类型 | 使用的字段 | 说明 |
|----------|------------|------|
| **关键词过滤** | `content` | 在 content 中搜索关键词 |
| **去重** | `content` | 基于 content 的 MD5 哈希去重 |
| **长度过滤** | `content` | 检查 content 的字符长度 |
| **时间过滤** | `timestamp` | 检查是否在时间范围内 |
| **置信度过滤** | `confidence` | 检查 confidence 是否达标 |
| **质量评分** | `content`, `title`, `source`, `timestamp`, `sentiment`, `sentiment_score`, `metadata` | 综合计算质量分数 |
| **排序** | `sort_by` 指定的字段 | 支持任意字段排序 |

---

## 八、质量评分算法

质量评分用于 `_filter_by_quality` 方法，计算每条数据的质量分数（0.0-1.0）：

| 评分维度 | 权重 | 评分规则 |
|----------|------|----------|
| 内容长度 | 30% | ≥50字: 0.3分, ≥20字: 0.2分, ≥10字: 0.1分 |
| 信息完整性 | 30% | 有 title: +0.1, 有 source: +0.1, 有 timestamp: +0.1 |
| 情感丰富度 | 20% | 有 sentiment: +0.1, 有 sentiment_score: +0.1 |
| 元数据完整性 | 20% | metadata.author: +0.1, metadata.likes/shares/comments: +0.1 |

---

## 九、默认过滤规则

初始化时自动创建以下默认规则：

| rule_id | description | condition |
|---------|-------------|-----------|
| `min_length` | 最小内容长度规则 | length >= 10 |
| `max_length` | 最大内容长度规则 | length <= 10000 |
| `exclude_duplicates` | 去重规则 | unique |
| `exclude_keywords` | 排除关键词规则 | 包含 ["广告", "推广", "营销", "advertisement", "spam"] 时过滤 |

---

## 十、使用示例

```python
from workflow_engine.src.agents.filter_agent import FilterAgent

# 初始化
agent = FilterAgent(workflow_id="wf_12345")

# 准备数据
data = [
    {
        "content": "这是一条正常内容，内容足够长",
        "title": "正常标题",
        "timestamp": "2026-04-07T10:00:00",
        "confidence": 0.9
    },
    {
        "content": "广告推广内容",
        "title": "促销活动",
        "timestamp": "2026-04-07T11:00:00",
        "confidence": 0.8
    },
    {
        "content": "短",
        "timestamp": "2026-04-07T12:00:00",
        "confidence": 0.6
    }
]

# 执行过滤
result = agent.filter_data(
    data=data,
    filter_criteria={
        "exclude_duplicates": True,
        "min_length": 5,
        "exclude_keywords": ["广告", "推广"],
        "min_confidence": 0.7,
        "sort_by": "timestamp",
        "limit": 100
    }
)

# 获取结果
filtered_data = result["filtered_data"]
print(f"过滤完成: {result['original_count']} -> {result['filtered_count']}")
print(f"过滤详情: {result['filter_stats']}")

# 关闭连接
agent.close()
```

---

## 十一、错误处理

| 场景 | 返回状态 | 说明 |
|------|----------|------|
| 正常执行 | `extra_data.status: "success"` | 过滤成功 |
| 无输入数据 | `filtered_data: []` | 返回空结果 |
| 数据格式错误 | 跳过错误项 | 记录警告日志 |
| 时间解析失败 | 保留数据 | 无法解析时跳过时间过滤 |

---

## 十二、注意事项

1. **必填字段**: 只有 `content` 是必填的，其他字段均为可选
2. **字段保留**: 过滤后会保留所有原始字段，不会删除任何数据
3. **新增字段**: 仅在启用质量评分过滤（`quality_threshold > 0`）时，会新增 `quality_score` 字段
4. **空值处理**: 时间解析失败时会保留数据，置信度默认为 1.0
5. **数据类型**: 输入输出都是 `List[Dict]`，可以直接序列化为 JSON

---

## 十三、依赖服务

- **数据库服务**: `DataStorageService` - 存储过滤结果
- **记忆服务**: `AgentMemoryService` - 管理过滤规则
- **日志服务**: `get_logger("filter_agent")` - 日志记录