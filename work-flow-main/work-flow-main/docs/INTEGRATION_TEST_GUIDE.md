# 融合系统测试文档

> **测试目标**：验证「XHS数据过滤引擎」与「智能体工作流引擎」的对接是否正常运行。
>
> 整体流程：工作流引擎收到 query → 调用过滤引擎 API → 拿到高质量帖子 → 情感分析 → 生成报告

---

## 一、环境检查

### 1.1 确认两个服务的端口

| 服务 | 目录 | 默认端口 |
|------|------|---------|
| 数据过滤引擎 | `e:\xhs-crawler\` | **8081** |
| 工作流引擎 | `e:\xhs-crawler\work-flow-main\work-flow-main\workflow_engine\` | **8000** |

---

## 二、启动服务

### 2.1 启动数据过滤引擎（窗口一）

```cmd
cd e:\xhs-crawler
uv run python -m filter_engine.api
```

启动成功标志：

```
INFO:     Uvicorn running on http://0.0.0.0:8081
```

验证：浏览器访问 http://localhost:8081/docs 能看到 Swagger 界面。

---

### 2.2 启动工作流引擎（窗口二，按对方同事的方式）

```cmd
cd e:\xhs-crawler\work-flow-main\work-flow-main
python -m uvicorn workflow_engine.api.server:app --port 8000 --reload
```

启动成功标志：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 三、快速冒烟测试（推荐先做这步）

在启动工作流引擎之前，先单独验证过滤引擎的连通性。

### 3.1 测试过滤引擎是否正常

```cmd
curl -X POST http://localhost:8081/api/filter/auto ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"丽江旅游攻略\", \"platform\": \"xhs\", \"max_posts\": 50}"
```

**期望响应**：

```json
{
  "session_id": "sess_20260427_xxxxxx",
  "query": "丽江旅游攻略",
  "stats": {
    "l1_total_posts": 50,
    "l2_passed_posts": 23,
    "l3_passed_posts": 12
  },
  "performance": { "total": 15.3 }
}
```

拿到 `session_id` 后，继续查询结果：

```cmd
curl http://localhost:8081/api/sessions/sess_20260427_xxxxxx/results
```

**期望响应**：返回 `posts` 数组，每条包含 `id`、`title`、`content` 等字段。

---

## 四、主流程测试：用工作流 JSON 直接运行

### 4.1 运行融合工作流

工作流文件已准备好：`test_data/xhs_opinion_workflow.json`

```cmd
cd e:\xhs-crawler\work-flow-main\work-flow-main\workflow_engine
python main.py --file ../test_data/xhs_opinion_workflow.json
```

> **注意**：`main.py` 在 `workflow_engine/` 目录下运行。

### 4.2 修改 query（可选）

打开 `test_data/xhs_opinion_workflow.json`，修改第 7 行的 `topic` 字段：

```json
"variables": {
  "topic": "你想测试的关键词"
}
```

---

## 五、预期输出

运行成功后，终端会打印如下结构：

```
============================================================
工作流名称: XHS舆情分析工作流（含三层数据过滤）
执行引擎: LangGraph
============================================================

正在构建工作流图...
正在执行工作流...

============================================================
工作流执行结果
============================================================

[xhs_filter]
  输出: {
    "status": "success",
    "collected_data": [...],     ← 过滤后的帖子列表
    "total_count": 12,
    "session_id": "sess_xxx",
    "filter_stats": {
      "l1_total_posts": 50,
      "l2_passed_posts": 23,
      "l3_passed_posts": 12
    },
    "query": "丽江旅游攻略"
  }

[sentiment]
  输出: { ... }                  ← 情感分析结果

[report]
  输出: { ... }                  ← 生成的报告
```

执行报告会自动保存到 `workflow_engine/logs/execution_report_xxx.json`。

---

## 六、常见问题排查

### Q1：`xhs_filter` 节点报 `ConnectionRefusedError`

**原因**：数据过滤引擎（8081）没有启动。  
**解决**：先启动过滤引擎，再运行工作流。

---

### Q2：`xhs_filter` 节点返回 `total_count: 0`

**原因**：数据库 `filtered_posts` 表里没有数据。  
**解决**：先运行爬虫采集数据，或检查数据库连接配置（`e:\xhs-crawler\.env`）。

---

### Q3：schema 验证失败 `type is not a valid enum member`

**原因**：`schema.py` 的改动没有生效（可能有 `.pyc` 缓存）。  
**解决**：

```cmd
cd e:\xhs-crawler\work-flow-main\work-flow-main
del /s /q workflow_engine\src\core\__pycache__
python main.py --file test_data/xhs_opinion_workflow.json
```

---

### Q4：节点报 `query 参数为空`

**原因**：工作流 JSON 中 `"query": "$context.topic"` 的引用没有解析到。  
**临时解决**：把 JSON 里的 query 改成直接写死的字符串：

```json
"params": {
  "query": "丽江旅游攻略",
  ...
}
```

---

## 七、只测试 XHSFilterNode（不依赖工作流引擎）

如果只想验证节点代码本身，可以用这个最小脚本：

```python
# e:\xhs-crawler\work-flow-main\work-flow-main\test_xhs_node.py
import sys
sys.path.insert(0, "workflow_engine")

from workflow_engine.src.core.schema import NodeDefinition, NodeConfig, WorkflowState

node_def = NodeDefinition(
    id="xhs_filter",
    type="XHSFilterAgent",
    config=NodeConfig(
        title="测试",
        params={
            "query": "丽江旅游攻略",
            "platform": "xhs",
            "max_posts": 50,
            "min_relevance": 0.5,
            "filter_api_base": "http://localhost:8081"
        }
    )
)

state = WorkflowState(context={}, node_outputs={}, messages=[])

from workflow_engine.src.nodes.xhs_filter_node import XHSFilterNode
node = XHSFilterNode(node_def)
result = node.execute(state)

print(f"状态: {result['status']}")
print(f"帖子数: {result['total_count']}")
print(f"Session: {result['session_id']}")
print(f"过滤统计: {result['filter_stats']}")
```

运行：

```cmd
cd e:\xhs-crawler\work-flow-main\work-flow-main
python test_xhs_node.py
```

---

## 八、改动文件速查

| 文件 | 改动内容 |
|------|---------|
| `workflow_engine/src/nodes/xhs_filter_node.py` | **新建**，融合节点主体逻辑 |
| `workflow_engine/src/core/builder.py` | 注册 `XHSFilterAgent` → `XHSFilterNode` |
| `workflow_engine/src/core/schema.py` | `Literal` 类型加入 `"XHSFilterAgent"` |
| `test_data/xhs_opinion_workflow.json` | **新建**，完整融合工作流示例 |
| `filter_engine/api.py` | 加了 CORS 中间件（解决前端跨域） |
