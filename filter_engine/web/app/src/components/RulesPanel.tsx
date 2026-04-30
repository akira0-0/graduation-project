import { useEffect, useState } from 'react'
import { useAppStore } from '../store/app'
import { rulesApi } from '../lib/api'
import type { Rule, RuleCreate, RuleType, RuleCategory, RuleAction } from '../types'
import { ToggleLeft, ToggleRight, Trash2, RefreshCw, Plus, Pencil, X, Search } from 'lucide-react'

const TYPE_COLOR: Record<string, string> = {
  keyword:  'bg-blue-50 text-blue-600 border border-blue-200',
  regex:    'bg-purple-50 text-purple-600 border border-purple-200',
  semantic: 'bg-amber-50 text-amber-600 border border-amber-200',
  llm:      'bg-emerald-50 text-emerald-600 border border-emerald-200',
}
const ACTION_COLOR: Record<string, string> = {
  filter: 'bg-red-50 text-red-500 border border-red-200',
  select: 'bg-green-50 text-green-600 border border-green-200',
  flag:   'bg-yellow-50 text-yellow-600 border border-yellow-200',
}

const EMPTY_FORM: RuleCreate = {
  name: '', type: 'keyword', content: '',
  category: undefined, priority: 50,
  description: '', action: 'filter',
}

