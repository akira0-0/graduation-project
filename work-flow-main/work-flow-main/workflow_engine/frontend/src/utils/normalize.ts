import type {
  ExecutionSummary,
  JsonRecord,
  NormalizedExecuteResponse,
  RawExecuteResponse,
} from "../types/workflow";

const isObjectRecord = (value: unknown): value is JsonRecord =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const normalizeExecuteResponse = (
  raw: RawExecuteResponse
): NormalizedExecuteResponse => {
  let nodeOutputs: JsonRecord = {};

  if (isObjectRecord(raw.node_outputs)) {
    nodeOutputs = raw.node_outputs;
  } else if (isObjectRecord(raw.result) && isObjectRecord(raw.result.node_outputs)) {
    nodeOutputs = raw.result.node_outputs as JsonRecord;
  } else if (isObjectRecord(raw.result)) {
    nodeOutputs = raw.result;
  }

  const summary = isObjectRecord(raw.summary)
    ? (raw.summary as ExecutionSummary)
    : isObjectRecord(raw.result) && isObjectRecord(raw.result.summary)
    ? (raw.result.summary as ExecutionSummary)
    : null;

  const durationFromSummary = typeof summary?.duration === "number" ? summary.duration : null;

  const reportContent =
    typeof raw.report_content === "string"
      ? raw.report_content
      : isObjectRecord(raw.result) && typeof raw.result.report_content === "string"
      ? raw.result.report_content
      : null;

  return {
    status: raw.status ?? "unknown",
    executionId: raw.execution_id ?? null,
    summary,
    reportPath: raw.report_path ?? null,
    reportContent,
    nodeOutputs,
    durationSeconds: durationFromSummary,
    raw,
  };
};