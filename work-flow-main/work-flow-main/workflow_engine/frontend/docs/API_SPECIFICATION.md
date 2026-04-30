# 工作流引擎前端 API 接口规范

本文档详细描述了工作流引擎前端与后端交互的 API 接口规范，包括请求格式、响应格式、错误处理等。

## 🎯 接口概览

### 基础信息
- **基础URL**: `http://localhost:8000/api/v1`
- **认证方式**: Bearer Token (可选)
- **数据格式**: JSON
- **编码**: UTF-8

### 通用响应格式
```typescript
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  timestamp: string;
}
```

### 通用错误响应
```typescript
interface ErrorResponse {
  code: number;
  message: string;
  details?: any;
  timestamp: string;
}
```

## 📋 接口详细说明

### 1. 工作流管理接口

#### 1.1 获取工作流列表
```
GET /workflows
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | number | 否 | 页码，默认1 |
| limit | number | 否 | 每页数量，默认20 |
| search | string | 否 | 搜索关键词 |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "workflows": [
      {
        "id": "wf_123456",
        "name": "数据处理工作流",
        "description": "用于处理用户数据的自动化工作流",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T14:20:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20
  },
  "timestamp": "2024-01-15T15:30:00Z"
}
```

#### 1.2 获取工作流详情
```
GET /workflows/{workflow_id}
```

