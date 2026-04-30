import { CheckCircle2, Circle } from 'lucide-react'
import { useAppStore, PAGE_CONFIGS } from '../store/app'
import type { PageId } from '../types'

export default function PageNav() {
  const { currentPage, unlockedPages, goToPage } = useAppStore()

  return (
    <div className="flex items-center justify-center gap-0 mb-8 select-none">
      {PAGE_CONFIGS.map((page, idx) => {
        const unlocked = unlockedPages.has(page.id as PageId)
        const active = currentPage === page.id
        const done = (page.id as number) < currentPage

        return (
          <div key={page.id} className="flex items-center">
            {/* Step dot */}
            <button
              onClick={() => unlocked && goToPage(page.id as PageId)}
              disabled={!unlocked}
              className={`flex flex-col items-center gap-1.5 px-3 py-2 rounded-xl transition-all ${
                active
                  ? 'bg-indigo-50 ring-1 ring-indigo-200'
                  : unlocked
                  ? 'hover:bg-slate-50 cursor-pointer'
                  : 'opacity-40 cursor-not-allowed'
              }`}
            >
              <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold transition-all ${
                done
                  ? 'bg-emerald-500 text-white'
                  : active
                  ? 'bg-indigo-500 text-white'
                  : 'bg-slate-200 text-slate-500'
              }`}>
                {done
                  ? <CheckCircle2 size={16} />
                  : active
                  ? <span>{page.emoji}</span>
                  : <Circle size={14} />
                }
              </div>
              <div className="text-center">
                <div className={`text-xs font-semibold whitespace-nowrap ${
                  active ? 'text-indigo-700' : done ? 'text-emerald-600' : 'text-slate-400'
                }`}>
                  {page.title}
                </div>
                <div className="text-[10px] text-slate-400 whitespace-nowrap hidden sm:block">
                  {page.subtitle}
                </div>
              </div>
            </button>

            {/* Connector */}
            {idx < PAGE_CONFIGS.length - 1 && (
              <div className={`h-0.5 w-8 mx-1 rounded transition-colors ${
                (page.id as number) < currentPage ? 'bg-emerald-400' : 'bg-slate-200'
              }`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
