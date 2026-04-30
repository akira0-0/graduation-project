"""
数据收集智能体节点（增强版）
继承 BaseNode，集成 DataCollectionAgent 的功能

增强功能：
- 关键词联想与扩展：使用 LLM 生成相关关键词，扩大信息覆盖面
- 多轮迭代收集：支持迭代式数据收集，逐步扩大搜索范围
- 数据量控制：确保收集足够的数据量（目标：50-100条）
- 智能数据筛选：根据相关性评分筛选高质量数据
"""
from typing import Any, Dict
from .base import BaseNode
from ..core.schema import NodeDefinition, WorkflowState
from ..agents.data_collection_agent import DataCollectionAgent
from ..utils.logger import get_logger

logger = get_logger("data_collection_agent_node")


class DataCollectionAgentNode(BaseNode):
    """数据收集智能体节点（增强版）"""
    
    def __init__(self, node_def: NodeDefinition):
        """
        初始化数据收集智能体节点
        
        Args:
            node_def: 节点定义
        """
        super().__init__(node_def)
        self.agent = None
        
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        执行数据收集（增强版）
        
        支持两种模式：
        1. 智能收集模式（默认）：使用 LLM 进行关键词扩展和多轮迭代收集
        2. 传统模式：使用预设工作流收集
        
        Args:
            state: 工作流状态
            
        Returns:
            收集的数据结果
        """
        logger.info(f"执行数据收集智能体节点: {self.node_id}")
        
        try:
            # 获取参数
            topic = self.get_input_value(state, "topic")
            sources = self.get_input_value(state, "sources") or ["internet"]
            max_results = self.get_input_value(state, "max_results") or 50
            time_range = self.get_input_value(state, "time_range") or "week"
            
            # 增强参数
            use_intelligent_collection = self.get_input_value(state, "use_intelligent_collection")
            if use_intelligent_collection is None:
                use_intelligent_collection = True  # 默认启用智能收集
            
            use_keyword_expansion = self.get_input_value(state, "use_keyword_expansion")
            if use_keyword_expansion is None:
                use_keyword_expansion = True  # 默认启用关键词扩展
            
            evaluate_quality = self.get_input_value(state, "evaluate_quality")
            if evaluate_quality is None:
                evaluate_quality = True  # 默认启用质量评估
            
            target_count = self.get_input_value(state, "target_count") or 50
            max_iterations = self.get_input_value(state, "max_iterations") or 3
            language = self.get_input_value(state, "language") or "zh"
            
            if not topic:
                logger.warning("未指定搜索主题，使用默认主题")
                topic = "默认主题"
            
            logger.info(f"搜索主题: {topic}, 目标数量: {target_count}, 智能模式: {use_intelligent_collection}")
            
            # 从状态中获取 workflow_id（仅使用数据库主键ID；缺失时降级为不写库）
            workflow_id = state.workflow_id
            self.agent = DataCollectionAgent(
                workflow_id=workflow_id,
                auto_save=bool(workflow_id),
                use_llm=use_intelligent_collection  # 启用 LLM 增强功能
            )
            
            # 根据模式选择收集方式
            if use_intelligent_collection:
                logger.info("使用智能收集模式")
                result = self.agent.execute_intelligent_collection(
                    topic=topic,
                    target_count=target_count,
                    max_iterations=max_iterations,
                    use_keyword_expansion=use_keyword_expansion,
                    evaluate_quality=evaluate_quality,
                    language=language
                )
            else:
                logger.info("使用传统收集模式")
                result = self.agent.execute_preset_workflow(
                    topic=topic,
                    workflow_steps=["internet_search", "knowledge_base_search", "real_time_collection", "data_aggregation"],
                    use_intelligent_collection=False
                )
            
            collected_data = result.get("collected_data", [])
            # 统一统计口径：以 collected_data 实际长度为准
            total_count = len(collected_data)
            
            # 计算数据质量统计
            high_quality_count = sum(
                1 for item in collected_data
                if item.get("relevance_score", 0.5) >= 0.7
            )
            avg_relevance = sum(
                item.get("relevance_score", 0.5) for item in collected_data
            ) / total_count if total_count > 0 else 0

            # 返回结果
            return {
                "topic": topic,
                "sources": sources,
                "max_results": max_results,
                "time_range": time_range,
                "collected_data": collected_data,
                "total_count": total_count,
                "target_count": target_count,
                "target_achieved": total_count >= target_count,
                "expanded_keywords": result.get("expanded_keywords", [topic]),
                "iterations": result.get("iterations", 1),
                "quality_stats": {
                    "high_quality_count": high_quality_count,
                    "average_relevance_score": round(avg_relevance, 3)
                },
                "collection_method": "intelligent" if use_intelligent_collection else "traditional",
                "status": "success",
                "message": f"成功收集 {total_count} 条数据（目标: {target_count}）"
            }
            
        except Exception as e:
            logger.error(f"数据收集失败: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "collected_data": [],
                "total_count": 0,
                "message": f"数据收集失败: {str(e)}"
            }