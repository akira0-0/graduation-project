"""
代码执行节点实现
允许用户编写 Python 代码来处理数据
"""
from typing import Any, Dict
from .base import BaseNode
from ..core.schema import WorkflowState
from ..tools import mock_tools
from ..utils.logger import get_logger

logger = get_logger("code_node")


class CodeNode(BaseNode):
    """
    Python 代码执行节点
    模拟 Coze 的 Code 节点，允许用户编写 Python 代码来处理数据
    """
    
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        执行用户代码
        
        Args:
            state: 工作流当前状态
            
        Returns:
            代码执行结果
            
        安全警告：
        使用 exec() 执行用户代码存在安全风险，生产环境应使用沙箱环境！
        """
        # 获取用户编写的代码
        code_str = self.config.params.get("code", "")
        if not code_str:
            logger.error(f"未提供代码", node_id=self.node_id)
            return {"error": "未提供代码"}
        
        logger.debug(f"执行代码节点", node_id=self.node_id, code_length=len(code_str))
            
        # 获取输入变量定义
        input_mapping = self.config.params.get("inputs", {})
        
        # 准备执行环境（使用 globals 以便函数内部可见）
        exec_globals = {}
        
        # 注入 Mock 工具
        # 允许用户代码中直接调用这些函数，如 mock_collect_data()
        for name in dir(mock_tools):
            if name.startswith("mock_"):
                exec_globals[name] = getattr(mock_tools, name)
        
        # 注入输入变量
        for input_name, input_value_ref in input_mapping.items():
            # 使用基类的引用解析方法
            val = self.get_input_value(state, input_name)
            exec_globals[input_name] = val
            
            logger.debug(
                f"注入变量",
                node_id=self.node_id,
                variable_name=input_name
            )
        
        # 包装用户代码到函数中执行
        # 强制用户定义一个 main 函数
        wrapped_code = f"{code_str}\n"
        
        try:
            # 使用 exec 执行代码定义
            # 安全警告：这是极其危险的操作，仅用于 Demo，生产环境必须使用沙箱
            # 将变量直接注入到 globals 中，这样 main 函数可以直接访问
            exec(wrapped_code, exec_globals)
            
            # 调用 main 函数
            if 'main' in exec_globals and callable(exec_globals['main']):
                result = exec_globals['main']()
                logger.info(f"代码执行成功", node_id=self.node_id)
                return result if isinstance(result, dict) else {"result": result}
            else:
                logger.error(f"未找到 main 函数", node_id=self.node_id)
                return {"error": "未找到 main 函数"}
                
        except Exception as e:
            logger.error(f"代码执行失败: {str(e)}", node_id=self.node_id)
            return {"error": f"代码执行失败: {str(e)}"}