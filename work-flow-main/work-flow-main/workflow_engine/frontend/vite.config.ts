import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // ── 工作流引擎（端口 8123）──────────────────────────────
      // 必须放在通配 /api 之前，Vite 按声明顺序匹配
      '/api/v1': {
        target: 'http://localhost:8123',
        changeOrigin: true,
      },

      // ── 过滤引擎（端口 8081）──────────────────────────────
      // /api/sessions/*  → 查询 session 元数据 / 结果
      '/api/sessions': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      // /api/frontend/*  → CommentData 适配器 / 轮询 status
      '/api/frontend': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      // /api/filter/*    → 三层过滤接口
      '/api/filter': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      // /api/db/*        → 数据库统计 / 样本
      '/api/db': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },

      // ── Lumina 后端（端口 8000）—— 兜底规则 ──────────────
      // /api/generate-report 及其他未匹配的 /api 路径
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
