# WorkFlow - 智能工作流引擎平台

基于 LangGraph 的现代化工作流引擎平台，支持可视化编辑、AI 对话生成、智能体编排和实时监控。

## 项目简介

WorkFlow 是一个功能完整的工作流自动化平台，让用户通过可视化界面或自然语言对话创建和执行复杂的工作流。平台集成了多种智能体节点，支持数据收集、情感分析、报告生成等常见业务场景。

### 核心功能

- **可视化工作流编辑器**：拖拽式节点编辑、贝塞尔曲线连线、实时预览
- **AI 对话式工作流生成**：通过自然语言描述自动生成工作流
- **多种节点类型**：Start、End、LLM、Code、Condition、Loop、智能体节点
- **智能体节点系统**：数据收集、情感分析、报告生成、信息过滤
- **多执行引擎支持**：LangGraph（默认）、CrewAI
- **数据持久化**：PostgreSQL 数据库集成
- **实时执行监控**：节点状态追踪、执行日志、统计报告

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+（前端开发）
- PostgreSQL（可选，用于数据持久化）

### 安装步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd WorkFlow

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r workflow_engine/requirements.txt

# 4. 配置环境变量
cp workflow_engine/.env.example workflow_engine/.env
# 编辑 .env 文件，配置 API 密钥和数据库连接
```

### 启动服务

```bash
# 启动后端 API 服务
cd workflow_engine
python3 -m uvicorn api.server:app --host 0.0.0.0 --port 8123 --reload

# 启动前端开发服务器（新终端）
cd workflow_engine/frontend
npm install
npm run dev
```

### 验证安装

```bash
# 健康检查
curl http://localhost:8123/health
# 期望返回: {"status":"ok"}

# 测试规划智能体
python workflow_engine/main.py --plan "生成一个舆情分析工作流"
```

## 项目结构

```
WorkFlow/
├── workflow_engine/           # 核心引擎代码
│   ├── src/                   # 源代码
│   │   ├── core/              # 核心模块（schema, builder）
│   │   ├── nodes/             # 节点实现
│   │   ├── agents/            # 智能体模块
│   │   ├── services/          # 业务服务
│   │   ├── database/          # 数据库模型
│   │   └── utils/             # 工具函数
│   ├── api/                   # FastAPI 接口
│   ├── frontend/              # Vue.js 前端
│   ├── test/                  # 测试文件
│   └── main.py                # CLI 入口
├── tests/                     # 项目级测试
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   └── e2e/                   # 端到端测试
├── test_data/                 # 测试数据
│   ├── public_opinion_workflow.json
│   └── advanced_workflow.json
├── logs/                      # 日志文件
├── pytest.ini                 # pytest 配置
└── README.md                  # 项目说明
```

## 技术栈

### 后端

- **Python 3.11+**：主要开发语言
- **FastAPI**：高性能 Web 框架
- **LangGraph**：工作流编排引擎
- **LangChain**：LLM 应用框架
- **SQLAlchemy**：ORM 框架
- **PostgreSQL**：数据持久化
- **Pydantic**：数据验证

### 前端

- **Vue.js 3**：渐进式前端框架
- **Vite**：构建工具
- **TypeScript**：类型安全
- **Pinia**：状态管理

### AI/LLM

- **DeepSeek API**：大语言模型服务
- **OpenAI API 兼容**：支持多种 LLM 提供商

## 节点类型

### 基础节点

| 节点类型 | 描述 | 用途 |
|---------|------|------|
| Start | 开始节点 | 工作流入口 |
| End | 结束节点 | 工作流出口 |
| LLM | 大语言模型节点 | 文本生成、分析 |
| Code | 代码节点 | 执行 Python 代码 |
| Condition | 条件节点 | 条件分支判断 |
| Loop | 循环节点 | 循环迭代处理 |

### 智能体节点

| 节点类型 | 描述 | 主要功能 |
|---------|------|---------|
| DataCollectionAgent | 数据收集智能体 | 多源数据收集、搜索、汇总 |
| FilterAgent | 信息过滤智能体 | 数据过滤、去重、质量评分 |
| SentimentAgent | 情感分析智能体 | 情感倾向分析、关键词提取 |
| ReportAgent | 报告生成智能体 | 报告生成、模板渲染 |

## API 接口

### 工作流管理

```http
# 生成工作流
POST /api/v1/workflows/generate
Body: { "intent": "创建一个舆情分析工作流" }

