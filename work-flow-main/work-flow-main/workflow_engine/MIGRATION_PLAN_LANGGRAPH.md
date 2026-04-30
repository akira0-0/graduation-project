# CrewAI 迁移方案：统一使用 LangGraph

## 1. 迁移概述

### 1.1 迁移目标

将项目从双引擎架构（LangGraph + CrewAI）迁移为单一 LangGraph 架构，简化系统复杂度，更好地支持可视化工作流编排。

### 1.2 迁移原因

| 维度 | LangGraph 优势 | CrewAI 劣势 |
|------|----------------|-------------|
| 可视化编排 | 节点-边模型与 UI 天然对应 | 智能体协作是隐式的，无法可视化 |
| 条件分支 | 原生支持条件边和分支路由 | 需要额外实现，不直观 |
| 循环控制 | 原生支持循环节点 | 实现复杂 |
| 状态管理 | 完全可控，每个节点状态可追踪 | 黑盒，调试困难 |
| 扩展性 | 灵活自定义节点类型 | 受限于框架约定 |

### 1.3 影响范围

**直接影响的文件**：
- `workflow_engine/src/core/crew_builder.py` - 将被删除
- `workflow_engine/src/services/execution_service.py` - 移除 CrewAI 分支
- `workflow_engine/main.py` - 移除 `--engine` 参数
- `workflow_engine/requirements.txt` - 移除 crewai 依赖
- `workflow_engine/api/server.py` - 移除 engine 参数相关代码
- `workflow_engine/api/models.py` - 移除 engine 相关模型字段

**间接影响的文件**：
- 文档文件（README.md 等）
- 测试文件

---

## 2. 迁移步骤

### 第一阶段：移除 CrewAI 核心代码

#### 步骤 1: 删除 crew_builder.py

```bash
rm workflow_engine/src/core/crew_builder.py
```

#### 步骤 2: 修改 execution_service.py

移除 `_execute_with_crewai` 方法和相关导入：

```python
# 移除导入
# from ..core.crew_builder import CrewAIBuilder

# 移除 engine 参数中的 "crewai" 选项
def execute_workflow(
    self,
    workflow_def: WorkflowDefinition,
    enable_monitoring: bool = True,
    variables: Optional[Dict[str, Any]] = None,
    workflow_id: Optional[str] = None
) -> Dict[str, Any]:
    # 直接使用 LangGraph 执行
    return self._execute_with_langgraph(workflow_def, monitor, variables, workflow_id)
```

#### 步骤 3: 修改 main.py

移除 `--engine` 参数：

```python
# 移除
# parser.add_argument("--engine", type=str, default="langgraph",
#                   choices=["langgraph", "crewai"],
#                   help="执行引擎类型")

# 简化执行逻辑
run_workflow(workflow_def)  # 不再需要 engine 参数
```

#### 步骤 4: 修改 API 模型

修改 `api/models.py`：

```python
# 移除 ExecuteRequest 中的 engine 字段
class ExecuteRequest(BaseModel):
    workflow: Dict[str, Any]
    variables: Optional[Dict[str, Any]] = None
    # engine: Optional[str] = "langgraph"  # 删除此行
```

#### 步骤 5: 更新 requirements.txt

```diff
langchain
langchain-openai
langgraph
pydantic
python-dotenv
- crewai
langchain-community
fastapi
uvicorn
asyncpg
sqlalchemy
alembic
jinja2
```

---

### 第二阶段：增强 LangGraph 智能体能力

由于移除 CrewAI 后，智能体角色定义能力需要保留，我们可以通过增强 LangGraph 节点来实现。

#### 步骤 6: 创建增强型智能体节点基类

创建 `workflow_engine/src/nodes/agent_node_base.py`：

```python
"""
智能体节点基类
提供类似 CrewAI 的角色定义能力，但使用 LangGraph 执行
"""
from abc import abstractmethod
from typing import Any, Dict, Optional
from langchain_openai import ChatOpenAI
from .base import BaseNode
from ..core.schema import NodeDefinition, WorkflowState
from ..utils.logger import get_logger

logger = get_logger("agent_node_base")


class AgentNodeBase(BaseNode):
    """
    智能体节点基类
    
    提供 CrewAI 风格的角色定义，但使用 LangChain 直接调用
    """
    
    def __init__(self, node_def: NodeDefinition):
        super().__init__(node_def)
        
        # 从配置中提取智能体角色信息
        self.role = node_def.config.agent_role or "通用助手"
        self.goal = node_def.config.agent_goal or "完成任务"
        self.backstory = node_def.config.agent_backstory or ""
        
        # 初始化 LLM
        self.llm = self._init_llm()
    
    def _init_llm(self) -> ChatOpenAI:
        """初始化 LLM"""
        import os
        return ChatOpenAI(
            model=self.config.params.get("model", "deepseek-chat"),
            temperature=self.config.params.get("temperature", 0.1),
            openai_api_base=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            openai_api_key=os.environ.get("OPENAI_API_KEY")
        )
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return f"""你是一个{self.role}。

目标: {self.goal}

背景: {self.backstory}

请根据以上设定完成任务。"""
    
    @abstractmethod
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """执行节点逻辑（子类实现）"""
        pass
    
    def call_llm(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """
        调用 LLM
        
        Args:
            prompt: 用户提示词
            context: 额外上下文
            
        Returns:
            LLM 响应
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=self._build_system_prompt()),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        return response.content
```

