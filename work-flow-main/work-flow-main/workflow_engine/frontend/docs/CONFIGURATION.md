# 前端配置文档

本文档详细说明工作流引擎前端的所有配置选项，包括构建配置、环境变量、代理设置等。

## 📋 配置概览

### 配置文件列表
```
frontend/
├── vite.config.ts          # Vite 构建配置
├── tsconfig.json           # TypeScript 配置
├── tsconfig.app.json       # 应用 TypeScript 配置
├── tsconfig.node.json      # Node.js TypeScript 配置
├── tailwind.config.js      # Tailwind CSS 配置
├── postcss.config.js       # PostCSS 配置
├── eslint.config.js        # ESLint 配置
├── .env                    # 环境变量
├── .env.example           # 环境变量示例
└── package.json           # 项目依赖配置
```

## ⚙️ 构建配置

### Vite 配置 (vite.config.ts)

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // 基础配置
  base: './',
  publicDir: 'public',
  
  // 插件配置
  plugins: [react()],
  
  // 开发服务器配置
  server: {
    host: 'localhost',
    port: 5173,
    open: true,
    cors: true,
    
    // 代理配置
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path,
        configure: (proxy, options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Sending Request to the Target:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
          });
        }
      }
    }
  },
  
  // 构建配置
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'ui-vendor': ['@radix-ui/react-dialog', 'lucide-react'],
          'flow-vendor': ['@xyflow/react'],
          'query-vendor': ['@tanstack/react-query'],
          'utils-vendor': ['zustand', 'clsx', 'tailwind-merge']
        }
      }
    }
  },
  
  // 路径别名配置
  resolve: {
    alias: {
      '@': '/src',
      '@components': '/src/components',
      '@api': '/src/api',
      '@types': '/src/types',
      '@utils': '/src/utils',
      '@store': '/src/store',
      '@features': '/src/features',
      '@mappers': '/src/mappers'
    }
  },
  
  // CSS 配置
  css: {
    postcss: './postcss.config.js'
  },
  
  // 优化配置
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      '@xyflow/react',
      '@tanstack/react-query',
      'zustand'
    ]
  }
})
```

### TypeScript 配置 (tsconfig.json)

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ],
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"],
      "@api/*": ["src/api/*"],
      "@types/*": ["src/types/*"],
      "@utils/*": ["src/utils/*"],
      "@store/*": ["src/store/*"],
      "@features/*": ["src/features/*"],
      "@mappers/*": ["src/mappers/*"]
    }
  }
}
```

