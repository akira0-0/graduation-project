"""
数据存储服务
管理收集数据的持久化存储
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..database.connection import get_session
from ..database.repositories import WorkflowRepository
from ..database.memory_service import AgentMemoryService
from ..utils.logger import get_logger

logger = get_logger("data_storage_service")


class DataStorageService:
    """
    数据存储服务
    负责将收集的数据存储到数据库，并管理与工作流的关联
    """
    
    def __init__(self, workflow_id: Optional[str] = None):
        """
        初始化数据存储服务
        
        Args:
            workflow_id: 工作流ID（可选）
        """
        self.session = get_session()
        self.memory_service = AgentMemoryService(self.session)
        self.workflow_repo = WorkflowRepository(self.session)
        self.workflow_id = workflow_id

    def _resolve_persistable_workflow_id(
        self,
        workflow_id: Optional[str],
        operation: str
    ) -> Optional[str]:
        """
        写库前校验 workflow_id（必须为 UUID 且存在于 workflows 表）
        不满足时降级为“不写库但继续执行”。
        """
        if not workflow_id:
            logger.warning(f"{operation} 降级：workflow_id 缺失，跳过写库")
            return None

        normalized = str(workflow_id).strip()
        try:
            uuid.UUID(normalized)
        except (ValueError, TypeError):
            logger.warning(
                f"{operation} 降级：workflow_id 非UUID，跳过写库",
                workflow_id=workflow_id
            )
            return None

        try:
            if self.workflow_repo.get_by_id(normalized) is None:
                logger.warning(
                    f"{operation} 降级：workflow_id 不存在于workflows，跳过写库",
                    workflow_id=normalized
                )
                return None
        except Exception as e:
            logger.warning(
                f"{operation} 降级：workflow_id 校验失败，跳过写库",
                workflow_id=normalized,
                error=str(e)
            )
            return None

        return normalized
    
    def store_collected_data(
        self,
        data: List[Dict[str, Any]],
        agent_type: str = "data_collection",
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        存储收集的数据
        
        Args:
            data: 收集的数据列表
            agent_type: 智能体类型
            workflow_id: 工作流ID（可选，优先使用参数）
            
        Returns:
            存储结果统计
        """
        wf_id = self._resolve_persistable_workflow_id(
            workflow_id or self.workflow_id,
            operation="store_collected_data"
        )
        if not wf_id:
            return {
                "total": len(data),
                "stored": 0,
                "failed": 0,
                "skipped": len(data),
                "degraded": True,
                "errors": None
            }
        
        logger.info(f"存储收集数据: {len(data)}条, 工作流: {wf_id}")
        
        stored_count = 0
        errors = []
        
        for idx, item in enumerate(data):
            try:
                # 生成唯一键
                key = item.get("id", f"data_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{idx}")
                
                # 存储为智能体记忆
                memory_record = self.memory_service.save_memory(
                    workflow_id=wf_id,
                    agent_type=agent_type,
                    memory_type="collected_data",
                    key=key,
                    value=item,
                    extra_data={
                        "source": item.get("source", "unknown"),
                        "timestamp": item.get("timestamp", datetime.utcnow().isoformat()),
                        "stored_at": datetime.utcnow().isoformat()
                    }
                )

                if memory_record is not None:
                    stored_count += 1
                else:
                    errors.append(f"存储数据项 {idx} 被降级跳过")
                
            except Exception as e:
                error_msg = f"存储数据项 {idx} 失败: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        result = {
            "total": len(data),
            "stored": stored_count,
            "failed": len(data) - stored_count,
            "errors": errors if errors else None
        }
        
        logger.info(f"数据存储完成: 成功{stored_count}条, 失败{len(data) - stored_count}条")
        return result
    
    def store_analysis_result(
        self,
        result: Dict[str, Any],
        analysis_type: str,
        agent_type: str,
        workflow_id: Optional[str] = None
    ) -> bool:
        """
        存储分析结果
        
        Args:
            result: 分析结果
            analysis_type: 分析类型（如 sentiment, filter）
            agent_type: 智能体类型
            workflow_id: 工作流ID
            
        Returns:
            存储是否成功
        """
        wf_id = self._resolve_persistable_workflow_id(
            workflow_id or self.workflow_id,
            operation="store_analysis_result"
        )
        if not wf_id:
            return False
        
        try:
            key = f"{analysis_type}_result_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            memory_record = self.memory_service.save_memory(
                workflow_id=wf_id,
                agent_type=agent_type,
                memory_type="analysis_result",
                key=key,
                value=result,
                extra_data={
                    "analysis_type": analysis_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            if memory_record is None:
                logger.warning(f"存储分析结果降级跳过: {analysis_type}")
                return False
            
            logger.info(f"存储分析结果成功: {analysis_type}")
            return True
            
        except Exception as e:
            logger.error(f"存储分析结果失败: {e}")
            return False
    
    def get_collected_data(
        self,
        workflow_id: Optional[str] = None,
        agent_type: str = "data_collection",
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取收集的数据
        
        Args:
            workflow_id: 工作流ID
            agent_type: 智能体类型
            source: 数据来源（可选）
            limit: 返回的最大数量
            
        Returns:
            数据列表
        """
        wf_id = workflow_id or self.workflow_id
        if not wf_id:
            raise ValueError("必须提供workflow_id")
        
        memories = self.memory_service.get_memory(
            workflow_id=wf_id,
            agent_type=agent_type,
            memory_type="collected_data"
        )
        
        data = []
        for m in memories[:limit]:
            item = m.value
            if source and item.get("source") != source:
                continue
            data.append(item)
        
        return data
    
    def get_analysis_results(
        self,
        workflow_id: Optional[str] = None,
        analysis_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取分析结果
        
        Args:
            workflow_id: 工作流ID
            analysis_type: 分析类型（可选）
            
        Returns:
            分析结果列表
        """
        wf_id = workflow_id or self.workflow_id
        if not wf_id:
            raise ValueError("必须提供workflow_id")
        
        # 获取所有智能体类型的分析结果
        agent_types = ["sentiment_analysis", "filter_agent", "data_collection"]
        results = []
        
        for agent_type in agent_types:
            memories = self.memory_service.get_memory(
                workflow_id=wf_id,
                agent_type=agent_type,
                memory_type="analysis_result"
            )
            
            for m in memories:
                result = {
                    "id": m.key,
                    "agent_type": agent_type,
                    "data": m.value,
                    "extra_data": m.extra_data
                }
                
                # 如果指定了分析类型，进行过滤
                if analysis_type and m.extra_data:
                    if m.extra_data.get("analysis_type") != analysis_type:
                        continue
                
                results.append(result)
        
        # 按时间排序
        results.sort(key=lambda x: x.get("extra_data", {}).get("timestamp", ""), reverse=True)
        
        return results
    
    def store_report(
        self,
        report_content: str,
        report_format: str = "markdown",
        metadata: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> str:
        """
        存储生成的报告
        
        Args:
            report_content: 报告内容
            report_format: 报告格式
            metadata: 报告元数据
            workflow_id: 工作流ID
            
        Returns:
            报告ID
        """
        wf_id = self._resolve_persistable_workflow_id(
            workflow_id or self.workflow_id,
            operation="store_report"
        )
        report_id = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        if not wf_id:
            return f"{report_id}_degraded"
        
        memory_record = self.memory_service.save_memory(
            workflow_id=wf_id,
            agent_type="report_generation",
            memory_type="report",
            key=report_id,
            value={
                "content": report_content,
                "format": report_format,
                "created_at": datetime.utcnow().isoformat()
            },
            extra_data=metadata or {}
        )

        if memory_record is None:
            logger.warning(f"报告写库被降级跳过: {report_id}")
            return f"{report_id}_degraded"
        
        logger.info(f"报告存储成功: {report_id}")
        return report_id
    
    def get_report(
        self,
        workflow_id: Optional[str] = None,
        report_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取报告
        
        Args:
            workflow_id: 工作流ID
            report_id: 报告ID（可选，如果不提供则返回最新的）
            
        Returns:
            报告内容
        """
        wf_id = workflow_id or self.workflow_id
        if not wf_id:
            raise ValueError("必须提供workflow_id")
        
        if report_id:
            # 获取指定报告
            memories = self.memory_service.get_memory(
                workflow_id=wf_id,
                agent_type="report_generation",
                memory_type="report",
                key=report_id
            )
            if memories:
                m = memories[0]
                return {
                    "id": m.key,
                    **m.value,
                    "metadata": m.extra_data
                }
        else:
            # 获取最新报告
            memories = self.memory_service.get_memory(
                workflow_id=wf_id,
                agent_type="report_generation",
                memory_type="report"
            )
            if memories:
                # 按时间排序，返回最新的
                memories.sort(key=lambda x: x.value.get("created_at", ""), reverse=True)
                m = memories[0]
                return {
                    "id": m.key,
                    **m.value,
                    "metadata": m.extra_data
                }
        
        return None
    
    def get_workflow_data_summary(
        self,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取工作流数据摘要
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            数据摘要
        """
        wf_id = workflow_id or self.workflow_id
        if not wf_id:
            raise ValueError("必须提供workflow_id")
        
        # 获取各类数据统计
        collected_data = self.memory_service.get_memory(
            workflow_id=wf_id,
            agent_type="data_collection",
            memory_type="collected_data"
        )
        
        sentiment_results = self.memory_service.get_memory(
            workflow_id=wf_id,
            agent_type="sentiment_analysis",
            memory_type="analysis_result"
        )
        
        filter_results = self.memory_service.get_memory(
            workflow_id=wf_id,
            agent_type="filter_agent",
            memory_type="analysis_result"
        )
        
        reports = self.memory_service.get_memory(
            workflow_id=wf_id,
            agent_type="report_generation",
            memory_type="report"
        )
        
        return {
            "workflow_id": wf_id,
            "collected_data_count": len(collected_data),
            "sentiment_analysis_count": len(sentiment_results),
            "filter_results_count": len(filter_results),
            "reports_count": len(reports),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def close(self):
        """关闭数据库会话"""
        if self.session:
            self.session.close()