"""
工作流引擎主入口
支持命令行运行工作流和生成工作流（使用 LangGraph 引擎）
"""
import json
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# 添加 workflow_engine 到 Python 路径以支持从项目根目录运行
import sys
from pathlib import Path
workflow_engine_dir = Path(__file__).parent
if str(workflow_engine_dir) not in sys.path:
    sys.path.insert(0, str(workflow_engine_dir))

env_path = workflow_engine_dir / ".env"
load_dotenv(env_path, override=True)

from src.core.schema import WorkflowDefinition
from src.core.builder import GraphBuilder
from src.planner.llm_planner import LLMPlanner
from src.monitoring import ExecutionMonitor

# 加载环境变量（用于 OpenAI Key）
load_dotenv()


def load_workflow(file_path: str) -> WorkflowDefinition:
    """
    从 JSON 文件加载工作流定义
    
    Args:
        file_path: 工作流文件路径
        
    Returns:
        工作流定义对象
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return WorkflowDefinition(**data)


def run_workflow(workflow_def: WorkflowDefinition):
    """
    运行工作流
    
    Args:
        workflow_def: 工作流定义
    """
    print(f"\n{'='*60}")
    print(f"工作流名称: {workflow_def.name}")
    print(f"描述: {workflow_def.description}")
    print(f"执行引擎: LangGraph")
    print(f"{'='*60}\n")
    
    # 创建执行监控器
    monitor = ExecutionMonitor(
        workflow_id=workflow_def.name.replace(" ", "_"),
        workflow_name=workflow_def.name
    )
    
    try:
        # 构建图
        print("正在构建工作流图...")
        builder = GraphBuilder(workflow_def, monitor=monitor)
        app = builder.build()
        
        # 运行图
        print("正在执行工作流...\n")
        # 初始化状态
        initial_state = {
            "context": workflow_def.variables,
            "node_outputs": {},
            "messages": [],
            "loop_counters": {},
            "loop_outputs": {},
            "branch_decisions": {},
            "current_node": ""
        }
        
        # 执行
        final_state = app.invoke(initial_state)
        
        # 输出结果
        print("\n" + "="*60)
        print("工作流执行结果")
        print("="*60)
        node_outputs = final_state.get("node_outputs", {})
        for node_id, output in node_outputs.items():
            print(f"\n[{node_id}]")
            if isinstance(output, dict) and "error" in output:
                print(f"  错误: {output['error']}")
            else:
                print(f"  输出: {output}")
        
        # 输出监控摘要
        print("\n" + "="*60)
        print("执行摘要")
        print("="*60)
        summary = monitor.get_summary()
        for key, value in summary.items():
            if key != "statistics":
                print(f"{key}: {value}")
        
        print("\n统计信息:")
        stats = summary.get("statistics", {})
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 保存执行报告
        report_path = f"logs/execution_report_{monitor.execution_id}.json"
        monitor.complete_workflow(success=True)
        monitor.save_report(report_path)
        print(f"\n执行报告已保存到: {report_path}")

    except Exception as e:
        print(f"\n执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 记录失败
        monitor.complete_workflow(success=False)
        
        # 简单的 debug 提示
        if "OPENAI_API_KEY" not in os.environ:
             print("提示: 请检查 .env 文件中是否设置了 OPENAI_API_KEY")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="工作流引擎命令行工具")
    parser.add_argument("--file", type=str, help="工作流 JSON 文件路径")
    parser.add_argument("--plan", type=str, help="使用自然语言描述生成工作流")
    parser.add_argument("--model", type=str, default="deepseek-chat",
                      help="用于规划的 LLM 模型")
    
    args = parser.parse_args()
    
    if args.plan:
        if "OPENAI_API_KEY" not in os.environ:
            print("错误: 规划功能需要设置 OPENAI_API_KEY。请在 .env 文件中配置。")
            return
            
        planner = LLMPlanner(model_name=args.model)
        print(f"正在根据意图生成工作流: {args.plan}")
        workflow_def = planner.plan(args.plan)
        
        # 保存生成的配置
        output_file = "generated_workflow.json"
        with open(output_file, "w", encoding='utf-8') as f:
            f.write(workflow_def.model_dump_json(indent=2))
        print(f"\n[信息] 生成的工作流已保存到 {output_file}\n")
            
        run_workflow(workflow_def)
        
    elif args.file:
        try:
            workflow_def = load_workflow(args.file)
            run_workflow(workflow_def)
        except FileNotFoundError:
            print(f"错误: 未找到工作流文件: {args.file}")
    else:
        # 默认运行示例文件
        demo_path = Path("workflow_engine/data/simple_workflow.json")
        if demo_path.exists():
            print(f"未提供参数，运行示例: {demo_path}")
            workflow_def = load_workflow(str(demo_path))
            run_workflow(workflow_def)
        else:
             # 尝试本地路径
             demo_path = Path("data/simple_workflow.json")
             if demo_path.exists():
                print(f"未提供参数，运行示例: {demo_path}")
                workflow_def = load_workflow(str(demo_path))
                run_workflow(workflow_def)
             else:
                parser.print_help()


if __name__ == "__main__":
    main()
