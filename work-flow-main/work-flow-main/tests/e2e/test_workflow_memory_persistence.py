"""
端到端测试：工作流生成-执行-记忆持久化全链路验证
验证智能体记忆和工作流数据确实落在数据库中，没有走降级策略
"""
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime

# 添加项目路径 - 需要将 workflow_engine 目录添加到 sys.path
project_root = Path(__file__).parent.parent
workflow_engine_dir = project_root / "workflow_engine"
if str(workflow_engine_dir) not in sys.path:
    sys.path.insert(0, str(workflow_engine_dir))

import pytest
from dotenv import load_dotenv

# 加载环境变量
env_path = workflow_engine_dir / '.env'
if env_path.exists():
    load_dotenv(env_path)

from sqlalchemy import text
from src.database import (
    init_db,
    get_session,
    close_db,
    Workflow,
    Conversation,
    Memory,
    AuditLog,
    ExecutionRun,
    ExecutionNodeTrace,
    ConversationMemoryService,
    AgentMemoryService,
    AuditLogService
)
from src.database.repositories import (
    WorkflowRepository,
    MemoryRepository,
    ExecutionRepository
)
from src.services.planner_service import PlannerService
from src.services.execution_service import ExecutionService
from src.core.schema import WorkflowDefinition
from src.utils.logger import get_logger

logger = get_logger("test_workflow_memory_persistence")


