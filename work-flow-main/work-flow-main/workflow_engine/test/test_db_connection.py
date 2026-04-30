#!/usr/bin/env python3
"""
数据库连接测试脚本
用于验证 PostgreSQL 数据库连接和表结构
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from src.database.connection import get_session, close_db
from src.database.models import Workflow, Conversation, Memory, AuditLog
from src.utils.logger import get_logger
from datetime import datetime
import uuid

logger = get_logger("test_db_connection")


def test_connection():
    """测试数据库连接"""
    print("\n" + "=" * 60)
    print("测试 1: 数据库连接")
    print("=" * 60)
    
    try:
        session = get_session()
        result = session.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"✅ 连接成功")
        print(f"数据库版本: {version.split(',')[0]}")
        session.close()
        return True
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        return False


def test_table_structure():
    """测试表结构"""
    print("\n" + "=" * 60)
    print("测试 2: 表结构验证")
    print("=" * 60)
    
    try:
        session = get_session()
        
        # 检查每个表
        tables = {
            'workflows': Workflow,
            'conversations': Conversation,
            'memories': Memory,
            'audit_logs': AuditLog
        }
        
        for table_name, model in tables.items():
            try:
                # 查询表记录数
                count = session.query(model).count()
                print(f"✅ 表 {table_name}: {count} 条记录")
            except Exception as e:
                print(f"❌ 表 {table_name}: {str(e)}")
                return False
        
        session.close()
        return True
    except Exception as e:
        print(f"❌ 表结构验证失败: {str(e)}")
        return False


def test_crud_operations():
    """测试 CRUD 操作"""
    print("\n" + "=" * 60)
    print("测试 3: CRUD 操作")
    print("=" * 60)
    
    session = get_session()
    test_workflow_id = str(uuid.uuid4())
    
    try:
        # Create - 创建测试工作流
        print("\n创建测试工作流...")
        workflow = Workflow(
            id=test_workflow_id,
            name="测试工作流",
            description="这是一个测试工作流",
            definition={"test": "data"},
            is_active=True
        )
        session.add(workflow)
        session.commit()
        print(f"✅ 创建成功: {test_workflow_id}")
        
        # Read - 读取工作流
        print("\n读取测试工作流...")
        saved_workflow = session.query(Workflow).filter_by(id=test_workflow_id).first()
        if saved_workflow:
            print(f"✅ 读取成功: {saved_workflow.name}")
        else:
            print("❌ 读取失败: 工作流不存在")
            return False
        
        # Update - 更新工作流
        print("\n更新测试工作流...")
        saved_workflow.name = "更新后的测试工作流"
        saved_workflow.updated_at = datetime.utcnow()
        session.commit()
        updated_workflow = session.query(Workflow).filter_by(id=test_workflow_id).first()
        print(f"✅ 更新成功: {updated_workflow.name}")
        
        # Create related records - 创建关联记录
        print("\n创建关联记录...")
        
        # 创建对话记录
        conversation = Conversation(
            id=str(uuid.uuid4()),
            workflow_id=test_workflow_id,
            user_message="测试消息",
            assistant_response="测试响应",
            context={"test": "context"}
        )
        session.add(conversation)
        
        # 创建记忆记录
        memory = Memory(
            workflow_id=test_workflow_id,
            agent_type="test_agent",
            memory_type="test_memory",
            key="test_key",
            value={"test": "value"}
        )
        session.add(memory)
        
        # 创建审计日志
        audit_log = AuditLog(
            workflow_id=test_workflow_id,
            operation_type="test_operation",
            operator="test_operator",
            status="success"
        )
        session.add(audit_log)
        
        session.commit()
        print("✅ 关联记录创建成功")
        
        # Verify relationships - 验证关联关系
        print("\n验证关联关系...")
        workflow_with_relations = session.query(Workflow).filter_by(id=test_workflow_id).first()
        print(f"  - 对话记录: {len(workflow_with_relations.conversations)} 条")
        print(f"  - 记忆记录: {len(workflow_with_relations.memories)} 条")
        print(f"  - 审计日志: {len(workflow_with_relations.audit_logs)} 条")
        
        # Delete - 删除测试数据
        print("\n清理测试数据...")
        session.delete(workflow_with_relations)
        session.commit()
        print("✅ 删除成功（级联删除关联记录）")
        
        # Verify deletion - 验证删除
        deleted = session.query(Workflow).filter_by(id=test_workflow_id).first()
        if not deleted:
            print("✅ 验证成功: 工作流已被删除")
        
        return True
    except Exception as e:
        print(f"❌ CRUD 操作失败: {str(e)}")
        session.rollback()
        return False
    finally:
        session.close()


def test_indexes():
    """测试索引"""
    print("\n" + "=" * 60)
    print("测试 4: 索引验证")
    print("=" * 60)
    
    try:
        session = get_session()
        
        # 查询索引
        query = text("""
        SELECT
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
        """)
        
        result = session.execute(query)
        indexes = result.fetchall()
        
        print(f"\n找到 {len(indexes)} 个索引:")
        current_table = None
        for row in indexes:
            if row[0] != current_table:
                current_table = row[0]
                print(f"\n表: {current_table}")
            print(f"  - {row[1]}")
        
        session.close()
        return True
    except Exception as e:
        print(f"❌ 索引验证失败: {str(e)}")
        return False


def test_performance():
    """测试性能"""
    print("\n" + "=" * 60)
    print("测试 5: 性能测试")
    print("=" * 60)
    
    try:
        session = get_session()
        
        # 测试查询性能
        import time
        
        print("\n测试查询性能...")
        start = time.time()
        for _ in range(100):
            session.query(Workflow).limit(10).all()
        elapsed = time.time() - start
        
        print(f"✅ 100 次查询耗时: {elapsed:.3f} 秒")
        print(f"   平均每次查询: {elapsed/100*1000:.2f} 毫秒")
        
        session.close()
        return True
    except Exception as e:
        print(f"❌ 性能测试失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("PostgreSQL 数据库连接测试")
    print("=" * 60)
    
    # 加载环境变量
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"\n✅ 已加载环境配置文件: {env_path}")
    else:
        print(f"\n⚠️  未找到环境配置文件: {env_path}")
    
    # 运行测试
    tests = [
        ("数据库连接", test_connection),
        ("表结构验证", test_table_structure),
        ("CRUD 操作", test_crud_operations),
        ("索引验证", test_indexes),
        ("性能测试", test_performance)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{test_name}' 发生异常: {str(e)}")
            results.append((test_name, False))
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！数据库配置正确。")
    else:
        print("\n⚠️  部分测试失败，请检查数据库配置。")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        sys.exit(1)
    finally:
        close_db()