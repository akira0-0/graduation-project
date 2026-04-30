# 智能体功能改进文档

## 版本 2.5 - 情感分析智能体 V2：真正的 AI Agent 实现 (2026-03-25)

### 🎯 概述

本次更新将情感分析智能体从简单的 LLM 调用器升级为真正的 AI Agent，具备以下核心特性：

1. **ReAct 推理循环**：Thought → Action → Observation → Continue 迭代推理
2. **工具调用能力**：6 个专业情感分析工具，Agent 可自动选择和调用
3. **记忆系统**：短期工作记忆 + 长期知识存储
4. **降级策略**：V2 Agent 失败时自动回退到 V1 实现

---

## ✅ 新增文件

### 1. `workflow_engine/src/tools/sentiment_tools.py` - 情感分析工具集

定义了 6 个可被 Agent 调用的工具：

| 工具名称 | 功能 | 输入 | 输出 |
|---------|------|------|------|
| `analyze_text_sentiment` | 单条文本情感分析 | text, context | 情感标签、置信度、情绪细分 |
| `batch_analyze_sentiment` | 批量情感分析 | texts[] | 分析结果 + 统计汇总 |
| `extract_insights` | 关键洞察提取 | analyzed_data, topic | 主题、痛点、亮点、建议 |
| `predict_trend` | 情感趋势预测 | historical_data[] | 趋势方向、预测、建议 |
| `query_domain_knowledge` | 查询领域知识 | query, workflow_id | 相关知识、案例模式 |
| `update_memory` | 更新智能体记忆 | key, value, memory_type | 操作结果 |

所有工具使用 `@tool` 装饰器定义，符合 LangChain 工具规范。

### 2. `workflow_engine/src/agents/sentiment_agent_v2.py` - ReAct Agent 核心

实现真正的 AI Agent：

```python
class SentimentAgentV2:
    """
    核心特性：
    - ReAct 循环：自动推理-行动-观察迭代
    - 工具调用：通过 LangChain Tool Calling 机制
    - 工作记忆：存储对话历史和中间结果
    - 降级策略：失败时回退到 V1 实现
    """
    
    def analyze(self, data, task_description, context):
        # Agent 自动选择工具、执行分析
        result = self.agent_executor.invoke({
            "input": input_text,
            "chat_history": chat_history
        })
        return result
```

---

## ✅ 文件修改

### 1. `workflow_engine/src/core/schema.py` - 新增协作字段

为多智能体协作添加状态字段：

```python
class WorkflowState(BaseModel):
    # ... 原有字段 ...
    
    # 协作请求队列
    collaboration_requests: Annotated[List[Dict[str, Any]], operator.add]
    
    # 协作响应存储
    collaboration_responses: Annotated[Dict[str, Any], operator.or_]
    
    # 智能体工作记忆
    agent_memory: Annotated[Dict[str, Any], operator.or_]
    
    # 工具调用记录
    tool_call_history: Annotated[List[Dict[str, Any]], operator.add]
```

### 2. `workflow_engine/src/nodes/sentiment_agent_node.py` - 集成 V2 Agent

支持 V2 和 V1 两种模式：

```python
class SentimentAgentNode(BaseNode):
    def execute(self, state: WorkflowState):
        # 获取参数
        use_v2_agent = self.get_input_value(state, "use_v2_agent")
        
        if use_v2_agent:
            # V2 模式：ReAct Agent
            result = self._execute_v2_agent(state, workflow_id, data, ...)
        else:
            # V1 模式：原有实现
            result = self._execute_v1_agent(workflow_id, data, ...)
```

---

## 🔄 架构对比

### V1 架构（原有）

```
用户请求 → SentimentAgentNode → SentimentAnalysisAgent → LLM 直接调用
                                    ↓
                              预设分析方法
```

**问题**：
- 没有工具调用能力
- 无法动态选择分析方法
- 缺少推理和反思过程

### V2 架构（新）

```
用户请求 → SentimentAgentNode → SentimentAgentV2 → ReAct 循环
                                    ↓
                           ┌────────────────────────┐
                           │     工具集 (6个)        │
                           │  - analyze_text        │
                           │  - batch_analyze       │
                           │  - extract_insights    │
                           │  - predict_trend       │
                           │  - query_knowledge     │
                           │  - update_memory       │
                           └────────────────────────┘
                                    ↓
                           降级策略 → SentimentAnalysisAgent (V1)
```

**优势**：
- 自动选择合适的工具
- 支持多步骤推理
- 失败自动降级

---

## 📊 使用方式

### 在工作流 DSL 中使用

