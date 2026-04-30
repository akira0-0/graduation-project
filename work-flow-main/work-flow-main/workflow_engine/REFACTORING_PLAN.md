# 工作流引擎三层架构重构计划

> 创建时间：2026-03-04
> 完成时间：2026-03-04
> 目标：将项目改造为接口层、接口实现层、数据层的三层架构

---

## 一、重构目标

将当前混合的代码结构改造为清晰的三层架构：

```
┌─────────────────────────────────────────────────────────────┐
│                      接口层 (API Layer)                      │
│  - FastAPI路由定义                                           │
│  - 请求验证/响应格式化                                        │
│  - 依赖注入配置                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    接口实现层 (Service Layer)                 │
│  - WorkflowService（工作流管理服务）                          │
│  - ExecutionService（执行服务）                               │
│  - AgentService（智能体服务）                                 │
│  - PlannerService（规划服务）                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                       数据层 (Data Layer)                     │
│  - WorkflowRepository（工作流仓储）                           │
│  - ConversationRepository（对话仓储）                         │
│  - MemoryRepository（记忆仓储）                               │
│  - AuditLogRepository（审计日志仓储）                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、重构任务清单

### Phase 1: 数据层完善 ✅ 已完成

- [x] **1.1 创建Repository接口基类**
  - 文件：`src/database/repositories/base.py`
  - 内容：定义通用的CRUD接口

- [x] **1.2 创建WorkflowRepository**
  - 文件：`src/database/repositories/workflow_repository.py`
  - 功能：工作流的增删改查

- [x] **1.3 创建ConversationRepository**
  - 文件：`src/database/repositories/conversation_repository.py`
  - 功能：对话历史的增删改查

- [x] **1.4 创建MemoryRepository**
  - 文件：`src/database/repositories/memory_repository.py`
  - 功能：智能体记忆的增删改查

- [x] **1.5 创建AuditLogRepository**
  - 文件：`src/database/repositories/audit_log_repository.py`
  - 功能：审计日志的增删改查

- [x] **1.6 创建Repository模块初始化文件**
  - 文件：`src/database/repositories/__init__.py`
  - 功能：导出所有Repository

### Phase 2: 业务服务层创建 ✅ 已完成

- [x] **2.1 创建服务层目录结构**
  - 目录：`src/services/`

- [x] **2.2 创建WorkflowService**
  - 文件：`src/services/workflow_service.py`
  - 功能：工作流生成、保存、查询、删除

- [x] **2.3 创建ExecutionService**
  - 文件：`src/services/execution_service.py`
  - 功能：工作流执行、监控

- [x] **2.4 创建AgentService**
  - 文件：`src/services/agent_service.py`
  - 功能：智能体模板管理

- [x] **2.5 创建PlannerService**
  - 文件：`src/services/planner_service.py`
  - 功能：LLM规划服务

- [x] **2.6 创建Service模块初始化文件**
  - 文件：`src/services/__init__.py`
  - 功能：导出所有Service

### Phase 3: 接口层重构 ✅ 已完成

- [x] **3.1 创建依赖注入配置**
  - 文件：`api/dependencies.py`
  - 功能：定义依赖注入工厂函数

- [x] **3.2 重构server.py**
  - 文件：`api/server.py`
  - 改动：使用Service层替代直接调用

- [ ] **3.3 创建路由模块（可选）**
  - 文件：`api/routes/workflow_routes.py`
  - 功能：将路由按功能拆分
  - 状态：暂不实施，当前架构已足够清晰

### Phase 4: 测试与验证 ✅ 已完成

- [x] **4.1 验证API导入**
  - 状态：成功导入所有模块

- [x] **4.2 创建单元测试**
  - 文件：`test/test_services.py`
  - 验证：依赖注入单例、Service创建、工作流验证逻辑

- [x] **4.3 创建API测试**
  - 文件：`test/test_api.py`
  - 验证：FastAPI应用创建、路由注册、版本信息

- [x] **4.4 运行验证测试**
  - 所有测试通过

### Phase 5: 前后端联调与端到端测试 ✅ 已完成

- [x] **5.1 启动后端服务**
  - 命令：`python -m uvicorn api.server:app --host 0.0.0.0 --port 8123`
  - 状态：成功启动

- [x] **5.2 测试健康检查接口**
  - 接口：`GET /health`
  - 结果：`{"status":"ok","timestamp":"2026-03-04T21:51:47.764049"}`

- [x] **5.3 测试工作流生成接口**
  - 接口：`POST /api/v1/workflows/generate`
  - 测试数据：`{"intent": "帮我分析一下京东的舆情信息"}`
  - 结果：成功生成"京东舆情分析工作流"，包含7个节点和7条边

- [x] **5.4 测试工作流执行接口**
  - 接口：`POST /api/v1/workflows/execute`
  - 结果：`{"status":"completed","execution_id":"exec_20260304_215438","statistics":{"success_rate":"100.0%"}}`

- [x] **5.5 测试智能体模板接口**
  - 接口：`GET /api/v1/agents/templates`
  - 结果：返回4个智能体模板（DataCollectionAgent、SentimentAgent、FilterAgent、ReportAgent）

---

## 三、已实现的架构

### 3.1 数据层 (Repository)

```
workflow_engine/src/database/repositories/
├── __init__.py           # 模块导出
├── base.py               # Repository基类接口
├── workflow_repository.py     # 工作流仓储
├── conversation_repository.py # 对话仓储
├── memory_repository.py       # 记忆仓储
└── audit_log_repository.py    # 审计日志仓储
```

### 3.2 业务服务层 (Service)

```
workflow_engine/src/services/
├── __init__.py           # 模块导出
├── workflow_service.py   # 工作流管理服务
├── execution_service.py  # 执行服务
├── agent_service.py      # 智能体服务
└── planner_service.py    # 规划服务
```

### 3.3 接口层 (API)

```
workflow_engine/api/
├── server.py             # FastAPI路由（已重构使用Service层）
├── models.py             # Pydantic模型
└── dependencies.py       # 依赖注入配置
```

---

## 四、依赖注入架构

```python
# API 层使用依赖注入
@app.post("/api/v1/workflows/generate")
async def generate_workflow(
    request: GenerateRequest,
    planner_service: PlannerService = Depends(get_planner_service)
):
    workflow_def = planner_service.generate_workflow(
        intent=request.intent,
        model=request.model
    )
    return GenerateResponse(workflow=workflow_def, ...)

