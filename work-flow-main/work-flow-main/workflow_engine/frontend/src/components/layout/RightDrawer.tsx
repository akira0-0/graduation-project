import { useEffect, useMemo, useState } from "react";
import Editor from "@monaco-editor/react";
import type { ExecutionNodeTrace, NormalizedExecuteResponse, WorkflowNode } from "../../types/workflow";
import { useExecutionReportQuery } from "../../api/workflowHooks";
import { Button } from "../ui/button";
import { Drawer, DrawerContent } from "../ui/drawer";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";

interface RightDrawerProps {
  open: boolean;
  node: WorkflowNode | null;
  execution: NormalizedExecuteResponse | null;
  nodeTraces: ExecutionNodeTrace[];
  executionId: string | null;
  onOpenChange: (open: boolean) => void;
  onUpdateTitle: (title: string) => void;
  onUpdateParams: (params: Record<string, unknown>) => void;
}

const statusLabelMap: Record<string, string> = {
  completed: "已完成",
  success: "成功",
  failed: "失败",
  error: "错误",
  running: "运行中",
  pending: "待执行",
};

const getStatusLabel = (status: string): string => {
  const lower = status.toLowerCase();
  return statusLabelMap[lower] ?? status;
};

const formatDuration = (ms: number | null): string => {
  if (ms === null || ms === 0) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
};

const formatTimestamp = (iso: string | null): string => {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString("zh-CN");
  } catch {
    return iso;
  }
};

