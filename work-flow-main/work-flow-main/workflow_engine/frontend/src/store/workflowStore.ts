import { create } from "zustand";
import type {
  ChatMessage,
  ExecutionDetailResponse,
  ExecutionNodeStatus,
  ExecutionNodeTrace,
  NormalizedExecuteResponse,
  WorkflowDefinition,
} from "../types/workflow";

type VersionStatus = "saved" | "unsaved";
type ExecutionPhase = "idle" | "running" | "success" | "error";

interface WorkflowStoreState {
  workflow: WorkflowDefinition | null;
  workflowId: string | null;
  conversationId: string | null;
  latestConversationWorkflow: WorkflowDefinition | null;
  messages: ChatMessage[];
  selectedNodeId: string | null;
  execution: NormalizedExecuteResponse | null;
  executionId: string | null;
  executionPhase: ExecutionPhase;
  nodeStatusMap: Record<string, ExecutionNodeStatus>;
  nodeTraces: ExecutionNodeTrace[];
  versionStatus: VersionStatus;
  error: string | null;
  setIdentifiers: (payload: { workflowId: string | null; conversationId: string | null }) => void;
  setWorkflow: (workflow: WorkflowDefinition, markUnsaved?: boolean) => void;
  setLatestConversationWorkflow: (workflow: WorkflowDefinition | null) => void;
  applyLatestWorkflow: () => WorkflowDefinition | null;
  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: ChatMessage) => void;
  setSelectedNodeId: (nodeId: string | null) => void;
  setNodeStatusMap: (statusMap: Record<string, ExecutionNodeStatus>) => void;
  setExecutionId: (executionId: string | null) => void;
  setExecutionRunning: () => void;
  setExecutionResult: (result: NormalizedExecuteResponse) => void;
  setExecutionError: (message: string) => void;
  updateExecutionFromPolling: (detail: ExecutionDetailResponse) => void;
  setError: (message: string | null) => void;
  setWorkflowName: (name: string) => void;
  updateNodeTitle: (nodeId: string, title: string) => void;
  updateNodeParams: (nodeId: string, params: Record<string, unknown>) => void;
  markSaved: () => void;
  markUnsaved: () => void;
  resetExecution: () => void;
  loadWorkflow: (payload: { workflowId: string; workflow: WorkflowDefinition; conversationId?: string | null }) => void;
}

export const createMessage = (
  role: ChatMessage["role"],
  content: string
): ChatMessage => ({
  id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  role,
  content,
  createdAt: new Date().toISOString(),
});

const inferNodeStatus = (output: unknown): ExecutionNodeStatus => {
  if (typeof output !== "object" || output === null) {
    return "success";
  }

  const record = output as Record<string, unknown>;
  const status = typeof record.status === "string" ? record.status.toLowerCase() : "";

  if (status === "failed" || status === "error" || typeof record.error === "string") {
    return "error";
  }

  if (status === "running") {
    return "running";
  }

  return "success";
};

const buildNodeStatusMap = (result: NormalizedExecuteResponse): Record<string, ExecutionNodeStatus> => {
  const entries = Object.entries(result.nodeOutputs ?? {});
  return entries.reduce<Record<string, ExecutionNodeStatus>>((acc, [nodeId, output]) => {
    acc[nodeId] = inferNodeStatus(output);
    return acc;
  }, {});
};

const buildNodeStatusMapFromTraces = (traces: ExecutionNodeTrace[]): Record<string, ExecutionNodeStatus> => {
  return traces.reduce<Record<string, ExecutionNodeStatus>>((acc, trace) => {
    const status = trace.status.toLowerCase();
    if (status === "completed" || status === "success") {
      acc[trace.nodeId] = "success";
    } else if (status === "failed" || status === "error") {
      acc[trace.nodeId] = "error";
    } else if (status === "running") {
      acc[trace.nodeId] = "running";
    } else {
      acc[trace.nodeId] = "pending";
    }
    return acc;
  }, {});
};

const mapTraceStatusToPhase = (status: string): ExecutionPhase => {
  const lower = status.toLowerCase();
  if (lower === "completed" || lower === "success") return "success";
  if (lower === "failed" || lower === "error") return "error";
  if (lower === "running") return "running";
  return "running";
};

