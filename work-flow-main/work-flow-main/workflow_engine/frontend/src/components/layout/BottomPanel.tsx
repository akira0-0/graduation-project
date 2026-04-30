import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useMemo } from "react";
import type { ExecutionStatsViewModel } from "../../features/execution/stats";
import type { ExecutionNodeTrace } from "../../types/workflow";

interface BottomPanelProps {
  stats: ExecutionStatsViewModel;
  nodeTraces: ExecutionNodeTrace[];
  executionId: string | null;
}

const barColors: Record<string, string> = {
  成功: "#16a34a",
  失败: "#dc2626",
  运行中: "#2563eb",
  待执行: "#64748b",
};

const statusLabelMap: Record<string, string> = {
  completed: "已完成",
  success: "成功",
  failed: "失败",
  error: "错误",
  running: "运行中",
  pending: "待执行",
  idle: "空闲",
};

const getStatusLabel = (status: string): string => {
  const lower = status.toLowerCase();
  return statusLabelMap[lower] ?? status;
};

export const BottomPanel = ({ stats, nodeTraces, executionId }: BottomPanelProps) => {
  const latestTraces = useMemo(() => {
    if (!nodeTraces || nodeTraces.length === 0) return [];
    return nodeTraces.slice(-5);
  }, [nodeTraces]);

  return (
    <footer className="h-44 border-t border-border bg-card p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-6 text-sm">
          <div>
            全局状态：<span className="font-semibold">{getStatusLabel(stats.statusText)}</span>
          </div>
          <div>
            执行耗时：<span className="font-semibold">{stats.durationSeconds.toFixed(3)}s</span>
          </div>
          <div>
            节点总数：<span className="font-semibold">{stats.total}</span>
          </div>
          {executionId && (
            <div className="text-xs text-slate-500">
              执行ID：<span className="font-mono">{executionId.slice(0, 8)}...</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-4">
        <div className="h-[110px] flex-1">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stats.chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {stats.chartData.map((entry) => (
                  <Cell key={entry.name} fill={barColors[entry.name] ?? "#64748b"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {latestTraces.length > 0 && (
          <div className="flex h-[110px] w-80 flex-col overflow-hidden rounded-md border border-border bg-background p-2">
            <div className="mb-1 text-xs font-medium text-slate-600">节点追踪</div>
            <div className="flex-1 overflow-auto text-xs">
              {latestTraces.map((trace) => (
                <div
                  key={`${trace.executionId}-${trace.nodeId}`}
                  className="flex items-center justify-between border-b border-border py-1 last:border-0"
                >
                  <span className="truncate text-slate-700">{trace.nodeId}</span>
                  <span
                    className={`ml-2 ${
                      trace.status.toLowerCase() === "completed" || trace.status.toLowerCase() === "success"
                        ? "text-green-600"
                        : trace.status.toLowerCase() === "failed" || trace.status.toLowerCase() === "error"
                          ? "text-red-600"
                          : "text-blue-600"
                    }`}
                  >
                    {getStatusLabel(trace.status)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </footer>
  );
};