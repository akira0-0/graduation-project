# Workflow Engine (MVP) 🤖

PyCoze Engine 是一个开源的轻量级工作流引擎，专为复刻 **Coze (扣子)** 的核心体验而设计。它构建在强大的 **LangGraph** 之上，提供了一套灵活的图编排机制，支持通过 JSON DSL 定义复杂工作流，并具备利用 LLM 自动规划工作流的智能特性。

## ✨ 核心特性

*   **🧠 双重编排模式**
    *   **人工编排 (Manual)**: 加载 JSON DSL 文件，精准控制每一个节点和连线。
    *   **AI 自动规划 (Auto-Planning)**: 只要说出你的意图（例如"分析 DeepSeek 的舆情"），内置的 Planner 智能体就能自动生成完整的工作流图。

*   **⚙️ LangGraph 执行引擎**
    *   基于**图编排**的核心引擎，适合需要精细控制状态和条件分支的场景。
    *   原生支持**条件分支**和**循环节点**，完美适配可视化工作流编排。
    *   每个节点状态可追踪，便于调试和监控。
    *   **循环节点增强**: 支持显式分支标识（`loop_body`/`loop_exit`），防止死循环，可配置最大迭代次数。

*   **🔧 统一配置管理**
    *   使用 **Pydantic Settings** 实现统一配置管理，支持环境变量和 `.env` 文件。
    *   集中管理 LLM、数据库、循环、缓存等配置项。
    *   提供全局安全限制（如 `loop_max_iterations`），防止工作流失控。

*   **🔌 灵活的节点生态**
    *   **LLM Node**: 内置 DeepSeek API 支持，使用 Jinja2 模板引擎管理 Prompt。
    *   **Code Node**: 安全的 Python 沙箱环境，支持自定义逻辑，并具备自动依赖注入能力。

*   **🧪 子智能体模拟 (Mock Agents)**
    *   内置了一套 Mock 工具集，可以模拟 **数据收集**、**情感分析**、**数据清洗**、**报告生成** 等业务场景，让你在没有真实数据的情况下也能验证复杂的业务编排逻辑。

*   **🤖 四个专业智能体 (新增)**
    *   **数据收集智能体**: 支持预设工作流（先搜索知识库再收集实时信息），根据需求收集汇总信息。
    *   **情感分析智能体 V2**: 真正的 AI Agent 实现，具备 ReAct 推理循环、工具调用能力（6 个专业工具）、工作记忆和降级策略。
    *   **报告生成智能体**: 采用模板/规则记忆和审计日志，通过既定模板和规则生成专业报告。
    *   **信息过滤智能体**: 预留接口，待后续实现具体过滤逻辑。

*   **🛠️ 智能体工具系统 (V2 新增)**
    *   **情感分析工具集**: 6 个专业工具支持 ReAct Agent 自动选择和调用。
        - `analyze_text_sentiment`: 单条文本情感分析
        - `batch_analyze_sentiment`: 批量情感分析
        - `extract_insights`: 关键洞察提取
        - `predict_trend`: 情感趋势预测
        - `query_domain_knowledge`: 查询领域知识
        - `update_memory`: 更新智能体记忆
    *   **多智能体协作字段**: WorkflowState 新增协作请求队列、响应存储、工作记忆等字段。

*   **💾 对话记忆持久化 (新增)**
    *   基于 PostgreSQL 数据库的对话历史持久化系统，支持不同工作流记忆隔离。
    *   提供 Workflow、Conversation、Memory、AuditLog 四个核心数据表。
    *   支持领域知识、案例模式、模板、规则等多种记忆类型。

*   **🌐 RESTful API (新增)**
    *   提供基于 FastAPI 的 HTTP 接口，支持通过 API 调用生成工作流，便于前端集成。

## 🚀 快速开始

### 1. 环境配置

本项目需要 Python 3.10+ 环境。

```bash
# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r workflow_engine/requirements.txt
```

### 2. API 设置

在 `workflow_engine` 目录下创建 `.env` 文件，配置你的 DeepSeek API Key 和 PostgreSQL 数据库连接：

```env
# LLM 配置 (必需)
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# PostgreSQL 数据库配置 (可选，用于持久化)
DATABASE_URL=postgresql://user:password@localhost:5432/workflow_db

# 循环节点安全配置 (可选)
LOOP_MAX_ITERATIONS=100        # 全局最大迭代次数限制
LOOP_DEFAULT_ITERATIONS=10     # 默认迭代次数

# 缓存配置 (可选)
CACHE_ENABLED=true
CACHE_TTL=3600
```

提示：可以参考 `.env.example` 文件查看完整的配置选项。

### 3. 运行示例

#### 方式 A: 运行现有工作流文件

```bash
python workflow_engine/main.py --file workflow_engine/data/simple_workflow.json
```

#### 方式 B: AI 自动规划 (推荐体验) 🔥

体验 AI 如何帮你设计工作流：

