import { useState, useEffect } from 'react'
import { useAppStore } from '../../store/app'
import { fetchSSE } from '../../lib/api'
import { ChevronRight, CheckCircle, XCircle, Loader } from 'lucide-react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
} from 'recharts'
import SSEProgress from '../SSEProgress'

const PIE_COLORS = ['#10b981', '#ef4444', '#f59e0b']

export default function Step5Filter() {
  const {
    query, scenario, contents, queryIntent,
    setFilterResult, filterResult,
    completeStep, sseStart, ssePush, sseDone, sseError, sseClear,
    sse,
  } = useAppStore()
  const [loading, setLoading] = useState(false)

  const runFilter = async () => {
    setLoading(true)
    sseClear()
    sseStart()
    ssePush({ type: 'start', message: '🚀 启动智能过滤管道...', progress: 5 })

    await fetchSSE({
      url: '/filter/smart',
      body: {
        query,
        contents,
        scenario: queryIntent?.scenario ?? scenario,
        apply_gap_rules: true,
      },
      onEvent: (evt) => {
        ssePush(evt)
        if (evt.type === 'complete' && evt.data) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          setFilterResult(evt.data as any)
        }
      },
      onError: (e) => sseError(e.message),
      onDone: () => { sseDone(); setLoading(false) },
    })

    // 若 SSE 未返回流式数据，fallback 到直接 fetch
    if (!filterResult) {
      try {
        const res = await fetch('/api/filter/smart', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, contents, scenario: queryIntent?.scenario ?? scenario, apply_gap_rules: true }),
        })
        if (res.ok) {
          const data = await res.json()
          setFilterResult(data)
          ssePush({ type: 'complete', message: '✅ 过滤完成', progress: 100 })
          sseDone()
        }
      } catch { /* ignore */ }
    }
    setLoading(false)
  }

  // 触发后直接运行
  useEffect(() => {
    if (!filterResult && !loading && !sse.running && contents.length > 0) {
      runFilter()
    }
  }, [])

  const pieData = filterResult ? [
    { name: '通过', value: filterResult.passed },
    { name: '过滤', value: filterResult.filtered },
  ] : []

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="text-center space-y-1">
        <div className="text-4xl animate-float">🎯</div>
        <h2 className="text-xl font-bold text-slate-900">智能过滤结果</h2>
        <p className="text-slate-500 text-xs">Layer-2：场景规则 + LLM 缺口分析</p>
      </div>

      {/* SSE 进度 */}
      {(sse.running || (sse.events.length > 0 && !filterResult)) && (
        <SSEProgress />
      )}

      {/* 加载中占位 */}
      {loading && !filterResult && (
        <div className="glass rounded-2xl p-8 flex flex-col items-center gap-3 text-slate-500">
          <Loader size={32} className="animate-spin-slow text-indigo-400" />
          <p className="text-sm">正在处理 {contents.length} 条内容...</p>
        </div>
      )}

      {filterResult && (
        <>
          {/* 统计卡片 */}
          <div className="grid grid-cols-3 gap-3">
            <div className="glass-strong rounded-2xl p-3 text-center">
              <div className="text-2xl font-bold text-slate-900">{filterResult.total_input}</div>
              <div className="text-xs text-slate-400 mt-1">总计</div>
            </div>
            <div className="glass-strong rounded-2xl p-3 text-center">
              <div className="text-2xl font-bold text-emerald-600">{filterResult.passed}</div>
              <div className="text-xs text-slate-400 mt-1">通过</div>
            </div>
            <div className="glass-strong rounded-2xl p-3 text-center">
              <div className="text-2xl font-bold text-red-500">{filterResult.filtered}</div>
              <div className="text-xs text-slate-400 mt-1">过滤</div>
            </div>
          </div>

          {/* 饼图 */}
          <div className="glass rounded-2xl p-4">
            <div className="text-xs text-slate-500 mb-2">通过/过滤分布</div>
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 12, color: '#0f172a', boxShadow: '0 4px 16px rgba(0,0,0,0.08)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* 内容结果列表 */}
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {filterResult.results?.map((r, i) => (
              <div key={i} className={`glass rounded-xl p-3 flex gap-3 border ${r.passed ? 'border-emerald-300/60 bg-emerald-50/40' : 'border-red-300/60 bg-red-50/40'}`}>
                <div className="shrink-0 mt-0.5">
                  {r.passed
                    ? <CheckCircle size={14} className="text-emerald-500" />
                    : <XCircle size={14} className="text-red-500" />
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-700 line-clamp-2">{r.text}</p>
                  {r.matched_rules?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {r.matched_rules.slice(0, 2).map(rule => (
                        <span key={rule.id} className="text-[10px] px-1.5 py-0.5 bg-red-50 text-red-600 rounded border border-red-200">
                          {rule.name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={() => completeStep(5)}
            className="w-full flex items-center justify-center gap-2 gradient-bg-primary glow-primary text-white font-semibold py-3 rounded-2xl hover:scale-[1.02] transition-all"
          >
            进入相关性排序 <ChevronRight size={16} />
          </button>
        </>
      )}
    </div>
  )
}