# 执行工作流
POST /api/v1/workflows/execute
Body: { "workflow_id": "xxx", "engine": "langgraph" }

# 获取工作流列表
GET /api/v1/workflows

# 保存工作流
PUT /api/v1/workflows/{workflow_id}

# 删除工作流
DELETE /api/v1/workflows/{workflow_id}
```

### AI 对话

```http
# 开始对话生成工作流
POST /api/v1/conversations/start
Body: { "user_intent": "创建一个舆情分析工作流" }

# 继续对话调整工作流
POST /api/v1/conversations/continue
Body: { "workflow_id": "xxx", "user_message": "添加一个过滤节点" }

# 获取对话历史
GET /api/v1/conversations/{workflow_id}/history
```

### 智能体模板

```http
# 获取智能体模板列表
GET /api/v1/agents/templates

# 生成舆情分析工作流
POST /api/v1/workflows/generate-public-opinion
Body: { "topic": "某品牌用户评价分析" }
```

## 工作流示例

### 简单 LLM 工作流

```json
{
  "name": "文本总结工作流",
  "nodes": [
    { "id": "start", "type": "Start" },
    { "id": "llm", "type": "LLM", "config": { "params": { "prompt": "总结：{{input}}" } } },
    { "id": "end", "type": "End" }
  ],
  "edges": [
    { "source": "start", "target": "llm" },
    { "source": "llm", "target": "end" }
  ]
}
```

### 舆情分析工作流

```json
{
  "name": "舆情分析工作流",
  "nodes": [
    { "id": "start", "type": "Start" },
    { "id": "collector", "type": "DataCollectionAgent", 
      "config": { "params": { "topic": "AI发展趋势", "sources": ["internet"] } } },
    { "id": "filter", "type": "FilterAgent",
      "config": { "params": { "data": "$collector", "filters": { "min_confidence": 0.6 } } } },
    { "id": "sentiment", "type": "SentimentAgent",
      "config": { "params": { "data": "$filter" } } },
    { "id": "report", "type": "ReportAgent",
      "config": { "params": { "report_type": "sentiment_analysis" } } },
    { "id": "end", "type": "End" }
  ],
  "edges": [
    { "source": "start", "target": "collector" },
    { "source": "collector", "target": "filter" },
    { "source": "filter", "target": "sentiment" },
    { "source": "sentiment", "target": "report" },
    { "source": "report", "target": "end" }
  ]
}
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit -v

# 运行集成测试
pytest tests/integration -v

# 运行端到端测试
pytest tests/e2e -v

# 生成覆盖率报告
pytest --cov=workflow_engine --cov-report=html
```

### 测试结构

```
tests/
├── unit/              # 单元测试
│   ├── test_llm_node.py
│   ├── test_workflow_state.py
│   └── ...
├── integration/       # 集成测试
│   ├── test_integration.py
│   ├── test_api_direct.py
│   └── ...
└── e2e/               # 端到端测试
    ├── test_frontend_backend.py
    └── ...
```

## 配置说明

### 环境变量

```bash
# .env 文件配置示例

# LLM 配置
OPENAI_API_KEY=sk-xxxxx
OPENAI_API_BASE=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/workflow

# 服务配置
API_HOST=0.0.0.0
API_PORT=8123
```

## 开发指南

### 添加新节点类型

1. 在 `workflow_engine/src/nodes/` 创建节点文件
2. 继承 `BaseNode` 基类
3. 实现 `execute()` 方法
4. 在 `__init__.py` 中注册节点
5. 在 `builder.py` 中添加节点映射

### 扩展智能体

1. 在 `workflow_engine/src/agents/` 创建智能体模块
2. 实现智能体业务逻辑
3. 创建对应的智能体节点类
4. 添加 API 端点支持

## 相关文档

- [工作流标准格式](工作流标准格式.md) - 工作流 JSON 配置规范
- [条件节点分支连线说明](条件节点分支连线功能说明.md) - 条件分支功能详解
- [改进记录](IMPROVEMENTS.md) - 历史改进和优化记录
- [Playwright 测试配置](PLAYWRIGHT_SETUP.md) - E2E 测试配置指南
- [手动测试指南](MANUAL_TEST_GUIDE.md) - 功能测试手册

## 许可证

MIT License

## 贡献指南

欢迎提交 Issue 和 Pull Request。请确保：

1. 代码遵循项目风格规范
2. 新功能包含相应测试
3. 文档保持同步更新