```json
{
  "id": "sentiment_agent_1",
  "type": "SentimentAgent",
  "config": {
    "title": "情感分析",
    "params": {
      "use_v2_agent": true,
      "task_description": "分析这些评论的情感倾向",
      "topic": "产品评价"
    }
  }
}
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `use_v2_agent` | bool | true | 是否使用 V2 Agent |
| `task_description` | string | null | 自定义任务描述 |
| `topic` | string | null | 分析主题 |
| `extract_insights` | bool | true | 是否提取洞察 |
| `use_deep_analysis` | bool | true | V1 模式的深度分析开关 |

---

## 🧪 测试建议

```python
# 测试 V2 Agent
from workflow_engine.src.agents.sentiment_agent_v2 import SentimentAgentV2

agent = SentimentAgentV2(workflow_id="test")
result = agent.analyze(
    data=[{"content": "这个产品非常好用！"}],
    task_description="分析情感"
)
print(result["tools_used"])  # 查看使用了哪些工具
```

---

## 版本 2.4 - 多链路并行执行与报告生成降级策略优化 (2026-03-19)

### 🎯 概述

本次更新解决了两个关键问题：
1. **多链路并行执行**：修复了 GraphBuilder 只处理 Start 节点第一条边的问题，现在支持从 Start 节点扇出多条并行链路
2. **报告生成降级策略**：扩展了 LLM 报告生成支持，当报告类型不是 `sentiment_analysis` 时，使用 LLM 动态生成通用报告模板

---

## ✅ 多链路并行执行修复

### 问题描述

在 DSL 定义中，Start 节点可以有多条出边，指向多个并行执行的数据收集节点。但原代码在 `builder.py` 中只处理了第一条边：

```python
# 原代码问题
if source == start_node.id if start_node else False:
    target = edges[0].target  # ❌ 只取第一条边
    self.graph.set_entry_point(target)
    continue  # ❌ 跳过其他边
```

这导致工作流 DSL 中定义的三条并行链路（景点、美食、住宿）只有第一条被执行。

### 解决方案

修改 `workflow_engine/src/core/builder.py` 中的边处理逻辑：

```python
# 特殊处理 Start 节点：设置入口点（支持多链路并行）
if source == start_node.id if start_node else False:
    if len(edges) == 1:
        # 单入口：直接设置入口点
        self.graph.set_entry_point(edges[0].target)
    else:
        # 多入口（并行链路）：添加虚拟起始节点实现扇出
        def create_fan_out_node(node_id: str):
            def fan_out(state: WorkflowState) -> Dict[str, Any]:
                if self.monitor:
                    self.monitor.start_node(node_id, "Start", {})
                    self.monitor.complete_node(node_id, {"fan_out": True})
                return {}
            return fan_out
        
        virtual_start_id = "_workflow_fan_out_start_"  # 避免与 LangGraph 保留名称冲突
        if virtual_start_id not in self.graph.nodes:
            self.graph.add_node(virtual_start_id, create_fan_out_node(virtual_start_id))
        self.graph.set_entry_point(virtual_start_id)
        
        # 从虚拟起始节点连接到所有目标
        for edge in edges:
            self.graph.add_edge(virtual_start_id, edge.target)
```

### 技术细节

- **虚拟起始节点**：使用 `__start__` 作为虚拟节点 ID，不执行实际逻辑，仅作为入口点
- **扇出模式**：从虚拟节点向所有目标节点添加普通边，LangGraph 会自动并行执行
- **防御性检查**：确保虚拟节点不重复添加到图中
- **监控集成**：扇出节点也会触发监控回调

### 执行流程变化

**修复前**：
```
start → data_collector_attractions (仅此一条链路)
```

**修复后**：
```
start → __start__ (虚拟入口)
            ├── data_collector_attractions
            ├── data_collector_food
            └── data_collector_accommodation
```

---

## ✅ 报告生成降级策略优化

### 问题描述

原代码中，LLM 智能报告生成只支持 `sentiment_analysis` 类型：

```python
# 原代码问题
if use_llm_report and report_type == "sentiment_analysis":
    # LLM 智能报告生成模式
else:
    # 模板模式（降级）
```

当 `report_type="travel_guide"` 时，即使 `use_llm_report=True`，也会走模板模式，生成简化的降级报告。

### 解决方案

修改 `workflow_engine/src/nodes/report_agent_node.py`，新增 `_generate_llm_generic_report` 方法：

```python
# 根据模式选择报告生成方式
if use_llm_report:
    if report_type == "sentiment_analysis":
        # 原有的情感分析 LLM 报告
        report_result = self.agent.generate_llm_report(...)
    else:
        # 新增：通用 LLM 报告生成
        report_result = self._generate_llm_generic_report(
            topic=topic,
            report_type=report_type,
            report_data=report_data,
            data=data,
            language=language,
            report_style=report_style
        )
