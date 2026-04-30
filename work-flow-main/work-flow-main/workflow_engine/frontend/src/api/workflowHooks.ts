import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { workflowApi } from "./workflowApi";
import type {
  ContinueConversationRequest,
  CreateWorkflowRequest,
  ExecuteWorkflowRequest,
  PublicOpinionGenerateRequest,
  StartConversationRequest,
  WorkflowDefinition,
} from "../types/workflow";

export const workflowQueryKeys = {
  workflows: ["workflows"] as const,
  workflow: (workflowId: string) => ["workflow", workflowId] as const,
  executionDetail: (executionId: string) => ["execution", executionId] as const,
  workflowExecutions: (workflowId: string) => ["executions", workflowId] as const,
  executionReport: (executionId: string) => ["report", executionId] as const,
};

export const useWorkflowsQuery = () =>
  useQuery({
    queryKey: workflowQueryKeys.workflows,
    queryFn: workflowApi.getWorkflows,
  });

export const useWorkflowQuery = (workflowId: string | null) =>
  useQuery({
    queryKey: workflowQueryKeys.workflow(workflowId ?? ""),
    queryFn: () => workflowApi.getWorkflow(workflowId!),
    enabled: !!workflowId,
  });

export const useStartConversationMutation = () =>
  useMutation({
    mutationFn: (payload: StartConversationRequest) => workflowApi.startConversation(payload),
  });

export const useContinueConversationMutation = () =>
  useMutation({
    mutationFn: (payload: ContinueConversationRequest) => workflowApi.continueConversation(payload),
  });

export const useExecuteWorkflowMutation = () =>
  useMutation({
    mutationFn: (payload: ExecuteWorkflowRequest) => workflowApi.executeWorkflow(payload),
  });

export const useGeneratePublicOpinionWorkflowMutation = () =>
  useMutation({
    mutationFn: (payload: PublicOpinionGenerateRequest) => workflowApi.generatePublicOpinionWorkflow(payload),
  });

export const useSaveWorkflowMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ workflowId, workflow }: { workflowId: string; workflow: WorkflowDefinition }) =>
      workflowApi.saveWorkflow(workflowId, workflow),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowQueryKeys.workflows });
    },
  });
};

export const useCreateWorkflowMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateWorkflowRequest) => workflowApi.createWorkflow(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowQueryKeys.workflows });
    },
  });
};

export const useExecutionDetailQuery = (executionId: string | null, options?: { enabled?: boolean; refetchInterval?: number | false }) =>
  useQuery({
    queryKey: workflowQueryKeys.executionDetail(executionId ?? ""),
    queryFn: () => workflowApi.getExecutionDetail(executionId!),
    enabled: !!executionId && (options?.enabled ?? true),
    refetchInterval: options?.refetchInterval,
  });

export const useWorkflowExecutionsQuery = (workflowId: string | null, limit = 20, offset = 0) =>
  useQuery({
    queryKey: workflowQueryKeys.workflowExecutions(workflowId ?? ""),
    queryFn: () => workflowApi.getWorkflowExecutions(workflowId!, limit, offset),
    enabled: !!workflowId,
  });

export const useExecutionReportQuery = (executionId: string | null) =>
  useQuery({
    queryKey: workflowQueryKeys.executionReport(executionId ?? ""),
    queryFn: () => workflowApi.getExecutionReport(executionId!),
    enabled: !!executionId,
  });