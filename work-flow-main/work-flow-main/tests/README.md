# 测试文档

本文档说明如何运行工作流引擎项目的各种测试。

## 目录结构

```
tests/
├── __init__.py           # 测试包初始化文件
├── conftest.py           # pytest配置和共享fixtures
├── unit/                # 单元测试
│   ├── __init__.py
│   ├── test_node_instantiation.py
│   ├── test_node_import.py
│   ├── test_create_node_func.py
│   ├── test_workflow_state.py
│   ├── test_llm_node.py
│   └── test_langgraph_simple.py
├── integration/           # 集成测试
│   ├── __init__.py
│   ├── test_simple_condition.py
│   ├── test_integration.py
│   ├── test_builder_debug.py
│   ├── test_advanced_workflow.py
│   └── test_api.py
├── e2e/                # 端到端测试
│   ├── __init__.py
│   ├── workflow-editor.spec.ts  # TypeScript/JavaScript测试
│   └── test_frontend_backend.py    # Python Playwright测试
├── fixtures/            # 测试fixtures
│   └── example_client.py
└── utils/               # 测试工具
    ├── __init__.py
    └── test_helpers.py
```

## 环境要求

### Python测试
- Python 3.11+
- pip
- 虚拟环境（推荐）

### Playwright测试
- Node.js 16+
- npm 或 yarn
- Playwright浏览器驱动

## 安装依赖

### 1. 激活虚拟环境

```bash
source .venv/bin/activate
```

### 2. 安装Python依赖

```bash
pip install -r requirements.txt
pip install pytest-playwright playwright
```

### 3. 安装Playwright浏览器驱动

```bash
playwright install chromium
```

### 4. 安装Node.js依赖（用于E2E测试）

```bash
npm install
```

## 运行测试

### 运行所有测试

```bash
# 运行所有测试
pytest tests/

# 运行所有测试并显示详细输出
pytest tests/ -v

# 运行所有测试并生成覆盖率报告
pytest tests/ --cov=workflow_engine --cov-report=html
```

### 运行特定类型的测试

```bash
# 只运行单元测试
pytest tests/unit/ -v

# 只运行集成测试
pytest tests/integration/ -v

# 只运行E2E测试
pytest tests/e2e/ -v -m playwright
```

### 使用标记运行测试

```bash
# 运行所有单元测试
pytest -m unit -v

# 运行所有集成测试
pytest -m integration -v

# 运行所有E2E测试
pytest -m e2e -v

# 运行所有Playwright测试
pytest -m playwright -v

# 跳过慢速测试
pytest -m "not slow" -v
```

### 运行特定测试文件

```bash
# 运行单个测试文件
pytest tests/unit/test_workflow_state.py -v

# 运行单个测试函数
pytest tests/unit/test_workflow_state.py::test_workflow_state_graph -v

# 运行包含特定名称的测试
pytest -k "workflow" -v
```

## Playwright E2E测试

### TypeScript/JavaScript测试

```bash
# 运行所有E2E测试
npm run test:e2e

# 使用UI模式运行测试（可以看到浏览器）
npm run test:e2e:ui

# 使用调试模式运行测试
npm run test:e2e:debug

# 使用有头模式运行测试
npm run test:e2e:headed
```

### Python Playwright测试

```bash
# 运行Python Playwright测试
pytest tests/e2e/test_frontend_backend.py -v -m playwright

# 使用有头模式运行
pytest tests/e2e/test_frontend_backend.py -v -m playwright --headed

# 运行特定测试类
pytest tests/e2e/test_frontend_backend.py::TestWorkflowEditor -v -m playwright
```

## 测试配置

### pytest.ini

主要配置文件包含：
- 测试路径
- 文件模式
- 标记定义
- Playwright配置

### conftest.py

包含共享的fixtures：
- `api_client`: API测试客户端
- `base_url`: 基础URL
- `test_workflow_data`: 测试工作流数据
- `event_loop_policy`: 异步事件循环策略

## 前后端联调测试

### 准备工作

1. **启动后端服务器**：

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动FastAPI服务器
uvicorn workflow_engine.api.server:app --reload --host 0.0.0.0 --port 8000
```

2. **启动前端服务器**：

```bash
# 在另一个终端中
cd frontend  # 或包含index.html的目录
python -m http.server 3000
```

### 运行联调测试

```bash
# 运行所有E2E测试
pytest tests/e2e/ -v -m playwright

# 或使用npm运行TypeScript测试
npm run test:e2e
```

### 测试覆盖范围

联调测试涵盖：
- 页面加载和渲染
- 工作流创建和编辑
- 节点添加和连接
- 工作流保存和执行
- API端点测试
- 响应式设计测试
- 错误处理测试

## 调试测试

### 使用pytest调试

```bash
# 进入pdb调试器
pytest tests/unit/test_workflow_state.py -v --pdb

# 使用pdb++（更好的调试体验）
pytest tests/unit/test_workflow_state.py -v --pdbcls
```

### 使用Playwright UI模式

```bash
# 使用UI模式可以看到浏览器操作
npm run test:e2e:ui
```

### 查看详细输出

```bash
# 显示print语句输出
pytest tests/ -v -s

# 显示更详细的traceback
pytest tests/ -v --tb=long
```

## 测试报告

### 生成HTML报告

```bash
pytest tests/ --html=report.html
```

### 生成覆盖率报告

```bash
pytest tests/ --cov=workflow_engine --cov-report=html
# 报告将保存在 htmlcov/ 目录
```

### 生成Junit XML报告

```bash
pytest tests/ --junitxml=report.xml
```

## 持续集成

### GitHub Actions示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-playwright playwright
        playwright install chromium
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=workflow_engine
```

## 常见问题

### 测试超时

如果测试超时，可以：
1. 增加超时时间：`pytest --timeout=300`
2. 跳过慢速测试：`pytest -m "not slow"`
3. 使用并行测试：`pytest -n auto`

### Playwright浏览器未安装

```bash
# 重新安装浏览器驱动
playwright install --force chromium
```

### 导入错误

```bash
# 确保在项目根目录运行测试
cd /path/to/WorkFlow
pytest tests/
```

### 端口冲突

如果端口被占用：
1. 修改`pytest.ini`中的`base_url`
2. 或修改服务器启动命令中的端口

## 贡献指南

### 添加新测试

1. 在相应的目录创建测试文件
2. 使用清晰的测试名称和描述
3. 添加适当的标记（unit, integration, e2e）
4. 编写测试文档字符串
5. 确保测试独立且可重复运行

### 测试最佳实践

- 每个测试应该独立
- 使用fixtures共享测试数据
- 测试应该快速且可重复
- 使用描述性的测试名称
- 在测试中添加断言和错误消息
- 对异步测试使用适当的fixtures

## 联系方式

如有问题，请：
- 查看项目文档
- 提交Issue
- 联系维护团队