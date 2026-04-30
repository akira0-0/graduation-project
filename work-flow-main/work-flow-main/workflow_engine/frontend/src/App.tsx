import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ReactFlowProvider } from "@xyflow/react";
import { TopBar } from "./components/layout/TopBar";
import { ChatPanel } from "./components/layout/ChatPanel";
import { CanvasPanel } from "./components/layout/CanvasPanel";
import { RightDrawer } from "./components/layout/RightDrawer";
import { BottomPanel } from "./components/layout/BottomPanel";
import {
  useContinueConversationMutation,
  useCreateWorkflowMutation,
  useExecuteWorkflowMutation,
  useExecutionDetailQuery,
  useGeneratePublicOpinionWorkflowMutation,
  useSaveWorkflowMutation,
  useStartConversationMutation,
  useWorkflowQuery,
  useWorkflowsQuery,
} from "./api/workflowHooks";
import { normalizeWorkflowDefinition } from "./mappers/workflowGraph";
import { buildExecutionStats } from "./features/execution/stats";
import { createMessage, useWorkflowStore } from "./store/workflowStore";
import type { WorkflowDefinition } from "./types/workflow";

const POLLING_INTERVAL_MS = 2500;
const POLLING_MAX_COUNT = 60;

const AppContent = () => {
  const workflow = useWorkflowStore((state) => state.workflow);
  const workflowId = useWorkflowStore((state) => state.workflowId);
  const conversationId = useWorkflowStore((state) => state.conversationId);
  const latestConversationWorkflow = useWorkflowStore((state) => state.latestConversationWorkflow);
  const messages = useWorkflowStore((state) => state.messages);
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId);
  const execution = useWorkflowStore((state) => state.execution);
  const executionId = useWorkflowStore((state) => state.executionId);
  const executionPhase = useWorkflowStore((state) => state.executionPhase);
  const nodeStatusMap = useWorkflowStore((state) => state.nodeStatusMap);
  const nodeTraces = useWorkflowStore((state) => state.nodeTraces);
  const versionStatus = useWorkflowStore((state) => state.versionStatus);
  const error = useWorkflowStore((state) => state.error);

  const setIdentifiers = useWorkflowStore((state) => state.setIdentifiers);
  const setWorkflow = useWorkflowStore((state) => state.setWorkflow);
  const setLatestConversationWorkflow = useWorkflowStore((state) => state.setLatestConversationWorkflow);
  const applyLatestWorkflow = useWorkflowStore((state) => state.applyLatestWorkflow);
  const addMessage = useWorkflowStore((state) => state.addMessage);
  const setSelectedNodeId = useWorkflowStore((state) => state.setSelectedNodeId);
  const setExecutionId = useWorkflowStore((state) => state.setExecutionId);
  const setExecutionRunning = useWorkflowStore((state) => state.setExecutionRunning);
  const setExecutionResult = useWorkflowStore((state) => state.setExecutionResult);
  const setExecutionError = useWorkflowStore((state) => state.setExecutionError);
  const updateExecutionFromPolling = useWorkflowStore((state) => state.updateExecutionFromPolling);
  const setError = useWorkflowStore((state) => state.setError);
  const setWorkflowName = useWorkflowStore((state) => state.setWorkflowName);
  const updateNodeTitle = useWorkflowStore((state) => state.updateNodeTitle);
  const updateNodeParams = useWorkflowStore((state) => state.updateNodeParams);
  const markSaved = useWorkflowStore((state) => state.markSaved);
  const loadWorkflow = useWorkflowStore((state) => state.loadWorkflow);

  const [chatInput, setChatInput] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const pollingCountRef = useRef(0);

  const workflowsQuery = useWorkflowsQuery();
  const startConversationMutation = useStartConversationMutation();
  const continueConversationMutation = useContinueConversationMutation();
  const executeWorkflowMutation = useExecuteWorkflowMutation();
  const generatePublicOpinionWorkflowMutation = useGeneratePublicOpinionWorkflowMutation();
  const saveWorkflowMutation = useSaveWorkflowMutation();
  const createWorkflowMutation = useCreateWorkflowMutation();

  const shouldPoll = executionPhase === "running" && executionId !== null && pollingCountRef.current < POLLING_MAX_COUNT;
  
  const executionDetailQuery = useExecutionDetailQuery(executionId, {
    enabled: shouldPoll,
    refetchInterval: shouldPoll ? POLLING_INTERVAL_MS : false,
  });

  useEffect(() => {
    if (executionDetailQuery.data && shouldPoll) {
      pollingCountRef.current += 1;
      updateExecutionFromPolling(executionDetailQuery.data);
    }
  }, [executionDetailQuery.data, shouldPoll, updateExecutionFromPolling]);

  useEffect(() => {
    if (executionPhase !== "running") {
      pollingCountRef.current = 0;
    }
  }, [executionPhase]);

  const selectedNode = useMemo(
    () => workflow?.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [workflow, selectedNodeId]
  );

  const stats = useMemo(
    () => buildExecutionStats(execution, nodeStatusMap, workflow?.nodes.length ?? 0),
    [execution, nodeStatusMap, workflow?.nodes.length]
  );

  const handleSelectNode = useCallback(
    (nodeId: string | null) => {
      setSelectedNodeId(nodeId);
      setDrawerOpen(Boolean(nodeId));
    },
    [setSelectedNodeId]
  );

  const handleSendMessage = useCallback(async () => {
    const content = chatInput.trim();
    if (!content) {
      return;
    }

    setChatInput("");
    setError(null);
    addMessage(createMessage("user", content));

    try {
      const response = workflowId
        ? await continueConversationMutation.mutateAsync({
            workflow_id: workflowId,
            user_message: content,
          })
        : await startConversationMutation.mutateAsync({
            user_intent: content,
          });

      setIdentifiers({
        workflowId: response.workflow_id,
        conversationId: response.conversation_id,
      });
      setLatestConversationWorkflow(normalizeWorkflowDefinition(response.workflow));
      addMessage(createMessage("assistant", response.message));
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "消息发送失败";
      setError(message);
      addMessage(createMessage("system", `错误：${message}`));
    }
  }, [
    addMessage,
    chatInput,
    continueConversationMutation,
    setError,
    setIdentifiers,
    setLatestConversationWorkflow,
    startConversationMutation,
    workflowId,
  ]);

  const handleApplyToCanvas = useCallback(() => {
    const applied = applyLatestWorkflow();
    if (applied) {
      setWorkflow(normalizeWorkflowDefinition(applied), true);
    }
  }, [applyLatestWorkflow, setWorkflow]);

  const handleQuickPublicOpinion = useCallback(async () => {
    const topic = chatInput.trim() || "近期网络舆情";
    setError(null);

    try {
      const response = await generatePublicOpinionWorkflowMutation.mutateAsync({ topic });
      const normalizedWorkflow = normalizeWorkflowDefinition(response.workflow);
      setLatestConversationWorkflow(normalizedWorkflow);
      setWorkflow(normalizedWorkflow, true);
      addMessage(createMessage("system", `已生成舆情分析工作流并应用到画布，主题：${topic}`));
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "舆情分析工作流生成失败";
      setError(message);
      addMessage(createMessage("system", `舆情分析快捷入口失败：${message}`));
    }
  }, [
    addMessage,
    chatInput,
    generatePublicOpinionWorkflowMutation,
    setError,
    setLatestConversationWorkflow,
    setWorkflow,
  ]);

  const handleExecute = useCallback(async () => {
    if (!workflow) {
      return;
    }

    setError(null);
    setExecutionRunning();
    pollingCountRef.current = 0;

    try {
      const response = await executeWorkflowMutation.mutateAsync({
        workflow: normalizeWorkflowDefinition(workflow),
        workflow_id: workflowId ?? undefined,
        enable_monitoring: true,
      });
      setExecutionResult(response);
      if (response.executionId) {
        setExecutionId(response.executionId);
      }
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "执行失败";
      setExecutionError(message);
    }
  }, [
    executeWorkflowMutation,
    setError,
    setExecutionError,
    setExecutionResult,
    setExecutionRunning,
    setExecutionId,
    workflow,
    workflowId,
  ]);

  const handleSave = useCallback(async () => {
    if (!workflow) {
      return;
    }

    try {
      // 如果没有 workflowId，先创建工作流
      if (!workflowId) {
        const createResponse = await createWorkflowMutation.mutateAsync({
          workflow: normalizeWorkflowDefinition(workflow),
        });

        // 设置新创建的 workflowId
        setIdentifiers({
          workflowId: createResponse.workflow_id,
          conversationId,
        });

        markSaved();
        setError(null);
      } else {
        // 已有 workflowId，直接更新
        await saveWorkflowMutation.mutateAsync({
          workflowId,
          workflow: normalizeWorkflowDefinition(workflow),
        });

        markSaved();
        setError(null);
      }
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "保存失败";
      setError(message);
    }
  }, [
    conversationId,
    createWorkflowMutation,
    markSaved,
    saveWorkflowMutation,
    setError,
    setIdentifiers,
    workflow,
    workflowId,
  ]);

  const handleImportWorkflow = useCallback(
    (nextWorkflow: WorkflowDefinition) => {
      setWorkflow(normalizeWorkflowDefinition(nextWorkflow), true);
      setError(null);
    },
    [setError, setWorkflow]
  );

  const handleExportWorkflow = useCallback(() => {
    if (!workflow) {
      return;
    }

    const blob = new Blob([JSON.stringify(workflow, null, 2)], {
      type: "application/json;charset=utf-8",
    });

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${workflow.name || "workflow"}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [workflow]);

  const handleDrawerOpenChange = useCallback(
    (open: boolean) => {
      setDrawerOpen(open);
      if (!open) {
        setSelectedNodeId(null);
      }
    },
    [setSelectedNodeId]
  );

  const [loadWorkflowId, setLoadWorkflowId] = useState<string | null>(null);
  const workflowDetailQuery = useWorkflowQuery(loadWorkflowId);

  useEffect(() => {
    if (workflowDetailQuery.data && loadWorkflowId) {
      const detail = workflowDetailQuery.data;
      loadWorkflow({
        workflowId: detail.id,
        workflow: normalizeWorkflowDefinition(detail.definition),
      });
      setLoadWorkflowId(null);
    }
  }, [workflowDetailQuery.data, loadWorkflowId, loadWorkflow]);

  const handleLoadWorkflow = useCallback((workflowId: string) => {
    setError(null);
    setLoadWorkflowId(workflowId);
  }, [setError]);

  useEffect(() => {
    if (workflowDetailQuery.error && loadWorkflowId) {
      const message = "加载工作流失败";
      setError(message);
      setLoadWorkflowId(null);
    }
  }, [workflowDetailQuery.error, loadWorkflowId, setError]);

  return (
    <div className="flex h-screen min-h-screen flex-col">
      <TopBar
        workflowName={workflow?.name ?? "未命名工作流"}
        versionStatus={versionStatus}
        isSaving={saveWorkflowMutation.isPending}
        isExecuting={executeWorkflowMutation.isPending}
        onWorkflowNameChange={setWorkflowName}
        onSave={handleSave}
        onExecute={handleExecute}
        onStop={() => undefined}
        onImportWorkflow={handleImportWorkflow}
        onExportWorkflow={handleExportWorkflow}
      />

      <div className="flex min-h-0 flex-1">
        <ChatPanel
          messages={messages}
          chatInput={chatInput}
          chatLoading={startConversationMutation.isPending || continueConversationMutation.isPending}
          quickEntryLoading={generatePublicOpinionWorkflowMutation.isPending}
          workflowList={workflowsQuery.data?.workflows ?? []}
          conversationId={conversationId}
          workflowId={workflowId}
          hasPendingWorkflow={Boolean(latestConversationWorkflow)}
          onLoadWorkflow={handleLoadWorkflow}
          onChatInputChange={setChatInput}
          onSendMessage={handleSendMessage}
          onApplyToCanvas={handleApplyToCanvas}
          onQuickPublicOpinion={handleQuickPublicOpinion}
        />

        <main className="flex min-w-0 flex-1 flex-col gap-2 p-3">
          <CanvasPanel
            workflow={workflow}
            nodeStatusMap={nodeStatusMap}
            selectedNodeId={selectedNodeId}
            onSelectNode={handleSelectNode}
            onWorkflowChange={(nextWorkflow) => setWorkflow(nextWorkflow, true)}
          />

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
              {error}
            </div>
          )}
        </main>
      </div>

      <BottomPanel stats={stats} nodeTraces={nodeTraces} executionId={executionId} />

      <RightDrawer
        open={drawerOpen}
        node={selectedNode}
        execution={execution}
        nodeTraces={nodeTraces}
        executionId={executionId}
        onOpenChange={handleDrawerOpenChange}
        onUpdateTitle={(title) => selectedNode && updateNodeTitle(selectedNode.id, title)}
        onUpdateParams={(params) => selectedNode && updateNodeParams(selectedNode.id, params)}
      />
    </div>
  );
};

function App() {
  return (
    <ReactFlowProvider>
      <AppContent />
    </ReactFlowProvider>
  );
}

export default App;