#### 应用配置 (tsconfig.app.json)

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    
    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    
    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    
    /* Path mapping */
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@components/*": ["./src/components/*"],
      "@api/*": ["./src/api/*"],
      "@types/*": ["./src/types/*"],
      "@utils/*": ["./src/utils/*"],
      "@store/*": ["./src/store/*"],
      "@features/*": ["./src/features/*"],
      "@mappers/*": ["./src/mappers/*"]
    }
  },
  "include": ["src"]
}
```

### Tailwind CSS 配置 (tailwind.config.js)

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    // 如果作为库使用，需要包含使用方的路径
    // "../../src/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        // 基础颜色系统
        border: "hsl(214 32% 91%)",
        input: "hsl(214 32% 91%)",
        ring: "hsl(221 83% 53%)",
        background: "hsl(220 20% 98%)",
        foreground: "hsl(222 47% 11%)",
        
        // 主色调
        primary: {
          DEFAULT: "hsl(221 83% 53%)",
          foreground: "hsl(210 40% 98%)",
          50: "hsl(221 83% 95%)",
          100: "hsl(221 83% 90%)",
          200: "hsl(221 83% 80%)",
          300: "hsl(221 83% 70%)",
          400: "hsl(221 83% 60%)",
          500: "hsl(221 83% 53%)",
          600: "hsl(221 83% 45%)",
          700: "hsl(221 83% 35%)",
          800: "hsl(221 83% 25%)",
          900: "hsl(221 83% 15%)"
        },
        
        // 次要色调
        secondary: {
          DEFAULT: "hsl(214 32% 91%)",
          foreground: "hsl(222 47% 11%)",
          50: "hsl(214 32% 95%)",
          100: "hsl(214 32% 90%)",
          200: "hsl(214 32% 80%)",
          300: "hsl(214 32% 70%)",
          400: "hsl(214 32% 60%)",
          500: "hsl(214 32% 91%)",
          600: "hsl(214 32% 85%)",
          700: "hsl(214 32% 75%)",
          800: "hsl(214 32% 65%)",
          900: "hsl(214 32% 55%)"
        },
        
        // 破坏性操作颜色
        destructive: {
          DEFAULT: "hsl(0 84% 60%)",
          foreground: "hsl(210 40% 98%)"
        },
        
        // 静音颜色
        muted: {
          DEFAULT: "hsl(210 40% 96%)",
          foreground: "hsl(215 16% 47%)"
        },
        
        // 强调颜色
        accent: {
          DEFAULT: "hsl(213 27% 94%)",
          foreground: "hsl(222 47% 11%)"
        },
        
        // 卡片颜色
        card: {
          DEFAULT: "hsl(0 0% 100%)",
          foreground: "hsl(222 47% 11%)"
        },
        
        // 弹窗颜色
        popover: {
          DEFAULT: "hsl(0 0% 100%)",
          foreground: "hsl(222 47% 11%)"
        },
        
        // 工作流节点状态颜色
        workflow: {
          pending: {
            DEFAULT: "#f1f5f9",
            foreground: "#64748b",
            border: "#cbd5e1"
          },
          running: {
            DEFAULT: "#dbeafe",
            foreground: "#1d4ed8",
            border: "#3b82f6"
          },
          success: {
            DEFAULT: "#dcfce7",
            foreground: "#166534",
            border: "#22c55e"
          },
          error: {
            DEFAULT: "#fef2f2",
            foreground: "#dc2626",
            border: "#ef4444"
          }
        }
      },
      
      // 边框半径
      borderRadius: {
        xl: "calc(0.5rem + 4px)",
        lg: "0.5rem",
        md: "calc(0.25rem + 2px)",
        sm: "calc(0.125rem + 1px)",
        xs: "0.125rem"
      },
      
      // 字体大小
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1rem" }],
        sm: ["0.875rem", { lineHeight: "1.25rem" }],
        base: ["1rem", { lineHeight: "1.5rem" }],
        lg: ["1.125rem", { lineHeight: "1.75rem" }],
        xl: ["1.25rem", { lineHeight: "1.75rem" }],
        "2xl": ["1.5rem", { lineHeight: "2rem" }],
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],
        "4xl": ["2.25rem", { lineHeight: "2.5rem" }]
      },
      
      // 动画
      animation: {
        "fade-in": "fade-in 0.5s ease-in-out",
        "slide-in": "slide-in 0.3s ease-out",
        "pulse-slow": "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite"
      },
      
      // 关键帧动画
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" }
        },
        "slide-in": {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(0)" }
        }
      },
      
      // 布局尺寸
      spacing: {
        "18": "4.5rem",
        "88": "22rem",
        "128": "32rem",
        "144": "36rem"
      },
      
      // 高度
      height: {
        "18": "4.5rem",
        "88": "22rem",
        "128": "32rem",
        "144": "36rem"
      },
      
      // 宽度
      width: {
        "18": "4.5rem",
        "88": "22rem",
        "128": "32rem",
        "144": "36rem"
      },
      
      // 最小高度
      minHeight: {
        "128": "32rem",
        "144": "36rem"
      },
      
      // 最大高度
      maxHeight: {
        "128": "32rem",
        "144": "36rem"
      },
      
      // 盒子阴影
      boxShadow: {
        "workflow": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        "workflow-lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        "node": "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
        "node-hover": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)"
      }
    }
  },
  plugins: [],
  // 暗黑模式支持（可选）
  darkMode: "class"
}
```

## 🔧 环境变量配置

### 基础环境变量 (.env)

```bash
# API 配置
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
VITE_API_RETRY_COUNT=3

# 应用配置
VITE_APP_NAME=Workflow Engine
VITE_APP_VERSION=1.0.0
VITE_APP_ENV=development

# 功能开关
VITE_ENABLE_CHAT=true
VITE_ENABLE_MONITORING=true
VITE_ENABLE_EXPORT=true

# UI 配置
VITE_DEFAULT_LANGUAGE=zh-CN
VITE_ENABLE_DARK_MODE=true
VITE_ANIMATION_ENABLED=true

# 性能配置
VITE_ENABLE_BUNDLE_ANALYZER=false
VITE_ENABLE_SOURCE_MAP=true

# 外部服务
VITE_WEBSOCKET_URL=ws://localhost:8000/ws
VITE_CDN_URL=https://cdn.example.com

# 安全配置
VITE_ENABLE_CSRF=true
VITE_CSRF_HEADER_NAME=X-CSRF-Token
```

### 环境变量说明

| 变量名 | 说明 | 默认值 | 可选值 |
|--------|------|--------|--------|
| VITE_API_BASE_URL | API 基础地址 | http://localhost:8000 | 任意有效URL |
| VITE_API_TIMEOUT | API 超时时间 | 30000 | 数字（毫秒） |
| VITE_API_RETRY_COUNT | API 重试次数 | 3 | 数字 |
| VITE_APP_NAME | 应用名称 | Workflow Engine | 字符串 |
| VITE_APP_VERSION | 应用版本 | 1.0.0 | 版本号格式 |
| VITE_APP_ENV | 应用环境 | development | development/production/test |
| VITE_ENABLE_CHAT | 启用聊天功能 | true | true/false |
| VITE_ENABLE_MONITORING | 启用监控 | true | true/false |
| VITE_ENABLE_EXPORT | 启用导出功能 | true | true/false |
| VITE_DEFAULT_LANGUAGE | 默认语言 | zh-CN | zh-CN/en-US |
| VITE_ENABLE_DARK_MODE | 启用暗黑模式 | true | true/false |
| VITE_ANIMATION_ENABLED | 启用动画 | true | true/false |
| VITE_ENABLE_BUNDLE_ANALYZER | 启用包分析 | false | true/false |
| VITE_ENABLE_SOURCE_MAP | 启用源码映射 | true | true/false |
| VITE_WEBSOCKET_URL | WebSocket地址 | ws://localhost:8000/ws | 有效WebSocket URL |
| VITE_CDN_URL | CDN地址 | 空 | 有效URL |
| VITE_ENABLE_CSRF | 启用CSRF防护 | true | true/false |
| VITE_CSRF_HEADER_NAME | CSRF头名称 | X-CSRF-Token | 字符串 |

## 🌐 代理配置

### 开发环境代理

```typescript
// vite.config.ts 中的代理配置
server: {
  proxy: {
    // API 代理
    '/api': {
      target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
      ws: true,
      rewrite: (path) => path,
      
      // 请求头处理
      headers: {
        'X-Forwarded-Proto': 'http',
        'X-Forwarded-Host': 'localhost:5173',
        'X-Real-IP': '127.0.0.1'
      },
      
      // 错误处理
      onError: (err, req, res) => {
        console.error('Proxy error:', err);
        res.statusCode = 500;
        res.end('Proxy error');
      },
      
      // 代理请求拦截
      onProxyReq: (proxyReq, req, res) => {
        console.log(`Proxying ${req.method} ${req.url} to ${proxyReq.path}`);
        
        // 添加认证头
        const token = req.headers.authorization;
        if (token) {
          proxyReq.setHeader('Authorization', token);
        }
        
        // 添加CSRF头
        const csrfToken = req.headers['x-csrf-token'];
        if (csrfToken) {
          proxyReq.setHeader('X-CSRF-Token', csrfToken);
        }
      },
      
      // 代理响应拦截
      onProxyRes: (proxyRes, req, res) => {
        console.log(`Received ${proxyRes.statusCode} from proxy`);
        
        // 处理CORS
        proxyRes.headers['access-control-allow-origin'] = '*';
        proxyRes.headers['access-control-allow-methods'] = 'GET, POST, PUT, DELETE, OPTIONS';
        proxyRes.headers['access-control-allow-headers'] = 'Content-Type, Authorization, X-CSRF-Token';
      }
    },
    
    // WebSocket 代理
    '/ws': {
      target: process.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000',
      changeOrigin: true,
      ws: true,
      rewrite: (path) => path.replace(/^\/ws/, '/ws')
    },
    
    // 文件上传代理
    '/upload': {
      target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
      changeOrigin: true,
      timeout: 300000, // 5分钟超时
      headers: {
        'Connection': 'keep-alive'
      }
    }
  }
}
```

### 生产环境代理配置

```nginx
# Nginx 配置示例
server {
    listen 80;
    server_name workflow.example.com;
    
    # 前端静态文件
    location / {
        root /var/www/workflow-frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # 缓存控制
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API 代理
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
    
    # WebSocket 代理
    location /ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 超时
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

## 🎨 样式配置

### CSS 变量配置

```css
/* src/styles/variables.css */
:root {
  /* 颜色系统 */
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;
  --color-primary-active: #1d4ed8;
  
  --color-secondary: #64748b;
  --color-secondary-hover: #475569;
  --color-secondary-active: #334155;
  
  --color-success: #10b981;
  --color-success-hover: #059669;
  --color-success-active: #047857;
  
  --color-warning: #f59e0b;
  --color-warning-hover: #d97706;
  --color-warning-active: #b45309;
  
  --color-error: #ef4444;
  --color-error-hover: #dc2626;
  --color-error-active: #b91c1c;
  
  /* 字体系统 */
  --font-family-base: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --font-family-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 1.875rem;
  
  /* 间距系统 */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --spacing-2xl: 3rem;
  --spacing-3xl: 4rem;
  
  /* 圆角系统 */
  --radius-sm: 0.125rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-2xl: 1rem;
  --radius-full: 9999px;
  
  /* 阴影系统 */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  
  /* 工作流特定变量 */
  --workflow-node-width: 180px;
  --workflow-node-height: 80px;
  --workflow-node-min-width: 120px;
  --workflow-node-min-height: 60px;
  --workflow-edge-stroke: #64748b;
  --workflow-edge-stroke-width: 2px;
  --workflow-edge-stroke-hover: #3b82f6;
  --workflow-edge-stroke-width-hover: 3px;
  
  /* 动画变量 */
  --animation-duration-fast: 150ms;
  --animation-duration-normal: 250ms;
  --animation-duration-slow: 350ms;
  --animation-easing-ease: ease;
  --animation-easing-ease-in: ease-in;
  --animation-easing-ease-out: ease-out;
  --animation-easing-ease-in-out: ease-in-out;
}