**路径参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| workflow_id | string | 是 | 工作流ID |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "wf_123456",
    "name": "数据处理工作流",
    "description": "用于处理用户数据的自动化工作流",
    "definition": {
      "name": "数据处理工作流",
      "description": "用于处理用户数据的自动化工作流",
      "nodes": [
        {
          "id": "node_1",
          "type": "Start",
          "config": {
            "title": "开始节点",
            "description": "工作流入口",
            "params": {}
          },
          "position": {
            "x": 100,
            "y": 100
          }
        },
        {
          "id": "node_2",
          "type": "DataProcessor",
          "config": {
            "title": "数据处理",
            "description": "处理用户数据",
            "params": {
              "processing_type": "clean",
              "output_format": "json"
            }
          },
          "position": {
            "x": 300,
            "y": 100
          }
        }
      ],
      "edges": [
        {
          "source": "node_1",
          "target": "node_2",
          "condition": null,
          "branch": null
        }
      ],
      "variables": {}
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T14:20:00Z"
  },
  "timestamp": "2024-01-15T15:30:00Z"
}
```

#### 1.3 创建工作流
```
POST /workflows
```

**请求体**
```json
{
  "workflow": {
    "name": "新工作流",
    "description": "新创建的工作流",
    "nodes": [
      {
        "id": "node_1",
        "type": "Start",
        "config": {
          "title": "开始节点",
          "params": {}
        }
      }
    ],
    "edges": [],
    "variables": {}
  },
  "description": "新创建的工作流"
}
```

**响应示例**
```json
{
  "code": 201,
  "message": "Workflow created successfully",
  "data": {
    "workflow_id": "wf_789012",
    "name": "新工作流",
    "description": "新创建的工作流",
    "created_at": "2024-01-15T16:00:00Z",
    "status": "active"
  },
  "timestamp": "2024-01-15T16:00:00Z"
}
```

#### 1.4 更新工作流
```
PUT /workflows/{workflow_id}
```

**路径参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| workflow_id | string | 是 | 工作流ID |

**请求体**
```json
{
  "workflow": {
    "name": "更新后的工作流",
    "description": "更新描述",
    "nodes": [...],
    "edges": [...],
    "variables": {}
  }
}
```

**响应示例**
```json
{
  "code": 200,
  "message": "Workflow updated successfully",
  "data": {
    "workflow_id": "wf_123456",
    "name": "更新后的工作流",
    "updated_at": "2024-01-15T16:30:00Z"
  },
  "timestamp": "2024-01-15T16:30:00Z"
}
```

### 2. 对话接口

#### 2.1 开始对话
```
POST /conversations/start
```

**请求体**
```json
{
  "user_intent": "创建一个数据处理工作流，用于清洗CSV文件",
  "workflow_type": "data_processing"
}
```

**响应示例**
```json
{
  "code": 200,
  "message": "Conversation started successfully",
  "data": {
    "conversation_id": "conv_123456",
    "workflow_id": "wf_abcdef",
    "workflow": {
      "name": "CSV数据处理工作流",
      "description": "用于清洗和处理CSV文件数据",
      "nodes": [...],
      "edges": [...]
    },
    "message": "我已经为您创建了一个CSV数据处理工作流，包含文件读取、数据清洗和结果输出三个主要步骤。"
  },
  "timestamp": "2024-01-15T16:45:00Z"
}
```

#### 2.2 继续对话
```
POST /conversations/continue
```

**请求体**
```json
{
  "workflow_id": "wf_abcdef",
  "user_message": "请添加数据验证步骤"
}
```

**响应示例**
```json
{
  "code": 200,
  "message": "Message processed successfully",
  "data": {
    "conversation_id": "conv_123456",
    "workflow_id": "wf_abcdef",
    "workflow": {
      "name": "CSV数据处理工作流",
      "description": "用于清洗和处理CSV文件数据，包含数据验证",
      "nodes": [...],
      "edges": [...]
    },
    "message": "已在数据清洗步骤后添加了数据验证节点，确保数据质量。"
  },
  "timestamp": "2024-01-15T16:50:00Z"
}
```

### 3. 工作流执行接口

#### 3.1 执行工作流
```
POST /workflows/execute
```

**请求体**
```json
{
  "workflow": {
    "name": "数据处理工作流",
    "nodes": [...],
    "edges": [...],
    "variables": {}
  },
  "workflow_id": "wf_123456",
  "model": "gpt-4",
  "enable_monitoring": true
}
```

**响应示例**
```json
{
  "code": 200,
  "message": "Workflow execution started",
  "data": {
    "status": "running",
    "execution_id": "exec_789012",
    "summary": {
      "execution_id": "exec_789012",
      "workflow_id": "wf_123456",
      "workflow_name": "数据处理工作流",
      "status": "running",
      "start_time": "2024-01-15T17:00:00Z",
      "duration": 0,
      "statistics": {
        "total_nodes": 5,
        "success_nodes": 0,
        "failed_nodes": 0,
        "skipped_nodes": 0,
        "success_rate": "0%"
      }
    },
    "node_outputs": {},
    "duration_seconds": 0,
    "raw": {
      "status": "running",
      "execution_id": "exec_789012",
      "result": null,
      "node_outputs": {},
      "summary": {
        "execution_id": "exec_789012",
        "workflow_id": "wf_123456",
        "status": "running"
      }
    }
  },
  "timestamp": "2024-01-15T17:00:00Z"
}
```

#### 3.2 获取执行详情
```
GET /executions/{execution_id}?include_node_traces=true
```

**路径参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| execution_id | string | 是 | 执行ID |

**查询参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| include_node_traces | boolean | 否 | 是否包含节点跟踪信息，默认true |

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "executionId": "exec_789012",
    "workflowId": "wf_123456",
    "status": "completed",
    "startedAt": "2024-01-15T17:00:00Z",
    "completedAt": "2024-01-15T17:02:30Z",
    "durationMs": 150000,
    "triggerSource": "manual",
    "errorMessage": null,
    "finalReportPath": "/reports/exec_789012_report.html",
    "nodeTraces": [
      {
        "executionId": "exec_789012",
        "nodeId": "node_1",
        "nodeType": "Start",
        "status": "completed",
        "inputPayload": null,
        "outputPayload": {
          "start_time": "2024-01-15T17:00:00Z"
        },
        "errorMessage": null,
        "startedAt": "2024-01-15T17:00:00Z",
        "completedAt": "2024-01-15T17:00:05Z",
        "durationMs": 5000,
        "createdAt": "2024-01-15T17:00:00Z"
      },
      {
        "executionId": "exec_789012",
        "nodeId": "node_2",
        "nodeType": "DataProcessor",
        "status": "completed",
        "inputPayload": {
          "data": "..."
        },
        "outputPayload": {
          "processed_data": "...",
          "record_count": 1250
        },
        "errorMessage": null,
        "startedAt": "2024-01-15T17:00:05Z",
        "completedAt": "2024-01-15T17:02:25Z",
        "durationMs": 140000,
        "createdAt": "2024-01-15T17:00:05Z"
      }
    ]
  },
  "timestamp": "2024-01-15T17:02:30Z"
}
```

### 4. 舆情分析专用接口

#### 4.1 生成舆情分析工作流
```
POST /workflows/generate-public-opinion
```

