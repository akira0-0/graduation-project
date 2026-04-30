import type { Edge, Node } from "@xyflow/react";
import type {
  ExecutionNodeStatus,
  WorkflowDefinition,
  WorkflowEdge,
  WorkflowNode,
} from "../types/workflow";

export interface CanvasNodeData {
  label: string;
  title: string;
  type: string;
  status: ExecutionNodeStatus;
  [key: string]: unknown;
}

export type CanvasFlowNode = Node<CanvasNodeData>;
export type CanvasFlowEdge = Edge;

const X_GAP = 220;
const Y_GAP = 120;
const START_X = 80;
const START_Y = 80;

const getNodePosition = (node: WorkflowNode, index: number) => {
  if (node.position && Number.isFinite(node.position.x) && Number.isFinite(node.position.y)) {
    return node.position;
  }

  if (Number.isFinite(node.x) && Number.isFinite(node.y)) {
    return { x: Number(node.x), y: Number(node.y) };
  }

  return {
    x: START_X + (index % 4) * X_GAP,
    y: START_Y + Math.floor(index / 4) * Y_GAP,
  };
};

const getEdgeLabel = (edge: WorkflowEdge) => {
  if (edge.condition) {
    return `条件: ${edge.condition}`;
  }

  if (edge.branch) {
    return `分支: ${edge.branch}`;
  }

  return undefined;
};

export const normalizeWorkflowDefinition = (workflow: WorkflowDefinition): WorkflowDefinition => {
  const nodes = Array.isArray(workflow.nodes)
    ? workflow.nodes.map((node, index) => ({
        ...node,
        id: node.id || `node_${index + 1}`,
        type: node.type || "Code",
        config: {
          ...(node.config ?? {}),
          title: node.config?.title || `${node.type || "Code"} 节点`,
          params: node.config?.params ?? {},
        },
      }))
    : [];

  const nodeIdSet = new Set(nodes.map((node) => node.id));

  const edges = Array.isArray(workflow.edges)
    ? workflow.edges.filter((edge) => nodeIdSet.has(edge.source) && nodeIdSet.has(edge.target))
    : [];

  return {
    ...workflow,
    nodes,
    edges,
    variables: workflow.variables ?? {},
  };
};

export const workflowToFlow = (
  workflow: WorkflowDefinition,
  nodeStatusMap: Record<string, ExecutionNodeStatus> = {}
): { nodes: CanvasFlowNode[]; edges: CanvasFlowEdge[] } => {
  const normalized = normalizeWorkflowDefinition(workflow);

  const nodes: CanvasFlowNode[] = normalized.nodes.map((node, index) => ({
    id: node.id,
    type: "workflowNode",
    position: getNodePosition(node, index),
    data: {
      label: `${node.config?.title || node.id} (${node.type})`,
      title: node.config?.title || node.id,
      type: node.type,
      status: nodeStatusMap[node.id] ?? "pending",
    },
    draggable: true,
    connectable: true,
    selectable: true,
  }));

  const edges: CanvasFlowEdge[] = normalized.edges.map((edge, index) => ({
    id: `${edge.source}-${edge.target}-${index + 1}`,
    source: edge.source,
    target: edge.target,
    label: getEdgeLabel(edge),
    animated: false,
  }));

  return { nodes, edges };
};

export const flowToWorkflow = (
  baseWorkflow: WorkflowDefinition,
  nodes: CanvasFlowNode[],
  edges: CanvasFlowEdge[]
): WorkflowDefinition => {
  const baseNodeMap = new Map(baseWorkflow.nodes.map((node) => [node.id, node]));
  const baseEdgeMap = new Map(baseWorkflow.edges.map((edge) => [`${edge.source}-${edge.target}`, edge]));

  const nextNodes: WorkflowNode[] = nodes.map((node) => {
    const existing = baseNodeMap.get(node.id);
    const titleFromData = typeof node.data?.title === "string" ? node.data.title : undefined;

    return {
      id: node.id,
      type: existing?.type ?? (typeof node.data?.type === "string" ? node.data.type : "Code"),
      config: {
        ...(existing?.config ?? {}),
        title: titleFromData ?? existing?.config?.title ?? node.id,
        params: (existing?.config?.params ?? {}) as Record<string, unknown>,
      },
      position: {
        x: node.position.x,
        y: node.position.y,
      },
    };
  });

  const nextEdges: WorkflowEdge[] = edges.map((edge) => {
    const key = `${edge.source}-${edge.target}`;
    const existing = baseEdgeMap.get(key);

    return {
      source: edge.source,
      target: edge.target,
      condition: existing?.condition,
      branch: existing?.branch,
    };
  });

  return {
    ...baseWorkflow,
    nodes: nextNodes,
    edges: nextEdges,
  };
};