/* 暗黑模式变量 */
[data-theme="dark"] {
  --color-primary: #60a5fa;
  --color-primary-hover: #3b82f6;
  --color-primary-active: #2563eb;
  
  --color-background: #0f172a;
  --color-foreground: #f8fafc;
  
  /* 其他暗黑模式变量... */
}
```

### 主题切换配置

```typescript
// src/config/theme.ts
export interface ThemeConfig {
  colors: {
    primary: string;
    secondary: string;
    success: string;
    warning: string;
    error: string;
  };
  fonts: {
    family: string;
    sizes: Record<string, string>;
  };
  spacing: Record<string, string>;
  borderRadius: Record<string, string>;
  shadows: Record<string, string>;
}

export const lightTheme: ThemeConfig = {
  colors: {
    primary: '#3b82f6',
    secondary: '#64748b',
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444'
  },
  fonts: {
    family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    sizes: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem'
    }
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem'
  },
  borderRadius: {
    sm: '0.125rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem',
    full: '9999px'
  },
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
  }
};

export const darkTheme: ThemeConfig = {
  colors: {
    primary: '#60a5fa',
    secondary: '#94a3b8',
    success: '#34d399',
    warning: '#fbbf24',
    error: '#f87171'
  },
  // 其他暗黑模式配置...
};
```

## 🔍 性能优化配置

### 代码分割配置

```typescript
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      manualChunks: (id) => {
        // React 相关
        if (id.includes('react') || id.includes('react-dom')) {
          return 'react-vendor';
        }
        
        // UI 组件库
        if (id.includes('@radix-ui') || id.includes('lucide-react')) {
          return 'ui-vendor';
        }
        
        // 工作流相关
        if (id.includes('@xyflow')) {
          return 'flow-vendor';
        }
        
        // 状态管理
        if (id.includes('zustand') || id.includes('@tanstack/react-query')) {
          return 'state-vendor';
        }
        
        // 工具函数
        if (id.includes('clsx') || id.includes('tailwind-merge')) {
          return 'utils-vendor';
        }
        
        // Monaco 编辑器（大文件）
        if (id.includes('monaco-editor')) {
          return 'editor-vendor';
        }
        
        // 图表库
        if (id.includes('recharts')) {
          return 'charts-vendor';
        }
      }
    }
  }
}
```

### 预加载配置

```html
<!-- index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <link rel="icon" type="image/svg+xml" href="/vite.svg" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  
  <!-- 预加载关键资源 -->
  <link rel="preload" href="/src/main.tsx" as="script" />
  <link rel="preload" href="/src/index.css" as="style" />
  
  <!-- 预连接外部域名 -->
  <link rel="preconnect" href="https://api.example.com" />
  <link rel="dns-prefetch" href="https://api.example.com" />
  
  <!-- 字体预加载 -->
  <link rel="preload" href="/fonts/inter-var-latin.woff2" as="font" type="font/woff2" crossorigin />
  
  <title>工作流引擎</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