```

### 新增方法：`_generate_llm_generic_report`

功能特点：
- **动态模板生成**：使用 LLM 根据实际数据动态生成报告内容
- **多语言支持**：支持中英文报告
- **多报告类型**：支持 `travel_guide`、`data_collection` 等类型
- **防御性降级**：如果 LLM 生成失败或内容过短，自动降级到基础模板
- **数据摘要提取**：新增 `_extract_data_summary` 方法，从节点输出中提取关键信息

### 报告类型映射

| 报告类型 | 中文描述 | LLM 提示模板 |
|---------|---------|-------------|
| `sentiment_analysis` | 情感分析报告 | 专业情感分析报告（原有逻辑） |
| `travel_guide` | 旅游攻略报告 | 专业旅游攻略报告 |
| `data_collection` | 数据收集报告 | 专业数据收集报告 |
| 其他 | 通用报告 | 基于 {report_type} 的专业报告 |

### 降级链路

```
LLM 通用报告生成
    ↓ (失败或内容不足)
基础模板报告 (agent.generate_report)
    ↓ (失败)
兜底报告 (_build_fallback_report_content)
```

---

## 📝 修改文件清单

| 文件 | 修改内容 |
|-----|---------|
| `workflow_engine/src/core/builder.py` | 多链路并行执行支持（第333-368行） |
| `workflow_engine/src/nodes/report_agent_node.py` | 通用 LLM 报告生成方法（新增约200行） |

---

## 🧪 测试建议

1. **多链路并行测试**：
   - 创建包含多个并行数据收集节点的工作流
   - 验证所有链路是否被正确执行
   - 检查执行日志中的节点执行顺序

2. **通用报告生成测试**：
   - 创建 `travel_guide` 类型的工作流
   - 验证 LLM 是否被调用生成报告
   - 测试 LLM 失败时的降级逻辑

3. **数据汇聚测试**：
   - 验证多个数据收集节点的输出是否正确汇聚到下游节点
   - 检查 `itinerary_planner` 是否能接收所有链路的数据

---

## 版本 2.3 - 智能体记忆持久化验证与防御性编码 (2026-03-19)

### 🎯 概述

本次更新完成了智能体记忆机制的全面验证，通过端到端测试确认了工作流生成-执行过程中智能体记忆和工作流数据确实落在数据库中，没有走降级策略。同时验证了防御性编码的实现。

---

## ✅ 数据库配置和连接验证

### 1. 数据库架构确认

#### 数据库表结构
- **workflows**: 工作流定义和元数据存储
- **conversations**: 工作流对话历史记录
- **memories**: 智能体记忆存储（领域知识、案例模式、模板、规则）
- **audit_logs**: 审计日志记录
- **execution_runs**: 工作流执行记录
- **execution_node_traces**: 节点执行追踪记录

#### 连接配置
- PostgreSQL 数据库连接正常
- 连接池配置：pool_size=10, max_overflow=20
- 环境变量配置：`DATABASE_URL=postgresql://workflow_user:workflow_password@localhost:5432/workflow_db`

---

## 🧠 智能体记忆机制

### 1. 记忆服务架构

#### AgentMemoryService
```python
class AgentMemoryService:
    """智能体记忆服务：管理智能体的知识、案例、模板等记忆"""
    
    def save_memory(workflow_id, agent_type, memory_type, key, value, extra_data)
    def get_memory(workflow_id, agent_type, memory_type, key)
    def get_domain_knowledge(workflow_id, agent_type)
    def get_case_patterns(workflow_id, agent_type)
    def get_templates(workflow_id, agent_type)
    def get_rules(workflow_id, agent_type)
```

#### 记忆类型
- **domain_knowledge**: 领域知识记忆
- **case_pattern**: 案例模式记忆
- **template**: 模板记忆
- **rule**: 规则记忆

### 2. 持久化校验机制

#### 防御性编码实现
```python
def _is_persistable_workflow_id(self, workflow_id: Optional[str]) -> bool:
    """检查 workflow_id 是否可用于持久化（UUID 且在 workflows 表存在）"""
    if not workflow_id:
        return False
    
    try:
        uuid.UUID(str(workflow_id))
    except (ValueError, TypeError):
        return False
    
    try:
        return self.db.query(Workflow).filter(Workflow.id == str(workflow_id)).first() is not None
    except Exception as e:
        logger.warning(f"校验 workflow_id 可持久化性失败，降级为不写库: {e}")
        return False
```

