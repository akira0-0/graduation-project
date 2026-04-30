import { useAppStore } from '../store/app'
import type { SSEEventType } from '../types'

const eventIcon: Record<SSEEventType, string> = {
  start: '🚀',
  analyzing: '🧠',
  matching: '⚡',
  gap_found: '🔍',
  generating: '🛠️',
  filtering: '🎯',
  relevance_checking: '✨',
  item_result: '📄',
  progress: '📊',
  complete: '✅',
  error: '❌',
}

export default function SSEProgress() {
  const { sse } = useAppStore()

  if (!sse.running && sse.events.length === 0) return null

  return (
    <div className="glass rounded-2xl p-4 space-y-3">
      {/* 进度条 */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full gradient-bg-primary rounded-full transition-all duration-500"
            style={{ width: `${sse.progress}%` }}
          />
        </div>
        <span className="text-xs text-slate-500 tabular-nums w-10 text-right">
          {sse.progress}%
        </span>
      </div>

      {/* 当前消息 */}
      {sse.currentMessage && (
        <p className={`text-sm text-slate-600 ${sse.running ? 'sse-cursor' : ''}`}>
          {sse.currentMessage}
        </p>
      )}

      {/* 事件日志（最近5条） */}
      <div className="space-y-1 max-h-32 overflow-y-auto">
        {sse.events.slice(-8).map((evt, i) => (
          <div key={i} className="flex items-start gap-2 text-xs text-slate-500 animate-slide-up">
            <span className="shrink-0">{eventIcon[evt.type] ?? '📌'}</span>
            <span className="opacity-80">{evt.message ?? evt.type}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
