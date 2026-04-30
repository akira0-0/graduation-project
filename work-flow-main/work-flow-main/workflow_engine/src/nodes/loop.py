"""
循环节点
支持多次迭代执行，用于批量处理和重复任务
"""
from typing import Any, Dict, List, Optional
from .base import BaseNode
from ..core.schema import WorkflowState
from ..utils.logger import get_logger
from ..config import get_settings

logger = get_logger("loop_node")


class LoopNode(BaseNode):
    """
    循环节点
    支持固定次数循环和条件循环
    """
    
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        执行循环逻辑
        
        Args:
            state: 工作流当前状态
            
        Returns:
            包含循环结果的字典
        """
        # 获取配置的最大迭代次数
        settings = get_settings()
        global_max_iterations = settings.loop_max_iterations
        default_iterations = settings.loop_default_iterations
        
        # 获取循环配置
        loop_type = self.config.params.get("loop_type", "count")  # count, condition, foreach
        # 限制最大迭代次数不超过全局配置
        max_iterations = min(
            self.config.params.get("max_iterations", default_iterations),
            global_max_iterations
        )
        loop_condition = self.config.params.get("condition", "")  # 循环条件表达式
        input_data = self.config.params.get("input", None)  # foreach 的输入数据
        inputs = self.config.params.get("inputs", {})  # 输入变量
        
        # 获取或初始化循环计数器
        current_count = state.loop_counters.get(self.node_id, 0)
        
        # 获取之前的输出（用于积累结果）
        previous_outputs = state.loop_outputs.get(self.node_id, [])
        
        # 合并输入变量到data字典中
        data = {}
        if inputs and isinstance(inputs, dict):
            data.update(inputs)
        
        logger.debug(
            f"执行循环逻辑",
            node_id=self.node_id,
            loop_type=loop_type,
            current_count=current_count,
            max_iterations=max_iterations,
            inputs=inputs
        )
        
        try:
            # 根据循环类型执行不同的逻辑
            if loop_type == "count":
                result = self._execute_count_loop(state, current_count, max_iterations, data)
            elif loop_type == "condition":
                result = self._execute_condition_loop(state, current_count, loop_condition, max_iterations, data)
            elif loop_type == "foreach":
                result = self._execute_foreach_loop(state, input_data, previous_outputs, data)
            else:
                raise ValueError(f"不支持的循环类型: {loop_type}")
            
            # 更新循环计数器
            new_count = current_count + result.get("iterations", 0)
            
            # 累积循环输出
            accumulated_outputs = previous_outputs + result.get("outputs", [])
            
            logger.info(
                f"循环执行完成",
                node_id=self.node_id,
                iterations=result.get("iterations", 0),
                total_count=new_count,
                loop_status=result.get("loop_status")
            )
            
            # 返回状态更新（LangGraph 需要返回更新字典）
            return {
                **result,
                "current_count": new_count,
                "total_outputs": accumulated_outputs,
                # 关键：返回 loop_counters 和 loop_outputs 更新
                "loop_counters": {self.node_id: new_count},
                "loop_outputs": {self.node_id: accumulated_outputs}
            }
            
        except Exception as e:
            logger.error(f"循环执行失败: {str(e)}", node_id=self.node_id)
            return {
                "error": str(e),
                "iterations": 0,
                "outputs": []
            }
    
    def _execute_count_loop(self, state: WorkflowState, current_count: int, max_count: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行固定次数循环
        
        Args:
            state: 工作流状态
            current_count: 当前迭代次数
            max_count: 最大迭代次数
            data: 输入数据字典
            
        Returns:
            循环结果
        """
        outputs = []
        iterations = 0
        
        # 计算还需要执行的次数
        remaining = max_count - current_count
        
        if remaining <= 0:
            logger.info(f"循环已达到最大次数", node_id=self.node_id, max_count=max_count)
            return {
                "loop_status": "completed",
                "iterations": 0,
                "outputs": [],
                "message": "循环已完成"
            }
        
        # 执行一次迭代
        # 注意：实际迭代次数由 LangGraph 控制，这里只返回状态
        outputs.append({
            "iteration": current_count + 1,
            "data": data,
            "value": f"迭代 {current_count + 1} 的结果"
        })
        
        return {
            "loop_status": "running" if current_count + 1 < max_count else "completed",
            "iterations": 1,
            "outputs": outputs
        }
    
    def _execute_condition_loop(
        self,
        state: WorkflowState,
        current_count: int,
        condition: str,
        max_count: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行条件循环
        
        Args:
            state: 工作流状态
            current_count: 当前迭代次数
            condition: 循环条件表达式
            max_count: 最大迭代次数（防止死循环）
            data: 输入数据字典
            
        Returns:
            循环结果
        """
        # 准备变量上下文
        variables = {
            "data": data,
            "context": state.context,
            "node_outputs": state.node_outputs,
            "iteration": current_count,
            "count": current_count
        }
        
        try:
            # 评估循环条件
            should_continue = eval(condition, {"__builtins__": {}}, variables)
            
            # 检查是否达到最大迭代次数
            if current_count >= max_count:
                logger.warning(
                    f"循环达到最大迭代次数，强制退出",
                    node_id=self.node_id,
                    max_count=max_count
                )
                return {
                    "loop_status": "completed",
                    "iterations": 0,
                    "outputs": [],
                    "message": "达到最大迭代次数"
                }
            
            if not should_continue:
                logger.info(f"循环条件不满足，退出循环", node_id=self.node_id)
                return {
                    "loop_status": "completed",
                    "iterations": 0,
                    "outputs": [],
                    "message": "循环条件不满足"
                }
            
            # 执行一次迭代
            output = {
                "iteration": current_count + 1,
                "data": data,
                "value": f"条件循环迭代 {current_count + 1} 的结果"
            }
            
            return {
                "loop_status": "running",
                "iterations": 1,
                "outputs": [output]
            }
            
        except Exception as e:
            logger.error(f"条件评估失败: {str(e)}", node_id=self.node_id, condition=condition)
            raise
    
    def _execute_foreach_loop(
        self,
        state: WorkflowState,
        input_data: Any,
        previous_outputs: List[Any],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行 foreach 循环
        
        Args:
            state: 工作流状态
            input_data: 要迭代的输入数据（列表或可迭代对象）
            previous_outputs: 之前的输出结果
            data: 输入数据字典
            
        Returns:
            循环结果
        """
        # 转换输入为列表
        if input_data is None:
            return {
                "loop_status": "completed",
                "iterations": 0,
                "outputs": [],
                "message": "无输入数据"
            }
        
        # 检查input_data是否是字符串（可能是引用上游节点的表达式）
        if isinstance(input_data, str):
            # 尝试从上游节点获取数据
            import re
            def replace_var(match):
                var_path = match.group(1)
                parts = var_path.split('.')
                value = data.get(parts[0]) if parts[0] in data else state.node_outputs.get(parts[0])
                for part in parts[1:]:
                    if isinstance(value, dict):
                        value = value.get(part)
                    elif hasattr(value, part):
                        value = getattr(value, part)
                return value if value is not None else None
            
            # 替换变量引用
            input_expr = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_.]*)', replace_var, input_data)
            
            try:
                # 尝试评估表达式获取实际数据
                input_data = eval(input_expr, {"__builtins__": {}}, {"data": data, **state.node_outputs})
            except:
                # 如果评估失败，保持原样
                pass
        
        if not isinstance(input_data, list):
            # 如果不是列表，尝试转换为列表
            try:
                input_list = list(input_data)
            except Exception as e:
                logger.error(f"无法转换输入数据为列表: {str(e)}", node_id=self.node_id)
                raise ValueError("输入数据必须是可迭代的")
        else:
            input_list = input_data
        
        # 计算还需要处理的项目
        processed_count = len(previous_outputs)
        remaining_items = input_list[processed_count:]
        
        if not remaining_items:
            logger.info(f"Foreach 循环已完成", node_id=self.node_id, total=len(input_list))
            return {
                "loop_status": "completed",
                "iterations": 0,
                "outputs": [],
                "message": "所有项目已处理"
            }
        
        # 处理下一个项目
        next_item = remaining_items[0]
        output = {
            "index": processed_count,
            "item": next_item,
            "data": data,
            "value": f"处理项目 {processed_count} 的结果"
        }
        
        return {
            "loop_status": "running" if processed_count + 1 < len(input_list) else "completed",
            "iterations": 1,
            "outputs": [output],
            "total_items": len(input_list),
            "processed_items": processed_count + 1
        }