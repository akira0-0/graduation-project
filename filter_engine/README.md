# 过滤引擎 v2

简化版规则过滤引擎，支持规则过滤 + LLM语义过滤 + 协同决策。

## 目录结构

```
filter_engine_v2/
├── config.py          # 配置 (30行)
├── main.py            # CLI入口
├── api.py             # FastAPI接口 + 前端
├── pipeline.py        # 过滤管道
├── __init__.py
├── requirements.txt
│
├── core/              # 核心引擎
│   ├── rule_engine.py   # 规则引擎 (AC自动机+正则)
│   ├── llm_engine.py    # LLM引擎
│   └── decision.py      # 协同决策
│
├── rules/             # 规则管理
│   ├── models.py        # 数据模型
│   └── manager.py       # CRUD操作
│
└── data/
    ├── schema.sql       # 数据库结构
    ├── rules.db         # SQLite数据库
    └── output/          # 过滤结果
```

## 快速开始

### 1. 安装依赖

```bash
cd filter_engine_v2
pip install -r requirements.txt
```

### 2. 启动API服务

```bash
# 方式1: 使用CLI
python -m filter_engine_v2.main serve --port 8081

# 方式2: 直接运行
cd e:\xhs-crawler
uv run uvicorn filter_engine_v2.api:app --port 8081
```

访问 http://localhost:8081 可以看到管理界面。

### 3. CLI使用

```bash
# 查看规则
python -m filter_engine_v2.main rules list

# 添加规则
python -m filter_engine_v2.main rules add --name test --type keyword --content "广告,推广" --category ad

# 过滤文本
python -m filter_engine_v2.main filter -t "加微信领取免费资料"

# 过滤JSON文件
python -m filter_engine_v2.main filter -f data.json --field content -o result.json
```

### 4. Python调用

```python
from filter_engine_v2 import FilterPipeline, RuleManager

# 过滤文本
pipeline = FilterPipeline(use_llm=False)
result = pipeline.filter_text("加微信领取免费资料")
print(result.is_spam)  # True
print(result.matched_rules)  # ['spam_keywords']

# 批量过滤
items = [
    {"id": "1", "content": "正常内容"},
    {"id": "2", "content": "加微信领取资料"},
]
results = pipeline.filter_and_split(items)
print(f"正常: {len(results['clean'])}, 垃圾: {len(results['spam'])}")

# 规则管理
manager = RuleManager()
rules = manager.list()
```

## API接口

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/rules` | 获取规则列表 |
| GET | `/api/rules/{id}` | 获取单条规则 |
| POST | `/api/rules` | 创建规则 |
| PUT | `/api/rules/{id}` | 更新规则 |
| DELETE | `/api/rules/{id}` | 删除规则 |
| PUT | `/api/rules/{id}/toggle` | 切换启用状态 |
| GET | `/api/rules/{id}/versions` | 版本历史 |
| POST | `/api/rules/{id}/rollback/{version}` | 版本回滚 |
| GET | `/api/rules/export` | 导出规则 |
| POST | `/api/rules/import` | 导入规则 |
| POST | `/api/filter` | 过滤单条文本 |
| POST | `/api/filter/batch` | 批量过滤 |

## 配置

通过环境变量或 `.env` 文件配置：

```env
# LLM配置
LLM_PROVIDER=qwen
LLM_API_KEY=your_api_key
LLM_MODEL=qwen-turbo

# 协同决策权重
RULE_WEIGHT=0.6
LLM_WEIGHT=0.4
CONFIDENCE_THRESHOLD=0.7
```

## 对比旧版

| 项目 | 旧版 (filter_engine) | 新版 (filter_engine_v2) |
|------|---------------------|------------------------|
| 配置文件 | 206行 | **30行** |
| 数据库表 | 6张 | **2张** |
| 目录结构 | 复杂 | **精简** |
| API接口 | 无 | **完整CRUD** |
| 前端界面 | 无 | **内置** |
| 核心功能 | 相同 | 相同 |
