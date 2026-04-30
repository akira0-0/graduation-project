# 工作流引擎前端 - Workflow Engine Frontend

基于 React + TypeScript + Vite 构建的现代工作流可视化编辑器，提供直观的拖拽式工作流设计界面。

## 🚀 技术栈

- **框架**: React 19 + TypeScript
- **构建工具**: Vite 5
- **状态管理**: Zustand
- **工作流可视化**: React Flow (@xyflow/react)
- **UI 组件**: Radix UI + Tailwind CSS
- **HTTP 客户端**: Fetch API + React Query
- **代码编辑器**: Monaco Editor
- **图表**: Recharts

## 📦 主要依赖

```json
{
  "react": "^19.2.0",
  "react-dom": "^19.2.0",
  "@xyflow/react": "^12.8.5",     // 工作流可视化
  "zustand": "^5.0.11",           // 状态管理
  "@tanstack/react-query": "^5.90.21", // 数据获取
  "@monaco-editor/react": "^4.7.0",    // 代码编辑器
  "recharts": "^3.8.0",           // 图表组件
  "tailwindcss": "^3.4.17",       // CSS 框架
  "lucide-react": "^0.577.0"      // 图标库
}
```

## 🏗️ 项目结构

```
frontend/
├── src/
│   ├── api/                    # API 接口层
│   │   ├── workflowApi.ts      # 工作流相关 API
│   │   └── workflowHooks.ts    # React Query hooks
│   ├── components/             # 组件
│   │   ├── layout/            # 布局组件
│   │   │   ├── TopBar.tsx     # 顶部工具栏
│   │   │   ├── CanvasPanel.tsx # 工作流画布
│   │   │   ├── ChatPanel.tsx  # 聊天面板
│   │   │   ├── RightDrawer.tsx # 右侧面板
│   │   │   └── BottomPanel.tsx # 底部状态栏
│   │   └── ui/                # UI 组件
│   ├── features/              # 功能模块
│   ├── mappers/               # 数据映射
│   ├── store/                 # 状态管理
│   ├── types/                 # TypeScript 类型定义
│   └── utils/                 # 工具函数
├── public/                    # 静态资源
└── package.json               # 项目配置
```

## 🎯 核心功能

### 1. 工作流可视化编辑
- **拖拽式节点操作**: 支持添加、删除、连接节点
- **实时状态显示**: 节点执行状态可视化（待执行/运行中/成功/失败）
- **智能布局**: 自动节点排列和连接线优化

### 2. AI 驱动的对话界面
- **自然语言生成工作流**: 通过对话快速创建工作流
- **上下文感知**: 支持多轮对话优化工作流
- **快捷模板**: 内置舆情分析等常用模板

### 3. 工作流执行与监控
- **实时执行监控**: 显示节点执行进度和状态
- **执行统计**: 成功率、耗时等指标展示
- **错误处理**: 详细的错误信息和调试支持

### 4. 数据持久化
- **工作流保存/加载**: 支持本地存储和云端同步
- **导入/导出**: JSON 格式的工作流文件交换
- **版本管理**: 自动保存和版本对比

## 🚦 快速开始

### 环境要求
- Node.js >= 18.0.0
- npm >= 9.0.0 或 yarn >= 1.22.0

### 安装依赖
```bash
npm install
# 或
yarn install
```

### 开发模式
```bash
npm run dev
# 或
yarn dev
```
访问 http://localhost:5173 查看应用

### 构建生产版本
```bash
npm run build
# 或
yarn build
```

### 预览构建结果
```bash
npm run preview
# 或
yarn preview
```

## 🔧 配置说明

### API 代理配置
在 `vite.config.ts` 中配置后端 API 代理：

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // 后端服务地址
        changeOrigin: true,
      },
    },
  },
})
```

### 环境变量
支持通过环境变量配置 API 地址：
```bash
VITE_API_BASE_URL=http://your-api-server.com
```

## 📋 开发规范

### 代码风格
- 使用 TypeScript 严格模式
- 遵循 React Hooks 最佳实践
- 组件采用函数式编程风格
- 使用 ESLint 和 Prettier 进行代码格式化

### 文件命名
- 组件文件：PascalCase（如 `TopBar.tsx`）
- 工具函数：camelCase（如 `workflowApi.ts`）
- 类型定义：PascalCase + `.ts`（如 `WorkflowTypes.ts`）

### 状态管理
- 全局状态：使用 Zustand 管理
- 组件状态：使用 React useState/useReducer
- 服务器状态：使用 React Query 管理

## 🔌 API 接口

### 工作流管理
- `GET /api/v1/workflows` - 获取工作流列表
- `GET /api/v1/workflows/:id` - 获取工作流详情
- `POST /api/v1/workflows` - 创建工作流
- `PUT /api/v1/workflows/:id` - 更新工作流

### 对话接口
- `POST /api/v1/conversations/start` - 开始新对话
- `POST /api/v1/conversations/continue` - 继续对话

### 执行接口
- `POST /api/v1/workflows/execute` - 执行工作流
- `GET /api/v1/executions/:id` - 获取执行详情

详细 API 文档请参考 [API 技术文档](./docs/API.md)

## 🎨 主题定制

使用 Tailwind CSS 进行样式定制，主要颜色变量：

```css
--border: hsl(214 32% 91%)
--background: hsl(220 20% 98%)
--primary: hsl(221 83% 53%)
--secondary: hsl(214 32% 91%)
```

## 📚 相关文档

- [React Flow 文档](https://reactflow.dev/)
- [Zustand 文档](https://zustand.docs.pmnd.rs/)
- [Tailwind CSS 文档](https://tailwindcss.com/)
- [React Query 文档](https://tanstack.com/query/latest)

## 🤝 贡献指南

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

此项目基于 MIT 许可证开源 - 查看 [LICENSE](../LICENSE) 文件了解详情

## 🆘 支持

如遇到问题，请在 GitHub Issues 中提交，我们会尽快回复。

---
**注意**: 这是工作流引擎的前端部分，需要配合后端服务使用。完整的系统架构请参考 [系统架构文档](../docs/ARCHITECTURE.md)。
