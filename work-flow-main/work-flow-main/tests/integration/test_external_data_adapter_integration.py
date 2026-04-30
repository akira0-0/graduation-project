"""
外部数据适配器集成测试
验证适配器输出能够被后续分析智能体正确读取
"""
import pytest
from workflow_engine.src.utils.external_data_adapter import (
    ExternalDataAdapter,
    adapt_external_filter_output
)
from workflow_engine.src.nodes.sentiment_agent_node import SentimentAgentNode
from workflow_engine.src.core.schema import NodeDefinition, WorkflowState


class TestExternalDataAdapterIntegration:
    """测试外部数据适配器与后续节点的集成"""
    
    @pytest.fixture
    def sample_external_data_list(self):
        """示例外部数据列表（来自用户提供格式）"""
        return [
            {
                "id": "5255301945365254",
                "original_id": "5255301945365254",
                "platform": "weibo",
                "type": "image",
                "url": "https://m.weibo.cn/detail/5255301945365254",
                "title": "特朗普是否会对伊朗发动袭击？",
                "content": "特朗普是否会对伊朗发动袭击？媒体们都在寻找蛛丝马迹：航班追踪网站称伊朗已关闭其空域。",
                "publish_time": None,
                "author_id": "2174585797",
                "author_nickname": "王冰汝",
                "author_ip_location": "发布于 美国",
                "author_is_verified": True,
                "metrics_likes": 210,
                "metrics_collects": 0,
                "metrics_comments": 71,
                "metrics_shares": 31,
                "tags": ["特朗普", "伊朗"],
                "source_keyword": "",
                "filter_batch_id": "batch_20260407_164517_f05cd3",
                "filter_passed_rules": [],
                "filter_rejected_rules": [],
                "quality_score": None,
                "relevance_score": 0.85,
                "filter_layer": 1,
                "created_at": "2026-04-07T08:45:22.145818",
                "relevance_level": "high"
            },
            {
                "id": "5255301945365255",
                "original_id": "5255301945365255",
                "platform": "weibo",
                "type": "text",
                "url": "https://m.weibo.cn/detail/5255301945365255",
                "title": "另一条测试标题",
                "content": "这是一条正面的测试内容，表达了支持和赞赏的态度。",
                "publish_time": "2026-04-07T10:00:00",
                "author_id": "1234567890",
                "author_nickname": "测试用户",
                "author_ip_location": "发布于 北京",
                "author_is_verified": False,
                "metrics_likes": 50,
                "metrics_collects": 10,
                "metrics_comments": 5,
                "metrics_shares": 3,
                "tags": ["测试"],
                "source_keyword": "测试关键词",
                "filter_batch_id": "batch_20260407_164517_f05cd4",
                "filter_passed_rules": ["规则1", "规则2"],
                "filter_rejected_rules": [],
                "quality_score": 0.75,
                "relevance_score": 0.65,
                "filter_layer": 1,
                "created_at": "2026-04-07T10:30:00.000000",
                "relevance_level": "medium"
            }
        ]
    
    def test_adapter_output_matches_filter_node_format(self, sample_external_data_list):
        """测试适配器输出格式与 FilterAgentNode 输出格式一致"""
        adapter = ExternalDataAdapter()
        result = adapter.adapt_batch(sample_external_data_list)
        
        # FilterAgentNode 输出格式
        filter_node_output = {
            "status": "success",
            "filtered_data": result["data"],
            "original_count": result["stats"]["total"],
            "filtered_count": result["stats"]["successful"],
            "message": f"成功适配外部数据，共 {result['stats']['successful']} 条"
        }
        
        # 验证格式
        assert "filtered_data" in filter_node_output
        assert isinstance(filter_node_output["filtered_data"], list)
        assert len(filter_node_output["filtered_data"]) == 2
        assert filter_node_output["status"] == "success"
    
    def test_sentiment_node_can_parse_adapter_output(self, sample_external_data_list):
        """测试情感分析节点能够解析适配器输出"""
        # 1. 使用适配器转换数据
        adapter = ExternalDataAdapter()
        adapted_result = adapter.adapt_batch(sample_external_data_list)
        
        # 2. 模拟 FilterAgentNode 的输出格式
        filter_node_output = {
            "status": "success",
            "filtered_data": adapted_result["data"],
            "original_count": adapted_result["stats"]["total"],
            "filtered_count": adapted_result["stats"]["successful"]
        }
        
        # 3. 创建情感分析节点并测试数据解析
        from workflow_engine.src.core.schema import NodeConfig
        node_def = NodeDefinition(
            id="test_sentiment_node",
            type="SentimentAgent",
            config=NodeConfig(title="测试情感分析节点")
        )
        
        sentiment_node = SentimentAgentNode(node_def)
        
        # 4. 使用节点的 _parse_input_data 方法解析数据
        parsed_data = sentiment_node._parse_input_data(filter_node_output)
        
        # 5. 验证解析结果
        assert isinstance(parsed_data, list)
        assert len(parsed_data) == 2
        
        # 验证每条数据都有必要字段
        for item in parsed_data:
            assert "id" in item
            assert "content" in item
            assert "source" in item
    
    def test_data_item_has_required_fields_for_sentiment_analysis(self, sample_external_data_list):
        """测试适配后的数据项包含情感分析所需字段"""
        adapter = ExternalDataAdapter()
        result = adapter.adapt_batch(sample_external_data_list)
        
        for item in result["data"]:
            # 必须有内容字段用于情感分析
            assert "content" in item
            assert isinstance(item["content"], str)
            assert len(item["content"]) > 0
            
            # 必须有唯一标识
            assert "id" in item
            
            # 应该有来源信息
            assert "source" in item
            
            # 应该有时间戳
            assert "timestamp" in item
    
    def test_data_item_has_sentiment_field(self, sample_external_data_list):
        """测试适配后的数据项包含 sentiment 字段（默认值）"""
        adapter = ExternalDataAdapter()
        result = adapter.adapt_batch(sample_external_data_list)
        
        for item in result["data"]:
            # sentiment 字段应该存在（默认为 "unknown"）
            assert "sentiment" in item
            assert item["sentiment"] == "unknown"
    
    def test_adapter_preserves_rich_metadata(self, sample_external_data_list):
        """测试适配器保留丰富的元数据"""
        adapter = ExternalDataAdapter()
        result = adapter.adapt_batch(sample_external_data_list)
        
        # 验证第一条数据保留了丰富的元数据
        item = result["data"][0]
        
        # 原始字段映射
        assert item["id"] == "5255301945365254"
        assert item["source"] == "weibo"
        assert item["author"] == "王冰汝"
        assert item["likes"] == 210
        assert item["relevance_score"] == 0.85
        
        # 衍生字段
        assert "total_engagement" in item
        assert item["total_engagement"] == 210 + 0 + 71 + 31
        
        assert "content_length" in item
        
        # 过滤相关字段
        assert "filter_passed_rules" in item
        assert "filter_rejected_rules" in item
        assert "passed_filter" in item
    
    def test_full_workflow_simulation(self, sample_external_data_list):
        """模拟完整工作流：外部数据 -> 适配器 -> 模拟后续节点处理"""
        # 1. 外部数据通过适配器
        adapter = ExternalDataAdapter()
        adapted_result = adapter.adapt_batch(sample_external_data_list)
        
        # 2. 构建类似 FilterAgentNode 的输出
        filter_output = {
            "status": "success",
            "filtered_data": adapted_result["data"],
            "original_count": adapted_result["stats"]["total"],
            "filtered_count": adapted_result["stats"]["successful"],
            "filters_applied": {
                "source": "external_filter_component",
                "filter_batch_id": "batch_20260407_164517_f05cd3"
            }
        }
        
        # 3. 模拟后续节点读取数据
        # 类似情感分析节点的处理方式
        if "filtered_data" in filter_output:
            data_for_analysis = filter_output["filtered_data"]
        else:
            data_for_analysis = []
        
        # 4. 验证数据可用于分析
        assert len(data_for_analysis) == 2
        
        # 5. 模拟简单的情感分析处理
        for item in data_for_analysis:
            # 确保可以访问内容进行分析
            content = item.get("content", "")
            assert len(content) > 0
            
            # 确保有元数据可用于报告
            assert item.get("author") is not None
            assert item.get("source") is not None
    
    def test_adapter_stats_tracking(self, sample_external_data_list):
        """测试适配器统计追踪功能"""
        adapter = ExternalDataAdapter()
        
        # 批量适配
        result = adapter.adapt_batch(sample_external_data_list)
        
        # 验证统计信息
        stats = adapter.get_stats()
        assert stats["total_processed"] == 2
        assert stats["successful"] == 2
        assert stats["failed"] == 0
    
    def test_adapter_with_comments(self):
        """测试适配器处理包含评论的数据"""
        data_with_comments = [{
            "id": "123",
            "content": "主内容",
            "platform": "weibo",
            "author_nickname": "作者",
            "comments": [
                {
                    "id": "comment1",
                    "content": "评论内容",
                    "author_nickname": "评论者",
                    "metrics_likes": 10
                }
            ]
        }]
        
        adapter = ExternalDataAdapter()
        result = adapter.adapt_batch(data_with_comments)
        
        assert len(result["data"]) == 1
        assert "comments" in result["data"][0]
        assert len(result["data"][0]["comments"]) == 1
        assert result["data"][0]["comments"][0]["author"] == "评论者"
    
    def test_adapter_output_compatibility_with_report_generation(self, sample_external_data_list):
        """测试适配器输出与报告生成智能体的兼容性"""
        adapter = ExternalDataAdapter()
        result = adapter.adapt_batch(sample_external_data_list)
        
        # 报告生成通常需要的字段
        for item in result["data"]:
            # 基础信息
            assert "id" in item
            assert "content" in item
            assert "source" in item
            
            # 可用于统计的字段
            if "likes" in item:
                assert isinstance(item["likes"], int)
            if "relevance_score" in item and item["relevance_score"] is not None:
                assert isinstance(item["relevance_score"], (int, float))
            
            # 可用于分类的字段
            if "tags" in item:
                assert isinstance(item["tags"], list)
            if "relevance_category" in item:
                assert item["relevance_category"] in ["high", "medium", "low", "unknown"]