**请求体**
```json
{
  "topic": "新能源汽车行业发展趋势",
  "requirements": {
    "analysis_depth": "comprehensive",
    "time_range": "最近3个月",
    "platforms": ["微博", "知乎", "抖音"]
  },
  "model": "gpt-4"
}
```

**响应示例**
```json
{
  "code": 200,
  "message": "Public opinion workflow generated successfully",
  "data": {
    "workflow": {
      "name": "新能源汽车行业发展趋势舆情分析",
      "description": "针对新能源汽车行业发展趋势的全面舆情分析",
      "nodes": [
        {
          "id": "collect_1",
          "type": "DataCollection",
          "config": {
            "title": "数据采集",
            "description": "从多个平台采集相关数据",
            "params": {
              "platforms": ["微博", "知乎", "抖音"],
              "keywords": ["新能源汽车", "电动汽车", "行业发展"],
              "time_range": "最近3个月"
            }
          }
        },
        {
          "id": "analyze_1",
          "type": "SentimentAnalysis",
          "config": {
            "title": "情感分析",
            "description": "分析用户情感倾向",
            "params": {
              "analysis_model": "advanced",
              "sentiment_categories": ["positive", "negative", "neutral"]
            }
          }
        },
        {
          "id": "report_1",
          "type": "ReportGeneration",
          "config": {
            "title": "报告生成",
            "description": "生成分析报告",
            "params": {
              "report_type": "comprehensive",
              "include_charts": true
            }
          }
        }
      ],
      "edges": [
        {
          "source": "collect_1",
          "target": "analyze_1"
        },
        {
          "source": "analyze_1",
          "target": "report_1"
        }
      ]
    },
    "status": "generated",
    "metadata": {
      "estimated_duration": "15-20分钟",
      "complexity": "high",
      "data_sources": 3
    }
  },
  "timestamp": "2024-01-15T18:00:00Z"
}
```

## ⚠️ 错误处理

### 错误响应格式
```json
{
  "code": 400,
  "message": "Invalid request parameters",
  "details": {
    "field": "workflow.name",
    "reason": "Workflow name is required"
  },
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### 常见错误码
| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查请求参数格式和必填字段 |
| 401 | 未授权 | 检查认证token是否有效 |
| 404 | 资源不存在 | 确认请求的资源ID是否正确 |
| 409 | 资源冲突 | 检查是否有重复操作或并发修改 |
| 422 | 业务逻辑错误 | 检查业务规则约束 |
| 429 | 请求频率限制 | 降低请求频率 |
| 500 | 服务器内部错误 | 联系技术支持 |
| 503 | 服务不可用 | 稍后重试 |

## 📊 状态码说明

### 工作流状态
- `draft`: 草稿状态
- `active`: 激活状态
- `inactive`: 非激活状态
- `archived`: 已归档

### 执行状态
- `pending`: 等待执行
- `running`: 执行中
- `completed`: 执行完成
- `failed`: 执行失败
- `cancelled`: 已取消

### 节点状态
- `pending`: 待执行
- `running`: 执行中
- `success`: 执行成功
- `error`: 执行失败
- `skipped`: 已跳过

## 🔒 安全规范

### 认证方式
```http
Authorization: Bearer <token>
```

### 请求签名（可选）
```http
X-Request-Signature: <signature>
X-Timestamp: <timestamp>
X-Nonce: <nonce>
```

### 数据加密
敏感数据传输建议使用 HTTPS，必要时可进行额外加密。

## 📈 性能指标

### 响应时间要求
| 接口类型 | 最大响应时间 | 目标响应时间 |
|----------|-------------|-------------|
| 查询类 | 2秒 | 500ms |
| 操作类 | 5秒 | 1秒 |
| 执行类 | 30秒 | 5秒 |
| 批量类 | 60秒 | 10秒 |

### 并发要求
- 支持至少 100 并发请求
- 支持水平扩展
- 具备熔断和降级机制

## 🧪 测试接口

### 健康检查
```
GET /health
```

**响应示例**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T12:00:00Z",
  "version": "1.0.0"
}
```

### 版本信息
```
GET /version
```

**响应示例**
```json
{
  "version": "1.0.0",
  "build": "20240115.1",
  "commit": "abc123def456",
  "timestamp": "2024-01-15T12:00:00Z"
}
```