#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试脚本：验证条件分支和循环功能
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from workflow_engine.main import run_workflow, load_workflow


def test_advanced_workflow():
    """测试高级工作流（包含条件分支和循环）"""
    print("="*70)
    print("测试：高级工作流（条件分支 + 循环）")
    print("="*70)
    
    # 加载高级工作流
    workflow_file = project_root / "test_data" / "advanced_workflow.json"
    
    if not workflow_file.exists():
        print(f"错误：未找到工作流文件 {workflow_file}")
        return False
    
    try:
        workflow_def = load_workflow(str(workflow_file))
        
        # 执行工作流
        run_workflow(workflow_def, engine="langgraph")
        
        print("\n" + "="*70)
        print("测试完成！")
        print("="*70)
        
        # 检查日志目录
        logs_dir = project_root / "logs"
        if logs_dir.exists():
            print(f"\n日志文件位置：{logs_dir}")
            log_files = list(logs_dir.glob("*.json"))
            if log_files:
                print(f"执行报告文件：{log_files[-1]}")
        
        return True
        
    except Exception as e:
        print(f"\n测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_workflow():
    """测试简单工作流（基本功能）"""
    print("\n" + "="*70)
    print("测试：简单工作流（基本功能）")
    print("="*70)
    
    # 加载简单工作流
    workflow_file = project_root / "简单的总结工作流.json"
    
    if not workflow_file.exists():
        print(f"警告：未找到简单工作流文件 {workflow_file}")
        return None
    
    try:
        workflow_def = load_workflow(str(workflow_file))
        run_workflow(workflow_def, engine="langgraph")
        return True
    except Exception as e:
        print(f"\n测试失败：{str(e)}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试工作流引擎新功能")
    parser.add_argument(
        "--test",
        type=str,
        choices=["advanced", "simple", "all"],
        default="all",
        help="测试类型：advanced（高级功能）、simple（基本功能）、all（全部）"
    )
    
    args = parser.parse_args()
    
    # 创建必要的目录
    (project_root / "logs").mkdir(exist_ok=True)
    
    results = {}
    
    if args.test in ["simple", "all"]:
        print("\n开始测试基本功能...\n")
        results["simple"] = test_simple_workflow()
    
    if args.test in ["advanced", "all"]:
        print("\n开始测试高级功能...\n")
        results["advanced"] = test_advanced_workflow()
    
    # 汇总结果
    print("\n" + "="*70)
    print("测试汇总")
    print("="*70)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name.upper():20s} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*70)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查日志")
    print("="*70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())