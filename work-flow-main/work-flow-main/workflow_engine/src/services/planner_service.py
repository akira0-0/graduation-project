"""
规划服务
封装工作流规划的逻辑，提供给上层服务调用
"""
from typing import Optional, Dict, Any
from ..core.schema import WorkflowDefinition
from ..planner.llm_planner import LLMPlanner
from ..planner.enhanced_planner import EnhancedLLMPlanner
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger("planner_service")


def _normalize_model_name(model: Optional[str]) -> Optional[str]:
    normalized = model.strip() if isinstance(model, str) else model
    if not normalized:
        return None
    if normalized == "deepseek-chat":
        configured_model = get_settings().llm_model
        if configured_model and configured_model != "deepseek-chat":
            return configured_model
    return normalized


class PlannerService:
    """
    规划服务
    负责将自然语言意图转换为工作流定义
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        初始化规划服务
        
        Args:
            model_name: LLM 模型名称
        """
        self.model_name = model_name
        self._llm_planner: Optional[LLMPlanner] = None
        self._enhanced_planner: Optional[EnhancedLLMPlanner] = None
    
    @property
    def llm_planner(self) -> LLMPlanner:
        """获取 LLM 规划器（懒加载）"""
        if self._llm_planner is None:
            self._llm_planner = LLMPlanner(model_name=self.model_name)
        return self._llm_planner
    
    @property
    def enhanced_planner(self) -> EnhancedLLMPlanner:
        """获取增强版规划器（懒加载）"""
        if self._enhanced_planner is None:
            self._enhanced_planner = EnhancedLLMPlanner(model_name=self.model_name)
        return self._enhanced_planner
    
    def generate_workflow(
        self,
        intent: str,
        model: Optional[str] = None
    ) -> WorkflowDefinition:
        """
        根据自然语言意图生成工作流定义
        
        Args:
            intent: 用户的自然语言描述
            model: 指定使用的模型（可选）
            
        Returns:
            生成的工作流定义
        """
        model_name = _normalize_model_name(model) or self.model_name
        logger.info(f"开始生成工作流", intent_length=len(intent), model=model_name)
        
        # 如果模型不同，创建新的规划器
        if model_name and model_name != self.model_name:
            planner = LLMPlanner(model_name=model_name)
        else:
            planner = self.llm_planner
        
        try:
            workflow_def = planner.plan(user_intent=intent)
            logger.info(
                "工作流生成成功",
                workflow_name=workflow_def.name,
                node_count=len(workflow_def.nodes),
                edge_count=len(workflow_def.edges)
            )
            return workflow_def
        except Exception as e:
            logger.error(f"工作流生成失败: {str(e)}", intent=intent[:100])
            raise
    
    def generate_public_opinion_workflow(
        self,
        topic: str,
        requirements: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None
    ) -> WorkflowDefinition:
        """
        生成舆论分析工作流
        
        Args:
            topic: 分析主题
            requirements: 额外需求配置
            model: 指定使用的模型（可选）
            
        Returns:
            生成的舆论分析工作流定义
        """
        model_name = _normalize_model_name(model) or self.model_name
        logger.info(f"开始生成舆论分析工作流", topic=topic, model=model_name)
        
        # 如果模型不同，创建新的规划器
        if model_name and model_name != self.model_name:
            planner = EnhancedLLMPlanner(model_name=model_name)
        else:
            planner = self.enhanced_planner
        
        try:
            workflow_def = planner.plan_public_opinion_workflow(
                topic=topic,
                requirements=requirements
            )
            logger.info(
                "舆论分析工作流生成成功",
                workflow_name=workflow_def.name,
                node_count=len(workflow_def.nodes)
            )
            return workflow_def
        except Exception as e:
            logger.error(f"舆论分析工作流生成失败: {str(e)}", topic=topic)
            raise
    
    def get_agent_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有预设的智能体模板
        
        Returns:
            智能体模板字典
        """
        try:
            templates = self.enhanced_planner.get_agent_templates()
            logger.info("获取智能体模板成功", template_count=len(templates))
            return templates
        except Exception as e:
            logger.error(f"获取智能体模板失败: {str(e)}")
            raise
    
    def validate_workflow(self, workflow_def: WorkflowDefinition) -> bool:
        """
        验证工作流定义的有效性
        
        Args:
            workflow_def: 工作流定义
            
        Returns:
            是否有效
        """
        # 检查节点
        if not workflow_def.nodes:
            logger.warning("工作流没有节点")
            return False
        
        # 检查边
        if not workflow_def.edges:
            logger.warning("工作流没有边")
            return False
        
        # 检查是否有 Start 和 End 节点
        has_start = any(n.type == "Start" for n in workflow_def.nodes)
        has_end = any(n.type == "End" for n in workflow_def.nodes)
        
        if not has_start:
            logger.warning("工作流缺少 Start 节点")
            return False
        
        if not has_end:
            logger.warning("工作流缺少 End 节点")
            return False
        
        # 检查节点 ID 唯一性
        node_ids = [n.id for n in workflow_def.nodes]
        if len(node_ids) != len(set(node_ids)):
            logger.warning("工作流存在重复的节点 ID")
            return False
        
        # 检查边的引用是否存在
        node_id_set = set(node_ids)
        for edge in workflow_def.edges:
            if edge.source not in node_id_set:
                logger.warning(f"边的源节点不存在: {edge.source}")
                return False
            if edge.target not in node_id_set:
                logger.warning(f"边的目标节点不存在: {edge.target}")
                return False
        
        logger.debug("工作流验证通过")
        return True