# 依赖注入工厂函数
def get_workflow_service_dep(
    db: Session = Depends(get_db),
    planner_service: PlannerService = Depends(get_planner_service)
) -> WorkflowService:
    return get_workflow_service(db, planner_service)
```

---

## 五、文件变更记录

### 新增文件

| 文件路径 | 用途 | 行数 |
|---------|------|------|
| `src/database/repositories/__init__.py` | Repository模块导出 | ~20 |
| `src/database/repositories/base.py` | Repository基类接口 | ~50 |
| `src/database/repositories/workflow_repository.py` | 工作流数据访问 | ~150 |
| `src/database/repositories/conversation_repository.py` | 对话历史数据访问 | ~100 |
| `src/database/repositories/memory_repository.py` | 智能体记忆数据访问 | ~120 |
| `src/database/repositories/audit_log_repository.py` | 审计日志数据访问 | ~100 |
| `src/services/__init__.py` | Service模块导出 | ~15 |
| `src/services/planner_service.py` | 规划服务 | ~190 |
| `src/services/workflow_service.py` | 工作流服务 | ~370 |
| `src/services/execution_service.py` | 执行服务 | ~370 |
| `src/services/agent_service.py` | 智能体服务 | ~280 |
| `api/dependencies.py` | 依赖注入配置 | ~275 |

### 修改文件

| 文件路径 | 修改内容 |
|---------|----------|
| `api/server.py` | 重构为使用Service层和依赖注入 |

---

## 六、当前进度

**状态**：✅ 重构全部完成

**已完成**：
- ✅ Phase 1: 数据层完善 - 创建Repository
- ✅ Phase 2: 业务服务层创建 - 创建Service
- ✅ Phase 3: 接口层重构
- ✅ Phase 4: 测试与验证
- ✅ Phase 5: 前后端联调与端到端测试

**端到端测试结果**：

| 接口 | 方法 | 路径 | 状态 |
|-----|------|------|------|
| 健康检查 | GET | `/health` | ✅ 通过 |
| 工作流生成 | POST | `/api/v1/workflows/generate` | ✅ 通过 |
| 工作流执行 | POST | `/api/v1/workflows/execute` | ✅ 通过 |
| 智能体模板 | GET | `/api/v1/agents/templates` | ✅ 通过 |
| 舆情分析 | POST | `/api/v1/workflows/generate-public-opinion` | ✅ 可用 |

---

## 七、验收标准

- [x] 所有现有API接口保持不变
- [x] 代码结构清晰，职责分明
- [x] 支持依赖注入，便于测试
- [x] 无数据库模式下可正常运行（使用内存存储后备）
- [x] 单元测试通过（依赖注入、Service层验证）
- [x] API测试通过（路由注册、版本信息）
- [x] 端到端测试通过（所有核心API接口）
- [x] 文档更新完整

---

## 八、技术亮点

1. **依赖注入模式**：使用 FastAPI 的 Depends 实现依赖注入，支持测试时 Mock
2. **懒加载设计**：Service 层使用 `@property` 实现依赖的懒加载，降低初始化复杂度
3. **可选依赖**：Repository 作为可选参数传入 Service，支持无数据库运行场景
4. **向后兼容**：保持所有现有 API 接口不变，旧代码无需修改
5. **单一职责**：每层职责清晰，API 层只负责路由，Service 层负责业务逻辑，Repository 层负责数据访问