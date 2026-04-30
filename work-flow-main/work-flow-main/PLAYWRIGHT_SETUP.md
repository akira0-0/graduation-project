# Playwright配置和使用指南

本文档提供Playwright的配置说明和使用指南，用于工作流引擎项目的前后端联调测试。

## 目录

- [概述](#概述)
- [安装](#安装)
- [配置](#配置)
- [运行测试](#运行测试)
- [测试类型](#测试类型)
- [故障排除](#故障排除)

## 概述

Playwright是一个现代化的浏览器自动化工具，支持Chromium、Firefox和WebKit。本项目使用Playwright进行：

1. **端到端测试（E2E）**：测试完整用户流程
2. **前后端联调测试**：验证前端和后端的集成
3. **API测试**：直接测试后端API端点

### 为什么选择Playwright？

- ✅ 跨浏览器支持（Chrome、Firefox、Safari）
- ✅ 自动等待机制，减少flaky测试
- ✅ 强大的选择器API
- ✅ 内置截图和录像功能
- ✅ 并行测试支持
- ✅ 网络拦截和模拟能力

## 安装

### 前置要求

- Python 3.11+
- Node.js 16+ (用于TypeScript测试)
- pip (Python包管理器)
- npm (Node.js包管理器)

### 步骤1：安装Python依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装pytest和playwright
pip install pytest-playwright playwright

# 安装浏览器驱动
playwright install chromium
```

### 步骤2：安装Node.js依赖（可选）

如果需要运行TypeScript/JavaScript测试：

```bash
# 安装npm依赖
npm install

# 这将安装：
# - @playwright/test
# - @types/node
# - typescript
```

## 配置

### Python pytest配置

项目包含`pytest.ini`配置文件：

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Playwright配置
base_url = http://localhost:8000
browser_channel = chrome
headless = false
screenshot = only-on-failure
video = retain-on-failure
trace = retain-on-failure
```

### TypeScript配置

项目包含`playwright.config.ts`配置文件：

```typescript
export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
```

### 共享Fixtures

`tests/conftest.py`提供共享的测试fixtures：

```python
@pytest.fixture
def api_client(base_url):
    """API测试客户端"""
    from fastapi.testclient import TestClient
    return TestClient(app, base_url=base_url)

@pytest.fixture
def test_workflow_data():
    """测试工作流数据"""
    return { ... }
```

## 运行测试

### 准备环境

在运行测试之前，需要启动服务：

#### 1. 启动后端服务器

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动FastAPI服务器（端口8000）
uvicorn workflow_engine.api.server:app --reload --host 0.0.0.0 --port 8000
```

#### 2. 启动前端服务器

```bash
# 在另一个终端中
# 方式1：使用Python HTTP服务器
python -m http.server 3000

# 方式2：如果使用Node.js
npm run dev
```

### 运行Python测试

```bash
# 运行所有测试
pytest tests/ -v

# 只运行单元测试
pytest tests/unit/ -v

# 只运行集成测试
pytest tests/integration/ -v

# 运行Playwright测试
pytest tests/e2e/ -v -m playwright

# 使用有头模式运行
pytest tests/e2e/ -v -m playwright --headed
```

### 运行TypeScript测试

```bash
# 运行所有E2E测试
npm run test:e2e

# 使用UI模式运行
npm run test:e2e:ui

# 使用调试模式运行
npm run test:e2e:debug

# 使用有头模式运行
npm run test:e2e:headed
```

## 测试类型

### 单元测试

**位置**：`tests/unit/`

**目的**：测试单个函数、类和模块

**示例**：
- 节点实例化测试
- LangGraph状态测试
- 节点导入测试

**运行**：
```bash
pytest tests/unit/ -v
```

### 集成测试

**位置**：`tests/integration/`

**目的**：测试多个组件的交互

**示例**：
- 工作流执行测试
- 条件分支测试
- API集成测试

**运行**：
```bash
pytest tests/integration/ -v
```

### 端到端测试

**位置**：`tests/e2e/`

**目的**：测试完整的用户流程

**示例**：
- 工作流编辑器UI测试
- 前后端联调测试
- 响应式设计测试

**运行**：
```bash
# Python版本
pytest tests/e2e/ -v -m playwright

# TypeScript版本
npm run test:e2e
```

## 测试标记

项目使用pytest标记来分类测试：

```bash
# 运行特定类型的测试
pytest -m unit        # 只运行单元测试
pytest -m integration # 只运行集成测试
pytest -m e2e         # 只运行E2E测试
pytest -m playwright  # 只运行Playwright测试
pytest -m "not slow" # 跳过慢速测试
```

## 高级用法

### 并行测试

```bash
# 使用所有CPU核心运行测试
pytest -n auto

# 使用特定数量的worker
pytest -n 4
```

### 调试模式

```bash
# 使用pytest调试器
pytest tests/unit/test_workflow.py -v --pdb

# 使用Playwright UI模式
npm run test:e2e:ui
```

### 生成测试报告

```bash
# HTML报告
pytest tests/ --html=report.html

# 覆盖率报告
pytest tests/ --cov=workflow_engine --cov-report=html

# JUnit XML报告
pytest tests/ --junitxml=report.xml
```

### 截图和录像

Playwright自动在测试失败时：
- 保存截图
- 录制视频
- 保存trace文件

查看trace：
```bash
playwright show-trace trace.zip
```

## 故障排除

### 问题：Playwright浏览器未安装

**错误**：`Executable doesn't exist`

**解决方案**：
```bash
playwright install chromium
# 或重新安装
playwright install --force chromium
```

### 问题：端口被占用

**错误**：`Address already in use`

**解决方案**：
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或修改配置文件中的端口
```

### 问题：测试超时

**错误**：`Timeout waiting for selector`

**解决方案**：
```bash
# 增加超时时间
pytest tests/ --timeout=300

# 在代码中增加等待时间
await page.wait_for_selector('.element', timeout=30000)
```

### 问题：元素未找到

**错误**：`Timeout waiting for selector`

**解决方案**：
1. 检查选择器是否正确
2. 增加等待时间
3. 使用更宽松的选择器
4. 检查元素是否在iframe中

```python
# 方式1：使用文本选择器
page.get_by_text("提交").click()

# 方式2：使用role选择器
page.get_by_role("button", name="提交").click()

# 方式3：使用CSS选择器
page.locator("button[type='submit']").click()
```

### 问题：测试不稳定（flaky）

**原因**：网络延迟、异步加载、竞争条件

**解决方案**：
```python
# 使用自动等待
page.wait_for_load_state('networkidle')
page.wait_for_selector('.element')

# 使用重试机制
@pytest.mark.flaky(reruns=3)
def test_something():
    pass

# 使用fixtures准备环境
@pytest.fixture(autouse=True)
def setup_page(page):
    page.goto(base_url)
```

## 最佳实践

### 1. 测试独立性

每个测试应该独立运行，不依赖其他测试的状态。

```python
# ✓ 好
def test_create_workflow(page):
    page.goto('/new')
    page.fill('#name', 'Test')
    page.click('#save')

# ✗ 不好
def test_create_workflow(page):
    # 依赖前面的测试
    page.click('#continue-from-last-test')
```

### 2. 使用描述性测试名称

```python
# ✓ 好
def test_create_workflow_with_valid_data(page):
    pass

# ✗ 不好
def test_workflow(page):
    pass
```

### 3. 使用Page Object模式

```python
class WorkflowPage:
    def __init__(self, page):
        self.page = page
    
    def create_workflow(self, name):
        self.page.goto('/new')
        self.page.fill('#name', name)
        self.page.click('#save')

def test_create_workflow(page):
    workflow_page = WorkflowPage(page)
    workflow_page.create_workflow('Test')
```

### 4. 清理测试数据

```python
@pytest.fixture
def cleanup_workflow(api_client):
    workflows = []
    
    yield
    
    # 清理创建的工作流
    for workflow_id in workflows:
        api_client.delete(f'/workflows/{workflow_id}')
```

### 5. 使用适当的等待策略

```python
# 等待元素可见
page.wait_for_selector('.element', state='visible')

# 等待网络空闲
page.wait_for_load_state('networkidle')

# 等待DOM加载
page.wait_for_load_state('domcontentloaded')
```

## 参考资源

- [Playwright官方文档](https://playwright.dev/python/)
- [pytest-playwright文档](https://pytest-playwright.readthedocs.io/)
- [Playwright最佳实践](https://playwright.dev/python/docs/best-practices)
- [测试金字塔](https://martinfowler.com/articles/practical-test-pyramid.html)

## 贡献

添加新测试时，请遵循：

1. 将测试放在合适的目录（unit/integration/e2e）
2. 使用清晰的测试名称和描述
3. 添加适当的测试标记
4. 确保测试独立且可重复
5. 在测试失败时提供有用的错误消息
6. 为新功能添加测试

## 支持

如有问题或建议，请：
- 查看项目文档
- 提交Issue
- 联系维护团队