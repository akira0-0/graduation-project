import { useCallback, useEffect, useMemo } from "react";
import type { Connection } from "@xyflow/react";
import {
  addEdge,
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button } from "../ui/button";
import type { ExecutionNodeStatus, WorkflowDefinition } from "../../types/workflow";
import {
  flowToWorkflow,
  workflowToFlow,
  type CanvasFlowEdge,
  type CanvasFlowNode,
} from "../../mappers/workflowGraph";

interface CanvasPanelProps {
  workflow: WorkflowDefinition | null;
  nodeStatusMap: Record<string, ExecutionNodeStatus>;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string | null) => void;
  onWorkflowChange: (workflow: WorkflowDefinition) => void;
}

const statusClassMap: Record<ExecutionNodeStatus, string> = {
  pending: "border-slate-300 bg-white text-slate-700",
  running: "border-blue-500 bg-blue-50 text-blue-700",
  success: "border-emerald-500 bg-emerald-50 text-emerald-700",
  error: "border-red-500 bg-red-50 text-red-700",
};

const WorkflowNodeCard = ({ data }: { data: CanvasFlowNode["data"] }) => (
  <div className={`min-w-[180px] rounded-md border p-2 shadow-sm ${statusClassMap[data.status]}`}>
    <Handle type="target" position={Position.Top} className="!h-2 !w-2 !bg-slate-500" />
    <div className="text-sm font-semibold">{String(data.title ?? "-")}</div>
    <div className="mt-1 text-xs">{String(data.type ?? "-")}</div>
    <div className="mt-1 text-[11px] uppercase opacity-80">{data.status}</div>
    <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !bg-slate-500" />
  </div>
);

const CanvasToolbar = ({ onFitView }: { onFitView: () => void }) => (
  <div className="absolute right-3 top-3 z-20">
    <Button variant="outline" size="sm" onClick={onFitView}>
      Fit View
    </Button>
  </div>
);

const CanvasInner = ({
  workflow,
  nodeStatusMap,
  selectedNodeId,
  onSelectNode,
  onWorkflowChange,
}: CanvasPanelProps) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<CanvasFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<CanvasFlowEdge>([]);
  const reactFlow = useReactFlow<CanvasFlowNode, CanvasFlowEdge>();

  const nodeTypes = useMemo(() => ({ workflowNode: WorkflowNodeCard }), []);

  useEffect(() => {
    if (!workflow) {
      setNodes([]);
      setEdges([]);
      return;
    }
    const { nodes: mappedNodes, edges: mappedEdges } = workflowToFlow(workflow, nodeStatusMap);
    setNodes(mappedNodes);
    setEdges(mappedEdges);
  }, [workflow, nodeStatusMap, setEdges, setNodes]);

  const syncWorkflow = useCallback(
    (nextNodes: CanvasFlowNode[], nextEdges: CanvasFlowEdge[]) => {
      if (!workflow) {
        return;
      }
      onWorkflowChange(flowToWorkflow(workflow, nextNodes, nextEdges));
    },
    [onWorkflowChange, workflow]
  );

  const handleConnect = useCallback(
    (connection: Connection) => {
      setEdges((prev) => {
        const next = addEdge(
          {
            ...connection,
            id: `${connection.source ?? "s"}-${connection.target ?? "t"}-${Date.now()}`,
          },
          prev
        );
        syncWorkflow(nodes, next);
        return next;
      });
    },
    [nodes, setEdges, syncWorkflow]
  );

  const handleNodeDragStop = useCallback(() => {
    syncWorkflow(nodes, edges);
  }, [edges, nodes, syncWorkflow]);

  const handleNodesDelete = useCallback(
    (deletedNodes: CanvasFlowNode[]) => {
      const deleted = new Set(deletedNodes.map((node) => node.id));
      const nextNodes = nodes.filter((node) => !deleted.has(node.id));
      const nextEdges = edges.filter((edge) => !deleted.has(edge.source) && !deleted.has(edge.target));
      syncWorkflow(nextNodes, nextEdges);
      if (selectedNodeId && deleted.has(selectedNodeId)) {
        onSelectNode(null);
      }
    },
    [edges, nodes, onSelectNode, selectedNodeId, syncWorkflow]
  );

  const handleEdgesDelete = useCallback(
    (deletedEdges: CanvasFlowEdge[]) => {
      const deletedIds = new Set(deletedEdges.map((edge) => edge.id));
      const nextEdges = edges.filter((edge) => !deletedIds.has(edge.id));
      syncWorkflow(nodes, nextEdges);
    },
    [edges, nodes, syncWorkflow]
  );

  return (
    <div className="relative flex-1 rounded-md border border-border bg-white">
      <CanvasToolbar onFitView={() => reactFlow.fitView({ padding: 0.2 })} />
      {workflow ? (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={handleConnect}
          onPaneClick={() => onSelectNode(null)}
          onNodeClick={(_, node) => onSelectNode(node.id)}
          onNodeDragStop={handleNodeDragStop}
          onNodesDelete={handleNodesDelete}
          onEdgesDelete={handleEdgesDelete}
          fitView
          deleteKeyCode={["Backspace", "Delete"]}
        >
          <Background />
          <MiniMap />
          <Controls />
        </ReactFlow>
      ) : (
        <div className="grid h-full min-h-[360px] place-items-center text-sm text-slate-500">
          对话生成并应用后，工作流会展示在画布中
        </div>
      )}
    </div>
  );
};

export const CanvasPanel = (props: CanvasPanelProps) => <CanvasInner {...props} />;