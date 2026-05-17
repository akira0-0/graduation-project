# 三层过滤系统完整文档

## 📖 目录

1. [系统概述](#系统概述)
2. [架构设计](#架构设计)
3. [快速开始](#快速开始)
4. [三层过滤详解](#三层过滤详解)
5. [API 接口](#api-接口)
6. [数据格式规范](#数据格式规范)
7. [配置说明](#配置说明)
8. [性能优化](#性能优化)
9. [常见问题](#常见问题)

---

## 系统概述

### 简介

三层过滤系统是一个基于**规则引擎 + 大语言模型**的智能内容过滤框架，用于从社交媒体爬取的海量数据中筛选出高质量、高相关性的内容。

### 核心特性

- ✅ **三层渐进式过滤**：基础规则 → 场景智能 → 语义相关性
- ✅ **AC自动机加速**：关键词匹配时间复杂度 O(n+z)
- ✅ **LLM智能补充**：动态生成规则，填补规则库缺口
- ✅ **场景自动识别**：7大场景（旅游/电商/社交/财经/医疗/教育/新闻）
- ✅ **协同决策引擎**：规则与LLM加权融合，提高准确率
- ✅ **统一数据格式**：跨平台数据标准化（小红书/微博）

### 技术栈

| 组件 | 技术选型 |
|------|---------|
| 规则引擎 | AC自动机（pyahocorasick）+ 预编译正则 |
| LLM服务 | DeepSeek / Qwen API |
| 数据库 | Supabase（PostgreSQL） |
| 后端框架 | FastAPI |
| 前端框架 | React 19 + TypeScript + Vite |
| 包管理 | uv |

---

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    数据采集层                                │
│  ┌──────────────┐              ┌──────────────┐             │
│  │ 小红书爬虫    │              │  微博爬虫     │             │
│  │ (CDP模式)    │              │ (HTTP请求)   │             │
│  └──────┬───────┘              └──────┬───────┘             │
└─────────┼──────────────────────────────┼─────────────────────┘
          │                              │
          ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Supabase (PostgreSQL 云数据库)                  │
│  posts / comments / filtered_posts / filtered_comments      │
│  session_l2_* / session_l3_results / session_metadata       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   三层过滤引擎 (端口 8081)                    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer-1: 基础规则过滤 (RuleEngine)                  │    │
│  │ • AC自动机 + 预编译正则                             │    │
│  │ • 8条通用规则（涉黄/涉政/广告/垃圾）                 │    │
│  │ • 匹配字段: title + content + tags                 │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │ 通过数据                                │
│                   ▼                                         │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer-2: 场景智能匹配 (SmartRuleMatcher)            │    │
│  │ • 场景识别 (QueryAnalyzer + LLM)                   │    │
│  │ • 39条场景规则动态加载                              │    │
│  │ • LLM四步思维链 (意图→规则→缺口→生成)              │    │
│  │ • filter/select 协同决策                           │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │ 通过数据                                │
│                   ▼                                         │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Layer-3: 语义相关性过滤 (RelevanceFilter)           │    │
│  │ • LLM相关性打分 (0-1)                              │    │
│  │ • 匹配字段: title + content (不含tags)             │    │
│  │ • 四级分类: high/medium/low/irrelevant            │    │
│  └────────────────┬───────────────────────────────────┘    │
└───────────────────┼─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                 前端可视化 (端口 5174)                        │
│  Page1: 查询配置 │ Page2: 思维链展示 │ Page3: 结果列表      │
│  RulesPanel: 规则管理 (增删查改)                             │
└─────────────────────────────────────────────────────────────┘
```

### 数据流转

```
原始爬虫数据 (posts/comments)
        │
        ▼
    Layer-1 过滤 (batch_filter.py)
        │ 通用规则
        ▼
   filtered_posts / filtered_comments
        │
        ▼
    Layer-2 过滤 (batch_scene_filter_smart.py)
        │ 场景规则 + LLM缺口规则
        ▼
   session_l2_posts / session_l2_comments
        │
        ▼
    Layer-3 过滤 (batch_llm_filter.py)
        │ LLM相关性打分
        ▼
   session_l3_results (最终结果)
```

---

## 快速开始

### 环境准备

```bash
# 1. Python 版本要求
Python 3.11 - 3.12 (推荐 3.11)

# 2. 安装 uv 包管理器
pip install uv

# 3. 安装依赖
cd xhs-crawler
uv sync

# 4. 配置 LLM API
# 在 filter_engine/ 目录创建 .env 文件
FILTER_LLM_PROVIDER=qwen
FILTER_LLM_API_KEY=your_api_key
FILTER_LLM_MODEL=qwen-plus
```

### 启动服务

```bash
# 启动过滤引擎服务（端口 8081）
cd filter_engine
uv run python api.py

# 启动爬虫服务（端口 8080，可选）
cd ..
uv run python api.py

# 启动前端服务（端口 5174，可选）
cd filter_engine/web/app
npm run dev
```

### 一键过滤示例

```bash
# 三层完整流水线
curl -X POST "http://localhost:8081/api/filter/three-layer" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "丽江旅游攻略",
    "contents": [
      "丽江古城深度游攻略，推荐这几个必去景点...",
      "加微信xxx，低价代购旅游套餐！",
      "今天天气真好，心情不错"
    ],
    "enable_layer1": true,
    "enable_layer2": true,
    "enable_layer3": true,
    "min_relevance": "medium"
  }'
```

---

## 三层过滤详解

### Layer-1: 基础规则过滤

**核心文件**: `filter_engine/core/rule_engine.py`

**功能**: 过滤明显的垃圾/广告/违禁内容

#### 规则库

| 规则名 | 类型 | 用途 | 示例关键词 |
|--------|------|------|-----------|
| 通用-涉黄词库 | keyword | filter | 色情、裸体、... |
| 通用-涉政词库 | keyword | filter | 政治敏感词 |
| 通用-暴力词库 | keyword | filter | 暴力、血腥、... |
| 通用-广告 | regex | filter | `\d{10,}` (QQ号) |
| 通用-广告-关键词 | keyword | filter | 加微信、私聊、... |
| 通用-垃圾-乱码 | regex | filter | `(.)\1{5,}` (重复字符) |
| 通用-垃圾-系统提示 | keyword | filter | 系统错误、... |
| 通用-质量-有效内容 | regex | select | `[\u4e00-\u9fa5]{4,}` (4字中文) |

#### 匹配算法

**AC自动机**（关键词型规则）:

```
时间复杂度: O(n + z)
n = 文本长度
z = 命中次数

对比朴素匹配: O(n × m × k)
m = 规则数
k = 平均关键词长度
```

**预编译正则**（正则型规则）:

```python
# 初始化时预编译
regex_patterns.append(re.compile(pattern, re.IGNORECASE))

# 匹配时设置超时保护（防止 ReDoS）
REGEX_TIMEOUT = 1.0  # 秒
```

#### 置信度计算公式

**单条规则置信度**:
- 关键词匹配: `c = 1.0` (固定)
- 正则匹配: `c = min(len(matched_text) / 20, 1.0)`

**多规则综合置信度**:

$$\text{confidence} = \min\left(\max_{i} c_i + 0.1 \times \min(|\text{rules}| - 1, 2), 1.0\right)$$

**判定阈值**:
- `τ_spam = 0.7` (垃圾判定阈值)
- `τ_suspicious = 0.4` (疑似阈值，触发LLM复核)

---

### Layer-2: 场景智能匹配

**核心文件**: `filter_engine/llm/smart_matcher.py`

**功能**: 场景识别 + 动态规则选择 + LLM缺口补充

#### 场景分类

| 场景 | 前缀 | 规则数 | 典型关键词 |
|------|------|--------|-----------|
| 旅游 (travel) | `旅游-` | 1 | 景点、攻略、民宿 |
| 电商 (ecommerce) | `电商-` | 7 | 刷单、拼团、私信 |
| 社交 (social) | `社交-` | 5 | 引流、营销、负能量 |
| 财经 (finance) | `财经-` | 6 | 荐股、喊单、虚假承诺 |
| 医疗 (medical) | `医疗-` | 6 | 虚假疗效、伪科学 |
| 教育 (education) | `教育-` | 6 | 焦虑营销、虚假承诺 |
| 新闻 (news) | `新闻-` | 4 | 标题党、谣言、敏感 |
| 通用 (normal) | 无 | 仅用通用规则 | - |

#### LLM 四步思维链 (Chain of Thought)

```
Step 1: 意图提取 + 主题锚定
  输入: 用户 query
  输出: 
    - 核心实体关键词 (如 "丽江")
    - 过滤/保留约束列表
    - 强制生成主题锚定 select 规则

Step 2: 规则匹配
  输入: 场景专属规则库
  方法: 逐条检查 content_keywords 语义覆盖
  输出: matched_rules (已有规则命中列表)

Step 3: 缺口分析
  输入: Step2 未覆盖的约束
  分类:
    a) 词汇缺口 → 生成关键词/正则规则
    b) 语义模糊 → 标记 needs_llm_semantic=true

Step 4: 补充规则生成
  输入: Step3 a类缺口
  要求:
    - 每条规则 5-10 个关键词（宽松覆盖）
    - 使用场景前缀命名
    - 不重复已有关键词
  输出: gap_rules (即时补充规则列表)
```

#### filter / select 协同决策

**决策树**:

```python
if 命中 filter 规则:
    return False  # 拦截（filter 优先级最高）
elif 存在 select 规则:
    if 命中 select 规则:
        return True   # 保留（白名单模式）
    else:
        return False  # 拦截（未在白名单中）
else:
    return True  # 默认通过（无 select 规则，黑名单模式）
```

**用途说明**:
- `filter`: 过滤删除，命中即拦截（垃圾/广告/敏感）
- `select`: 筛选保留，OR 逻辑，任意关键词匹配即通过

---

### Layer-3: 语义相关性过滤

**核心文件**: `filter_engine/core/relevance_filter.py`

**功能**: LLM 深度语义理解，判断内容与 query 的相关性

#### 相关性评分

**混合模式**（关键词 + LLM）:

$$S_{\text{keyword}} = \min\left(0.5 \cdot \mathbf{1}[\text{entity} \in \text{text}] + 0.1 \times \sum_{k} \mathbf{1}[k \in \text{text}], 1.0\right)$$

**LLM 融合**（当 $0.15 \leq S_{kw} < 0.7$ 时）:

$$S_{\text{final}} = 0.7 \times S_{\text{llm}} + 0.3 \times S_{\text{keyword}}$$

**llm_only 模式**:

```
完全依赖 LLM 打分，不进行关键词预筛选
适用场景: 高质量内容筛选、语义复杂场景
```

#### 四级分类

| 分数区间 | 级别 | 说明 |
|----------|------|------|
| S ≥ 0.7 | HIGH | 高度相关，核心内容 |
| 0.4 ≤ S < 0.7 | MEDIUM | 中度相关，有参考价值 |
| 0.15 ≤ S < 0.4 | LOW | 低相关，边缘内容 |
| S < 0.15 | IRRELEVANT | 不相关 |

---

## API 接口

### 1. 三层完整流水线

**端点**: `POST /api/filter/three-layer`

**请求参数**:

```json
{
  "query": "丽江旅游攻略",
  "contents": ["内容1", "内容2", "..."],
  "enable_layer1": true,
  "enable_layer2": true,
  "enable_layer3": true,
  "min_relevance": "medium",
  "llm_only": true,
  "batch_size": 100,
  "max_workers": 3
}
```

**响应格式**:

```json
{
  "session_id": "sess_xxx",
  "query": "丽江旅游攻略",
  "stats": {
    "total_input": 100,
    "layer1_passed": 85,
    "layer2_passed": 42,
    "layer3_passed": 28,
    "final_count": 28
  },
  "results": [
    {
      "index": 0,
      "content": "丽江古城深度游攻略...",
      "relevance_score": 0.92,
      "relevance_level": "high",
      "layers_passed": ["layer1_passed", "layer2_passed", "layer3_passed"]
    }
  ],
  "performance": {
    "layer1": 0.5,
    "layer2": 12.3,
    "layer3": 8.7,
    "total": 21.5
  }
}
```

### 2. Layer-2 智能匹配分析

**端点**: `POST /api/smart-match`

**请求参数**:

```json
{
  "query": "丽江便宜的民宿",
  "scenario": "travel"  // 可选
}
```

**响应格式**:

```json
{
  "detected_scenario": "travel",
  "thought_trace": {
    "step_1_extraction": ["约束1：保留性价比高的民宿 (select)", "..."],
    "step_2_match": ["规则 旅游-xxx [ID:50] 覆盖约束1", "..."],
    "step_3_gap_analysis": ["缺口：无'性价比'相关规则", "..."],
    "step_4_generation": ["生成规则：旅游-性价比-民宿关键词", "..."]
  },
  "matched_rules": [
    {"rule_id": 50, "rule_name": "旅游-xxx", "purpose": "filter"}
  ],
  "gap_rules": [
    {"name": "旅游-性价比-民宿", "type": "keyword", "content": ["性价比", "便宜", "..."], "purpose": "select"}
  ],
  "needs_llm_filter": true
}
```

### 3. 规则管理

**获取规则列表**: `GET /api/rules`

**创建规则**: `POST /api/rules`

```json
{
  "name": "旅游-广告-丽江",
  "type": "keyword",
  "content": "[\"加微信\", \"低价团\", \"代购\"]",
  "category": "ad",
  "purpose": "filter",
  "priority": 50,
  "enabled": true
}
```

**更新规则**: `PUT /api/rules/{rule_id}`

**删除规则**: `DELETE /api/rules/{rule_id}`

**规则测试**: `POST /api/rules/test?rule_id={id}&text={text}`

---

## 数据格式规范

### 帖子数据格式

```json
{
  "id": "唯一标识符",
  "platform": "xhs | weibo",
  "type": "video | image | text",
  "url": "内容链接",
  "title": "标题（可选）",
  "content": "完整文本内容",
  "publish_time": "YYYY-MM-DD HH:MM:SS",
  "author": {
    "id": "作者ID",
    "nickname": "作者昵称",
    "avatar": "头像URL",
    "is_verified": true,
    "ip_location": "IP归属地"
  },
  "media": {
    "images": ["图片URL1", "..."],
    "video_url": "视频URL"
  },
  "metrics": {
    "likes": 1523,
    "collects": 456,
    "comments": 89,
    "shares": 12
  },
  "tags": ["标签1", "标签2"],
  "source_keyword": "搜索关键词",
  "task_id": "任务ID",
  "crawl_time": "爬取时间戳"
}
```

### 评论数据格式

```json
{
  "id": "评论ID",
  "content_id": "所属帖子ID",
  "platform": "xhs | weibo",
  "content": "评论文本",
  "publish_time": "YYYY-MM-DD HH:MM:SS",
  "author": {
    "id": "作者ID",
    "nickname": "作者昵称",
    "ip_location": "IP归属地"
  },
  "metrics": {
    "likes": 12,
    "sub_comments": 3
  },
  "parent_comment_id": "父评论ID（一级评论为null）",
  "root_comment_id": "根评论ID",
  "task_id": "任务ID",
  "crawl_time": "爬取时间戳"
}
```

---

## 配置说明

### 环境变量 (.env)

在 `filter_engine/` 目录创建 `.env` 文件：

```env
# LLM 配置
FILTER_LLM_PROVIDER=qwen           # openai | qwen | glm
FILTER_LLM_API_KEY=your_api_key
FILTER_LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
FILTER_LLM_MODEL=qwen-plus
FILTER_LLM_TIMEOUT=30
FILTER_LLM_MAX_TOKENS=2000

# 决策配置
FILTER_SPAM_THRESHOLD=0.7          # 垃圾判定阈值
FILTER_SUSPICIOUS_THRESHOLD=0.4    # 疑似阈值
FILTER_LLM_WEIGHT=0.6              # LLM权重
FILTER_RULE_WEIGHT=0.4             # 规则权重

# 缓存配置
FILTER_CACHE_ENABLED=true
FILTER_CACHE_MAX_SIZE=1000
FILTER_CACHE_TTL=3600

# API 配置
FILTER_API_HOST=0.0.0.0
FILTER_API_PORT=8081
```

### 数据库配置 (Supabase)

在 `import_with_sdk.py` 或脚本中配置：

```python
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_KEY = "your_anon_key"
```

---

## 性能优化

### 1. 批量处理

```python
# Layer-1: 分批读取
page_size = 1000

# Layer-2: 分批写入
write_batch_size = 50

# Layer-3: 并发处理
batch_size = 100
max_workers = 3
```

### 2. 早停策略

```python
# Layer-1 无数据通过时，直接返回
if layer1_passed == 0:
    return early_stop_response

# Layer-2 无数据通过时，跳过 Layer-3
if layer2_passed == 0:
    return early_stop_response
```

### 3. 缓存优化

```python
# 对相同文本的过滤结果缓存
# TTL: 3600 秒
# 最大条目: 1000
```

### 4. 超时保护

```python
# 正则匹配超时
REGEX_TIMEOUT = 1.0  # 秒

# LLM 调用超时
LLM_TIMEOUT = 30  # 秒
```

---

## 常见问题

### Q1: 如何提高 Layer-2 过滤效果？

**A**: 优化 select 规则的关键词覆盖：

```python
# 不推荐：关键词太少
["便宜"]  # 可能漏掉 "实惠"、"性价比"

# 推荐：关键词覆盖面广
["便宜", "实惠", "性价比", "经济型", "高性价比", "划算", "物美价廉"]
```

### Q2: 如何调整过滤严格程度？

**A**: 调整阈值参数：

```python
# 宽松模式
min_relevance = "low"          # Layer-3 阈值降低
SPAM_THRESHOLD = 0.8           # Layer-1 阈值提高

# 严格模式
min_relevance = "high"         # Layer-3 阈值提高
SPAM_THRESHOLD = 0.6           # Layer-1 阈值降低
```

### Q3: 如何处理规则冲突？

**A**: 系统自动处理优先级：

```
filter 规则 > select 规则 > 默认通过
高 priority > 低 priority
ID 小 > ID 大
```

### Q4: 为什么 Layer-2 通过率很高？

**A**: 检查是否缺少 select 规则：

```python
# 只有 filter 规则 → 黑名单模式 → 默认通过
# 添加 select 规则 → 白名单模式 → 只有命中才通过
```

### Q5: 如何批量运行过滤？

**A**: 使用脚本模式：

```bash
# Layer-1
uv run python scripts/batch_filter.py --data-type all

# Layer-2
uv run python scripts/batch_scene_filter_smart.py \
  --query "过滤广告" --session-id xxx

# Layer-3
uv run python scripts/batch_llm_filter.py \
  --session-id xxx --query "丽江旅游" --min-relevance medium
```

---

## 附录

### 算法公式汇总

| 编号 | 公式 | 说明 |
|------|------|------|
| 1 | $O(n+z)$ | AC自动机时间复杂度 |
| 2 | $\min(\max_i c_i + 0.1 \times \min(n-1, 2), 1.0)$ | 规则置信度 |
| 3 | $w_r \cdot S_r + w_l \cdot S_l$ | 加权融合决策 |
| 4 | $0.7 \times S_{llm} + 0.3 \times S_{kw}$ | 相关性融合 |
| 5 | $\tau_{spam} = 0.7$ | 垃圾判定阈值 |

### 核心文件索引

| 功能 | 文件路径 |
|------|---------|
| 规则引擎 | `filter_engine/core/rule_engine.py` |
| 智能匹配器 | `filter_engine/llm/smart_matcher.py` |
| 相关性过滤 | `filter_engine/core/relevance_filter.py` |
| 协同决策 | `filter_engine/core/decision.py` |
| 场景分析 | `filter_engine/core/query_analyzer.py` |
| LLM 客户端 | `filter_engine/llm/client.py` |
| API 接口 | `filter_engine/api.py` |
| 规则管理 | `filter_engine/rules/manager.py` |

### 数据库表结构

| 表名 | 用途 | TTL |
|------|------|-----|
| `posts` | 爬虫原始帖子 | 永久 |
| `comments` | 爬虫原始评论 | 永久 |
| `filtered_posts` | Layer-1 通过帖子 | 永久 |
| `filtered_comments` | Layer-1 通过评论 | 永久 |
| `session_l2_posts` | Layer-2 通过帖子 | 2小时 |
| `session_l2_comments` | Layer-2 通过评论 | 2小时 |
| `session_l3_results` | Layer-3 最终结果 | 2小时 |
| `session_metadata` | Session 元数据 | 2小时 |

---

## 贡献指南

如需贡献代码或报告问题，请：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交改动 (`git commit -m 'Add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

---

## 许可证

本项目采用 MIT 许可证。

---

**最后更新**: 2026-05-17  
**文档版本**: v2.0
