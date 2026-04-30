"""
节点基类
定义所有工作流节点的通用接口和功能
"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from ..core.schema import NodeDefinition, WorkflowState
from ..utils.logger import get_logger

logger = get_logger("base_node")


class BaseNode(ABC):
    """所有节点的基类"""
    
    def __init__(self, node_def: NodeDefinition):
        """
        初始化节点
        
        Args:
            node_def: 节点定义
        """
        self.node_id = node_def.id
        self.node_type = node_def.type
        self.config = node_def.config
        
    @abstractmethod
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        执行节点逻辑（抽象方法，子类必须实现）
        
        Args:
            state: 当前工作流的全局状态
            
        Returns:
            节点的输出数据，将被合并到 state.node_outputs[self.node_id] 中
        """
        pass
        
    def get_input_value(self, state: WorkflowState, param_key: str) -> Any:
        """
        解析参数引用的辅助函数
        
        例如：参数值为 "$node_1" 或 "$node_1.output" 时，自动从 state 中查找节点输出
        
        Args:
            state: 工作流状态
            param_key: 参数键名
            
        Returns:
            解析后的参数值
        """
        # 检查配置参数
        raw_value = self.config.params.get(param_key)
        
        # 解析变量引用（以 $ 开头的字符串）
        if isinstance(raw_value, str) and raw_value.startswith("$"):
            var_path = raw_value[1:]  # 移除 $ 前缀
            # 格式可以是 node_id 或 node_id.field 或 context.var
            parts = var_path.split('.')
            
            # 首先尝试从节点输出中获取
            ref_node_id = parts[0]
            if ref_node_id in state.node_outputs:
                # 找到节点输出
                node_output = state.node_outputs.get(ref_node_id, {})
                
                # 如果有嵌套属性访问（如 node_id.result.field）
                if len(parts) >= 2:
                    for part in parts[1:]:
                        if isinstance(node_output, dict):
                            node_output = node_output.get(part)
                        elif hasattr(node_output, part):
                            node_output = getattr(node_output, part)
                        else:
                            logger.warning(
                                f"无法访问属性 {part}",
                                node_id=self.node_id,
                                ref_node_id=ref_node_id
                            )
                            return None
                
                return node_output
            
            # 如果不是节点输出，尝试从全局上下文获取
            elif ref_node_id in state.context:
                context_value = state.context.get(ref_node_id)
                
                # 支持嵌套属性访问
                if len(parts) >= 2:
                    for part in parts[1:]:
                        if isinstance(context_value, dict):
                            context_value = context_value.get(part)
                        elif hasattr(context_value, part):
                            context_value = getattr(context_value, part)
                        else:
                            logger.warning(
                                f"无法访问上下文属性 {part}",
                                node_id=self.node_id
                            )
                            return None
                
                return context_value
            
            else:
                logger.warning(
                    f"未找到引用目标: {var_path}",
                    node_id=self.node_id,
                    available_nodes=list(state.node_outputs.keys()),
                    available_context=list(state.context.keys())
                )
                return None
                
        return raw_value