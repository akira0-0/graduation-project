"""
条件分支节点
根据条件表达式决定工作流的执行路径
"""
from typing import Any, Dict, Optional
from .base import BaseNode
from ..core.schema import WorkflowState
from ..utils.logger import get_logger

logger = get_logger("condition_node")


class ConditionNode(BaseNode):
    """
    条件分支节点
    根据配置的条件表达式返回分支标识，用于控制工作流的执行路径
    """
    
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        执行条件判断
        
        Args:
            state: 工作流当前状态
            
        Returns:
            包含条件判断结果的字典
        """
        # 获取条件配置
        condition_expr = self.config.params.get("condition", "")
        condition_type = self.config.params.get("condition_type", "simple")  # simple, python
        inputs = self.config.params.get("inputs", {})
        
        # 合并输入变量到变量上下文
        # inputs 字段包含用户在节点配置中定义的输入参数
        if inputs and isinstance(inputs, dict):
            # 将inputs中的变量添加到data中，便于在表达式中引用
            data.update(inputs)
        
        logger.debug(
            f"执行条件判断",
            node_id=self.node_id,
            condition_expr=condition_expr,
            condition_type=condition_type,
            inputs=inputs
        )
        
        try:
            # 准备变量上下文
            variables = {}
            # 注入输入数据
            variables.update(data)
            # 注入全局变量
            variables.update(state.context)
            # 注入上游节点输出（便于在Python表达式中引用）
            variables.update(state.node_outputs)
            
            # 执行条件判断
            if condition_type == "simple":
                # 简单条件：比较值
                result = self._evaluate_simple_condition(condition_expr, variables)
            elif condition_type == "python":
                # Python 表达式：使用 eval 执行
                result = self._evaluate_python_condition(condition_expr, variables)
            else:
                raise ValueError(f"不支持的条件类型: {condition_type}")
            
            logger.info(f"条件判断结果: {result}", node_id=self.node_id)
            
            return {
                "result": result,
                "condition_type": condition_type
            }
            
        except Exception as e:
            logger.error(f"条件判断失败: {str(e)}", node_id=self.node_id)
            return {
                "error": str(e),
                "result": None
            }
    
    def _evaluate_simple_condition(self, condition_expr: str, variables: Dict[str, Any]) -> Optional[str]:
        """
        评估简单条件表达式
        
        支持两种格式：
        1. 完整表达式: "node_id.field == value" 或 "node_id.field > 10"
        2. 参数化配置: 使用 left_operand, operator, right_operand 构建
        
        Args:
            condition_expr: 条件表达式（如果使用参数化配置，此字段会被忽略）
            variables: 变量上下文
            
        Returns:
            条件结果标识
        """
        try:
            # 检查是否使用参数化配置（左操作数、运算符、右操作数）
            left_operand = self.config.params.get("left_operand")
            operator = self.config.params.get("operator")
            right_operand = self.config.params.get("right_operand")
            
            import re
            
            # 如果使用参数化配置，构建表达式
            if left_operand and operator and right_operand is not None:
                # 替换变量引用
                def replace_var(match):
                    var_path = match.group(1)
                    parts = var_path.split('.')
                    value = variables.get(parts[0])
                    for part in parts[1:]:
                        if isinstance(value, dict):
                            value = value.get(part)
                        elif hasattr(value, part):
                            value = getattr(value, part)
                        else:
                            return "None"
                    return str(value) if value is not None else "None"
                
                # 处理左操作数
                left_expr = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_.]*)', replace_var, left_operand)
                # 处理右操作数
                right_expr = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_.]*)', replace_var, right_operand)
                
                # 构建完整表达式
                expr = f"{left_expr} {operator} {right_expr}"
            else:
                # 使用完整的表达式字符串
                def replace_var(match):
                    var_path = match.group(1)
                    parts = var_path.split('.')
                    value = variables.get(parts[0])
                    for part in parts[1:]:
                        if isinstance(value, dict):
                            value = value.get(part)
                        elif hasattr(value, part):
                            value = getattr(value, part)
                        else:
                            return "None"
                    return str(value) if value is not None else "None"
                
                # 匹配 $variable 或 $variable.field 格式
                expr = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_.]*)', replace_var, condition_expr)
            
            # 评估表达式
            result = eval(expr)
            logger.debug(f"简单条件评估: {expr} -> {result}")
            
            # 返回条件标识
            return "true" if result else "false"
            
        except Exception as e:
            logger.error(f"简单条件评估失败: {str(e)}", condition_expr=condition_expr)
            raise
    
    def _evaluate_python_condition(self, condition_expr: str, variables: Dict[str, Any]) -> str:
        """
        评估 Python 表达式
        
        支持复杂的条件逻辑，可以返回任意字符串值作为分支标识
        
        Args:
            condition_expr: Python 表达式
            variables: 变量上下文
            
        Returns:
            分支标识（字符串）
        """
        try:
            # 使用 eval 执行表达式
            # 注意：在生产环境中应使用更安全的表达式解析器
            result = eval(condition_expr, {"__builtins__": {}}, variables)
            
            # 将结果转换为字符串作为分支标识
            branch_id = str(result)
            logger.debug(f"Python 表达式评估: {condition_expr} -> {branch_id}")
            
            return branch_id
            
        except Exception as e:
            logger.error(f"Python 表达式评估失败: {str(e)}", condition_expr=condition_expr)
            raise