class TestWorkflowMemoryPersistence:
    """工作流记忆持久化端到端测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前初始化数据库连接"""
        init_db()
        self.db = get_session()
        yield
        self.db.close()
    
    def _verify_database_connection(self):
        """验证数据库连接是否正常"""
        try:
            result = self.db.execute(text("SELECT 1")).scalar()
            return result == 1
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def test_database_connection_and_tables(self):
        """测试1: 验证数据库连接和表结构"""
        print("\n" + "="*60)
        print("测试 1: 数据库连接和表结构验证")
        print("="*60)
        
        # 验证连接
        assert self._verify_database_connection(), "数据库连接失败"
        print("✓ 数据库连接成功")
        
        # 验证表存在
        tables = ['workflows', 'conversations', 'memories', 'audit_logs', 'execution_runs', 'execution_node_traces']
        for table in tables:
            try:
                count = self.db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"✓ 表 {table} 存在，当前记录数: {count}")
            except Exception as e:
                print(f"✗ 表 {table} 不存在或查询失败: {e}")
                raise
    
    def test_workflow_create_and_persist(self):
        """测试2: 工作流创建并持久化到数据库"""
        print("\n" + "="*60)
        print("测试 2: 工作流创建并持久化")
        print("="*60)
        
        conv_service = ConversationMemoryService(self.db)
        
        # 创建工作流
        workflow = conv_service.create_workflow(
            name="测试工作流-记忆持久化",
            description="端到端测试工作流",
            definition={
                "name": "测试工作流",
                "nodes": [
                    {"id": "start", "type": "Start", "config": {"title": "开始"}},
                    {"id": "end", "type": "End", "config": {"title": "结束"}}
                ],
                "edges": [
                    {"source": "start", "target": "end"}
                ]
            }
        )
        
        assert workflow is not None, "工作流创建失败"
        assert workflow.id is not None, "工作流ID为空"
        print(f"✓ 工作流创建成功: {workflow.id}")
        
        # 验证数据库中存在
        saved = self.db.query(Workflow).filter_by(id=workflow.id).first()
        assert saved is not None, "工作流未持久化到数据库"
        assert saved.name == "测试工作流-记忆持久化"
        print(f"✓ 工作流已持久化到数据库: {saved.name}")
        
        # 清理
        self.db.delete(saved)
        self.db.commit()
    
    def test_agent_memory_persist(self):
        """测试3: 智能体记忆持久化验证"""
        print("\n" + "="*60)
        print("测试 3: 智能体记忆持久化验证")
        print("="*60)
        
        conv_service = ConversationMemoryService(self.db)
        workflow = conv_service.create_workflow(
            name="记忆测试工作流",
            description="测试智能体记忆持久化",
            definition={"test": "memory"}
        )
        print(f"✓ 创建测试工作流: {workflow.id}")
        
        memory_service = AgentMemoryService(self.db)
        
        # 测试不同类型的记忆
        memory_types = [
            ("domain_knowledge", "test_knowledge", {"definition": "测试领域知识"}),
            ("case_pattern", "test_pattern", {"pattern": "测试案例模式"}),
            ("template", "test_template", "# 测试模板\n{{ content }}"),
            ("rule", "test_rule", {"condition": "测试规则", "action": "执行"})
        ]
        
        saved_memories = []
        for memory_type, key, value in memory_types:
            memory = memory_service.save_memory(
                workflow_id=workflow.id,
                agent_type="test_agent",
                memory_type=memory_type,
                key=key,
                value=value
            )
            assert memory is not None, f"{memory_type} 记忆保存失败"
            saved_memories.append(memory)
            print(f"✓ 保存记忆成功: type={memory_type}, key={key}")
        
        # 验证数据库中的记录
        db_memories = self.db.query(Memory).filter_by(workflow_id=workflow.id).all()
        assert len(db_memories) == len(memory_types), "记忆数量不匹配"
        print(f"✓ 数据库中记忆记录数: {len(db_memories)}")
        
        # 验证检索
        for memory_type, key, value in memory_types:
            retrieved = memory_service.get_memory(
                workflow_id=workflow.id,
                agent_type="test_agent",
                memory_type=memory_type,
                key=key
            )
            assert len(retrieved) > 0, f"无法检索记忆: {memory_type}/{key}"
            print(f"✓ 检索记忆成功: {memory_type}/{key}")
        
        # 清理
        for m in db_memories:
            self.db.delete(m)
        self.db.delete(workflow)
        self.db.commit()
    
    def test_conversation_memory_persist(self):
        """测试4: 对话记忆持久化验证"""
        print("\n" + "="*60)
        print("测试 4: 对话记忆持久化验证")
        print("="*60)
        
        conv_service = ConversationMemoryService(self.db)
        workflow = conv_service.create_workflow(
            name="对话记忆测试",
            description="测试对话记忆持久化",
            definition={"test": "conversation"}
        )
        print(f"✓ 创建测试工作流: {workflow.id}")
        
        # 保存多条对话
        conversations = []
        for i in range(3):
            conv = conv_service.save_conversation(
                workflow_id=workflow.id,
                user_message=f"测试用户消息 {i+1}",
                assistant_response=f"测试助手响应 {i+1}",
                context={"turn": i+1}
            )
            conversations.append(conv)
            print(f"✓ 保存对话 {i+1}: {conv.id}")
        
        # 验证数据库中的记录
        db_convs = self.db.query(Conversation).filter_by(workflow_id=workflow.id).all()
        assert len(db_convs) == 3, "对话记录数量不匹配"
        print(f"✓ 数据库中对话记录数: {len(db_convs)}")
        
        # 验证历史检索
        history = conv_service.get_conversation_history(workflow.id)
        assert len(history) == 3, "历史检索数量不匹配"
        print(f"✓ 历史检索成功: {len(history)} 条")
        
        # 清理
        for c in db_convs:
            self.db.delete(c)
        self.db.delete(workflow)
        self.db.commit()
    
    def test_audit_log_persist(self):
        """测试5: 审计日志持久化验证"""
        print("\n" + "="*60)
        print("测试 5: 审计日志持久化验证")
        print("="*60)
        
        conv_service = ConversationMemoryService(self.db)
        workflow = conv_service.create_workflow(
            name="审计日志测试",
            description="测试审计日志持久化",
            definition={"test": "audit"}
        )
        print(f"✓ 创建测试工作流: {workflow.id}")
        
        audit_service = AuditLogService(self.db)
        
        # 记录多条审计日志
        operations = [
            ("data_collection", "DataCollectionAgent"),
            ("sentiment_analysis", "SentimentAgent"),
            ("report_generation", "ReportAgent")
        ]
        
        for op_type, operator in operations:
            log = audit_service.log_operation(
                workflow_id=workflow.id,
                operation_type=op_type,
                operator=operator,
                input_data={"test": "input"},
                output_data={"test": "output"},
                status="success"
            )
            assert log is not None, f"审计日志记录失败: {op_type}"
            print(f"✓ 记录审计日志: {op_type} by {operator}")
        
        # 验证数据库中的记录
        db_logs = self.db.query(AuditLog).filter_by(workflow_id=workflow.id).all()
        assert len(db_logs) == len(operations), "审计日志数量不匹配"
        print(f"✓ 数据库中审计日志数: {len(db_logs)}")
        
        # 清理
        for log in db_logs:
            self.db.delete(log)
        self.db.delete(workflow)
        self.db.commit()
    
    def test_execution_run_persist(self):
        """测试6: 执行记录持久化验证"""
        print("\n" + "="*60)
        print("测试 6: 执行记录持久化验证")
        print("="*60)
        
        conv_service = ConversationMemoryService(self.db)
        workflow = conv_service.create_workflow(
            name="执行记录测试",
            description="测试执行记录持久化",
            definition={"test": "execution"}
        )
        print(f"✓ 创建测试工作流: {workflow.id}")
        
        execution_repo = ExecutionRepository(self.db)
        
        # 创建执行记录
        execution_id = str(uuid.uuid4())
        execution_repo.create_execution_run(
            execution_id=execution_id,
            workflow_id=workflow.id,
            status="running",
            trigger_source="test",
            started_at=datetime.utcnow()
        )
        print(f"✓ 创建执行记录: {execution_id}")
        
        # 验证数据库中的记录
        db_run = self.db.query(ExecutionRun).filter_by(execution_id=execution_id).first()
        assert db_run is not None, "执行记录未持久化"
        assert db_run.status == "running"
        print(f"✓ 执行记录已持久化: status={db_run.status}")
        
        # 更新执行记录
        execution_repo.finalize_execution_run(
            execution_id=execution_id,
            status="completed"
        )
        self.db.refresh(db_run)
        assert db_run.status == "completed"
        assert db_run.completed_at is not None
        print(f"✓ 执行记录已更新: status={db_run.status}")
        
        # 清理
        self.db.delete(db_run)
        self.db.delete(workflow)
        self.db.commit()
    
    def test_execution_node_trace_persist(self):
        """测试7: 节点追踪记录持久化验证"""
        print("\n" + "="*60)
        print("测试 7: 节点追踪记录持久化验证")
        print("="*60)
        
        conv_service = ConversationMemoryService(self.db)
        workflow = conv_service.create_workflow(
            name="节点追踪测试",
            description="测试节点追踪持久化",
            definition={"test": "trace"}
        )
        print(f"✓ 创建测试工作流: {workflow.id}")
        
        execution_repo = ExecutionRepository(self.db)
        execution_id = str(uuid.uuid4())
        
        # 创建执行记录
        execution_repo.create_execution_run(
            execution_id=execution_id,
            workflow_id=workflow.id,
            status="running",
            trigger_source="test"
        )
        print(f"✓ 创建执行记录: {execution_id}")
        
        # 记录节点追踪
        nodes = [
            ("start", "Start", "completed"),
            ("data_collection", "DataCollectionAgent", "completed"),
            ("sentiment", "SentimentAgent", "completed"),
            ("report", "ReportAgent", "completed"),
            ("end", "End", "completed")
        ]
        
        for node_id, node_type, status in nodes:
            execution_repo.upsert_node_trace_status(
                execution_id=execution_id,
                node_id=node_id,
                status=status,
                node_type=node_type,
                input_payload={"test": "input"},
                output_payload={"test": "output"}
            )
            print(f"✓ 记录节点追踪: {node_id} ({node_type}) -> {status}")
        
        # 验证数据库中的记录
        db_traces = self.db.query(ExecutionNodeTrace).filter_by(execution_id=execution_id).all()
        assert len(db_traces) == len(nodes), "节点追踪数量不匹配"
        print(f"✓ 数据库中节点追踪数: {len(db_traces)}")
        
        # 清理
        for trace in db_traces:
            self.db.delete(trace)
        db_run = self.db.query(ExecutionRun).filter_by(execution_id=execution_id).first()
        if db_run:
            self.db.delete(db_run)
        self.db.delete(workflow)
        self.db.commit()
    
    def test_workflow_generation_with_memory(self):
        """测试8: 工作流生成并验证记忆落库"""
        print("\n" + "="*60)
        print("测试 8: 工作流生成并验证记忆落库")
        print("="*60)
        
        # 创建工作流
        conv_service = ConversationMemoryService(self.db)
        workflow = conv_service.create_workflow(
            name="生成测试工作流",
            description="测试工作流生成和记忆",
            definition={
                "name": "测试工作流",
                "nodes": [
                    {"id": "start", "type": "Start", "config": {"title": "开始"}},
                    {"id": "data", "type": "DataCollectionAgent", "config": {
                        "title": "数据收集",
                        "params": {"topic": "测试主题"}
                    }},
                    {"id": "end", "type": "End", "config": {"title": "结束"}}
                ],
                "edges": [
                    {"source": "start", "target": "data"},
                    {"source": "data", "target": "end"}
                ]
            }
        )
        print(f"✓ 创建工作流: {workflow.id}")
        
        # 保存对话记录
        conv = conv_service.save_conversation(
            workflow_id=workflow.id,
            user_message="生成一个舆情分析工作流",
            assistant_response="已为您生成工作流"
        )
        print(f"✓ 保存对话记录: {conv.id}")
        
        # 保存智能体记忆
        memory_service = AgentMemoryService(self.db)
        memory = memory_service.save_memory(
            workflow_id=workflow.id,
            agent_type="planning_agent",
            memory_type="domain_knowledge",
            key="workflow_template",
            value={"type": "public_opinion", "nodes": ["data_collection", "sentiment", "report"]}
        )
        assert memory is not None, "记忆保存失败"
        print(f"✓ 保存智能体记忆: {memory.key}")
        
        # 验证所有数据都已落库
        db_workflow = self.db.query(Workflow).filter_by(id=workflow.id).first()
        assert db_workflow is not None, "工作流未落库"
        print(f"✓ 工作流已落库: {db_workflow.name}")
        
        db_conv = self.db.query(Conversation).filter_by(workflow_id=workflow.id).first()
        assert db_conv is not None, "对话未落库"
        print(f"✓ 对话已落库")
        
        db_memory = self.db.query(Memory).filter_by(workflow_id=workflow.id).first()
        assert db_memory is not None, "记忆未落库"
        print(f"✓ 记忆已落库: {db_memory.key}")
        
        # 清理
        self.db.query(Memory).filter_by(workflow_id=workflow.id).delete()
        self.db.query(Conversation).filter_by(workflow_id=workflow.id).delete()
        self.db.delete(db_workflow)
        self.db.commit()
    
    def test_memory_service_is_persistable(self):
        """测试9: 记忆服务持久化校验逻辑"""
        print("\n" + "="*60)
        print("测试 9: 记忆服务持久化校验逻辑")
        print("="*60)
        
        memory_service = AgentMemoryService(self.db)
        
        # 测试1: 有效UUID且存在于workflows表
        conv_service = ConversationMemoryService(self.db)
        workflow = conv_service.create_workflow(
            name="持久化校验测试",
            description="测试持久化校验",
            definition={"test": "persistable"}
        )
        print(f"✓ 创建有效工作流: {workflow.id}")
        
        assert memory_service._is_persistable_workflow_id(workflow.id), "有效workflow_id应该可持久化"
        print(f"✓ 有效UUID + 存在于workflows表 -> 可持久化")
        
        # 测试2: 无效UUID
        assert not memory_service._is_persistable_workflow_id("invalid-uuid"), "无效UUID不应可持久化"
        print(f"✓ 无效UUID -> 不可持久化")
        
        # 测试3: 不存在的UUID
        fake_uuid = str(uuid.uuid4())
        assert not memory_service._is_persistable_workflow_id(fake_uuid), "不存在的UUID不应可持久化"
        print(f"✓ 不存在的UUID -> 不可持久化")
        
        # 测试4: None值
        assert not memory_service._is_persistable_workflow_id(None), "None不应可持久化"
        print(f"✓ None -> 不可持久化")
        
        # 清理
        self.db.delete(workflow)
        self.db.commit()
    
    def test_memory_save_with_invalid_workflow_id(self):
        """测试10: 无效workflow_id时记忆不落库（降级策略）"""
        print("\n" + "="*60)
        print("测试 10: 无效workflow_id降级策略")
        print("="*60)
        
        memory_service = AgentMemoryService(self.db)
        
        # 测试1: 使用不存在的UUID
        fake_uuid = str(uuid.uuid4())
        result = memory_service.save_memory(
            workflow_id=fake_uuid,
            agent_type="test_agent",
            memory_type="test",
            key="test_key",
            value={"test": "value"}
        )
        assert result is None, "无效workflow_id应返回None（降级）"
        print(f"✓ 不存在的workflow_id -> 返回None（降级）")
        
        # 测试2: 使用None
        result = memory_service.save_memory(
            workflow_id=None,
            agent_type="test_agent",
            memory_type="test",
            key="test_key",
            value={"test": "value"}
        )
        assert result is None, "None workflow_id应返回None（降级）"
        print(f"✓ None workflow_id -> 返回None（降级）")
        
        # 验证数据库中没有记录
        db_memories = self.db.query(Memory).filter_by(agent_type="test_agent").all()
        assert len(db_memories) == 0, "不应有记忆记录"
        print(f"✓ 数据库中无记忆记录（正确降级）")