#### 降级策略
- 无效 UUID 格式 → 返回 None，不写入数据库
- 不存在的 workflow_id → 返回 None，不写入数据库
- None 值 → 返回 None，不写入数据库
- 数据库异常 → 记录警告日志，降级执行

---

## 🧪 端到端测试验证

### 测试覆盖范围

| 测试项 | 验证内容 | 结果 |
|--------|----------|------|
| 数据库连接和表结构 | 验证 PostgreSQL 连接和表存在 | ✅ 通过 |
| 工作流创建并持久化 | 工作流定义写入 workflows 表 | ✅ 通过 |
| 智能体记忆持久化 | 四种类型记忆写入 memories 表 | ✅ 通过 |
| 对话记忆持久化 | 对话历史写入 conversations 表 | ✅ 通过 |
| 审计日志持久化 | 操作日志写入 audit_logs 表 | ✅ 通过 |
| 执行记录持久化 | 执行状态写入 execution_runs 表 | ✅ 通过 |
| 节点追踪记录持久化 | 节点状态写入 execution_node_traces 表 | ✅ 通过 |
| 工作流生成并验证记忆落库 | 完整流程验证 | ✅ 通过 |
| 记忆服务持久化校验逻辑 | 防御性编码验证 | ✅ 通过 |
| 无效 workflow_id 降级策略 | 降级逻辑验证 | ✅ 通过 |

### 测试结果
```
通过: 10/10
所有测试用例均通过验证
```

---

## 📁 相关文件

### 新增文件
- `workflow_engine/test/test_workflow_memory_persistence.py`: 端到端测试文件

### 核心文件
- `src/database/memory_service.py`: 记忆服务实现
- `src/database/repositories/memory_repository.py`: 记忆仓储实现
- `src/database/models.py`: 数据库模型定义
- `src/database/connection.py`: 数据库连接管理
- `src/services/agent_service.py`: 智能体服务封装

---

## 版本 2.2 - 循环节点修复与配置管理优化 (2026-03-11)

### 🎯 概述

本次更新修复了循环节点的关键路由问题，实现了统一的配置管理，并优化了工作流引擎的核心架构。

---

## 🐛 Bug 修复

### 1. 循环节点路由逻辑修复

#### 问题描述
- 循环节点无法正确退出，导致无限循环（GraphRecursionError）
- `loop_counters` 状态无法正确传递到下一次迭代
- 路由函数返回的节点ID与条件映射不匹配

#### 修复内容
- **`builder.py`**: 重构循环节点的条件边构建逻辑
  - 支持显式的 `branch` 字段（`loop_body` / `loop_exit`）
  - 修复退出目标指向 End 节点时返回 `END` 而非节点ID
  - 添加节点级别的 `max_iterations` 配置支持
  
- **`loop.py`**: 修复状态更新机制
  - 节点返回字典中包含 `loop_counters` 和 `loop_outputs` 更新
  - 确保 LangGraph 正确合并状态

- **`builder.py`**: 修复节点执行函数
  - 将循环状态更新传递到 LangGraph 状态管理

#### 测试结果
```
循环执行成功:
- loop_status: "completed"
- current_count: 3 (正确累积)
- total_outputs: 包含所有3次迭代输出
```

---

## ⚙️ 配置管理优化

### 1. 统一配置模块 (`src/config.py`)

#### 新增功能
- **Settings 类**: 使用 Pydantic Settings 实现统一配置管理
  - LLM 配置: `openai_api_key`, `openai_api_base`, `llm_model`
  - 数据库配置: `database_url`, `database_pool_size`
  - 循环节点配置: `loop_max_iterations`, `loop_default_iterations`
  - 缓存配置: `cache_enabled`, `cache_ttl`

- **LLMSettings 类**: 专门用于 LangChain LLM 实例创建
  - 集中管理 LLM 参数
  - 支持温度、最大令牌等配置

#### 使用方式
```python
from src.config import get_settings, get_llm_settings

# 获取应用配置
settings = get_settings()
max_iterations = settings.loop_max_iterations

# 获取 LLM 配置
llm_settings = get_llm_settings()
llm = ChatOpenAI(**llm_settings.model_dump())
```

#### 迁移模块
- `src/database/connection.py`
- `src/planner/llm_planner.py`
- `src/planner/enhanced_planner.py`
- `api/dependencies.py`
- `src/nodes/agent_node_base.py`
- `src/agents/planning_agent.py`
- `src/services/ai_conversation_service.py`
- `src/services/conversation_manager.py`

---