#### 步骤 7: 更新现有智能体节点

以 `DataCollectionAgentNode` 为例，继承新的基类：

```python
"""
数据收集智能体节点
"""
from .agent_node_base import AgentNodeBase
from ..core.schema import NodeDefinition, WorkflowState
from typing import Dict, Any


class DataCollectionAgentNode(AgentNodeBase):
    """数据收集智能体节点"""
    
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        # 获取参数
        topic = self.get_input_value(state, "topic")
        sources = self.get_input_value(state, "sources") or ["internet"]
        max_results = self.get_input_value(state, "max_results") or 10
        
        # 构建提示词
        prompt = f"""请收集关于"{topic}"的信息。
数据来源: {', '.join(sources)}
最大结果数: {max_results}

请返回收集到的数据列表。"""
        
        # 调用 LLM
        result = self.call_llm(prompt)
        
        return {
            "collected_data": result,
            "topic": topic,
            "sources": sources,
            "status": "completed"
        }
```

---

### 第三阶段：更新文档和测试

#### 步骤 8: 更新 README.md

移除所有 CrewAI 相关说明：

```markdown
## 核心特性

- **图编排引擎**: 基于 LangGraph 的图编排，适合精细控制状态和条件分支

- **智能体节点**: 
  - 数据收集智能体
  - 情感分析智能体
  - 报告生成智能体
  - 信息过滤智能体

## 运行示例

# 使用 LangGraph 引擎（默认）
python workflow_engine/main.py --file workflow_engine/data/simple_workflow.json
```

#### 步骤 9: 更新测试文件

移除 CrewAI 相关测试，更新为纯 LangGraph 测试。

---

## 3. 需要修改的文件清单

### 3.1 需要删除的文件

| 文件路径 | 说明 |
|----------|------|
| `workflow_engine/src/core/crew_builder.py` | CrewAI 构建器 |

### 3.2 需要修改的文件

| 文件路径 | 修改内容 |
|----------|----------|
| `workflow_engine/main.py` | 移除 `--engine` 参数 |
| `workflow_engine/src/services/execution_service.py` | 移除 CrewAI 执行分支 |
| `workflow_engine/api/server.py` | 移除 engine 参数处理 |
| `workflow_engine/api/models.py` | 移除 engine 相关字段 |
| `workflow_engine/requirements.txt` | 移除 crewai 依赖 |
| `workflow_engine/README.md` | 更新文档 |

### 3.3 需要新增的文件

| 文件路径 | 说明 |
|----------|------|
| `workflow_engine/src/nodes/agent_node_base.py` | 智能体节点基类 |

---

## 4. 迁移后架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Presentation Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   CLI Entry     │  │   REST API      │  │   Static Frontend   │  │
│  │   (main.py)     │  │   (FastAPI)     │  │   (agent-detail.js) │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Service Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ PlannerService  │  │ ExecutionService│  │   AgentService      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │WorkflowService  │  │ConversationMgr  │  │DataStorageService   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Core Layer (仅 LangGraph)                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Schema (DSL Definition)                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                 GraphBuilder (唯一引擎)                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                      Nodes (节点实现)                        │    │
│  │  BaseNode → AgentNodeBase → 智能体节点                      │    │
│  │  LLMNode, CodeNode, ConditionNode, LoopNode                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Data Layer                                  │
│          (无变化，保持 PostgreSQL + SQLAlchemy + Repository)         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. 迁移验证清单

### 5.1 功能验证

- [ ] 现有工作流使用 LangGraph 正常执行
- [ ] 所有智能体节点正常工作
- [ ] 条件分支节点正常工作
- [ ] 循环节点正常工作
- [ ] API 接口正常响应
- [ ] CLI 命令正常执行

### 5.2 性能验证

- [ ] 执行性能无明显下降
- [ ] 内存占用合理
- [ ] 并发执行正常

### 5.3 文档验证

- [ ] README 更新完整
- [ ] API 文档更新
- [ ] 架构图更新

---

## 6. 回滚方案

如果迁移后出现问题，可以按以下步骤回滚：

1. 恢复 `requirements.txt` 中的 crewai 依赖
2. 恢复 `crew_builder.py` 文件
3. 恢复 `execution_service.py` 中的 CrewAI 执行分支
4. 恢复 `main.py` 中的 `--engine` 参数
5. 恢复 API 模型中的 engine 字段

建议在迁移前创建 Git 分支保存当前代码。

---

## 7. 迁移时间估算

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| 第一阶段 | 移除 CrewAI 核心代码 | 1-2 小时 |
| 第二阶段 | 增强智能体节点 | 2-3 小时 |
| 第三阶段 | 更新文档和测试 | 1-2 小时 |
| 验证测试 | 功能和性能验证 | 2-3 小时 |
| **总计** | | **6-10 小时** |

---

*迁移方案生成时间: 2026-03-11*