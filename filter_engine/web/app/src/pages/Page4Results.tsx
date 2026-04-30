import { useState } from 'react'
import { Download, CheckSquare, Square, RotateCcw } from 'lucide-react'
import { useAppStore } from '../store/app'
import { filterApi } from '../lib/api'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 20

export default function Page4Results() {
  const {
    sessionId, query,
    datasetItems, datasetTotal, datasetFallback,
    selectedIndices, toggleSelected, selectAll, clearSelected,
    setDataset,
  } = useAppStore()

  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState<'all' | 'accepted' | 'rejected'>('all')
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)

  const filtered = datasetItems.filter(item =>
    filter === 'all' ? true : item.status === filter
  )

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
    } catch { /* ignore */ } finally { setLoading(false) }
  }

  const selected = Array.from(selectedIndices)
  const selectedItems = selected.map(i => datasetItems[i]).filter(Boolean)

  const handleExport = () => {
    const data = { query, total: selectedItems.length, items: selectedItems }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `dataset_${Date.now()}.json`; a.click()
    URL.revokeObjectURL(url)
  }

  const handleCopy = () => {
    const text = selectedItems.map(item => item.content).join('\n\n---\n\n')
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 2000)
    })
  }

  if (!sessionId) {
    return <div className="max-w-2xl mx-auto text-center text-slate-400 py-12">请先完成前三步筛选</div>
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center space-y-1">
        <h2 className="text-xl font-bold text-slate-900">✅ 数据集选择</h2>
        <p className="text-slate-500 text-sm">共 {datasetTotal} 条 · 已选 {selectedIndices.size} 条</p>
      </div>

      {datasetFallback && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-700">
          ⚠️ 当前为 Layer-2 fallback 数据
        </div>
      )}

      {/* 工具栏 */}
      <div className="glass rounded-2xl px-4 py-3 flex items-center gap-3 flex-wrap">
        <div className="flex gap-2">
          {(['all', 'accepted', 'rejected'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-all ${filter === f ? 'bg-indigo-50 border-indigo-300 text-indigo-700 font-medium' : 'border-slate-200 text-slate-500'}`}>
              {f === 'all' ? '全部' : f === 'accepted' ? '✅ 通过' : '❌ 过滤'}
            </button>
          ))}
        </div>
        <div className="ml-auto flex gap-2">
          <button onClick={() => selectAll(filtered.map((_, i) => i))}
            className="text-xs px-3 py-1.5 rounded-full border border-indigo-200 text-indigo-600 hover:bg-indigo-50 flex items-center gap-1">
            <CheckSquare size={12} />全选
          </button>
          <button onClick={clearSelected}
            className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-500 hover:bg-slate-50 flex items-center gap-1">
            <RotateCcw size={12} />清空
          </button>
        </div>
      </div>

      {/* 列表 */}
      {loading && <div className="text-center text-slate-400 text-sm py-4 animate-pulse">加载中…</div>}
      <div className="space-y-2">
        {filtered.map((item, i) => {
          const globalIdx = datasetItems.indexOf(item)
          const isSelected = selectedIndices.has(globalIdx)
          return (
            <div key={item.id ?? i}
              onClick={() => toggleSelected(globalIdx)}
              className={`rounded-xl px-4 py-3 border cursor-pointer transition-all ${isSelected ? 'bg-indigo-50 border-indigo-300' : 'bg-white border-slate-200 hover:border-indigo-200'}`}>
              <div className="flex items-start gap-3">
                <div className="shrink-0 mt-0.5">
                  {isSelected ? <CheckSquare size={14} className="text-indigo-500" /> : <Square size={14} className="text-slate-300" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-700 leading-relaxed">{item.content}</p>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className="text-[10px] text-slate-400">{item.user}</span>
                    <span className="text-[10px] text-slate-300">·</span>
                    <span className="text-[10px] text-slate-400">{item.platform}</span>
                    {item.likes > 0 && <span className="text-[10px] text-slate-400">❤ {item.likes}</span>}
                  </div>
                </div>
                <span className={`shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full border ${item.status === 'accepted' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-500 border-red-200'}`}>
                  {item.status === 'accepted' ? '通过' : '过滤'}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {datasetTotal > PAGE_SIZE && (
        <Pagination page={page} pageSize={PAGE_SIZE} total={datasetTotal} onChange={handlePageChange} />
      )}

      {/* 导出区 */}
      {selectedIndices.size > 0 && (
        <div className="glass-strong rounded-2xl p-4 flex items-center gap-3">
          <span className="text-sm text-slate-600 font-medium">已选 {selectedIndices.size} 条</span>
          <div className="ml-auto flex gap-2">
            <button onClick={handleCopy}
              className="text-xs px-4 py-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 transition-all">
              {copied ? '✅ 已复制' : '📋 复制文本'}
            </button>
            <button onClick={handleExport}
              className="text-xs px-4 py-2 rounded-xl bg-indigo-500 hover:bg-indigo-600 text-white font-semibold flex items-center gap-1.5 transition-all">
              <Download size={12} />导出 JSON
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