### 懒加载配置

```typescript
// src/router/lazyLoad.ts
import { lazy, Suspense } from 'react';
import { LoadingSpinner } from '@components/ui/loading';

// 路由懒加载
export const LazyCanvasPanel = lazy(() => 
  import('@components/layout/CanvasPanel').then(module => ({ 
    default: module.CanvasPanel 
  }))
);

export const LazyChatPanel = lazy(() => 
  import('@components/layout/ChatPanel').then(module => ({ 
    default: module.ChatPanel 
  }))
);

// 组件懒加载包装器
export function withLazyLoad(Component: React.ComponentType<any>) {
  return function LazyLoadedComponent(props: any) {
    return (
      <Suspense fallback={<LoadingSpinner />}>
        <Component {...props} />
      </Suspense>
    );
  };
}
```

## 🛡️ 安全配置

### 内容安全策略 (CSP)

```html
<!-- index.html -->
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net;
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  img-src 'self' data: https:;
  connect-src 'self' ws: wss: http: https:;
  worker-src 'self' blob:;
  frame-src 'none';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
">

<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="X-Frame-Options" content="DENY">
<meta http-equiv="X-XSS-Protection" content="1; mode=block">
<meta name="referrer" content="strict-origin-when-cross-origin">
```

### API 安全配置

