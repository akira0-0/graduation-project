# -*- coding: utf-8 -*-
"""
快速测试定时任务 - 直接执行一次完整流程
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入调度器的核心函数
from auto_hot_runner import job_master_runner, TEST_MODE

if __name__ == "__main__":
    print("🧪 开始单次测试...")
    print(f"📌 当前测试模式: {'开启' if TEST_MODE else '关闭'}")
    print("="*60)
    
    # 直接执行一次任务
    job_master_runner()
    
    print("="*60)
    print("✅ 测试完成！请检查输出日志和数据文件")
