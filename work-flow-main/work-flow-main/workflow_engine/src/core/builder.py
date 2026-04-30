"""
图构建引擎
将 JSON DSL 转换为 LangGraph 可执行图
"""
from typing import Dict, Any, Type, Callable
from langgraph.graph import StateGraph, END
from .schema import WorkflowDefinition, WorkflowState, NodeDefinition
from ..nodes.base import BaseNode
from ..nodes.llm import LLMNode
from ..nodes.code import CodeNode
from ..nodes.condition import ConditionNode
from ..nodes.loop import LoopNode
from ..nodes.data_collection_agent_node import DataCollectionAgentNode
from ..nodes.sentiment_agent_node import SentimentAgentNode
from ..nodes.report_agent_node import ReportAgentNode
from ..nodes.filter_agent_node import FilterAgentNode
from ..nodes.xhs_filter_node import XHSFilterNode
from ..monitoring import ExecutionMonitor
from ..utils.logger import get_logger

logger = get_logger("graph_builder")


class GraphBuilder:
    """图构建引擎，将工作流 DSL 转换为可执行图"""
    
    # 节点类型映射
    NODE_MAP: Dict[str, Type[BaseNode]] = {
        "LLM": LLMNode,
        "Code": CodeNode,
        "Condition": ConditionNode,
        "Loop": LoopNode,
        "DataCollectionAgent": DataCollectionAgentNode,
        "SentimentAgent": SentimentAgentNode,
        "ReportAgent": ReportAgentNode,
        "FilterAgent": FilterAgentNode,
        "XHSFilterAgent": XHSFilterNode,   # 三层智能过滤，替代 DataCollection + Filter 组合
    }
    
    def __init__(self, workflow_def: WorkflowDefinition, monitor: ExecutionMonitor = None):
        """
        初始化图构建器
        
        Args:
            workflow_def: 工作流定义
            monitor: 执行监控器（可选）
        """
        self.workflow_def = workflow_def
        self.graph = StateGraph(WorkflowState)
        self.monitor = monitor
        self.node_instances: Dict[str, BaseNode] = {}
        
    def _create_node_function(self, node_def: NodeDefinition) -> Callable:
        """
        创建 LangGraph 兼容的节点执行函数
        
        Args:
            node_def: 节点定义
            
        Returns:
            节点执行函数
        """
        node_type = node_def.type
        logger.debug(f"查找节点类型映射", node_id=node_def.id, node_type=node_type, available_types=list(self.NODE_MAP.keys()))
        
        NodeClass = self.NODE_MAP.get(node_def.type)
        logger.debug(f"节点类型映射结果", node_id=node_def.id, found=NodeClass is not None)
        
        # 对于 Start/End 节点，创建透传函数
        if not NodeClass:
            logger.warning(f"未找到节点类型映射，使用透传函数", node_id=node_def.id, node_type=node_type)
            def pass_through(state: WorkflowState):
                # 记录监控信息
                if self.monitor:
                    self.monitor.skip_node(node_def.id)
                return {}  # 不更新任何状态
            return pass_through

        # 创建节点实例
        try:
            node_instance = NodeClass(node_def)
            self.node_instances[node_def.id] = node_instance
            logger.debug(f"节点实例创建成功", node_id=node_def.id)
        except Exception as e:
            logger.error(f"节点实例创建失败", node_id=node_def.id, error=str(e))
            import traceback
            logger.debug(f"节点实例创建失败详情", detail=traceback.format_exc())
            # 返回None，让上层知道创建失败
            return None
        
        def execute_node(state: WorkflowState) -> Dict[str, Any]:
            """
            执行节点逻辑
            
            Args:
                state: 工作流当前状态
                
            Returns:
                状态更新
            """
            # 记录节点开始
            if self.monitor:
                self.monitor.start_node(
                    node_def.id,
                    node_def.type,
                    state.node_outputs.copy()
                )
            
            # 更新当前节点
            state.current_node = node_def.id
            
            try:
                # 执行节点逻辑
                result = node_instance.execute(state)
                
                # 更新状态：将结果写入 node_outputs
                new_outputs = state.node_outputs.copy()
                new_outputs[node_def.id] = result
                
                # 记录节点完成
                if self.monitor:
                    self.monitor.complete_node(node_def.id, result)
                
                # 构建状态更新字典
                state_update = {
                    "node_outputs": {node_def.id: result}
                }
                
                # 如果节点返回了循环状态更新，也需要包含在内
                if "loop_counters" in result:
                    state_update["loop_counters"] = result["loop_counters"]
                if "loop_outputs" in result:
                    state_update["loop_outputs"] = result["loop_outputs"]
                
                # 返回状态更新（LangGraph 期望返回更新后的部分状态）
                return state_update
                
            except Exception as e:
                logger.error(f"节点执行失败: {str(e)}", node_id=node_def.id)
                
                # 记录节点失败
                if self.monitor:
                    self.monitor.fail_node(node_def.id, str(e))
                
                # 返回错误信息到状态
                return {
                    "node_outputs": {node_def.id: {"error": str(e)}}
                }
        
        return execute_node

    def _route_condition(self, state: WorkflowState, condition_node_id: str) -> str:
        """
        条件分支路由函数
        
        Args:
            state: 工作流状态
            condition_node_id: 条件节点ID
            
        Returns:
            下一个节点ID
        """
        logger.debug(f"条件路由被调用", node_id=condition_node_id, node_outputs_keys=list(state.node_outputs.keys()))
        
        # 获取条件节点的执行结果
        condition_result = state.node_outputs.get(condition_node_id, {})
        logger.debug(f"条件节点输出", node_id=condition_node_id, condition_result=condition_result)
        
        branch_value = condition_result.get("result", "")
        logger.debug(f"提取的分支值", node_id=condition_node_id, branch_value=branch_value)
        
        # 记录分支决策
        state.branch_decisions[condition_node_id] = branch_value
        
        logger.info(f"条件分支路由", node_id=condition_node_id, branch=branch_value)
        
        # 直接返回分支值，LangGraph会根据condition_map自动路由到目标节点
        return branch_value
    
    def _route_loop(self, state: WorkflowState, loop_node_id: str) -> str:
        """
        循环路由函数
        
        Args:
            state: 工作流状态
            loop_node_id: 循环节点ID
            
        Returns:
            下一个节点ID（循环体节点或下一个节点）
        """
        from ..config import get_settings
        
        loop_result = state.node_outputs.get(loop_node_id, {})
        loop_status = loop_result.get("loop_status", "completed")
        iteration_count = state.loop_counters.get(loop_node_id, 0)
        
        # 获取配置的最大迭代次数
        settings = get_settings()
        max_iterations = settings.loop_max_iterations
        
        # 获取循环节点的配置
        loop_node = next((n for n in self.workflow_def.nodes if n.id == loop_node_id), None)
        node_max_iterations = max_iterations
        if loop_node:
            node_max_iterations = loop_node.config.params.get("max_iterations", max_iterations)
            node_max_iterations = min(node_max_iterations, max_iterations)  # 不超过全局限制
        
        logger.info(
            f"循环路由",
            node_id=loop_node_id,
            status=loop_status,
            iteration=iteration_count,
            max_iterations=max_iterations,
            node_max_iterations=node_max_iterations,
            loop_result=loop_result
        )
        
        # 安全检查：防止死循环
        if iteration_count >= node_max_iterations:
            logger.warning(
                f"循环达到最大迭代次数，强制退出",
                node_id=loop_node_id,
                iteration=iteration_count,
                max_iterations=node_max_iterations
            )
            loop_status = "completed"
        
        # 查找循环节点的所有边
        loop_edges = [e for e in self.workflow_def.edges if e.source == loop_node_id]
        
        # 使用显式的 branch 字段进行路由（推荐方式）
        loop_body_edge = None
        loop_exit_edge = None
        
        for edge in loop_edges:
            if edge.branch == "loop_body":
                loop_body_edge = edge
            elif edge.branch == "loop_exit":
                loop_exit_edge = edge
        
        if loop_status == "running":
            # 循环继续，返回循环体节点
            if loop_body_edge:
                logger.debug(f"循环继续，执行循环体", node_id=loop_node_id, target=loop_body_edge.target)
                return loop_body_edge.target
            
            # 兼容旧版本：如果没有 branch 字段，使用第一条边作为循环体
            if loop_edges:
                logger.debug(f"循环继续（兼容模式）", node_id=loop_node_id, target=loop_edges[0].target)
                return loop_edges[0].target
            
            logger.warning(f"循环节点缺少循环体边", node_id=loop_node_id)
            return END
        else:
            # 循环结束，返回循环后的节点或END
            end_node = next((n for n in self.workflow_def.nodes if n.type == "End"), None)
            end_node_id = end_node.id if end_node else None
            
            if loop_exit_edge:
                # 如果退出边指向 End 节点，返回 END
                if loop_exit_edge.target == end_node_id:
                    logger.info(f"循环结束，退出到END", node_id=loop_node_id)
                    return END
                logger.info(f"循环结束，退出到节点", node_id=loop_node_id, target=loop_exit_edge.target)
                return loop_exit_edge.target
            
            # 兼容旧版本：如果没有 branch 字段，使用第二条边作为退出
            if len(loop_edges) > 1:
                exit_target = loop_edges[1].target
                if exit_target == end_node_id:
                    logger.info(f"循环结束（兼容模式），退出到END", node_id=loop_node_id)
                    return END
                logger.info(f"循环结束（兼容模式）", node_id=loop_node_id, target=exit_target)
                return exit_target
            elif loop_edges:
                # 只有一条边，无法确定退出路径
                logger.warning(f"循环节点只有一条边，无法确定退出路径", node_id=loop_node_id)
                return END
            
            logger.warning(f"循环节点缺少退出边", node_id=loop_node_id)
            return END
    
    def build(self) -> StateGraph:
        """
        构建并编译工作流图
        
        Returns:
            编译后的状态图
        """
        logger.info(f"开始构建工作流图", workflow_name=self.workflow_def.name)
        
        # 1. 添加所有节点
        for node in self.workflow_def.nodes:
            if node.type == "Start":
                # Start 节点只是入口点，不添加到图中
                pass
            elif node.type == "End":
                # End 节点只是结束点，不添加到图中
                pass
            else:
                try:
                    node_func = self._create_node_function(node)
                    logger.debug(f"创建节点函数: {node.id} ({node.type})")
                    self.graph.add_node(node.id, node_func)
                    logger.debug(f"添加节点成功: {node.id} ({node.type})")
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    logger.error(f"添加节点失败: {node.id}", error=str(e), detail=error_detail)
                    # 检查是否是重复节点
                    existing_nodes = []
                    try:
                        existing_nodes = list(self.graph.nodes.keys())
                    except:
                        pass
                    logger.error(f"已存在的节点: {existing_nodes}")
                    raise
        
        # 2. 添加边
        # 查找 Start 和 End 节点
        start_node = next((n for n in self.workflow_def.nodes if n.type == "Start"), None)
        end_node = next((n for n in self.workflow_def.nodes if n.type == "End"), None)
        
        # 收集每个源节点的所有边，避免重复调用add_conditional_edges
        edges_by_source = {}
        for edge in self.workflow_def.edges:
            if edge.source not in edges_by_source:
                edges_by_source[edge.source] = []
            edges_by_source[edge.source].append(edge)
        
        # 按源节点分组处理边
        for source, edges in edges_by_source.items():
            source_node_def = next((n for n in self.workflow_def.nodes if n.id == source), None)
            
            # 特殊处理 Start 节点：设置入口点（支持多链路并行）
            if source == start_node.id if start_node else False:
                if len(edges) == 1:
                    # 单入口：直接设置入口点
                    self.graph.set_entry_point(edges[0].target)
                    logger.debug(f"设置入口点: {edges[0].target}")
                else:
                    # 多入口（并行链路）：添加虚拟起始节点实现扇出
                    def create_fan_out_node(node_id: str):
                        """创建扇出节点函数，记录监控信息"""
                        def fan_out(state: WorkflowState) -> Dict[str, Any]:
                            if self.monitor:
                                self.monitor.start_node(node_id, "Start", {})
                                self.monitor.complete_node(node_id, {"fan_out": True})
                            return {}
                        return fan_out
                    
                    # 使用带前缀的虚拟节点ID，避免与 LangGraph 保留名称冲突
                    virtual_start_id = "_workflow_fan_out_start_"
                    # 防御性检查：确保虚拟节点不重复添加
                    if virtual_start_id not in self.graph.nodes:
                        self.graph.add_node(virtual_start_id, create_fan_out_node(virtual_start_id))
                    self.graph.set_entry_point(virtual_start_id)
                    
                    # 从虚拟起始节点连接到所有目标
                    for edge in edges:
                        self.graph.add_edge(virtual_start_id, edge.target)
                        logger.debug(f"添加并行起始边: {virtual_start_id} -> {edge.target}")
                    
                    logger.info(f"检测到 {len(edges)} 条并行链路，已创建扇出节点: {[e.target for e in edges]}")
                continue
            
            # 检查是否需要条件边
            has_condition = any(e.condition for e in edges)
            has_branch = any(e.branch for e in edges)  # 检查是否有 branch 字段
            source_has_conditions = source_node_def and source_node_def.type in ["Condition", "Loop"]
            
            if source_node_def and source_node_def.type == "Loop":
                # 循环节点：使用条件边路由
                # 收集循环体和退出分支
                loop_body_target = None
                loop_exit_target = END
                end_node_id = end_node.id if end_node else None
                
                for edge in edges:
                    if edge.branch == "loop_body":
                        loop_body_target = edge.target
                    elif edge.branch == "loop_exit":
                        # 如果退出目标指向 End 节点，使用 END
                        if edge.target == end_node_id:
                            loop_exit_target = END
                        else:
                            loop_exit_target = edge.target
                
                # 如果没有显式 branch 字段，使用兼容模式
                if not loop_body_target and edges:
                    loop_body_target = edges[0].target
                if loop_exit_target == END and len(edges) > 1:
                    # 兼容模式：第二条边作为退出
                    exit_edge_target = edges[1].target
                    if exit_edge_target != end_node_id:
                        loop_exit_target = exit_edge_target
                
                # 构建条件映射：路由函数返回节点ID或END
                condition_map = {}
                if loop_body_target:
                    condition_map[loop_body_target] = loop_body_target
                condition_map[loop_exit_target] = loop_exit_target
                if END not in condition_map:
                    condition_map[END] = END
                
                self.graph.add_conditional_edges(
                    source,
                    lambda state, src=source: self._route_loop(state, src),
                    condition_map
                )
                logger.info(f"添加循环条件边: {source} -> body={loop_body_target}, exit={loop_exit_target}, map={condition_map}")
                
            elif source_has_conditions and has_condition:
                # 条件节点：使用条件边
                if source_node_def.type == "Condition":
                    # 收集所有条件分支
                    condition_map = {}
                    for edge in edges:
                        if edge.condition:
                            condition_map[edge.condition] = edge.target
                    
                    self.graph.add_conditional_edges(
                        source,
                        lambda state, src=source: self._route_condition(state, src),
                        condition_map
                    )
                    logger.debug(f"添加条件边: {source} -> {condition_map}")
            else:
                # 使用普通边
                for edge in edges:
                    # 特殊处理指向 End 的边
                    if edge.target == end_node.id if end_node else False:
                        self.graph.add_edge(source, END)
                        logger.debug(f"添加结束边: {source} -> END")
                    else:
                        self.graph.add_edge(source, edge.target)
                        logger.debug(f"添加普通边: {source} -> {edge.target}")
        
        logger.info(f"工作流图构建完成，包含 {len(self.workflow_def.nodes)} 个节点")
        
        # 编译并返回图
        return self.graph.compile()