```typescript
// src/api/security.ts
export interface SecurityConfig {
  csrf: {
    enabled: boolean;
    headerName: string;
    cookieName: string;
    tokenUrl: string;
  };
  cors: {
    enabled: boolean;
    allowedOrigins: string[];
    allowedMethods: string[];
    allowedHeaders: string[];
  };
  rateLimit: {
    enabled: boolean;
    maxRequests: number;
    windowMs: number;
  };
}

export const securityConfig: SecurityConfig = {
  csrf: {
    enabled: import.meta.env.VITE_ENABLE_CSRF === 'true',
    headerName: import.meta.env.VITE_CSRF_HEADER_NAME || 'X-CSRF-Token',
    cookieName: 'csrf-token',
    tokenUrl: '/api/csrf-token'
  },
  cors: {
    enabled: true,
    allowedOrigins: [
      'http://localhost:5173',
      'https://workflow.example.com'
    ],
    allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token']
  },
  rateLimit: {
    enabled: true,
    maxRequests: 100,
    windowMs: 15 * 60 * 1000 // 15分钟
  }
};
```

## 📊 构建配置

### 环境区分构建

```typescript
// build.config.ts
interface BuildConfig {
  mode: 'development' | 'production' | 'test';
  sourcemap: boolean;
  minify: boolean;
  analyze: boolean;
  gzip: boolean;
  brotli: boolean;
}

const buildConfigs: Record<string, BuildConfig> = {
  development: {
    mode: 'development',
    sourcemap: true,
    minify: false,
    analyze: false,
    gzip: false,
    brotli: false
  },
  production: {
    mode: 'production',
    sourcemap: false,
    minify: true,
    analyze: false,
    gzip: true,
    brotli: true
  },
  test: {
    mode: 'production',
    sourcemap: true,
    minify: true,
    analyze: false,
    gzip: false,
    brotli: false
  }
};

export const getBuildConfig = (env: string): BuildConfig => {
  return buildConfigs[env] || buildConfigs.development;
};
```