```bash
# 场景：生成一个舆情分析工作流
python workflow_engine/main.py --plan "生成一个工作流，分析主题'DeepSeek'的舆情。首先收集数据，然后过滤数据，接着进行情感分析，最后生成报告。"
```
> 运行成功后，你可以在 `generated_workflow.json` 中查看生成的工作流定义。

#### 方式 C: 启动 API 服务 🌐

启动 HTTP 服务器，对外提供工作流生成接口：

```bash
# 启动服务器 (默认端口 8000)
python workflow_engine/api/server.py
```

调用示例（使用 Python 脚本）：
```bash
python example_client.py
```

或者使用 curl：
```bash
curl -X POST "http://localhost:8000/api/v1/workflows/generate" \
     -H "Content-Type: application/json" \
     -d '{"intent": "分析最近的股市趋势", "model": "deepseek-chat"}'
```

## 📂 项目结构

```text
workflow_engine/
├── .env                 # 配置文件 (API Key)
├── main.py              # 命令行入口
├── README.md            # 项目文档
├── api/                 # HTTP API 服务
│   ├── server.py        # FastAPI 服务器
│   └── models.py        # 数据模型定义
├── data/                # 示例数据
│   └── simple_workflow.json
└── src/                 # 源码目录
    ├── core/            # 核心引擎 (DSL 解析, Graph/Crew 构建)
    ├── nodes/           # 节点实现 (LLM, Code)
    ├── planner/         # 规划智能体 (Intent -> JSON)
    └── tools/           # 工具库 (Mock Agents 实现)
```

## 📊 智能体使用指南

### 使用专业智能体

本引擎提供了四个专业智能体，支持数据库持久化和记忆管理：

#### 1. 数据收集智能体
```python
from src.agents import DataCollectionAgent

# 初始化智能体
agent = DataCollectionAgent(workflow_id="your_workflow_id")

# 执行预设工作流
result = agent.execute_preset_workflow(
    topic="DeepSeek",
    workflow_steps=["knowledge_base_search", "real_time_collection", "data_aggregation"]
)

# 获取收集历史
history = agent.get_collection_history()

# 关闭连接
agent.close()
```

#### 2. 情感分析智能体
```python
from src.agents import SentimentAnalysisAgent

# 初始化智能体
agent = SentimentAnalysisAgent(workflow_id="your_workflow_id")

# 分析情感
result = agent.analyze_sentiment(data=[
    {"content": "DeepSeek is amazing!", "source": "twitter"},
    {"content": "I hate this product.", "source": "reddit"}
])

# 从用户反馈学习
agent.learn_from_case({
    "content": "This is fantastic!",
    "expected_sentiment": "positive"
})

agent.close()
```

#### 3. 报告生成智能体
```python
from src.agents import ReportGenerationAgent

# 初始化智能体
agent = ReportGenerationAgent(workflow_id="your_workflow_id")

# 生成报告
report = agent.generate_report(
    report_type="sentiment_analysis",
    data={"topic": "DeepSeek", "total_analyzed": 100, ...}
)

# 获取审计日志
audit_logs = agent.get_audit_logs(limit=10)

# 添加自定义模板
agent.add_custom_template("my_template", "# {{ title }}\n{{ content }}")

agent.close()
```

#### 4. 信息过滤智能体
```python
from src.agents import FilterAgent

# 初始化智能体
agent = FilterAgent(workflow_id="your_workflow_id")

# 过滤数据（预留接口）
result = agent.filter_data(data=[...], filter_criteria={...})

agent.close()
```

### 对话记忆管理

```python
from src.database import get_session, ConversationMemoryService

# 创建服务
db = get_session()
service = ConversationMemoryService(db)

# 创建工作流
workflow = service.create_workflow(
    name="我的工作流",
    description="用于测试",
    definition={"key": "value"}
)

# 保存对话
conversation = service.save_conversation(
    workflow_id=workflow.id,
    user_message="用户输入",
    assistant_response="助手响应"
)

# 获取对话历史
history = service.get_conversation_history(workflow_id)

db.close()
```

## 🧪 测试指南

运行完整的功能测试：

```bash
# 运行所有智能体测试
python workflow_engine/test/test_agents.py
```

测试脚本会自动：
1. 测试数据库连接
2. 测试对话记忆服务
3. 测试数据收集智能体
4. 测试情感分析智能体
5. 测试报告生成智能体
6. 测试信息过滤智能体
7. 测试记忆服务

测试结果会显示在终端，并汇总通过/失败情况。

## 🧩 扩展指南

### 如何添加新的 Mock 工具？

1.  打开 `src/tools/mock_tools.py`。
2.  定义一个新的 Python 函数，例如 `def mock_send_email(content): ...`。
3.  在 `src/planner/llm_planner.py` 的 Prompt 中添加该工具的描述。
4.  现在，Planner 就能自动规划使用这个新工具了！

---
*Created with ❤️ by JoyCode Agent*