// ── 新建 / 编辑 弹窗 ──────────────────────────────────────
function RuleModal({
  initial, onSave, onClose,
}: {
  initial: RuleCreate & { id?: number }
  onSave: () => void
  onClose: () => void
}) {
  const [form, setForm] = useState<RuleCreate & { id?: number }>(initial)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const set = (patch: Partial<typeof form>) => setForm(f => ({ ...f, ...patch }))

  const submit = async () => {
    if (!form.name.trim()) return setErr('名称不能为空')
    if (!form.content.trim()) return setErr('规则内容不能为空')
    setSaving(true); setErr('')

    // 将用户输入自动转换为后端要求的 JSON 格式
    let contentJson: string
    const raw = form.content.trim()
    if (form.type === 'keyword' || form.type === 'regex') {
      // 若用户已经输入了 JSON 数组则直接用；否则按逗号/换行分割转换
      try {
        const parsed = JSON.parse(raw)
        contentJson = Array.isArray(parsed) ? raw : JSON.stringify([raw])
      } catch {
        const items = raw.split(/[,，\n]+/).map(s => s.trim()).filter(Boolean)
        contentJson = JSON.stringify(items)
      }
    } else {
      // semantic / llm：若已是合法 JSON 直接用，否则包成 JSON 字符串
      try {
        JSON.parse(raw)
        contentJson = raw
      } catch {
        contentJson = JSON.stringify(raw)
      }
    }

    try {
      const payload = { ...form, content: contentJson }
      if (form.id != null) {
        await rulesApi.update(form.id, payload)
      } else {
        await rulesApi.create(payload)
      }
      onSave()
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const field = 'glass rounded-xl px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-300'
  const label = 'text-xs font-medium text-slate-500 mb-1'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white/95 rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900">{form.id != null ? '编辑规则' : '新建规则'}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* body */}
        <div className="p-5 space-y-3 max-h-[70vh] overflow-y-auto">
          {/* 名称 */}
          <div>
            <div className={label}>名称 *</div>
            <input className={field} placeholder="规则名称" value={form.name}
              onChange={e => set({ name: e.target.value })} />
          </div>

          {/* 类型 + 动作 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className={label}>类型 *</div>
              <select className={field} value={form.type}
                onChange={e => set({ type: e.target.value as RuleType })}>
                <option value="keyword">keyword</option>
                <option value="regex">regex</option>
                <option value="semantic">semantic</option>
                <option value="llm">llm</option>
              </select>
            </div>
            <div>
              <div className={label}>动作</div>
              <select className={field} value={form.action ?? 'filter'}
                onChange={e => set({ action: e.target.value as RuleAction })}>
                <option value="filter">filter（过滤）</option>
                <option value="select">select（保留）</option>
                <option value="flag">flag（标记）</option>
              </select>
            </div>
          </div>

          {/* 内容 */}
          <div>
            <div className={label}>规则内容 *</div>
            <textarea className={`${field} resize-none`} rows={3}
              placeholder={
                form.type === 'keyword' ? '输入关键词，多个用逗号或换行分隔，如：广告,推广,代购' :
                form.type === 'regex'   ? '输入正则表达式，多个用逗号或换行分隔，如：\\d{11},1[3-9]\\d{9}' :
                                          '输入规则描述文本，如：包含情感化语言或主观判断的内容'
              }
              value={form.content} onChange={e => set({ content: e.target.value })} />
            <div className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              {(form.type === 'keyword' || form.type === 'regex')
                ? '💡 多个条目用逗号 / 换行分隔，自动转为 JSON 数组提交'
                : '💡 输入自然语言描述即可，无需手动格式化'}
            </div>
          </div>

          {/* 分类 + 优先级 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className={label}>分类</div>
              <select className={field} value={form.category ?? ''}
                onChange={e => set({ category: e.target.value as RuleCategory || undefined })}>
                <option value="">—</option>
                <option value="spam">spam</option>
                <option value="ad">ad</option>
                <option value="political">political</option>
                <option value="nsfw">nsfw</option>
                <option value="irrelevant">irrelevant</option>
                <option value="custom">custom</option>
              </select>
            </div>
            <div>
              <div className={label}>优先级（0–100）</div>
              <input type="number" min={0} max={100} className={field}
                value={form.priority ?? 50}
                onChange={e => set({ priority: Number(e.target.value) })} />
            </div>
          </div>

          {/* 描述 */}
          <div>
            <div className={label}>描述</div>
            <input className={field} placeholder="可选备注" value={form.description ?? ''}
              onChange={e => set({ description: e.target.value })} />
          </div>

          {err && <div className="text-xs text-red-500 bg-red-50 rounded-lg px-3 py-2">{err}</div>}
        </div>

        {/* footer */}
        <div className="flex gap-2 px-5 py-4 border-t border-slate-100 justify-end">
          <button onClick={onClose}
            className="glass rounded-xl px-4 py-2 text-xs text-slate-500 hover:text-slate-900 transition-colors">
            取消
          </button>
          <button onClick={submit} disabled={saving}
            className="rounded-xl px-4 py-2 text-xs text-white bg-indigo-500 hover:bg-indigo-600 transition-colors disabled:opacity-60">
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── 主组件 ────────────────────────────────────────────────
export default function RulesPanel() {
  const { rules, ruleStats, setRules, setRuleStats } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [modal, setModal] = useState<(RuleCreate & { id?: number }) | null>(null)

  const loadRules = async () => {
    setLoading(true)
    try {
      const [list, stats] = await Promise.all([rulesApi.list(), rulesApi.stats()])
      setRules(list)
      setRuleStats(stats)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadRules() }, [])

  const toggle = async (rule: Rule) => {
    await rulesApi.toggle(rule.id)
    loadRules()
  }

  const remove = async (rule: Rule) => {
    if (!confirm(`确认删除规则「${rule.name}」？`)) return
    await rulesApi.delete(rule.id)
    loadRules()
  }

  const openEdit = (rule: Rule) => setModal({
    id: rule.id, name: rule.name, type: rule.type,
    content: rule.content, category: rule.category ?? undefined,
    priority: rule.priority, description: rule.description, action: rule.action,
  })

  const filtered = rules.filter(r => {
    const matchType = typeFilter === 'all' || r.type === typeFilter
    const matchSearch = !search || r.name.includes(search) || r.content.includes(search)
    return matchType && matchSearch
  })

  return (
    <div className="space-y-4">
      {/* 统计 */}
      {ruleStats && (
        <div className="grid grid-cols-4 gap-3">
          <div className="glass rounded-xl p-3 text-center">
            <div className="text-xl font-bold text-slate-900">{ruleStats.total}</div>
            <div className="text-xs text-slate-500 mt-1">总规则</div>
          </div>
          <div className="glass rounded-xl p-3 text-center">
            <div className="text-xl font-bold text-emerald-600">{ruleStats.enabled}</div>
            <div className="text-xs text-slate-500 mt-1">已启用</div>
          </div>
          {Object.entries(ruleStats.by_type ?? {}).slice(0, 2).map(([type, count]) => (
            <div key={type} className="glass rounded-xl p-3 text-center">
              <div className="text-xl font-bold text-indigo-600">{count as number}</div>
              <div className="text-xs text-slate-500 mt-1">{type}</div>
            </div>
          ))}
        </div>
      )}

      {/* 操作栏 */}
      <div className="flex items-center gap-2">
        {/* 搜索 */}
        <div className="relative flex-1">
          <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input className="glass rounded-xl pl-8 pr-3 py-2 text-xs w-full focus:outline-none focus:ring-2 focus:ring-indigo-200"
            placeholder="搜索名称 / 内容…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        {/* 类型筛选 */}
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          className="glass rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-200">
          <option value="all">全部类型</option>
          <option value="keyword">keyword</option>
          <option value="regex">regex</option>
          <option value="semantic">semantic</option>
          <option value="llm">llm</option>
        </select>
        {/* 刷新 */}
        <button onClick={loadRules}
          className="glass rounded-xl p-2 text-slate-400 hover:text-slate-700 transition-colors">
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
        {/* 新建 */}
        <button onClick={() => setModal({ ...EMPTY_FORM })}
          className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs text-white bg-indigo-500 hover:bg-indigo-600 transition-colors">
          <Plus size={12} /> 新建规则
        </button>
      </div>

      <div className="text-xs text-slate-400">显示 {filtered.length} / {rules.length} 条</div>

      {/* 规则列表 */}
      <div className="space-y-2 max-h-[55vh] overflow-y-auto pr-1">
        {filtered.length === 0 && (
          <div className="text-center text-sm text-slate-400 py-10">暂无规则</div>
        )}
        {filtered.map(rule => (
          <div key={rule.id}
            className={`glass rounded-xl p-3 flex items-center gap-3 transition-opacity ${rule.enabled ? '' : 'opacity-50'}`}>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-slate-900 truncate">{rule.name}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${TYPE_COLOR[rule.type] ?? 'text-slate-500'}`}>
                  {rule.type}
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${ACTION_COLOR[rule.action] ?? 'text-slate-400'}`}>
                  {rule.action}
                </span>
                {rule.category && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                    {rule.category}
                  </span>
                )}
              </div>
              <div className="text-xs text-slate-500 truncate mt-0.5">{rule.content}</div>
              {rule.description && (
                <div className="text-[11px] text-slate-400 truncate mt-0.5">{rule.description}</div>
              )}
            </div>
            {/* 编辑 */}
            <button onClick={() => openEdit(rule)}
              className="shrink-0 text-slate-400 hover:text-indigo-500 transition-colors">
              <Pencil size={13} />
            </button>
            {/* 启用/禁用 */}
            <button onClick={() => toggle(rule)} className="shrink-0 text-slate-400 hover:text-slate-700 transition-colors">
              {rule.enabled
                ? <ToggleRight size={20} className="text-indigo-500" />
                : <ToggleLeft size={20} />}
            </button>
            {/* 删除 */}
            <button onClick={() => remove(rule)}
              className="shrink-0 text-slate-400 hover:text-red-500 transition-colors">
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      {/* 新建 / 编辑 弹窗 */}
      {modal && (
        <RuleModal
          initial={modal}
          onSave={() => { setModal(null); loadRules() }}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  )
}
