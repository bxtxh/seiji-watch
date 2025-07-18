"""
Tests for search functionality including full-text search, advanced filtering, and integrated search API.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ..src.search.full_text_search import (
    FullTextSearchEngine, SearchQuery, SearchMode, SearchField, 
    JapaneseTextProcessor, SearchResult, SearchResponse
)
from ..src.search.advanced_filtering import (
    AdvancedFilterEngine, FilterQuery, FilterGroup, FilterCondition, 
    FilterOperator, LogicalOperator, SortCriteria, SortOrder
)
from ..src.search.integrated_search_api import (
    IntegratedSearchAPI, IntegratedSearchRequest, IntegratedSearchResponse
)


class TestJapaneseTextProcessor:
    """Test Japanese text processing utilities"""
    
    @pytest.fixture
    def processor(self):
        """Create test processor instance"""
        return JapaneseTextProcessor()
    
    def test_normalize_text(self, processor):
        """Test text normalization"""
        # Full-width to half-width conversion
        input_text = "ＡＢＣＤ１２３４"
        expected = "ABCD1234"
        result = processor.normalize_text(input_text)
        assert result == expected
        
        # Katakana to hiragana conversion
        input_text = "カタカナ"
        expected = "かたかな"
        result = processor.normalize_text(input_text)
        assert result == expected
        
        # Whitespace normalization
        input_text = "  多重  空白  "
        expected = "多重 空白"
        result = processor.normalize_text(input_text)
        assert result == expected
    
    def test_tokenize_japanese(self, processor):
        """Test Japanese tokenization"""
        # Test with Japanese text
        text = "デジタル社会形成基本法案"
        tokens = processor.tokenize_japanese(text)
        assert len(tokens) > 0
        assert all(len(token) > 0 for token in tokens)
        
        # Test with empty text
        tokens = processor.tokenize_japanese("")
        assert tokens == []
        
        # Test with mixed text
        text = "令和3年度予算案について"
        tokens = processor.tokenize_japanese(text)
        assert len(tokens) > 0
    
    def test_extract_readings(self, processor):
        """Test reading extraction"""
        # Test with Japanese text (may require MeCab)
        text = "政府"
        readings = processor.extract_readings(text)
        # This test depends on MeCab availability
        assert isinstance(readings, list)


class TestFullTextSearchEngine:
    """Test full-text search engine"""
    
    @pytest.fixture
    def mock_engine(self):
        """Create mock database engine"""
        engine = Mock()
        engine.connect.return_value.__enter__.return_value = Mock()
        return engine
    
    @pytest.fixture
    def search_engine(self, mock_engine):
        """Create test search engine"""
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            return FullTextSearchEngine("postgresql://test")
    
    def test_build_search_vector(self, search_engine):
        """Test search vector building"""
        # Test with ALL fields
        vector = search_engine._build_search_vector([SearchField.ALL])
        assert "setweight" in vector
        assert "title" in vector
        assert "bill_outline" in vector
        
        # Test with specific fields
        vector = search_engine._build_search_vector([SearchField.TITLE, SearchField.OUTLINE])
        assert "title" in vector
        assert "bill_outline" in vector
    
    def test_process_advanced_query(self, search_engine):
        """Test advanced query processing"""
        # Test operator conversion
        query = "法案 AND 予算"
        result = search_engine._process_advanced_query(query)
        assert "&" in result
        
        # Test phrase handling
        query = '"デジタル社会"'
        result = search_engine._process_advanced_query(query)
        assert "デジタル社会" in result
    
    @patch('sqlalchemy.orm.sessionmaker')
    def test_search_simple_mode(self, mock_session_maker, search_engine):
        """Test simple search mode"""
        # Mock session and query result
        mock_session = Mock()
        mock_session_maker.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        
        # Mock query result
        mock_row = Mock()
        mock_row.bill_id = "test-1"
        mock_row.title = "テスト法案"
        mock_row.relevance_score = 0.5
        mock_row.submitter = "政府"
        mock_row.category = "その他"
        mock_row.status = "審議中"
        mock_row.diet_session = "204"
        mock_row.house_of_origin = "参議院"
        mock_row.submitted_date = date(2021, 1, 1)
        mock_row.bill_outline = "テスト用の法案概要"
        
        mock_session.execute.return_value.fetchall.return_value = [mock_row]
        mock_session.execute.return_value.fetchone.return_value = (1,)
        
        # Test search
        query = SearchQuery(
            query="テスト",
            mode=SearchMode.SIMPLE,
            fields=[SearchField.ALL],
            limit=10
        )
        
        result = search_engine.search(query)
        
        assert isinstance(result, SearchResponse)
        assert len(result.results) == 1
        assert result.results[0].bill_id == "test-1"
        assert result.results[0].title == "テスト法案"
    
    def test_generate_snippet(self, search_engine):
        """Test snippet generation"""
        mock_row = Mock()
        mock_row.bill_outline = "これは長い法案概要です。" * 20
        mock_row.background_context = "背景情報"
        mock_row.title = "テスト法案"
        
        query = SearchQuery(query="テスト", mode=SearchMode.SIMPLE)
        snippet = search_engine._generate_snippet(mock_row, query)
        
        assert len(snippet) <= search_engine.search_config['snippet_length'] + 3  # +3 for "..."
        assert "..." in snippet or len(snippet) <= search_engine.search_config['snippet_length']


class TestAdvancedFilterEngine:
    """Test advanced filtering engine"""
    
    @pytest.fixture
    def mock_engine(self):
        """Create mock database engine"""
        engine = Mock()
        engine.connect.return_value.__enter__.return_value = Mock()
        return engine
    
    @pytest.fixture
    def filter_engine(self, mock_engine):
        """Create test filter engine"""
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            return AdvancedFilterEngine("postgresql://test")
    
    def test_convert_value_date(self, filter_engine):
        """Test date value conversion"""
        # Test string to date
        result = filter_engine._convert_value('submitted_date', '2021-01-01')
        assert result == date(2021, 1, 1)
        
        # Test datetime to date
        result = filter_engine._convert_value('submitted_date', datetime(2021, 1, 1, 12, 0, 0))
        assert result == date(2021, 1, 1)
        
        # Test invalid date
        result = filter_engine._convert_value('submitted_date', 'invalid-date')
        assert result == 'invalid-date'  # Should return original value
    
    def test_convert_value_numeric(self, filter_engine):
        """Test numeric value conversion"""
        # Test string to float
        result = filter_engine._convert_value('quality_score', '0.75')
        assert result == 0.75
        
        # Test invalid float
        result = filter_engine._convert_value('quality_score', 'invalid')
        assert result == 'invalid'  # Should return original value
    
    def test_build_filter_condition(self, filter_engine):
        """Test filter condition building"""
        # Test EQUALS condition
        condition = FilterCondition(
            field='category',
            operator=FilterOperator.EQUALS,
            value='予算・決算'
        )
        
        sql_condition = filter_engine._build_filter_condition(condition)
        assert sql_condition is not None
        
        # Test CONTAINS condition
        condition = FilterCondition(
            field='title',
            operator=FilterOperator.CONTAINS,
            value='デジタル'
        )
        
        sql_condition = filter_engine._build_filter_condition(condition)
        assert sql_condition is not None
        
        # Test BETWEEN condition
        condition = FilterCondition(
            field='submitted_date',
            operator=FilterOperator.BETWEEN,
            value=['2021-01-01', '2021-12-31']
        )
        
        sql_condition = filter_engine._build_filter_condition(condition)
        assert sql_condition is not None
    
    def test_validate_filter_condition(self, filter_engine):
        """Test filter condition validation"""
        # Test valid condition
        condition = FilterCondition(
            field='category',
            operator=FilterOperator.EQUALS,
            value='予算・決算'
        )
        
        errors = filter_engine._validate_filter_condition(condition)
        assert len(errors) == 0
        
        # Test invalid field
        condition = FilterCondition(
            field='invalid_field',
            operator=FilterOperator.EQUALS,
            value='test'
        )
        
        errors = filter_engine._validate_filter_condition(condition)
        assert len(errors) > 0
        assert "Invalid field" in errors[0]
        
        # Test invalid operator for date field
        condition = FilterCondition(
            field='submitted_date',
            operator=FilterOperator.CONTAINS,
            value='2021'
        )
        
        errors = filter_engine._validate_filter_condition(condition)
        assert len(errors) > 0
        assert "not supported for date field" in errors[0]
    
    def test_validate_filter_query(self, filter_engine):
        """Test complete filter query validation"""
        # Test valid query
        query = FilterQuery(
            filters=FilterGroup(
                conditions=[
                    FilterCondition(
                        field='category',
                        operator=FilterOperator.EQUALS,
                        value='予算・決算'
                    )
                ]
            ),
            sort=[SortCriteria('submitted_date', SortOrder.DESC)],
            limit=50
        )
        
        errors = filter_engine.validate_filter_query(query)
        assert len(errors) == 0
        
        # Test invalid query
        query = FilterQuery(
            filters=FilterGroup(
                conditions=[
                    FilterCondition(
                        field='invalid_field',
                        operator=FilterOperator.EQUALS,
                        value='test'
                    )
                ]
            ),
            sort=[SortCriteria('invalid_sort_field', SortOrder.DESC)],
            limit=-1
        )
        
        errors = filter_engine.validate_filter_query(query)
        assert len(errors) > 0
        assert any("Invalid field" in error for error in errors)
        assert any("Invalid sort field" in error for error in errors)
        assert any("Limit must be positive" in error for error in errors)
    
    @patch('sqlalchemy.orm.sessionmaker')
    def test_get_filter_suggestions(self, mock_session_maker, filter_engine):
        """Test filter suggestions"""
        # Mock session and query result
        mock_session = Mock()
        mock_session_maker.return_value = mock_session
        mock_session.__enter__.return_value = mock_session
        
        # Mock query result
        mock_row = Mock()
        mock_row.value = "デジタル法案"
        mock_session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Test suggestions
        suggestions = filter_engine.get_filter_suggestions('title', 'デジタル', 5)
        
        assert isinstance(suggestions, list)
        # The test depends on the actual field configuration


class TestIntegratedSearchAPI:
    """Test integrated search API"""
    
    @pytest.fixture
    def mock_engines(self):
        """Create mock search engines"""
        mock_ft_engine = Mock()
        mock_filter_engine = Mock()
        return mock_ft_engine, mock_filter_engine
    
    @pytest.fixture
    def search_api(self, mock_engines):
        """Create test search API"""
        mock_ft_engine, mock_filter_engine = mock_engines
        with patch('services.ingest-worker.src.search.integrated_search_api.FullTextSearchEngine', return_value=mock_ft_engine), \
             patch('services.ingest-worker.src.search.integrated_search_api.AdvancedFilterEngine', return_value=mock_filter_engine):
            return IntegratedSearchAPI("postgresql://test")
    
    def test_validate_search_request(self, search_api):
        """Test search request validation"""
        # Test valid request
        request = IntegratedSearchRequest(
            text_query="デジタル",
            limit=50,
            offset=0
        )
        
        errors = search_api.validate_search_request(request)
        assert len(errors) == 0
        
        # Test invalid request
        request = IntegratedSearchRequest(
            text_query="a",  # Too short
            limit=0,  # Invalid limit
            offset=-1  # Invalid offset
        )
        
        errors = search_api.validate_search_request(request)
        assert len(errors) > 0
        assert any("at least 2 characters" in error for error in errors)
        assert any("must be positive" in error for error in errors)
        assert any("must be non-negative" in error for error in errors)
    
    def test_generate_cache_key(self, search_api):
        """Test cache key generation"""
        request1 = IntegratedSearchRequest(
            text_query="デジタル",
            limit=50
        )
        
        request2 = IntegratedSearchRequest(
            text_query="デジタル",
            limit=50
        )
        
        request3 = IntegratedSearchRequest(
            text_query="予算",
            limit=50
        )
        
        key1 = search_api._generate_cache_key(request1)
        key2 = search_api._generate_cache_key(request2)
        key3 = search_api._generate_cache_key(request3)
        
        assert key1 == key2  # Same request should generate same key
        assert key1 != key3  # Different request should generate different key
    
    def test_combined_search(self, search_api):
        """Test combined search functionality"""
        # Mock search response
        mock_search_result = Mock()
        mock_search_result.bill_id = "test-1"
        mock_search_result.title = "テスト法案"
        mock_search_result.relevance_score = 0.8
        mock_search_result.matched_fields = ["title"]
        mock_search_result.snippet = "テスト用の法案"
        mock_search_result.highlights = ["テスト用の<b>法案</b>"]
        mock_search_result.metadata = {"category": "その他"}
        
        mock_search_response = Mock()
        mock_search_response.results = [mock_search_result]
        mock_search_response.total_count = 1
        mock_search_response.query_time_ms = 50.0
        mock_search_response.suggestions = []
        mock_search_response.facets = {}
        mock_search_response.debug_info = {}
        
        search_api.full_text_engine.search.return_value = mock_search_response
        
        # Test combined search
        request = IntegratedSearchRequest(
            text_query="テスト",
            filters=FilterGroup(
                conditions=[
                    FilterCondition(
                        field='category',
                        operator=FilterOperator.EQUALS,
                        value='その他'
                    )
                ]
            )
        )
        
        result = search_api._combined_search(request)
        
        assert isinstance(result, IntegratedSearchResponse)
        assert len(result.results) == 1
        assert result.results[0]['bill_id'] == "test-1"
        assert result.has_text_search is True
        assert result.has_filters is True
    
    def test_text_search_only(self, search_api):
        """Test text search only functionality"""
        # Mock search response
        mock_search_result = Mock()
        mock_search_result.bill_id = "test-1"
        mock_search_result.title = "テスト法案"
        mock_search_result.relevance_score = 0.8
        mock_search_result.matched_fields = ["title"]
        mock_search_result.snippet = "テスト用の法案"
        mock_search_result.highlights = ["テスト用の<b>法案</b>"]
        mock_search_result.metadata = {"category": "その他"}
        
        mock_search_response = Mock()
        mock_search_response.results = [mock_search_result]
        mock_search_response.total_count = 1
        mock_search_response.query_time_ms = 30.0
        mock_search_response.suggestions = []
        mock_search_response.facets = {}
        mock_search_response.debug_info = {}
        
        search_api.full_text_engine.search.return_value = mock_search_response
        
        # Test text search
        request = IntegratedSearchRequest(
            text_query="テスト"
        )
        
        result = search_api._text_search_only(request)
        
        assert isinstance(result, IntegratedSearchResponse)
        assert len(result.results) == 1
        assert result.has_text_search is True
        assert result.has_filters is False
    
    def test_filter_search_only(self, search_api):
        """Test filter search only functionality"""
        # Mock filter response
        mock_filter_result = Mock()
        mock_filter_result.data = [
            {
                'bill_id': 'test-1',
                'title': 'テスト法案',
                'bill_outline': 'テスト用の法案概要',
                'submitter': '政府',
                'category': 'その他',
                'status': '審議中',
                'diet_session': '204',
                'house_of_origin': '参議院',
                'submitted_date': date(2021, 1, 1)
            }
        ]
        mock_filter_result.total_count = 1
        mock_filter_result.query_time_ms = 20.0
        mock_filter_result.sql_query = "SELECT * FROM bills WHERE category = 'その他'"
        mock_filter_result.parameters = {'category': 'その他'}
        
        search_api.filter_engine.apply_filters.return_value = mock_filter_result
        
        # Test filter search
        request = IntegratedSearchRequest(
            filters=FilterGroup(
                conditions=[
                    FilterCondition(
                        field='category',
                        operator=FilterOperator.EQUALS,
                        value='その他'
                    )
                ]
            )
        )
        
        result = search_api._filter_search_only(request)
        
        assert isinstance(result, IntegratedSearchResponse)
        assert len(result.results) == 1
        assert result.has_text_search is False
        assert result.has_filters is True
    
    def test_cache_functionality(self, search_api):
        """Test caching functionality"""
        # Test cache key generation
        request = IntegratedSearchRequest(text_query="テスト")
        cache_key = search_api._generate_cache_key(request)
        assert len(cache_key) > 0
        
        # Test cache clearing
        search_api._cache['test_key'] = Mock()
        search_api.clear_cache()
        assert len(search_api._cache) == 0
        
        # Test cache statistics
        search_api._cache['test_key'] = Mock()
        search_api._cache_timestamps['test_key'] = datetime.now()
        
        stats = search_api.get_cache_statistics()
        assert stats['cache_size'] == 1
        assert 'test_key' in stats['cache_entries']
    
    def test_get_search_suggestions(self, search_api):
        """Test search suggestions"""
        # Mock filter result for suggestions
        mock_filter_result = Mock()
        mock_filter_result.data = [
            {'title': 'デジタル社会形成基本法案'},
            {'title': 'デジタル改革関連法案'}
        ]
        
        search_api.filter_engine.apply_filters.return_value = mock_filter_result
        
        suggestions = search_api.get_search_suggestions("デジタル", 5)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5
    
    def test_get_field_suggestions(self, search_api):
        """Test field suggestions"""
        # Mock filter engine response
        search_api.filter_engine.get_filter_suggestions.return_value = ['予算・決算', '税制', '社会保障']
        
        suggestions = search_api.get_field_suggestions('category', '予算', 5)
        
        assert isinstance(suggestions, list)
        search_api.filter_engine.get_filter_suggestions.assert_called_once_with('category', '予算', 5)


class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    @pytest.fixture
    def mock_database(self):
        """Create mock database for integration tests"""
        # This would be a real database in full integration tests
        engine = Mock()
        session = Mock()
        return engine, session
    
    def test_full_search_pipeline(self, mock_database):
        """Test complete search pipeline"""
        engine, session = mock_database
        
        # Mock all components
        with patch('services.ingest-worker.src.search.integrated_search_api.FullTextSearchEngine') as mock_ft, \
             patch('services.ingest-worker.src.search.integrated_search_api.AdvancedFilterEngine') as mock_filter:
            
            # Setup mock responses
            mock_ft_instance = Mock()
            mock_filter_instance = Mock()
            mock_ft.return_value = mock_ft_instance
            mock_filter.return_value = mock_filter_instance
            
            # Create search API
            search_api = IntegratedSearchAPI("postgresql://test")
            
            # Test search request
            request = IntegratedSearchRequest(
                text_query="デジタル法案",
                filters=FilterGroup(
                    conditions=[
                        FilterCondition(
                            field='category',
                            operator=FilterOperator.EQUALS,
                            value='行政・公務員'
                        )
                    ]
                ),
                limit=20,
                include_facets=True,
                include_suggestions=True
            )
            
            # Mock search response
            mock_search_result = Mock()
            mock_search_result.bill_id = "test-1"
            mock_search_result.title = "デジタル改革関連法案"
            mock_search_result.relevance_score = 0.9
            mock_search_result.matched_fields = ["title", "bill_outline"]
            mock_search_result.snippet = "デジタル社会の形成を推進するための法案"
            mock_search_result.highlights = ["<b>デジタル</b>改革関連<b>法案</b>"]
            mock_search_result.metadata = {
                'category': '行政・公務員',
                'status': '審議中',
                'submitter': '政府'
            }
            
            mock_search_response = Mock()
            mock_search_response.results = [mock_search_result]
            mock_search_response.total_count = 1
            mock_search_response.query_time_ms = 45.0
            mock_search_response.suggestions = ["デジタル社会", "デジタル改革"]
            mock_search_response.facets = {
                'category': {'行政・公務員': 15, '経済・産業': 8},
                'status': {'審議中': 12, '成立': 5}
            }
            mock_search_response.debug_info = {}
            
            mock_ft_instance.search.return_value = mock_search_response
            
            # Execute search
            result = search_api.search(request)
            
            # Verify results
            assert isinstance(result, IntegratedSearchResponse)
            assert len(result.results) == 1
            assert result.results[0]['bill_id'] == "test-1"
            assert result.results[0]['title'] == "デジタル改革関連法案"
            assert result.total_count == 1
            assert result.has_text_search is True
            assert result.has_filters is True
            assert len(result.suggestions) == 2
            assert 'category' in result.facets
            assert 'status' in result.facets
    
    def test_search_performance(self, mock_database):
        """Test search performance characteristics"""
        engine, session = mock_database
        
        with patch('services.ingest-worker.src.search.integrated_search_api.FullTextSearchEngine') as mock_ft, \
             patch('services.ingest-worker.src.search.integrated_search_api.AdvancedFilterEngine') as mock_filter:
            
            # Setup mock with performance data
            mock_ft_instance = Mock()
            mock_filter_instance = Mock()
            mock_ft.return_value = mock_ft_instance
            mock_filter.return_value = mock_filter_instance
            
            # Mock fast response
            mock_search_response = Mock()
            mock_search_response.results = []
            mock_search_response.total_count = 0
            mock_search_response.query_time_ms = 25.0
            mock_search_response.suggestions = []
            mock_search_response.facets = {}
            mock_search_response.debug_info = {}
            
            mock_ft_instance.search.return_value = mock_search_response
            
            # Create search API
            search_api = IntegratedSearchAPI("postgresql://test")
            
            # Test multiple searches
            request = IntegratedSearchRequest(text_query="テスト")
            
            # First search (not cached)
            result1 = search_api.search(request)
            assert result1.query_time_ms > 0
            
            # Second search (should be cached)
            result2 = search_api.search(request)
            assert result2.query_time_ms == 0.0  # Cached result
            
            # Verify cache statistics
            stats = search_api.get_cache_statistics()
            assert stats['cache_size'] == 1
    
    def test_error_handling(self, mock_database):
        """Test error handling in search pipeline"""
        engine, session = mock_database
        
        with patch('services.ingest-worker.src.search.integrated_search_api.FullTextSearchEngine') as mock_ft, \
             patch('services.ingest-worker.src.search.integrated_search_api.AdvancedFilterEngine') as mock_filter:
            
            # Setup mock to raise exception
            mock_ft_instance = Mock()
            mock_filter_instance = Mock()
            mock_ft.return_value = mock_ft_instance
            mock_filter.return_value = mock_filter_instance
            
            # Mock search exception
            mock_ft_instance.search.side_effect = Exception("Database connection failed")
            
            # Create search API
            search_api = IntegratedSearchAPI("postgresql://test")
            
            # Test error handling
            request = IntegratedSearchRequest(text_query="テスト")
            result = search_api.search(request)
            
            # Verify error handling
            assert isinstance(result, IntegratedSearchResponse)
            assert len(result.results) == 0
            assert result.total_count == 0
            assert 'error' in result.debug_info
            assert result.debug_info['error'] == "Database connection failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])