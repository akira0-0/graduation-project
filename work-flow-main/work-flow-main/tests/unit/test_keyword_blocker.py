"""
关键词屏蔽功能单元测试
"""
import pytest
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from workflow_engine.src.utils.keyword_blocker import KeywordBlocker, get_keyword_blocker


class TestKeywordBlocker:
    """关键词屏蔽器测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.blocker = KeywordBlocker()
    
    def test_initialization(self):
        """测试初始化"""
        assert self.blocker is not None
        assert len(self.blocker.blocked_keywords) > 0
        assert len(self.blocker.category_keywords) > 0
    
    def test_default_categories(self):
        """测试默认类别"""
        categories = self.blocker.get_blocked_categories()
        assert "sensitive_political" in categories
        assert "violence" in categories
        assert "pornography" in categories
        assert "gambling" in categories
        assert "drugs" in categories
    
    def test_is_keyword_safe_normal(self):
        """测试正常关键词安全检查"""
        # 正常关键词应该是安全的
        assert self.blocker.is_keyword_safe("人工智能") == True
        assert self.blocker.is_keyword_safe("机器学习") == True
        assert self.blocker.is_keyword_safe("Python编程") == True
        assert self.blocker.is_keyword_safe("数据科学") == True
    
    def test_is_keyword_safe_blocked(self):
        """测试敏感关键词拦截"""
        # 敏感关键词应该被拦截
        assert self.blocker.is_keyword_safe("法轮功") == False
        assert self.blocker.is_keyword_safe("台独") == False
        assert self.blocker.is_keyword_safe("赌博网站") == False
        assert self.blocker.is_keyword_safe("毒品交易") == False
    
    def test_is_keyword_safe_partial_match(self):
        """测试部分匹配的关键词"""
        # 包含敏感词的关键词也应该被拦截
        assert self.blocker.is_keyword_safe("如何赌博") == False
        assert self.blocker.is_keyword_safe("色情视频") == False
        assert self.blocker.is_keyword_safe("恐怖袭击策划") == False
    
    def test_is_keyword_safe_empty(self):
        """测试空关键词"""
        assert self.blocker.is_keyword_safe("") == False
        assert self.blocker.is_keyword_safe("   ") == False
    
    def test_filter_keywords(self):
        """测试关键词列表过滤"""
        keywords = [
            "人工智能",
            "机器学习",
            "赌博",  # 敏感词
            "深度学习",
            "色情",  # 敏感词
            "数据分析"
        ]
        
        safe_keywords = self.blocker.filter_keywords(keywords)
        
        assert len(safe_keywords) == 4
        assert "人工智能" in safe_keywords
        assert "机器学习" in safe_keywords
        assert "深度学习" in safe_keywords
        assert "数据分析" in safe_keywords
        assert "赌博" not in safe_keywords
        assert "色情" not in safe_keywords
    
    def test_filter_content(self):
        """测试内容过滤"""
        content = "这是一段包含赌博和色情的敏感内容"
        filtered = self.blocker.filter_content(content)
        
        assert "赌博" not in filtered
        assert "色情" not in filtered
        assert "[已屏蔽]" in filtered
    
    def test_filter_search_results(self):
        """测试搜索结果过滤"""
        results = [
            {
                "id": "1",
                "title": "人工智能技术发展",
                "content": "人工智能的发展趋势",
                "source": "test"
            },
            {
                "id": "2",
                "title": "赌博网站推荐",  # 敏感标题
                "content": "这是赌博相关内容",
                "source": "test"
            },
            {
                "id": "3",
                "title": "机器学习教程",
                "content": "机器学习入门教程",
                "source": "test"
            },
            {
                "id": "4",
                "title": "技术文章",
                "content": "包含毒品相关内容",  # 敏感内容
                "source": "test"
            }
        ]
        
        filtered = self.blocker.filter_search_results(results)
        
        # 应该只保留正常结果
        assert len(filtered) == 2
        assert filtered[0]["title"] == "人工智能技术发展"
        assert filtered[1]["title"] == "机器学习教程"
    
    def test_add_blocked_keyword(self):
        """测试添加屏蔽关键词"""
        initial_count = len(self.blocker.blocked_keywords)
        
        # 添加新的屏蔽词
        self.blocker.add_blocked_keyword("测试敏感词", category="custom")
        
        assert len(self.blocker.blocked_keywords) == initial_count + 1
        assert self.blocker.is_keyword_safe("测试敏感词") == False
        assert "测试敏感词" in self.blocker.get_keywords_by_category("custom")
    
    def test_remove_blocked_keyword(self):
        """测试移除屏蔽关键词"""
        # 先添加一个词
        self.blocker.add_blocked_keyword("临时测试词", category="custom")
        assert self.blocker.is_keyword_safe("临时测试词") == False
        
        # 然后移除
        result = self.blocker.remove_blocked_keyword("临时测试词")
        
        assert result == True
        assert self.blocker.is_keyword_safe("临时测试词") == True
    
    def test_get_keywords_by_category(self):
        """测试获取类别关键词"""
        violence_keywords = self.blocker.get_keywords_by_category("violence")
        
        assert isinstance(violence_keywords, list)
        assert len(violence_keywords) > 0
        assert "暴力" in violence_keywords or "杀人" in violence_keywords
    
    def test_singleton(self):
        """测试单例模式"""
        blocker1 = get_keyword_blocker()
        blocker2 = get_keyword_blocker()
        
        assert blocker1 is blocker2


class TestDataCollectionAgentKeywordBlocking:
    """数据收集智能体关键词屏蔽测试"""
    
    def test_keyword_expander_blocks_sensitive(self):
        """测试关键词扩展器阻止敏感关键词"""
        from workflow_engine.src.agents.data_collection_agent import KeywordExpander
        
        # 不使用 LLM 的简化测试
        blocker = KeywordBlocker()
        expander = KeywordExpander(keyword_blocker=blocker)
        
        # 测试备用扩展对敏感词的处理
        result = expander._fallback_expand("赌博", 5)
        
        # 敏感词应该返回空列表
        assert result == []
    
    def test_keyword_expander_fallback_safe(self):
        """测试关键词扩展器备用方法对正常关键词的处理"""
        from workflow_engine.src.agents.data_collection_agent import KeywordExpander
        
        blocker = KeywordBlocker()
        expander = KeywordExpander(keyword_blocker=blocker)
        
        # 测试正常关键词的备用扩展
        result = expander._fallback_expand("人工智能", 5)
        
        # 应该返回扩展后的关键词
        assert len(result) > 0
        assert "人工智能" in result
        # 扩展的关键词都应该是安全的
        for kw in result:
            assert blocker.is_keyword_safe(kw)


def run_tests():
    """运行测试"""
    print("\n" + "="*60)
    print("关键词屏蔽功能测试")
    print("="*60)
    
    # 创建测试实例
    blocker_tests = TestKeywordBlocker()
    blocker_tests.setup_method()
    
    # 运行测试
    tests = [
        ("初始化测试", blocker_tests.test_initialization),
        ("默认类别测试", blocker_tests.test_default_categories),
        ("正常关键词安全检查", blocker_tests.test_is_keyword_safe_normal),
        ("敏感关键词拦截", blocker_tests.test_is_keyword_safe_blocked),
        ("部分匹配检测", blocker_tests.test_is_keyword_safe_partial_match),
        ("空关键词处理", blocker_tests.test_is_keyword_safe_empty),
        ("关键词列表过滤", blocker_tests.test_filter_keywords),
        ("内容过滤", blocker_tests.test_filter_content),
        ("搜索结果过滤", blocker_tests.test_filter_search_results),
        ("添加屏蔽关键词", blocker_tests.test_add_blocked_keyword),
        ("移除屏蔽关键词", blocker_tests.test_remove_blocked_keyword),
        ("获取类别关键词", blocker_tests.test_get_keywords_by_category),
        ("单例模式", blocker_tests.test_singleton),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}: 通过")
            passed += 1
        except AssertionError as e:
            print(f"❌ {name}: 失败 - {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {name}: 错误 - {e}")
            failed += 1
    
    # 数据收集智能体测试
    agent_tests = TestDataCollectionAgentKeywordBlocking()
    agent_test_list = [
        ("关键词扩展器阻止敏感词", agent_tests.test_keyword_expander_blocks_sensitive),
        ("关键词扩展器正常扩展", agent_tests.test_keyword_expander_fallback_safe),
    ]
    
    for name, test_func in agent_test_list:
        try:
            test_func()
            print(f"✅ {name}: 通过")
            passed += 1
        except AssertionError as e:
            print(f"❌ {name}: 失败 - {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {name}: 错误 - {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"测试结果: 通过 {passed} 个, 失败 {failed} 个")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)