export const useWorkflowStore = create<WorkflowStoreState>((set, get) => ({
  workflow: null,
  workflowId: null,
  conversationId: null,
  latestConversationWorkflow: null,
  messages: [createMessage("system", "请输入需求，我会生成或继续调整工作流。")],
  selectedNodeId: null,
  execution: null,
  executionId: null,
  executionPhase: "idle",
  nodeStatusMap: {},
  nodeTraces: [],
  versionStatus: "saved",
  error: null,

  setIdentifiers: ({ workflowId, conversationId }) => set({ workflowId, conversationId }),

  setWorkflow: (workflow, markUnsaved = true) =>
    set({
      workflow,
      versionStatus: markUnsaved ? "unsaved" : "saved",
      error: null,
    }),

  setLatestConversationWorkflow: (workflow) => set({ latestConversationWorkflow: workflow }),

  applyLatestWorkflow: () => {
    const latest = get().latestConversationWorkflow;
    if (!latest) {
      return null;
    }
    // 保留当前的 workflowId 和 conversationId，因为这些 ID 仍然有效
    set({
      workflow: latest,
      latestConversationWorkflow: null,
      versionStatus: "unsaved",
      selectedNodeId: null,
      error: null,
      execution: null,
      executionId: null,
      executionPhase: "idle",
      nodeStatusMap: {},
      nodeTraces: [],
      // 保留 workflowId 和 conversationId，确保执行时可以使用
    });
    return latest;
  },

  setMessages: (messages) => set({ messages }),

  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),

  setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId }),

  setNodeStatusMap: (statusMap) => set({ nodeStatusMap: statusMap }),

  setExecutionId: (executionId) => set({ executionId }),

  setExecutionRunning: () => {
    const workflow = get().workflow;
    const runningMap =
      workflow?.nodes.reduce<Record<string, ExecutionNodeStatus>>((acc, node) => {
        acc[node.id] = "running";
        return acc;
      }, {}) ?? {};
    set({
      executionPhase: "running",
      execution: null,
      executionId: null,
      nodeStatusMap: runningMap,
      nodeTraces: [],
      error: null,
    });
  },

  setExecutionResult: (result) =>
    set({
      execution: result,
      executionId: result.executionId,
      executionPhase: "success",
      nodeStatusMap: buildNodeStatusMap(result),
      error: null,
    }),

  setExecutionError: (message) => set({ executionPhase: "error", error: message }),

  updateExecutionFromPolling: (detail) => {
    const nodeTraces = detail.nodeTraces ?? [];
    const nodeStatusMap = buildNodeStatusMapFromTraces(nodeTraces);
    const phase = mapTraceStatusToPhase(detail.status);

    set({
      executionId: detail.executionId,
      executionPhase: phase,
      nodeStatusMap,
      nodeTraces,
      error: detail.errorMessage ?? null,
    });
  },

  resetExecution: () =>
    set({
      execution: null,
      executionId: null,
      executionPhase: "idle",
      nodeStatusMap: {},
      nodeTraces: [],
      error: null,
    }),

  setError: (message) => set({ error: message }),

  setWorkflowName: (name) =>
    set((state) => {
      if (!state.workflow) {
        return state;
      }
      return {
        workflow: {
          ...state.workflow,
          name,
        },
        versionStatus: "unsaved",
      };
    }),

  updateNodeTitle: (nodeId, title) =>
    set((state) => {
      if (!state.workflow) {
        return state;
      }
      return {
        workflow: {
          ...state.workflow,
          nodes: state.workflow.nodes.map((node) =>
            node.id === nodeId
              ? {
                  ...node,
                  config: {
                    ...(node.config ?? {}),
                    title,
                    params: (node.config?.params ?? {}) as Record<string, unknown>,
                  },
                }
              : node
          ),
        },
        versionStatus: "unsaved",
      };
    }),

  updateNodeParams: (nodeId, params) =>
    set((state) => {
      if (!state.workflow) {
        return state;
      }
      return {
        workflow: {
          ...state.workflow,
          nodes: state.workflow.nodes.map((node) =>
            node.id === nodeId
              ? {
                  ...node,
                  config: {
                    ...(node.config ?? {}),
                    title: node.config?.title ?? node.id,
                    params,
                  },
                }
              : node
          ),
        },
        versionStatus: "unsaved",
      };
    }),

  markSaved: () => set({ versionStatus: "saved" }),

  markUnsaved: () => set({ versionStatus: "unsaved" }),

  loadWorkflow: ({ workflowId, workflow, conversationId = null }) =>
    set({
      workflowId,
      workflow,
      conversationId,
      latestConversationWorkflow: null,
      selectedNodeId: null,
      execution: null,
      executionId: null,
      executionPhase: "idle",
      nodeStatusMap: {},
      nodeTraces: [],
      versionStatus: "saved",
      error: null,
      messages: [createMessage("system", `已加载工作流「${workflow.name}」，可继续编辑迭代。`)],
    }),
}));