"""
外部数据适配器单元测试
"""
import pytest
from datetime import datetime
from workflow_engine.src.utils.external_data_adapter import (
    ExternalDataAdapter,
    adapt_external_filter_output
)


class TestExternalDataAdapter:
    """测试 ExternalDataAdapter 类"""
    
    @pytest.fixture
    def adapter(self):
        """创建适配器实例"""
        return ExternalDataAdapter(strict_mode=False)
    
    @pytest.fixture
    def sample_external_data(self):
        """示例外部数据（来自用户提供格式）"""
        return {
            "id": "5255301945365254",
            "original_id": "5255301945365254",
            "platform": "weibo",
            "type": "image",
            "url": "https://m.weibo.cn/detail/5255301945365254",
            "title": "特朗普是否会对伊朗发动袭击？",
            "content": "特朗普是否会对伊朗发动袭击？媒体们都在寻找蛛丝马迹...",
            "publish_time": None,
            "author_id": "2174585797",
            "author_nickname": "王冰汝",
            "author_ip_location": "发布于 美国",
            "author_is_verified": True,
            "metrics_likes": 210,
            "metrics_collects": 0,
            "metrics_comments": 71,
            "metrics_shares": 31,
            "tags": ["特朗普"],
            "source_keyword": "",
            "filter_batch_id": "batch_20260407_164517_f05cd3",
            "filter_passed_rules": [],
            "filter_rejected_rules": ["通用-质量-有效中文内容"],
            "quality_score": None,
            "relevance_score": 0.85,
            "filter_layer": 1,
            "created_at": "2026-04-07T08:45:22.145818",
            "relevance_level": "high",
            "comments": [
                {
                    "id": "5255302314198351",
                    "original_id": "5255302314198351",
                    "content_id": "5255301945365254",
                    "platform": "weibo",
                    "content": "想到一个题外话:五角大楼加班是不是都只订披萨啊？",
                    "publish_time": None,
                    "author_id": "1909391191",
                    "author_nickname": "蜀地小女",
                    "author_ip_location": "来自四川",
                    "metrics_likes": 8,
                    "metrics_sub_comments": 11,
                    "parent_comment_id": None,
                    "root_comment_id": "5255302314198351",
                    "reply_to_user_id": None,
                    "reply_to_user_nickname": None,
                    "comment_level": 1,
                    "filter_batch_id": "batch_20260407_165044_8f9744",
                    "filter_passed_rules": [],
                    "filter_rejected_rules": ["通用-质量-有效中文内容"],
                    "quality_score": None,
                    "relevance_score": None,
                    "filter_layer": 1,
                    "created_at": "2026-04-07T08:50:52.057653"
                }
            ]
        }
    
    def test_adapt_single_basic_fields(self, adapter, sample_external_data):
        """测试基本字段映射"""
        result = adapter.adapt_single(sample_external_data)
        
        # 验证基本字段
        assert result["id"] == "5255301945365254"
        assert result["source"] == "weibo"
        assert result["content_type"] == "image"
        assert result["url"] == "https://m.weibo.cn/detail/5255301945365254"
        assert result["title"] == "特朗普是否会对伊朗发动袭击？"
        assert result["content"] == "特朗普是否会对伊朗发动袭击？媒体们都在寻找蛛丝马迹..."
    
    def test_adapt_single_author_fields(self, adapter, sample_external_data):
        """测试作者字段映射"""
        result = adapter.adapt_single(sample_external_data)
        
        assert result["author_id"] == "2174585797"
        assert result["author"] == "王冰汝"
        assert result["author_location"] == "发布于 美国"
        assert result["author_verified"] is True
    
    def test_adapt_single_metrics_fields(self, adapter, sample_external_data):
        """测试指标字段映射"""
        result = adapter.adapt_single(sample_external_data)
        
        assert result["likes"] == 210
        assert result["collects"] == 0
        assert result["comments_count"] == 71
        assert result["shares"] == 31
        assert isinstance(result["likes"], int)
    
    def test_adapt_single_filter_fields(self, adapter, sample_external_data):
        """测试过滤相关字段映射"""
        result = adapter.adapt_single(sample_external_data)
        
        assert result["filter_batch_id"] == "batch_20260407_164517_f05cd3"
        assert result["filter_passed_rules"] == []
        assert result["filter_rejected_rules"] == ["通用-质量-有效中文内容"]
        assert result["filter_layer"] == 1
    
    def test_adapt_single_score_fields(self, adapter, sample_external_data):
        """测试评分字段映射"""
        result = adapter.adapt_single(sample_external_data)
        
        assert result["relevance_score"] == 0.85
        assert result["relevance_level"] == "high"
        assert result["quality_score"] is None
    
    def test_adapt_single_derived_fields(self, adapter, sample_external_data):
        """测试衍生字段计算"""
        result = adapter.adapt_single(sample_external_data)
        
        # 总互动量
        assert result["total_engagement"] == 210 + 0 + 71 + 31
        
        # 内容长度
        assert result["content_length"] == len(sample_external_data["content"])
        
        # 是否通过过滤
        assert result["passed_filter"] is False  # 有被拒绝的规则
        
        # 相关度分类
        assert result["relevance_category"] == "high"  # relevance_score >= 0.7
    
    def test_adapt_single_comments(self, adapter, sample_external_data):
        """测试评论数据适配"""
        result = adapter.adapt_single(sample_external_data)
        
        assert "comments" in result
        assert len(result["comments"]) == 1
        
        comment = result["comments"][0]
        assert comment["id"] == "5255302314198351"
        assert comment["content"] == "想到一个题外话:五角大楼加班是不是都只订披萨啊？"
        assert comment["author"] == "蜀地小女"
        assert comment["likes"] == 8
        assert comment["comment_level"] == 1
    
    def test_adapt_single_empty_data(self, adapter):
        """测试空数据输入"""
        result = adapter.adapt_single(None)
        
        assert "id" in result
        assert result["content"] == ""
        assert result["source"] == "unknown"
        assert "error" in result["adapter_info"]
    
    def test_adapt_single_missing_fields(self, adapter):
        """测试缺失字段处理"""
        partial_data = {
            "id": "test123",
            "content": "测试内容"
        }
        
        result = adapter.adapt_single(partial_data)
        
        assert result["id"] == "test123"
        assert result["content"] == "测试内容"
        assert result["source"] == "external"  # 默认值
        assert "timestamp" in result
        assert result["sentiment"] == "unknown"
    
    def test_adapt_single_type_conversion(self, adapter):
        """测试类型转换"""
        data_with_strings = {
            "id": "test123",
            "metrics_likes": "100",  # 字符串形式的数字
            "metrics_comments": "50",
            "author_is_verified": "true",  # 字符串形式的布尔值
            "tags": "single_tag"  # 字符串形式的标签
        }
        
        result = adapter.adapt_single(data_with_strings)
        
        assert result["likes"] == 100
        assert isinstance(result["likes"], int)
        assert result["comments_count"] == 50
        assert result["author_verified"] is True
        assert result["tags"] == ["single_tag"]
    
    def test_adapt_single_time_parsing(self, adapter):
        """测试时间解析"""
        data_with_time = {
            "id": "test123",
            "content": "测试",
            "publish_time": "2026-04-07T08:45:22",
            "created_at": "2026-04-07T08:50:52.057653"
        }
        
        result = adapter.adapt_single(data_with_time)
        
        assert "publish_time" in result
        assert "collected_at" in result
        assert "timestamp" in result
    
    def test_adapt_batch(self, adapter, sample_external_data):
        """测试批量适配"""
        data_list = [
            sample_external_data,
            {**sample_external_data, "id": "test2", "content": "第二条数据"},
            {**sample_external_data, "id": "test3", "content": "第三条数据"}
        ]
        
        result = adapter.adapt_batch(data_list)
        
        assert "data" in result
        assert "stats" in result
        assert len(result["data"]) == 3
        assert result["stats"]["total"] == 3
        assert result["stats"]["successful"] == 3
        assert result["stats"]["failed"] == 0
    
    def test_adapt_batch_empty_list(self, adapter):
        """测试空列表批量适配"""
        result = adapter.adapt_batch([])
        
        assert result["data"] == []
        assert result["stats"]["total"] == 0
    
    def test_adapt_batch_with_failures(self, adapter, sample_external_data):
        """测试包含失败项的批量适配"""
        data_list = [
            sample_external_data,
            None,  # 会失败
            {},    # 会生成空内容但有效
        ]
        
        result = adapter.adapt_batch(data_list)
        
        # 空字典会生成默认结果，有id所以会被保留
        assert result["stats"]["total"] == 3
    
    def test_get_stats(self, adapter, sample_external_data):
        """测试统计信息获取"""
        adapter.adapt_single(sample_external_data)
        adapter.adapt_single(None)  # 失败
        
        stats = adapter.get_stats()
        
        assert stats["total_processed"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1
    
    def test_reset_stats(self, adapter, sample_external_data):
        """测试统计信息重置"""
        adapter.adapt_single(sample_external_data)
        adapter.reset_stats()
        
        stats = adapter.get_stats()
        
        assert stats["total_processed"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
    
    def test_strict_mode(self):
        """测试严格模式"""
        strict_adapter = ExternalDataAdapter(strict_mode=True)
        
        with pytest.raises(Exception):
            # 在严格模式下，某些错误会抛出异常
            # 这里测试一个会导致异常的情况
            strict_adapter._do_adapt_single(None)
    
    def test_adapter_info(self, adapter, sample_external_data):
        """测试适配器元数据"""
        result = adapter.adapt_single(sample_external_data)
        
        assert "adapter_info" in result
        assert result["adapter_info"]["adapter_version"] == "1.0.0"
        assert "adapted_at" in result["adapter_info"]
        assert result["adapter_info"]["source_platform"] == "weibo"
    
    def test_relevance_category_classification(self, adapter):
        """测试相关度分类"""
        # 高相关度
        high_relevance = {"id": "1", "content": "test", "relevance_score": 0.85}
        result_high = adapter.adapt_single(high_relevance)
        assert result_high["relevance_category"] == "high"
        
        # 中等相关度
        medium_relevance = {"id": "2", "content": "test", "relevance_score": 0.55}
        result_medium = adapter.adapt_single(medium_relevance)
        assert result_medium["relevance_category"] == "medium"
        
        # 低相关度
        low_relevance = {"id": "3", "content": "test", "relevance_score": 0.25}
        result_low = adapter.adapt_single(low_relevance)
        assert result_low["relevance_category"] == "low"
        
        # 未知相关度
        unknown_relevance = {"id": "4", "content": "test"}
        result_unknown = adapter.adapt_single(unknown_relevance)
        assert result_unknown["relevance_category"] == "unknown"


class TestConvenienceFunction:
    """测试便捷函数"""
    
    def test_adapt_external_filter_output(self):
        """测试便捷函数"""
        external_data = [
            {"id": "1", "content": "测试1", "platform": "weibo"},
            {"id": "2", "content": "测试2", "platform": "twitter"}
        ]
        
        result = adapt_external_filter_output(external_data)
        
        assert "data" in result
        assert "stats" in result
        assert len(result["data"]) == 2


class TestFilterAgentCompatibility:
    """测试与 FilterAgent 的兼容性"""
    
    @pytest.fixture
    def adapter(self):
        """创建适配器实例"""
        return ExternalDataAdapter()
    
    @pytest.fixture
    def sample_external_data(self):
        """示例外部数据"""
        return {
            "id": "5255301945365254",
            "content": "测试内容，长度足够用于过滤测试。",
            "platform": "weibo",
            "author_nickname": "测试用户",
            "metrics_likes": 100,
            "relevance_score": 0.75,
            "filter_rejected_rules": [],
            "tags": ["测试标签"]
        }
    
    def test_output_compatible_with_filter_agent(self, adapter, sample_external_data):
        """测试适配后的数据格式与 FilterAgent 兼容"""
        result = adapter.adapt_single(sample_external_data)
        
        # FilterAgent 需要的字段
        required_fields = ["id", "content", "source"]
        for field in required_fields:
            assert field in result, f"缺少必要字段: {field}"
        
        # 检查 content 字段可用于长度过滤
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
        
        # 检查 source 字段
        assert isinstance(result["source"], str)
        
        # 检查可选但常用的字段
        assert "timestamp" in result
    
    def test_batch_output_for_filter_pipeline(self, adapter):
        """测试批量输出可用于过滤管道"""
        data_list = [
            {"id": "1", "content": "短", "platform": "weibo"},
            {"id": "2", "content": "这是一条足够长度的内容用于过滤测试", "platform": "weibo"},
            {"id": "3", "content": "另一条足够长度的测试内容数据", "platform": "twitter"}
        ]
        
        result = adapter.adapt_batch(data_list)
        
        # 验证输出格式
        assert isinstance(result["data"], list)
        assert all("id" in item for item in result["data"])
        assert all("content" in item for item in result["data"])
        
        # 验证可以用于长度过滤
        filtered = [item for item in result["data"] if len(item.get("content", "")) > 10]
        assert len(filtered) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])