export type JsonRecord = Record<string, unknown>;

export type ExecutionNodeStatus = "pending" | "running" | "success" | "error";

export interface WorkflowNodeConfig {
  title?: string;
  description?: string;
  params?: JsonRecord;
  [key: string]: unknown;
}

export interface WorkflowNode {
  id: string;
  type: string;
  config?: WorkflowNodeConfig;
  x?: number;
  y?: number;
  position?: {
    x: number;
    y: number;
  };
}

export interface WorkflowEdge {
  source: string;
  target: string;
  condition?: string;
  branch?: string;
}

export interface WorkflowDefinition {
  name: string;
  description?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  variables?: JsonRecord;
}

export interface StartConversationRequest {
  user_intent: string;
  workflow_type?: string;
}

export interface ContinueConversationRequest {
  workflow_id: string;
  user_message: string;
}

export interface ConversationResponse {
  conversation_id: string;
  workflow_id: string;
  workflow: WorkflowDefinition;
  message: string;
}

export interface ExecuteWorkflowRequest {
  workflow: WorkflowDefinition;
  workflow_id?: string;
  model?: string;
  enable_monitoring?: boolean;
}

export interface ExecutionStatistics {
  total_nodes?: number;
  success_nodes?: number;
  failed_nodes?: number;
  skipped_nodes?: number;
  success_rate?: string;
}

export interface ExecutionSummary extends JsonRecord {
  execution_id?: string;
  workflow_id?: string;
  workflow_name?: string;
  status?: string;
  start_time?: string;
  end_time?: string | null;
  duration?: number | null;
  statistics?: ExecutionStatistics;
  error_count?: number;
}

export interface RawExecuteResponse {
  status?: string;
  execution_id?: string | null;
  result?: unknown;
  node_outputs?: unknown;
  summary?: unknown;
  report_path?: string | null;
  report_content?: string | null;
}

export interface NormalizedExecuteResponse {
  status: string;
  executionId: string | null;
  summary: ExecutionSummary | null;
  reportPath: string | null;
  reportContent: string | null;
  nodeOutputs: JsonRecord;
  durationSeconds: number | null;
  raw: RawExecuteResponse;
}

export interface WorkflowListItem {
  id: string;
  name: string;
  description?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface WorkflowListResponse {
  workflows: WorkflowListItem[];
}

export interface WorkflowDetailResponse {
  id: string;
  name: string;
  description?: string | null;
  definition: WorkflowDefinition;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CreateWorkflowRequest {
  workflow: WorkflowDefinition;
  description?: string;
}

export interface CreateWorkflowResponse {
  workflow_id: string;
  name: string;
  description?: string | null;
  created_at?: string | null;
  status: string;
}

export interface PublicOpinionGenerateRequest {
  topic: string;
  requirements?: JsonRecord;
  model?: string;
}

export interface PublicOpinionGenerateResponse {
  workflow: WorkflowDefinition;
  status: string;
  metadata?: JsonRecord;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
}

export interface ExecutionNodeTrace {
  executionId: string;
  nodeId: string;
  nodeType: string | null;
  status: string;
  inputPayload: JsonRecord | null;
  outputPayload: JsonRecord | null;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
  createdAt: string | null;
}

export interface ExecutionDetailResponse {
  executionId: string;
  workflowId: string;
  status: string;
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
  triggerSource: string | null;
  errorMessage: string | null;
  finalReportPath: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  nodeTraces: ExecutionNodeTrace[];
}

export interface ExecutionListItem {
  executionId: string;
  workflowId: string;
  status: string;
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
  triggerSource: string | null;
  errorMessage: string | null;
  finalReportPath: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  nodeTraces: ExecutionNodeTrace[];
}

export interface ExecutionListResponse {
  workflowId: string;
  total: number;
  limit: number;
  offset: number;
  items: ExecutionListItem[];
}

export interface ExecutionReportResponse {
  executionId: string;
  reportPath: string | null;
  reportContent: string | null;
  source: string;
}