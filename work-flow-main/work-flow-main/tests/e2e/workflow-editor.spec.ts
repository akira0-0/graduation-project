import { test, expect } from '@playwright/test';

/**
 * 工作流编辑器端到端测试
 * 测试前后端联调功能
 */

test.describe('工作流编辑器 - 前后端联调测试', () => {
  let baseURL = 'http://localhost:3000';

  test.beforeEach(async ({ page }) => {
    // 每个测试前访问页面
    await page.goto(baseURL);
    await page.waitForLoadState('networkidle');
  });

  test('应该能够加载工作流编辑器页面', async ({ page }) => {
    // 检查页面标题
    await expect(page).toHaveTitle(/工作流编辑器/);
    
    // 检查主要元素是否存在
    await expect(page.locator('body')).toBeVisible();
  });

  test('应该能够创建新的工作流', async ({ page }) => {
    // 点击创建工作流按钮
    await page.click('text=创建工作流');
    
    // 等待工作流创建完成
    await expect(page.locator('.workflow-canvas')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够添加节点到画布', async ({ page }) => {
    // 创建工作流
    await page.click('text=创建工作流');
    await page.waitForSelector('.workflow-canvas', { timeout: 5000 });
    
    // 添加开始节点
    await page.click('text=添加节点');
    await page.click('text=开始节点');
    
    // 验证节点已添加
    await expect(page.locator('.node-start')).toBeVisible();
  });

  test('应该能够连接两个节点', async ({ page }) => {
    // 创建工作流
    await page.click('text=创建工作流');
    await page.waitForSelector('.workflow-canvas', { timeout: 5000 });
    
    // 添加两个节点
    await page.click('text=添加节点');
    await page.click('text=开始节点');
    
    await page.click('text=添加节点');
    await page.click('text=任务节点');
    
    // 等待节点出现
    await expect(page.locator('.node-start')).toBeVisible();
    await expect(page.locator('.node-task')).toBeVisible();
    
    // 连接节点
    const startNode = page.locator('.node-start');
    const taskNode = page.locator('.node-task');
    
    // 从开始节点拖动到任务节点
    await startNode.dragTo(taskNode);
    
    // 验证连接线
    await expect(page.locator('.connection-line')).toBeVisible();
  });

  test('应该能够保存工作流', async ({ page }) => {
    // 创建并配置工作流
    await page.click('text=创建工作流');
    await page.waitForSelector('.workflow-canvas', { timeout: 5000 });
    
    // 填写工作流名称
    await page.fill('input[name="workflow-name"]', '测试工作流');
    
    // 点击保存按钮
    await page.click('text=保存');
    
    // 验证保存成功消息
    await expect(page.locator('.success-message')).toBeVisible();
    await expect(page.locator('.success-message')).toHaveText(/保存成功/);
  });

  test('应该能够执行工作流', async ({ page }) => {
    // 创建工作流
    await page.click('text=创建工作流');
    await page.waitForSelector('.workflow-canvas', { timeout: 5000 });
    
    // 添加简单节点
    await page.click('text=添加节点');
    await page.click('text=开始节点');
    
    // 点击执行按钮
    await page.click('text=执行工作流');
    
    // 验证执行状态
    await expect(page.locator('.execution-status')).toBeVisible();
  });

  test('应该能够查看工作流执行结果', async ({ page }) => {
    // 执行工作流
    await page.click('text=创建工作流');
    await page.waitForSelector('.workflow-canvas', { timeout: 5000 });
    
    await page.click('text=添加节点');
    await page.click('text=开始节点');
    
    await page.click('text=执行工作流');
    
    // 等待执行完成
    await page.waitForSelector('.execution-complete', { timeout: 10000 });
    
    // 查看结果
    await page.click('text=查看结果');
    await expect(page.locator('.execution-result')).toBeVisible();
  });

  test('应该能够处理API错误', async ({ page }) => {
    // 监听网络请求
    page.route('**/api/workflows/**', route => route.abort());
    
    // 尝试创建工作流
    await page.click('text=创建工作流');
    
    // 验证错误消息显示
    await expect(page.locator('.error-message')).toBeVisible();
  });
});

test.describe('API端点测试', () => {
  test('GET /health 应该返回200状态', async ({ request }) => {
    const response = await request.get('http://localhost:8000/health');
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('status', 'ok');
  });

  test('POST /api/v1/workflows 应该能够创建工作流', async ({ request }) => {
    const workflowData = {
      id: 'test-workflow',
      name: '测试工作流',
      description: 'API测试工作流',
      nodes: [
        {
          id: 'start',
          type: 'Start',
          config: { title: '开始', params: {} }
        }
      ],
      edges: [],
      variables: {}
    };

    const response = await request.post('http://localhost:8000/api/v1/workflows', {
      data: workflowData
    });
    
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('status', 'success');
  });

  test('GET /api/v1/workflows/{id} 应该返回工作流详情', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/workflows/test-workflow');
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('workflow');
  });
});