## 📝 数据模型更新

### EdgeDefinition 新增字段

```python
class EdgeDefinition(BaseModel):
    source: str
    target: str
    condition: Optional[str] = None
    branch: Optional[str] = None  # 新增: 'loop_body' 或 'loop_exit'
```

#### 使用示例
```json
{
  "edges": [
    {"source": "loop-node", "target": "process-node", "branch": "loop_body"},
    {"source": "loop-node", "target": "end-node", "branch": "loop_exit"}
  ]
}
```

---

## 🔧 API 端点

### 循环节点测试示例

```bash
curl -X POST http://localhost:8123/api/v1/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "nodes": [
        {"id": "start", "type": "Start", "config": {"title": "开始", "params": {}}},
        {"id": "loop", "type": "Loop", "config": {"title": "循环", "params": {"max_iterations": 3, "loop_type": "count"}}},
        {"id": "process", "type": "Code", "config": {"title": "处理", "params": {"code": "......"}}},
        {"id": "end", "type": "End", "config": {"title": "结束", "params": {}}}
      ],
      "edges": [
        {"source": "start", "target": "loop"},
        {"source": "loop", "target": "process", "branch": "loop_body"},
        {"source": "process", "target": "loop"},
        {"source": "loop", "target": "end", "branch": "loop_exit"}
      ]
    }
  }'
```

---

## 📦 依赖更新

- 新增: `pydantic-settings>=2.0.0`

---

*最后更新: 2026-03-11*

---

## 版本 2.0 - 真实数据收集与分析功能 (2026-03-05)

### 🎯 概述

本次更新将原有的 Mock 智能体升级为具有真实数据收集和分析能力的智能体系统。所有智能体现在都能够进行真实的数据处理，不再依赖模拟数据。

---

## ✨ 新增功能

### 1. 数据收集智能体 (DataCollectionAgent)

#### 真实数据源支持
- **DuckDuckGo 搜索集成**: 使用 ddgs 库实现真实的互联网搜索
- **Wikipedia API 集成**: 通过 wikipedia 库获取知识库数据
- **Reddit API 预留**: 集成 praw 库接口（需配置 API 凭证）
- **Twitter API 预留**: 集成 tweepy 库接口（需配置 API 凭证）

#### 核心功能
- search_internet(): 真实互联网搜索
- search_knowledge_base(): Wikipedia 知识库搜索
- collect_reddit_data(): Reddit 数据收集（预留）
- collect_twitter_data(): Twitter 数据收集（预留）
- execute_preset_workflow(): 执行完整数据收集工作流

---

### 2. 情感分析智能体 (SentimentAnalysisAgent)

#### 多种分析方法
- **词典分析方法**: 基于情感词典的情感分析
- **TextBlob 分析**: 英文文本情感分析
- **Jieba 中文分析**: 中文文本情感分析
- **集成分析方法**: 结合多种方法，投票决定最终结果

#### 核心功能
- analyze_sentiment(): 基础情感分析
- analyze_sentiment_advanced(): 高级情感分析（支持多种方法）
- detect_emotion(): 细粒度情感检测（joy, anger, sadness 等）
- analyze_aspects(): 方面级情感分析

---

### 3. 信息过滤智能体 (FilterAgent)

#### 多维度过滤策略
- **去重过滤**: 移除重复内容
- **关键词过滤**: 包含/排除特定关键词
- **长度过滤**: 根据内容长度筛选
- **时间范围过滤**: 根据时间戳筛选
- **置信度过滤**: 根据情感置信度筛选
- **质量评分过滤**: 综合质量评分

#### 核心功能
- filter_data(): 主过滤方法，支持组合过滤条件
- add_filter_rule(): 添加自定义过滤规则
- get_filter_rules(): 获取所有过滤规则
- remove_filter_rule(): 删除过滤规则

---

### 4. 报告生成智能体 (ReportGenerationAgent)

已具备完整的 Jinja2 模板系统和规则引擎，支持生成 Markdown 格式的专业报告。

---

## 📦 依赖库更新

### 新增依赖
- ddgs>=6.0.0 (DuckDuckGo 搜索)
- wikipedia>=1.4.0 (Wikipedia API)
- textblob>=0.17.0 (英文情感分析，可选)
- jieba>=0.42.1 (中文分词，可选)
- praw>=7.7.0 (Reddit API，可选)
- tweepy>=4.14.0 (Twitter API，可选)

---

## 🧪 测试

运行测试：python test/test_real_agents.py

测试覆盖：数据收集、情感分析、信息过滤、报告生成、端到端工作流

---

*最后更新: 2026-03-05*