class TestAdapterOutputFormat:
    """测试适配器输出格式的规范性"""
    
    @pytest.fixture
    def adapter(self):
        return ExternalDataAdapter()
    
    def test_output_format_consistency(self, adapter):
        """测试输出格式的一致性"""
        data1 = [{"id": "1", "content": "内容1", "platform": "weibo"}]
        data2 = [
            {"id": "2", "content": "内容2", "platform": "twitter"},
            {"id": "3", "content": "内容3", "platform": "facebook"}
        ]
        
        result1 = adapter.adapt_batch(data1)
        result2 = adapter.adapt_batch(data2)
        
        # 验证输出结构一致
        assert "data" in result1 and "data" in result2
        assert "stats" in result1 and "stats" in result2
        
        # 验证数据项字段一致
        keys1 = set(result1["data"][0].keys())
        keys2 = set(result2["data"][0].keys())
        assert keys1 == keys2
    
    def test_empty_data_handling(self, adapter):
        """测试空数据处理"""
        result = adapter.adapt_batch([])
        
        assert result["data"] == []
        assert result["stats"]["total"] == 0
        assert result["stats"]["successful"] == 0
        assert result["stats"]["failed"] == 0
    
    def test_convenience_function_output(self):
        """测试便捷函数输出格式"""
        data = [{"id": "1", "content": "测试", "platform": "weibo"}]
        
        result = adapt_external_filter_output(data)
        
        assert "data" in result
        assert "stats" in result
        assert isinstance(result["data"], list)
        assert isinstance(result["stats"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])