export const RightDrawer = ({
  open,
  node,
  execution,
  nodeTraces,
  executionId,
  onOpenChange,
  onUpdateTitle,
  onUpdateParams,
}: RightDrawerProps) => {
  const [title, setTitle] = useState("");
  const [paramsText, setParamsText] = useState("{}");
  const [codeText, setCodeText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showReport, setShowReport] = useState(false);

  const reportQuery = useExecutionReportQuery(executionId);

  const nodeOutput = useMemo(() => {
    if (!node || !execution) {
      return null;
    }
    return execution.nodeOutputs[node.id] ?? null;
  }, [execution, node]);

  const nodeTrace = useMemo(() => {
    if (!node || !nodeTraces || nodeTraces.length === 0) {
      return null;
    }
    return nodeTraces.find((t) => t.nodeId === node.id) ?? null;
  }, [nodeTraces, node]);

  useEffect(() => {
    if (!node) {
      return;
    }
    const nextTitle = node.config?.title ?? node.id;
    const params = (node.config?.params ?? {}) as Record<string, unknown>;
    const code = typeof params.code === "string" ? params.code : "";
    const { code: _, ...rest } = params;
    setTitle(nextTitle);
    setCodeText(code);
    setParamsText(JSON.stringify(rest, null, 2));
    setError(null);
  }, [node]);

  const handleSave = () => {
    if (!node) {
      return;
    }
    try {
      const parsed = JSON.parse(paramsText) as Record<string, unknown>;
      const nextParams = node.type === "Code" ? { ...parsed, code: codeText } : parsed;
      onUpdateTitle(title.trim() || node.id);
      onUpdateParams(nextParams);
      setError(null);
    } catch {
      setError("params 需要是合法 JSON");
    }
  };

  const reportContent = useMemo(() => {
    if (execution?.reportContent) {
      return execution.reportContent;
    }
    if (reportQuery.data?.reportContent) {
      return typeof reportQuery.data.reportContent === "string"
        ? reportQuery.data.reportContent
        : JSON.stringify(reportQuery.data.reportContent, null, 2);
    }
    return null;
  }, [execution?.reportContent, reportQuery.data]);

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent>
        <div className="flex h-full flex-col gap-4">
          <div>
            <div className="text-base font-semibold">节点配置</div>
            <div className="mt-1 text-xs text-slate-500">
              节点ID：{node?.id ?? "-"} ｜ 类型：{node?.type ?? "-"}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs font-medium text-slate-600">标题</div>
            <Input value={title} onChange={(event) => setTitle(event.target.value)} />
          </div>

          <div className="space-y-2">
            <div className="text-xs font-medium text-slate-600">Params(JSON)</div>
            <Textarea rows={8} value={paramsText} onChange={(event) => setParamsText(event.target.value)} />
          </div>

          {node?.type === "Code" && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-slate-600">Code（Monaco）</div>
              <div className="overflow-hidden rounded-md border border-border">
                <Editor
                  height="240px"
                  defaultLanguage="python"
                  value={codeText}
                  onChange={(value) => setCodeText(value ?? "")}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                  }}
                />
              </div>
            </div>
          )}

          {error && <div className="text-xs text-red-600">{error}</div>}

          <div className="flex justify-end">
            <Button onClick={handleSave}>保存节点配置</Button>
          </div>

          <div className="mt-2 border-t border-border pt-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold">报告级展示</div>
              {executionId && (
                <button
                  onClick={() => setShowReport(!showReport)}
                  className="text-xs text-blue-600 hover:underline"
                >
                  {showReport ? "隐藏报告" : "查看完整报告"}
                </button>
              )}
            </div>
            
            {showReport && (
              <div className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap rounded-md border border-border bg-background p-2 text-xs">
                {reportQuery.isLoading
                  ? "加载中..."
                  : reportContent?.trim()
                    ? reportContent
                    : "本次执行未返回报告正文（report_content 为空），请查看下方节点输出详情。"}
              </div>
            )}

            {nodeTrace && (
              <div className="mt-3 space-y-2">
                <div className="text-sm font-semibold">节点追踪详情</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-500">状态：</span>
                    <span
                      className={`font-medium ${
                        nodeTrace.status.toLowerCase() === "completed" ||
                        nodeTrace.status.toLowerCase() === "success"
                          ? "text-green-600"
                          : nodeTrace.status.toLowerCase() === "failed" ||
                              nodeTrace.status.toLowerCase() === "error"
                            ? "text-red-600"
                            : "text-blue-600"
                      }`}
                    >
                      {getStatusLabel(nodeTrace.status)}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">耗时：</span>
                    <span className="font-medium">{formatDuration(nodeTrace.durationMs)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">开始：</span>
                    <span className="font-medium">{formatTimestamp(nodeTrace.startedAt)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">完成：</span>
                    <span className="font-medium">{formatTimestamp(nodeTrace.completedAt)}</span>
                  </div>
                </div>

                {nodeTrace.errorMessage && (
                  <div className="mt-2 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-600">
                    <div className="font-medium">错误信息：</div>
                    <div className="mt-1 whitespace-pre-wrap">{nodeTrace.errorMessage}</div>
                  </div>
                )}

                <div className="mt-2">
                  <div className="text-xs font-medium text-slate-600">节点输入</div>
                  <pre className="mt-1 max-h-32 overflow-auto rounded-md border border-border bg-background p-2 text-xs">
                    {nodeTrace.inputPayload
                      ? JSON.stringify(nodeTrace.inputPayload, null, 2)
                      : "暂无输入数据"}
                  </pre>
                </div>

                <div className="mt-2">
                  <div className="text-xs font-medium text-slate-600">节点输出</div>
                  <pre className="mt-1 max-h-32 overflow-auto rounded-md border border-border bg-background p-2 text-xs">
                    {nodeTrace.outputPayload
                      ? JSON.stringify(nodeTrace.outputPayload, null, 2)
                      : "暂无输出数据"}
                  </pre>
                </div>
              </div>
            )}

            <div className="mt-3 text-sm font-semibold">最近执行输出</div>
            <div className="mt-1 text-xs text-slate-600">执行耗时：{execution?.durationSeconds ?? 0}s</div>
            <div className="mt-1 text-xs text-slate-600">执行状态：{execution?.status ?? "-"}</div>
            <pre className="mt-2 max-h-56 overflow-auto rounded-md border border-border bg-background p-2 text-xs">
              {nodeOutput ? JSON.stringify(nodeOutput, null, 2) : "暂无输出"}
            </pre>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
};