"""
智能体服务
封装智能体模板管理的业务逻辑
"""
from typing import Dict, Any, Optional
from .planner_service import PlannerService
from ..database.repositories import MemoryRepository
from ..utils.logger import get_logger

logger = get_logger("agent_service")


class AgentService:
    """
    智能体服务
    负责智能体模板管理、记忆管理等业务逻辑
    """
    
    def __init__(
        self,
        memory_repo: Optional[MemoryRepository] = None,
        planner_service: Optional[PlannerService] = None
    ):
        """
        初始化智能体服务
        
        Args:
            memory_repo: 记忆仓储（可选）
            planner_service: 规划服务（可选）
        """
        self.memory_repo = memory_repo
        self._planner_service = planner_service
    
    @property
    def planner_service(self) -> PlannerService:
        """获取规划服务（懒加载）"""
        if self._planner_service is None:
            self._planner_service = PlannerService()
        return self._planner_service
    
    def get_agent_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有预设的智能体模板
        
        Returns:
            智能体模板字典
        """
        logger.info("获取智能体模板")
        return self.planner_service.get_agent_templates()
    
    def get_agent_template(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """
        获取指定类型的智能体模板
        
        Args:
            agent_type: 智能体类型
            
        Returns:
            智能体模板，如果不存在则返回 None
        """
        templates = self.get_agent_templates()
        return templates.get(agent_type)
    
    def save_agent_memory(
        self,
        workflow_id: str,
        agent_type: str,
        memory_type: str,
        key: str,
        value: Any,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        保存智能体记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            memory_type: 记忆类型
            key: 记忆键
            value: 记忆值
            extra_data: 额外元数据
            
        Returns:
            记忆实体，如果没有 memory_repo 则返回 None
        """
        if not self.memory_repo:
            logger.warning("memory_repo 未初始化，无法保存记忆")
            return None
        
        logger.debug(
            "保存智能体记忆",
            workflow_id=workflow_id,
            agent_type=agent_type,
            memory_type=memory_type,
            key=key
        )
        
        return self.memory_repo.save_memory(
            workflow_id=workflow_id,
            agent_type=agent_type,
            memory_type=memory_type,
            key=key,
            value=value,
            extra_data=extra_data
        )
    
    def get_agent_memory(
        self,
        workflow_id: str,
        agent_type: str,
        memory_type: Optional[str] = None,
        key: Optional[str] = None
    ) -> list:
        """
        获取智能体记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            memory_type: 记忆类型（可选）
            key: 记忆键（可选）
            
        Returns:
            记忆列表
        """
        if not self.memory_repo:
            logger.warning("memory_repo 未初始化")
            return []
        
        return self.memory_repo.get_by_agent_type(
            workflow_id=workflow_id,
            agent_type=agent_type,
            memory_type=memory_type
        )
    
    def get_domain_knowledge(
        self,
        workflow_id: str,
        agent_type: str
    ) -> Dict[str, Any]:
        """
        获取智能体的领域知识
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            
        Returns:
            领域知识字典
        """
        if not self.memory_repo:
            return {}
        
        return self.memory_repo.get_domain_knowledge(workflow_id, agent_type)
    
    def get_case_patterns(
        self,
        workflow_id: str,
        agent_type: str
    ) -> list:
        """
        获取智能体的案例模式
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            
        Returns:
            案例模式列表
        """
        if not self.memory_repo:
            return []
        
        return self.memory_repo.get_case_patterns(workflow_id, agent_type)
    
    def get_templates(
        self,
        workflow_id: str,
        agent_type: str
    ) -> Dict[str, str]:
        """
        获取智能体的模板
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            
        Returns:
            模板字典
        """
        if not self.memory_repo:
            return {}
        
        return self.memory_repo.get_templates(workflow_id, agent_type)
    
    def get_rules(
        self,
        workflow_id: str,
        agent_type: str
    ) -> list:
        """
        获取智能体的规则
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            
        Returns:
            规则列表
        """
        if not self.memory_repo:
            return []
        
        return self.memory_repo.get_rules(workflow_id, agent_type)
    
    def clear_agent_memory(
        self,
        workflow_id: str,
        agent_type: Optional[str] = None,
        memory_type: Optional[str] = None
    ) -> int:
        """
        清除智能体记忆
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型（可选，如果指定则只清除该类型的记忆）
            memory_type: 记忆类型（可选，如果指定则只清除该类型的记忆）
            
        Returns:
            删除的记录数
        """
        if not self.memory_repo:
            logger.warning("memory_repo 未初始化")
            return 0
        
        if agent_type:
            return self.memory_repo.delete_by_agent_type(
                workflow_id=workflow_id,
                agent_type=agent_type,
                memory_type=memory_type
            )
        else:
            return self.memory_repo.delete_by_workflow(workflow_id)
    
    def get_agent_types_with_memory(self, workflow_id: str) -> list:
        """
        获取工作流中有记忆的所有智能体类型
        
        Args:
            workflow_id: 工作流 ID
            
        Returns:
            智能体类型列表
        """
        if not self.memory_repo:
            return []
        
        return self.memory_repo.get_agent_types(workflow_id)
    
    def get_memory_types_for_agent(
        self,
        workflow_id: str,
        agent_type: str
    ) -> list:
        """
        获取智能体的所有记忆类型
        
        Args:
            workflow_id: 工作流 ID
            agent_type: 智能体类型
            
        Returns:
            记忆类型列表
        """
        if not self.memory_repo:
            return []
        
        memories = self.memory_repo.get_by_agent_type(workflow_id, agent_type)
        return list(set(m.memory_type for m in memories))