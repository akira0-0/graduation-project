import type {
  ContinueConversationRequest,
  ConversationResponse,
  CreateWorkflowRequest,
  CreateWorkflowResponse,
  ExecuteWorkflowRequest,
  ExecutionDetailResponse,
  ExecutionListResponse,
  ExecutionReportResponse,
  NormalizedExecuteResponse,
  PublicOpinionGenerateRequest,
  PublicOpinionGenerateResponse,
  RawExecuteResponse,
  StartConversationRequest,
  WorkflowDetailResponse,
  WorkflowListResponse,
} from "../types/workflow";
import { normalizeExecuteResponse } from "../utils/normalize";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

class ApiRequestError extends Error {
  status: number;
  details: unknown;

  constructor(message: string, status: number, details: unknown) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.details = details;
  }
}

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  let body: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!response.ok) {
    throw new ApiRequestError("请求失败", response.status, body);
  }

  return body as T;
};

export const workflowApi = {
  getWorkflows: async (): Promise<WorkflowListResponse> =>
    request<WorkflowListResponse>("/api/v1/workflows", {
      method: "GET",
    }),

  getWorkflow: async (workflowId: string): Promise<WorkflowDetailResponse> =>
    request<WorkflowDetailResponse>(`/api/v1/workflows/${workflowId}`, {
      method: "GET",
    }),

  startConversation: async (
    payload: StartConversationRequest
  ): Promise<ConversationResponse> =>
    request<ConversationResponse>("/api/v1/conversations/start", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  continueConversation: async (
    payload: ContinueConversationRequest
  ): Promise<ConversationResponse> =>
    request<ConversationResponse>("/api/v1/conversations/continue", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  generatePublicOpinionWorkflow: async (
    payload: PublicOpinionGenerateRequest
  ): Promise<PublicOpinionGenerateResponse> =>
    request<PublicOpinionGenerateResponse>("/api/v1/workflows/generate-public-opinion", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  executeWorkflow: async (
    payload: ExecuteWorkflowRequest
  ): Promise<NormalizedExecuteResponse> => {
    const raw = await request<RawExecuteResponse>("/api/v1/workflows/execute", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    return normalizeExecuteResponse(raw);
  },

  saveWorkflow: async (workflowId: string, workflow: unknown): Promise<unknown> =>
    request<unknown>(`/api/v1/workflows/${workflowId}`, {
      method: "PUT",
      body: JSON.stringify(workflow),
    }),

  createWorkflow: async (payload: CreateWorkflowRequest): Promise<CreateWorkflowResponse> =>
    request<CreateWorkflowResponse>("/api/v1/workflows", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getExecutionDetail: async (
    executionId: string,
    includeNodeTraces = true
  ): Promise<ExecutionDetailResponse> =>
    request<ExecutionDetailResponse>(
      `/api/v1/executions/${executionId}?include_node_traces=${includeNodeTraces}`,
      { method: "GET" }
    ),

  getWorkflowExecutions: async (
    workflowId: string,
    limit = 20,
    offset = 0
  ): Promise<ExecutionListResponse> =>
    request<ExecutionListResponse>(
      `/api/v1/workflows/${workflowId}/executions?limit=${limit}&offset=${offset}`,
      { method: "GET" }
    ),

  getExecutionReport: async (executionId: string): Promise<ExecutionReportResponse> =>
    request<ExecutionReportResponse>(`/api/v1/executions/${executionId}/report`, {
      method: "GET",
    }),
};

export { ApiRequestError, API_BASE_URL };