def run_e2e_tests():
    """运行端到端测试"""
    print("\n" + "="*60)
    print("端到端测试：工作流记忆持久化验证")
    print("="*60)
    
    test_instance = TestWorkflowMemoryPersistence()
    test_instance.setup()
    
    tests = [
        ("数据库连接和表结构", test_instance.test_database_connection_and_tables),
        ("工作流创建并持久化", test_instance.test_workflow_create_and_persist),
        ("智能体记忆持久化", test_instance.test_agent_memory_persist),
        ("对话记忆持久化", test_instance.test_conversation_memory_persist),
        ("审计日志持久化", test_instance.test_audit_log_persist),
        ("执行记录持久化", test_instance.test_execution_run_persist),
        ("节点追踪记录持久化", test_instance.test_execution_node_trace_persist),
        ("工作流生成并验证记忆落库", test_instance.test_workflow_generation_with_memory),
        ("记忆服务持久化校验逻辑", test_instance.test_memory_service_is_persistable),
        ("无效workflow_id降级策略", test_instance.test_memory_save_with_invalid_workflow_id),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True))
            print(f"\n✅ {name} - 通过")
        except Exception as e:
            results.append((name, False))
            print(f"\n❌ {name} - 失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            test_instance.setup()  # 重置数据库连接
    
    # 打印汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  - {name}: {status}")
    
    return passed == total


if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)