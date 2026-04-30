/** 通用进度条 — loading 时走动画，完成时显示 100% */
interface ProgressBarProps {
  loading: boolean
  progress?: number // 0-100
  label?: string
  className?: string
}

export default function ProgressBar({ loading, progress = 0, label, className = '' }: ProgressBarProps) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      {label && (
        <div className="flex justify-between text-xs text-slate-500">
          <span>{label}</span>
          {!loading && <span className="text-indigo-600 font-medium">{progress}%</span>}
        </div>
      )}
      <div className="relative h-2 bg-slate-100 rounded-full overflow-hidden">
        {loading ? (
          /* indeterminate shimmer */
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-indigo-400 to-transparent animate-[shimmer_1.5s_infinite]"
               style={{ backgroundSize: '200% 100%' }} />
        ) : (
          <div
            className="h-full bg-indigo-500 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        )}
      </div>
    </div>
  )
}
