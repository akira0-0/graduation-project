"""
执行服务
封装工作流执行的核心业务逻辑（仅使用 LangGraph 引擎）
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from uuid import UUID
from ..core.schema import WorkflowDefinition
from ..core.builder import GraphBuilder
from ..monitoring import ExecutionMonitor
from ..database.repositories import WorkflowRepository, AuditLogRepository, ExecutionRepository
from ..utils.logger import get_logger

logger = get_logger("execution_service")


class ExecutionService:
    """
    执行服务
    负责工作流的执行、监控和结果管理
    """
    
    def __init__(
        self,
        workflow_repo: Optional[WorkflowRepository] = None,
        audit_log_repo: Optional[AuditLogRepository] = None,
        execution_repo: Optional[ExecutionRepository] = None
    ):
        """
        初始化执行服务
        
        Args:
            workflow_repo: 工作流仓储（可选）
            audit_log_repo: 审计日志仓储（可选）
            execution_repo: 执行记录仓储（可选）
        """
        self.workflow_repo = workflow_repo
        self.audit_log_repo = audit_log_repo
        self.execution_repo = execution_repo

    def _is_valid_workflow_id(self, workflow_id: Optional[str]) -> bool:
        """检查 workflow_id 是否为 UUID 格式"""
        if not workflow_id:
            return False
        try:
            UUID(str(workflow_id))
            return True
        except (ValueError, TypeError):
            return False

    def _normalize_workflow_id(
        self,
        workflow_id: Optional[str],
        workflow_name: str
    ) -> Optional[str]:
        """
        归一化 workflow_id：
        - 合法且存在于 workflows 表的 UUID：原样返回
        - 非 UUID / 不存在：降级为 None（继续执行但不写库）
        """
        if workflow_id is None:
            return None

        normalized = str(workflow_id).strip()
        if not normalized:
            return None

        if not self._is_valid_workflow_id(normalized):
            logger.warning(
                "检测到非UUID workflow_id，降级为不写库继续执行",
                workflow_id=workflow_id,
                workflow_name=workflow_name
            )
            return None

        if self.workflow_repo:
            try:
                if self.workflow_repo.get_by_id(normalized) is None:
                    logger.warning(
                        "workflow_id 不存在于workflows表，降级为不写库继续执行",
                        workflow_id=normalized,
                        workflow_name=workflow_name
                    )
                    return None
            except Exception as e:
                logger.warning(
                    "workflow_id 存在性校验失败，降级为不写库继续执行",
                    workflow_id=normalized,
                    workflow_name=workflow_name,
                    error=str(e)
                )
                return None

        return normalized

    def _extract_report_content(
        self,
        workflow_def: WorkflowDefinition,
        node_outputs: Dict[str, Any]
    ) -> Optional[str]:
        """
        从节点输出中提取报告正文内容：
        1) 优先按 ReportAgent 节点顺序提取
        2) 兜底扫描任意包含 report_content 的节点输出
        """
        if not isinstance(node_outputs, dict):
            return None

        # 1. 优先从 ReportAgent 节点提取
        report_node_ids = [node.id for node in workflow_def.nodes if node.type == "ReportAgent"]
        for node_id in report_node_ids:
            node_output = node_outputs.get(node_id)
            if isinstance(node_output, dict) and "report_content" in node_output:
                content = node_output.get("report_content")
                if content is None:
                    return None
                normalized = str(content).strip()
                return normalized if normalized else None

        # 2. 兜底：扫描任意节点输出
        for node_output in node_outputs.values():
            if isinstance(node_output, dict) and "report_content" in node_output:
                content = node_output.get("report_content")
                if content is None:
                    return None
                normalized = str(content).strip()
                return normalized if normalized else None

        return None

    def _has_executable_nodes(self, workflow_def: WorkflowDefinition) -> bool:
        """是否包含可执行节点（非 Start/End）"""
        return any(node.type not in {"Start", "End"} for node in workflow_def.nodes)

    @staticmethod
    def _to_iso_datetime(value: Optional[datetime]) -> Optional[str]:
        """将 datetime 转为 ISO 字符串"""
        return value.isoformat() if value else None

    @staticmethod
    def _normalize_trace_status(status: str) -> str:
        """归一化节点状态（监控 success -> 存储 completed）"""
        if status == "success":
            return "completed"
        return status

    def _serialize_execution_run(
        self,
        run: Any,
        node_traces: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        return {
            "execution_id": run.execution_id,
            "workflow_id": run.workflow_id,
            "status": run.status,
            "started_at": self._to_iso_datetime(run.started_at),
            "completed_at": self._to_iso_datetime(run.completed_at),
            "duration_ms": run.duration_ms,
            "trigger_source": run.trigger_source,
            "error_message": run.error_message,
            "final_report_path": run.final_report_path,
            "created_at": self._to_iso_datetime(run.created_at),
            "updated_at": self._to_iso_datetime(run.updated_at),
            "node_traces": node_traces or []
        }

    def _serialize_node_trace(self, trace: Any) -> Dict[str, Any]:
        return {
            "execution_id": trace.execution_id,
            "node_id": trace.node_id,
            "node_type": trace.node_type,
            "status": trace.status,
            "input_payload": trace.input_payload,
            "output_payload": trace.output_payload,
            "error_message": trace.error_message,
            "started_at": self._to_iso_datetime(trace.started_at),
            "completed_at": self._to_iso_datetime(trace.completed_at),
            "duration_ms": trace.duration_ms,
            "created_at": self._to_iso_datetime(trace.created_at)
        }

    def _persist_node_traces(self, execution_id: str, monitor: Optional[ExecutionMonitor]) -> None:
        """将监控器中的节点记录最小接入持久化"""
        if not self.execution_repo or not monitor:
            return

        for record in monitor.node_records.values():
            try:
                self.execution_repo.upsert_node_trace_status(
                    execution_id=execution_id,
                    node_id=record.node_id,
                    status=self._normalize_trace_status(record.status.value),
                    node_type=record.node_type,
                    input_payload=record.input_data,
                    output_payload=record.output_data,
                    error_message=record.error_message,
                    started_at=record.start_time,
                    completed_at=record.end_time
                )
            except Exception as trace_error:
                logger.warning(
                    "节点追踪持久化失败",
                    execution_id=execution_id,
                    node_id=record.node_id,
                    error=str(trace_error)
                )

    def execute_workflow(
        self,
        workflow_def: WorkflowDefinition,
        enable_monitoring: bool = True,
        variables: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行工作流
        
        Args:
            workflow_def: 工作流定义
            enable_monitoring: 是否启用监控
            variables: 工作流变量
            workflow_id: 工作流 ID（用于审计日志）
            
        Returns:
            执行结果字典
        """
        normalized_workflow_id = self._normalize_workflow_id(workflow_id, workflow_def.name)

        logger.info(
            "开始执行工作流",
            workflow_name=workflow_def.name,
            enable_monitoring=enable_monitoring,
            workflow_id=normalized_workflow_id
        )

        # 特殊场景：仅有 Start/End（无可执行节点）时，直接返回成功空结果，避免构图失败
        if not self._has_executable_nodes(workflow_def):
            logger.info(
                "工作流无可执行节点，直接返回空结果",
                workflow_name=workflow_def.name,
                workflow_id=normalized_workflow_id
            )
            return {
                "status": "completed",
                "execution_id": None,
                "result": {},
                "summary": None,
                "report_path": None,
                "report_content": None
            }
        
        # 创建监控器
        monitor = None
        if enable_monitoring:
            monitor = ExecutionMonitor(
                workflow_id=normalized_workflow_id,
                workflow_name=workflow_def.name
            )

        # 最小接入：若具备 workflow_id 且启用监控ID，则落 execution_runs 初始记录
        execution_id = monitor.execution_id if monitor else None
        if self.execution_repo and normalized_workflow_id and execution_id:
            try:
                self.execution_repo.create_execution_run(
                    execution_id=execution_id,
                    workflow_id=normalized_workflow_id,
                    status="running",
                    trigger_source="api",
                    started_at=monitor.start_time
                )
            except Exception as create_error:
                logger.warning(
                    "创建执行运行记录失败，降级继续执行",
                    execution_id=execution_id,
                    workflow_id=normalized_workflow_id,
                    error=str(create_error)
                )
        
        try:
            result = self._execute_with_langgraph(
                workflow_def,
                monitor,
                variables,
                normalized_workflow_id
            )

            # 完成监控（先完成，再回填 summary，确保状态/时间一致）
            if monitor:
                monitor.complete_workflow(success=True)
                result["summary"] = monitor.get_summary()

                # 报告在 _execute_with_langgraph 中已初次保存，这里覆盖写入最终状态
                report_path = result.get("report_path")
                if report_path:
                    try:
                        monitor.save_report(report_path)
                    except Exception as report_error:
                        logger.warning(f"更新执行报告失败: {str(report_error)}")

            # 最小接入：写入节点追踪与执行完成状态
            if self.execution_repo and normalized_workflow_id and execution_id:
                try:
                    self._persist_node_traces(execution_id=execution_id, monitor=monitor)
                    self.execution_repo.finalize_execution_run(
                        execution_id=execution_id,
                        status="completed",
                        final_report_path=result.get("report_path")
                    )
                except Exception as persist_error:
                    logger.warning(
                        "写入执行完成状态失败，降级继续返回执行结果",
                        execution_id=execution_id,
                        workflow_id=normalized_workflow_id,
                        error=str(persist_error)
                    )

            # 记录审计日志
            if self.audit_log_repo and normalized_workflow_id:
                self._log_execution(
                    workflow_id=normalized_workflow_id,
                    operator="langgraph_engine",
                    input_data={"variables": variables},
                    output_data=result,
                    status="success"
                )
            
            logger.info(
                "工作流执行成功",
                workflow_name=workflow_def.name
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"工作流执行失败: {str(e)}",
                workflow_name=workflow_def.name
            )
            
            # 记录失败审计日志
            if self.audit_log_repo and normalized_workflow_id:
                self._log_execution(
                    workflow_id=normalized_workflow_id,
                    operator="langgraph_engine",
                    input_data={"variables": variables},
                    status="failed",
                    error_message=str(e)
                )
            
            # 完成监控
            if monitor:
                monitor.complete_workflow(success=False)

            # 最小接入：写入失败节点追踪与执行失败状态
            if self.execution_repo and normalized_workflow_id and execution_id:
                try:
                    self._persist_node_traces(execution_id=execution_id, monitor=monitor)
                    self.execution_repo.finalize_execution_run(
                        execution_id=execution_id,
                        status="failed",
                        error_message=str(e)
                    )
                except Exception as persist_error:
                    logger.warning(
                        "写入执行失败状态失败，降级继续抛出原异常",
                        execution_id=execution_id,
                        workflow_id=normalized_workflow_id,
                        error=str(persist_error)
                    )
            
            raise
    
    def _execute_with_langgraph(
        self,
        workflow_def: WorkflowDefinition,
        monitor: Optional[ExecutionMonitor] = None,
        variables: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用 LangGraph 引擎执行工作流
        
        Args:
            workflow_def: 工作流定义
            monitor: 执行监控器
            variables: 工作流变量
            workflow_id: 工作流 ID
            
        Returns:
            执行结果
        """
        logger.debug("使用 LangGraph 引擎执行")
        
        # 构建图
        builder = GraphBuilder(workflow_def, monitor=monitor)
        app_graph = builder.build()
        
        # 初始化状态
        # 注意：current_node 必须是空字符串而非 None，因为使用了 operator.or_ 进行状态合并
        initial_state = {
            "workflow_id": workflow_id,  # 全链路仅使用数据库主键 workflow_id（UUID）
            "context": variables or workflow_def.variables or {},
            "node_outputs": {},
            "messages": [],
            "loop_counters": {},
            "loop_outputs": {},
            "branch_decisions": {},
            "current_node": ""  # 空字符串，避免 None | str 错误
        }
        
        # 执行工作流
        final_state = app_graph.invoke(initial_state)
        
        # 保存执行报告
        report_path = None
        if monitor:
            from pathlib import Path
            report_dir = Path("logs")
            report_dir.mkdir(exist_ok=True)
            report_path = report_dir / f"execution_report_{monitor.execution_id}.json"
            monitor.save_report(str(report_path))
        
        node_outputs = final_state.get("node_outputs", {}) or {}
        report_content = self._extract_report_content(workflow_def, node_outputs)

        return {
            "status": "completed",
            "execution_id": monitor.execution_id if monitor else None,
            "result": node_outputs,
            "summary": monitor.get_summary() if monitor else None,
            "report_path": str(report_path) if report_path else None,
            "report_content": report_content
        }
    
    def _log_execution(
        self,
        workflow_id: str,
        operator: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ):
        """
        记录执行审计日志
        
        Args:
            workflow_id: 工作流 ID
            operator: 操作者
            input_data: 输入数据
            output_data: 输出数据
            status: 状态
            error_message: 错误信息
        """
        if not self.audit_log_repo:
            return
        
        try:
            self.audit_log_repo.log_operation(
                workflow_id=workflow_id,
                operation_type="workflow_execution",
                operator=operator,
                input_data=input_data,
                output_data=output_data,
                status=status,
                error_message=error_message
            )
        except Exception as e:
            logger.warning(f"记录审计日志失败: {str(e)}")
    
    @staticmethod
    def _seconds_to_milliseconds(value: Any) -> Optional[int]:
        """将秒数转换为毫秒整数"""
        if value is None:
            return None
        try:
            seconds = float(value)
            if seconds < 0:
                return 0
            return int(seconds * 1000)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_error_message_from_report_content(content: Any) -> Optional[str]:
        """从报告内容中提取简要错误信息"""
        if not isinstance(content, dict):
            return None

        error_logs = content.get("error_logs")
        if isinstance(error_logs, list) and error_logs:
            return str(error_logs[0])

        return None

    def _build_execution_detail_from_report(
        self,
        execution_id: str,
        report_payload: Dict[str, Any],
        include_node_traces: bool = True
    ) -> Dict[str, Any]:
        """基于报告内容构造执行详情（execution_runs 缺失时兜底）"""
        report_path = report_payload.get("report_path")
        report_content = report_payload.get("report_content")

        workflow_id = "unknown"
        status = "completed"
        started_at = None
        completed_at = None
        duration_ms = None
        error_message = None
        node_traces: List[Dict[str, Any]] = []

        if isinstance(report_content, dict):
            workflow_id = str(report_content.get("workflow_id") or "unknown")
            status = self._normalize_trace_status(str(report_content.get("status") or "completed"))
            started_at = report_content.get("start_time")
            completed_at = report_content.get("end_time")
            duration_ms = self._seconds_to_milliseconds(report_content.get("duration"))
            error_message = self._extract_error_message_from_report_content(report_content)

            if include_node_traces:
                node_records = report_content.get("node_records")
                if isinstance(node_records, list):
                    for node_record in node_records:
                        if not isinstance(node_record, dict):
                            continue
                        node_started_at = node_record.get("start_time")
                        node_completed_at = node_record.get("end_time")
                        node_traces.append({
                            "execution_id": execution_id,
                            "node_id": str(node_record.get("node_id") or ""),
                            "node_type": node_record.get("node_type"),
                            "status": self._normalize_trace_status(str(node_record.get("status") or "pending")),
                            "input_payload": node_record.get("input_data"),
                            "output_payload": node_record.get("output_data"),
                            "error_message": node_record.get("error_message"),
                            "started_at": node_started_at,
                            "completed_at": node_completed_at,
                            "duration_ms": self._seconds_to_milliseconds(node_record.get("duration")),
                            "created_at": node_started_at
                        })

        return {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": duration_ms,
            "trigger_source": None,
            "error_message": error_message,
            "final_report_path": report_path,
            "created_at": started_at,
            "updated_at": completed_at or started_at,
            "node_traces": node_traces if include_node_traces else []
        }

    def _list_execution_runs_from_logs(self, workflow_id: str) -> List[Dict[str, Any]]:
        """从 logs 目录扫描执行报告并构造执行历史（execution_runs 缺失时兜底）"""
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return []

        items: List[Dict[str, Any]] = []
        for report_path in logs_dir.glob("execution_report_*.json"):
            try:
                import json
                with open(report_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
            except Exception:
                continue

            if not isinstance(content, dict):
                continue

            if str(content.get("workflow_id") or "") != workflow_id:
                continue

            execution_id = str(content.get("execution_id") or report_path.stem.replace("execution_report_", ""))
            started_at = content.get("start_time")
            completed_at = content.get("end_time")
            items.append({
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": self._normalize_trace_status(str(content.get("status") or "completed")),
                "started_at": started_at,
                "completed_at": completed_at,
                "duration_ms": self._seconds_to_milliseconds(content.get("duration")),
                "trigger_source": None,
                "error_message": self._extract_error_message_from_report_content(content),
                "final_report_path": str(report_path),
                "created_at": started_at,
                "updated_at": completed_at or started_at,
                "node_traces": []
            })

        items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return items

    def get_execution_by_id(
        self,
        execution_id: str,
        include_node_traces: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        按 execution_id 查询执行详情
        
        Args:
            execution_id: 执行 ID
            include_node_traces: 是否包含节点追踪
            
        Returns:
            执行详情字典，不存在返回 None
        """
        if self.execution_repo:
            try:
                run = self.execution_repo.get_execution_run_by_execution_id(execution_id)
            except Exception as db_error:
                run = None
                logger.warning(
                    "查询 execution_runs 失败，降级为日志报告兜底",
                    execution_id=execution_id,
                    error=str(db_error)
                )

            if run is not None:
                node_traces: List[Dict[str, Any]] = []
                if include_node_traces:
                    try:
                        traces = self.execution_repo.list_node_traces_by_execution_id(execution_id)
                        node_traces = [self._serialize_node_trace(trace) for trace in traces]
                    except Exception as trace_error:
                        logger.warning(
                            "查询 execution_node_traces 失败，返回不含节点追踪详情",
                            execution_id=execution_id,
                            error=str(trace_error)
                        )
                return self._serialize_execution_run(run, node_traces=node_traces)

        report_payload = self.get_execution_report(execution_id)
        if report_payload is None:
            return None

        return self._build_execution_detail_from_report(
            execution_id=execution_id,
            report_payload=report_payload,
            include_node_traces=include_node_traces
        )

    def list_workflow_executions(
        self,
        workflow_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        分页查询工作流执行历史
        """
        if self.execution_repo:
            runs = self.execution_repo.list_execution_runs_by_workflow_id(
                workflow_id=workflow_id,
                limit=limit,
                offset=offset
            )
            total = self.execution_repo.count({"workflow_id": workflow_id})
            if total > 0:
                return {
                    "workflow_id": workflow_id,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "items": [self._serialize_execution_run(run, node_traces=[]) for run in runs]
                }

        fallback_items = self._list_execution_runs_from_logs(workflow_id=workflow_id)

        return {
            "workflow_id": workflow_id,
            "total": len(fallback_items),
            "limit": limit,
            "offset": offset,
            "items": fallback_items[offset: offset + limit]
        }

    def get_execution_report(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取执行报告（优先 execution_run.final_report_path，其次默认 logs 路径）
        """
        candidate_paths: List[Path] = []
        source = "logs_default_path"

        if self.execution_repo:
            run = self.execution_repo.get_execution_run_by_execution_id(execution_id)
            if run and run.final_report_path:
                candidate_paths.append(Path(run.final_report_path))
                source = "execution_run_report_path"

        candidate_paths.append(Path("logs") / f"execution_report_{execution_id}.json")

        seen = set()
        for report_path in candidate_paths:
            normalized = str(report_path)
            if normalized in seen:
                continue
            seen.add(normalized)

            if not report_path.exists():
                continue

            try:
                import json
                with open(report_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
            except Exception:
                try:
                    with open(report_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as read_error:
                    logger.warning(
                        "读取执行报告失败",
                        execution_id=execution_id,
                        report_path=normalized,
                        error=str(read_error)
                    )
                    continue

            return {
                "execution_id": execution_id,
                "report_path": normalized,
                "report_content": content,
                "source": source if report_path in candidate_paths[:1] else "logs_default_path"
            }

        return None
    
    def validate_workflow_for_execution(
        self,
        workflow_def: WorkflowDefinition
    ) -> Dict[str, Any]:
        """
        验证工作流是否可以执行
        
        Args:
            workflow_def: 工作流定义
            
        Returns:
            验证结果字典
        """
        errors = []
        warnings = []
        
        # 检查节点
        if not workflow_def.nodes:
            errors.append("工作流没有定义任何节点")
        else:
            # 检查 Start 节点
            start_nodes = [n for n in workflow_def.nodes if n.type == "Start"]
            if not start_nodes:
                errors.append("工作流缺少 Start 节点")
            elif len(start_nodes) > 1:
                warnings.append(f"工作流有 {len(start_nodes)} 个 Start 节点，建议只有一个")
            
            # 检查 End 节点
            end_nodes = [n for n in workflow_def.nodes if n.type == "End"]
            if not end_nodes:
                errors.append("工作流缺少 End 节点")
            elif len(end_nodes) > 1:
                warnings.append(f"工作流有 {len(end_nodes)} 个 End 节点，建议只有一个")
            
            # 检查节点配置
            for node in workflow_def.nodes:
                if node.type in ["LLM", "Code"]:
                    if not node.config:
                        errors.append(f"节点 {node.id} 缺少配置")
                    elif not node.config.params:
                        warnings.append(f"节点 {node.id} 没有定义参数")
        
        # 检查边
        if not workflow_def.edges:
            errors.append("工作流没有定义任何边")
        else:
            # 检查边的引用
            node_ids = {n.id for n in workflow_def.nodes}
            for edge in workflow_def.edges:
                if edge.source not in node_ids:
                    errors.append(f"边的源节点 {edge.source} 不存在")
                if edge.target not in node_ids:
                    errors.append(f"边的目标节点 {edge.target} 不存在")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_workflow_statistics(
        self,
        workflow_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取工作流执行统计信息
        
        Args:
            workflow_id: 工作流 ID
            
        Returns:
            统计信息字典
        """
        if not self.audit_log_repo:
            return None
        
        try:
            # 获取执行日志
            logs = self.audit_log_repo.get_by_workflow(workflow_id)
            
            total_executions = len(logs)
            success_count = sum(1 for log in logs if log.status == "success")
            failed_count = sum(1 for log in logs if log.status == "failed")
            
            # 计算平均执行时间
            execution_times = [
                log.execution_time_ms for log in logs
                if log.execution_time_ms is not None
            ]
            avg_execution_time = (
                sum(execution_times) / len(execution_times)
                if execution_times else None
            )
            
            return {
                "workflow_id": workflow_id,
                "total_executions": total_executions,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": success_count / total_executions if total_executions > 0 else 0,
                "avg_execution_time_ms": avg_execution_time
            }
            
        except Exception as e:
            logger.error(f"获取工作流统计信息失败: {str(e)}")
            return None