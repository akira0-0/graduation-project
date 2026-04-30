import { useState, useEffect } from 'react'
import { useAppStore } from '../../store/app'
import { fetchSSE } from '../../lib/api'
import { Star, Download, RefreshCw } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import SSEProgress from '../SSEProgress'

const LEVEL_CONFIG = {
  high:   { label: '高相关', color: 'text-emerald-600', bar: '#10b981', bg: 'border-emerald-200 bg-emerald-50' },
  medium: { label: '中相关', color: 'text-indigo-600',  bar: '#6366f1', bg: 'border-indigo-200 bg-indigo-50' },
  low:    { label: '低相关', color: 'text-amber-600',   bar: '#f59e0b', bg: 'border-amber-200 bg-amber-50' },
  none:   { label: '不相关', color: 'text-slate-400',   bar: '#cbd5e1', bg: 'border-slate-200 bg-slate-50' },
}

export default function Step6Relevance() {
  const {
    query, filterResult, relevanceResult,
    setRelevanceResult, sse,
    sseStart, ssePush, sseDone, sseError, sseClear,
  } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [minLevel, setMinLevel] = useState<'high' | 'medium' | 'low'>('medium')

  const passedTexts = filterResult?.results?.filter(r => r.passed).map(r => r.text) ?? []

  const runRelevance = async () => {
    if (passedTexts.length === 0) return
    setLoading(true)
    sseClear()
    sseStart()
    ssePush({ type: 'start', message: '🚀 启动 Layer-3 LLM 语义相关性筛选...', progress: 5 })
    ssePush({ type: 'relevance_checking', message: `✨ 分析 ${passedTexts.length} 条内容的语义相关性...`, progress: 20 })

    await fetchSSE({
      url: '/filter/relevance',
      body: { query, texts: passedTexts, filter_spam: false, filter_relevance: true, min_relevance: minLevel },
      onEvent: (evt) => {
        ssePush(evt)
        if (evt.type === 'complete' && evt.data) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          setRelevanceResult(evt.data as any)
        }
      },
      onError: (e) => sseError(e.message),
      onDone: () => { sseDone(); setLoading(false) },
    })

    // fallback
    if (!relevanceResult) {
      try {
        const res = await fetch('/api/filter/relevance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, texts: passedTexts, filter_spam: false, filter_relevance: true, min_relevance: minLevel }),
        })
        if (res.ok) {
          const data = await res.json()
          setRelevanceResult(data)
          ssePush({ type: 'complete', message: '✅ 相关性分析完成', progress: 100 })
          sseDone()
        }
      } catch { /* ignore */ }
    }
    setLoading(false)
  }

  useEffect(() => {
    if (!relevanceResult && !loading && !sse.running && passedTexts.length > 0) {
      runRelevance()
    }
  }, [])

  // 图表数据
  const barData = Object.entries(LEVEL_CONFIG).map(([level, cfg]) => ({
    level: cfg.label,
    count: relevanceResult?.results?.filter(r => r.relevance_level === level).length ?? 0,
    fill: cfg.bar,
  }))

  const exportJSON = () => {
    if (!relevanceResult) return
    const blob = new Blob([JSON.stringify(relevanceResult, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `filter_result_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="text-center space-y-1">
        <div className="text-4xl animate-float">✨</div>
        <h2 className="text-xl font-bold text-slate-900">相关性排序</h2>
        <p className="text-slate-500 text-xs">Layer-3：LLM 语义深度筛选与排序</p>
      </div>

      {/* 参数选择 */}
      {!relevanceResult && (
        <div className="glass-strong rounded-2xl p-4 space-y-3">
          <div className="text-xs text-slate-500">最低相关性阈值</div>
          <div className="flex gap-2">
            {(['high', 'medium', 'low'] as const).map(l => (
              <button
                key={l}
                onClick={() => setMinLevel(l)}
                className={`flex-1 py-2 text-xs font-semibold rounded-xl border transition-all ${
                  minLevel === l
                    ? `${LEVEL_CONFIG[l].bg} ${LEVEL_CONFIG[l].color}`
                    : 'bg-white border-slate-200 text-slate-500 hover:text-slate-900 hover:border-slate-300'
                }`}
              >
                {LEVEL_CONFIG[l].label}
              </button>
            ))}
          </div>
          <button
            onClick={runRelevance}
            disabled={loading || passedTexts.length === 0}
            className="w-full gradient-bg-primary glow-primary text-white font-semibold py-3 rounded-2xl hover:scale-[1.02] transition-all disabled:opacity-40"
          >
            {loading ? '⚙️ 分析中...' : `分析 ${passedTexts.length} 条内容`}
          </button>
        </div>
      )}

      {/* SSE 进度 */}
      {(sse.running || (sse.events.length > 0 && !relevanceResult)) && <SSEProgress />}

      {relevanceResult && (
        <>
          {/* 统计 & 图表 */}
          <div className="glass rounded-2xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-700 font-medium">相关性分布</span>
              <div className="flex gap-2">
                <button onClick={runRelevance} className="p-1.5 glass rounded-lg text-slate-500 hover:text-slate-900 transition-colors">
                  <RefreshCw size={12} />
                </button>
                <button onClick={exportJSON} className="flex items-center gap-1 glass rounded-lg px-2 py-1.5 text-xs text-slate-500 hover:text-slate-900 transition-colors">
                  <Download size={12} />
                  导出
                </button>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={barData} margin={{ top: 4, right: 4, left: -20, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis dataKey="level" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 12, color: '#0f172a', boxShadow: '0 4px 16px rgba(0,0,0,0.08)' }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {barData.map((entry, i) => (
                    <rect key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* 结果列表 */}
          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {relevanceResult.results
              ?.sort((a, b) => b.relevance_score - a.relevance_score)
              .map((item, i) => {
                const cfg = LEVEL_CONFIG[item.relevance_level as keyof typeof LEVEL_CONFIG] ?? LEVEL_CONFIG.none
                return (
                  <div key={i} className={`glass rounded-xl p-3 border ${cfg.bg} animate-slide-up`}>
                    <div className="flex items-start gap-2">
                      <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
                        <Star size={12} className={cfg.color} fill={item.relevance_level === 'high' ? 'currentColor' : 'none'} />
                        <span className={`text-xs font-semibold ${cfg.color}`}>{cfg.label}</span>
                        <span className="text-xs text-slate-400 font-mono">{(item.relevance_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <p className="text-sm text-slate-700 mt-1.5 line-clamp-3">{item.text}</p>
                    {item.reason && (
                      <p className="text-xs text-slate-400 mt-1 italic">{item.reason}</p>
                    )}
                  </div>
                )
              })
            }
          </div>

          {/* 最终汇总 */}
          <div className="glass-strong rounded-2xl p-4 glow-success">
            <div className="text-center space-y-1">
              <div className="text-3xl">🎉</div>
              <p className="text-slate-900 font-bold">Pipeline 完成！</p>
              <p className="text-slate-500 text-xs">
                从 <span className="text-slate-900 font-semibold">{filterResult?.total_input}</span> 条内容
                → 过滤后 <span className="text-indigo-600 font-semibold">{passedTexts.length}</span> 条
                → 高相关 <span className="text-emerald-600 font-semibold">{relevanceResult.results?.filter(r => r.relevance_level === 'high').length ?? 0}</span> 条
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
