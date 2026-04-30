import type { ExecutionNodeStatus, NormalizedExecuteResponse } from "../../types/workflow";

export interface ExecutionStatItem {
  name: string;
  value: number;
}

export interface ExecutionStatsViewModel {
  statusText: string;
  durationSeconds: number;
  total: number;
  success: number;
  failed: number;
  running: number;
  pending: number;
  chartData: ExecutionStatItem[];
}

const toNumber = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

export const buildExecutionStats = (
  execution: NormalizedExecuteResponse | null,
  nodeStatusMap: Record<string, ExecutionNodeStatus>,
  fallbackNodeCount: number
): ExecutionStatsViewModel => {
  const statistics = execution?.summary?.statistics as Record<string, unknown> | undefined;

  const success =
    toNumber(statistics?.success_nodes) ??
    Object.values(nodeStatusMap).filter((status) => status === "success").length;

  const failed =
    toNumber(statistics?.failed_nodes) ??
    Object.values(nodeStatusMap).filter((status) => status === "error").length;

  const running = Object.values(nodeStatusMap).filter((status) => status === "running").length;
  const pending =
    fallbackNodeCount > 0 ? Math.max(fallbackNodeCount - success - failed - running, 0) : 0;

  const total = toNumber(statistics?.total_nodes) ?? Math.max(success + failed + running + pending, fallbackNodeCount);

  return {
    statusText: execution?.status ?? "idle",
    durationSeconds: execution?.durationSeconds ?? 0,
    total,
    success,
    failed,
    running,
    pending,
    chartData: [
      { name: "成功", value: success },
      { name: "失败", value: failed },
      { name: "运行中", value: running },
      { name: "待执行", value: pending },
    ],
  };
};