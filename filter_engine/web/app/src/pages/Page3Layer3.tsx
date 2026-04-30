import { useEffect, useRef, useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { useAppStore } from '../store/app'
import { filterApi } from '../lib/api'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 20

const STATUS_STYLE: Record<string, string> = {
  accepted: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-50 text-red-500 border-red-200',
  pending:  'bg-slate-50 text-slate-500 border-slate-200',
}

export default function Page3Layer3() {
  const {
    sessionId,
    datasetItems, datasetTotal, datasetFallback, revealedCount,
    setDataset, setRevealedCount,
    unlockPage, goToPage,
  } = useAppStore()

  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const revealTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!sessionId) return
    setLoading(true)
    setError('')
    filterApi.getDataset(sessionId, PAGE_SIZE, 0)
      .then(async res => {
        let items = res.data
        let total = res.total
        let fallback = false
        if (items.length === 0) {
          const r2 = await filterApi.getL2Dataset(sessionId, PAGE_SIZE, 0)
          items = r2.data; total = r2.total; fallback = true
        }
        setDataset(items, total, fallback)
        setLoading(false)
        setRevealedCount(0)
        let n = 0
        revealTimer.current = setInterval(() => {
          n += 1
          setRevealedCount(n)
          if (n >= items.length) clearInterval(revealTimer.current!)
        }, 80)
      })
      .catch(e => { setError(e.message); setLoading(false) })
    return () => { if (revealTimer.current) clearInterval(revealTimer.current) }
  }, [sessionId])

  const handlePageChange = async (p: number) => {
    if (!sessionId) return
    setPage(p)
    setLoading(true)
    try {
      const offset = (p - 1) * PAGE_SIZE
      const res = datasetFallback
        ? await filterApi.getL2Dataset(sessionId, PAGE_SIZE, offset)
        : await filterApi.getDataset(sessionId, PAGE_SIZE, offset)
      setDataset(res.data, res.total, datasetFallback)
      setRevealedCount(res.data.length)
    } catch { /* ignore */ } finally { setLoading(false) }
  }

  if (!sessionId) {
    return <div className="max-w-2xl mx-auto text-center text-slate-400 py-12">请先完成前两步筛选</div>
  }

  const visibleItems = datasetItems.slice(0, revealedCount)

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center space-y-1">
        <h2 className="text-xl font-bold text-slate-900">🧠 Layer-3 数据集</h2>
        <p className="text-slate-500 text-sm">语义研判结果 · 共 {datasetTotal} 条</p>
      </div>

      {datasetFallback && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-700">
          ⚠️ Layer-3 暂无结果，当前展示 Layer-2 通过数据（fallback）
        </div>
      )}

      {loading && <div className="text-center text-slate-400 text-sm py-4 animate-pulse">加载中…</div>}
      {error && <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">{error}</div>}

      <div className="space-y-2">
        {visibleItems.map((item, i) => (
          <div key={item.id ?? i}
            className={`rounded-xl px-4 py-3 border transition-all duration-300 ${STATUS_STYLE[item.status] ?? STATUS_STYLE.pending}`}
            style={{ opacity: 1, transform: 'translateY(0)' }}>
            <div className="flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-700 leading-relaxed">{item.content}</p>
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <span className="text-[10px] text-slate-400">{item.user}</span>
                  <span className="text-[10px] text-slate-300">·</span>
                  <span className="text-[10px] text-slate-400">{item.platform}</span>
                  {item.likes > 0 && <span className="text-[10px] text-slate-400">❤ {item.likes}</span>}
                  {item.rejectionReason && <span className="text-[10px] text-red-400">{item.rejectionReason}</span>}
                </div>
              </div>
              <span className={`shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full border ${STATUS_STYLE[item.status] ?? STATUS_STYLE.pending}`}>
                {item.status === 'accepted' ? '✅ 通过' : item.status === 'rejected' ? '❌ 过滤' : item.status}
              </span>
            </div>
          </div>
        ))}
      </div>

      {datasetTotal > PAGE_SIZE && (
        <Pagination page={page} pageSize={PAGE_SIZE} total={datasetTotal} onChange={handlePageChange} />
      )}

      {datasetItems.length > 0 && (
        <button onClick={() => { unlockPage(4); goToPage(4) }}
          className="w-full py-4 bg-indigo-500 hover:bg-indigo-600 text-white font-semibold rounded-2xl transition-all flex items-center justify-center gap-2 text-sm shadow-sm shadow-indigo-200">
          进入数据集选择<ArrowRight size={16} />
        </button>
      )}
    </div>
  )
}