### 分析工具配置

```typescript
// 安装: npm install rollup-plugin-visualizer
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    react(),
    // 包大小分析
    visualizer({
      filename: './dist/stats.html',
      open: process.env.VITE_ENABLE_BUNDLE_ANALYZER === 'true',
      gzipSize: true,
      brotliSize: true
    })
  ]
});
```

## 🚀 部署配置

### Docker 配置

```dockerfile
# Dockerfile
FROM node:18-alpine as builder

WORKDIR /app

# 复制依赖文件
COPY package*.json ./
RUN npm ci --only=production

# 复制源码
COPY . .
RUN npm run build

# 生产镜像
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/nginx.conf

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Nginx 配置

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    
    # 基本设置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    server {
        listen 80;
        server_name _;
        
        # 根目录
        root /usr/share/nginx/html;
        index index.html;
        
        # 安全头
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        
        # 缓存控制
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            add_header Vary "Accept-Encoding";
        }
        
        # HTML 文件不缓存
        location ~* \.html$ {
            expires -1;
            add_header Cache-Control "no-cache, no-store, must-revalidate";
            add_header Pragma "no-cache";
            add_header Expires "0";
        }
        
        # API 代理
        location /api {
            proxy_pass http://backend:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # CORS
            add_header Access-Control-Allow-Origin "*";
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-CSRF-Token";
            
            # 预检请求处理
            if ($request_method = 'OPTIONS') {
                return 204;
            }
        }
        
        # WebSocket 代理
        location /ws {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # 健康检查
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
        
        # 前端路由支持
        location / {
            try_files $uri $uri/ /index.html;
        }
        
        # 错误页面
        error_page 404 /index.html;
        error_page 500 502 503 504 /50x.html;
        location = /50x.html {
            root /usr/share/nginx/html;
        }
    }
}
```

## 📈 监控配置

### 性能监控

```typescript
// src/config/monitoring.ts
export interface MonitoringConfig {
  enabled: boolean;
  sampleRate: number;
  endpoints: {
    metrics: string;
    traces: string;
    logs: string;
  };
  performance: {
    measureRenderTime: boolean;
    measureNetworkTime: boolean;
    measureUserInteraction: boolean;
  };
}

export const monitoringConfig: MonitoringConfig = {
  enabled: import.meta.env.VITE_ENABLE_MONITORING === 'true',
  sampleRate: 0.1, // 10% 采样率
  endpoints: {
    metrics: '/api/metrics',
    traces: '/api/traces',
    logs: '/api/logs'
  },
  performance: {
    measureRenderTime: true,
    measureNetworkTime: true,
    measureUserInteraction: true
  }
};
```

## 🔧 开发工具配置

### ESLint 配置

```javascript
// eslint.config.js
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      '@typescript-eslint/no-unused-vars': ['error', { 
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_' 
      }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-empty-function': 'off',
      '@typescript-eslint/no-non-null-assertion': 'warn'
    },
  },
)
```

### Prettier 配置

```json
// .prettierrc
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "bracketSpacing": true,
  "arrowParens": "avoid",
  "endOfLine": "lf",
  "jsxSingleQuote": true,
  "jsxBracketSameLine": false,
  "overrides": [
    {
      "files": "*.md",
      "options": {
        "printWidth": 80,
        "proseWrap": "always"
      }
    }
  ]
}
```

**注意**: 配置文件修改后需要重启开发服务器才能生效。生产环境配置请谨慎修改，建议在测试环境验证后再部署到生产环境。