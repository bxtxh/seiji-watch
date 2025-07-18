"""
Integrated Search API combining full-text search and advanced filtering.
Provides a unified interface for comprehensive bill search capabilities.
"""

import logging
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import json

from .full_text_search import FullTextSearchEngine, SearchQuery, SearchMode, SearchField, SearchResponse
from .advanced_filtering import AdvancedFilterEngine, FilterQuery, FilterGroup, FilterCondition, FilterOperator, SortCriteria, SortOrder


@dataclass
class IntegratedSearchRequest:
    """Combined search request with full-text and filtering capabilities"""
    
    # Full-text search parameters
    text_query: Optional[str] = None
    search_mode: SearchMode = SearchMode.SIMPLE
    search_fields: List[SearchField] = field(default_factory=lambda: [SearchField.ALL])
    
    # Advanced filtering parameters
    filters: Optional[FilterGroup] = None
    
    # Sorting and pagination
    sort: List[SortCriteria] = field(default_factory=list)
    limit: int = 50
    offset: int = 0
    
    # Search options
    include_facets: bool = True
    include_suggestions: bool = True
    include_highlights: bool = True
    include_statistics: bool = False
    
    # Japanese-specific options
    use_morphological_analysis: bool = True
    enable_reading_search: bool = True
    
    # Performance options
    enable_caching: bool = True
    cache_ttl_seconds: int = 300


@dataclass
class IntegratedSearchResponse:
    """Combined search response with rich metadata"""
    
    # Core results
    results: List[Dict[str, Any]]
    total_count: int
    
    # Search metadata
    query_time_ms: float
    search_mode: str
    has_text_search: bool
    has_filters: bool
    
    # Full-text search specific
    suggestions: List[str] = field(default_factory=list)
    highlights: Dict[str, List[str]] = field(default_factory=dict)
    
    # Filtering specific
    facets: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Statistics
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    # Debug information
    debug_info: Dict[str, Any] = field(default_factory=dict)


class IntegratedSearchAPI:
    """Integrated search API combining full-text search and advanced filtering"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.logger = logging.getLogger(__name__)
        
        # Initialize search engines
        self.full_text_engine = FullTextSearchEngine(database_url)
        self.filter_engine = AdvancedFilterEngine(database_url)
        
        # Search configuration
        self.config = {
            'max_results': 1000,
            'default_limit': 50,
            'max_facet_values': 20,
            'snippet_length': 200,
            'highlight_fragments': 3,
        }
        
        # Cache for search results (simple in-memory cache)
        self._cache = {}
        self._cache_timestamps = {}
    
    def initialize_search_indexes(self):
        """Initialize all search indexes"""
        try:
            self.logger.info("Initializing search indexes...")
            self.full_text_engine.create_search_indexes()
            self.logger.info("Search indexes initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing search indexes: {e}")
            raise
    
    def search(self, request: IntegratedSearchRequest) -> IntegratedSearchResponse:
        """Perform integrated search"""
        start_time = datetime.now()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            if request.enable_caching and cache_key in self._cache:
                cached_result, timestamp = self._cache[cache_key], self._cache_timestamps[cache_key]
                if (datetime.now() - timestamp).total_seconds() < request.cache_ttl_seconds:
                    cached_result.query_time_ms = 0.0  # Cached result
                    return cached_result
            
            # Determine search strategy
            has_text_search = bool(request.text_query and request.text_query.strip())
            has_filters = bool(request.filters)
            
            if has_text_search and has_filters:
                # Combined search: full-text + filtering
                result = self._combined_search(request)
            elif has_text_search:
                # Full-text search only
                result = self._text_search_only(request)
            elif has_filters:
                # Filtering only
                result = self._filter_search_only(request)
            else:
                # No search criteria, return all with sorting/pagination
                result = self._browse_all(request)
            
            # Calculate query time
            query_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            result.query_time_ms = query_time_ms
            
            # Add metadata
            result.search_mode = request.search_mode.value
            result.has_text_search = has_text_search
            result.has_filters = has_filters
            
            # Cache result
            if request.enable_caching:
                self._cache[cache_key] = result
                self._cache_timestamps[cache_key] = datetime.now()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            return IntegratedSearchResponse(
                results=[],
                total_count=0,
                query_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                search_mode=request.search_mode.value,
                has_text_search=has_text_search,
                has_filters=has_filters,
                debug_info={'error': str(e)}
            )
    
    def _combined_search(self, request: IntegratedSearchRequest) -> IntegratedSearchResponse:
        """Perform combined full-text search and filtering"""
        
        # Step 1: Convert filters to search filters for full-text search
        search_filters = self._convert_filters_to_search_filters(request.filters)
        
        # Step 2: Create full-text search query
        search_query = SearchQuery(
            query=request.text_query,
            mode=request.search_mode,
            fields=request.search_fields,
            filters=search_filters,
            limit=min(request.limit, self.config['max_results']),
            offset=request.offset,
            sort_by=self._convert_sort_to_search_sort(request.sort),
            use_morphological_analysis=request.use_morphological_analysis,
            enable_reading_search=request.enable_reading_search
        )
        
        # Step 3: Execute full-text search
        search_response = self.full_text_engine.search(search_query)
        
        # Step 4: Convert results to integrated format
        results = []
        highlights = {}
        
        for search_result in search_response.results:
            result_dict = {
                'bill_id': search_result.bill_id,
                'title': search_result.title,
                'relevance_score': search_result.relevance_score,
                'matched_fields': search_result.matched_fields,
                'snippet': search_result.snippet,
                'metadata': search_result.metadata
            }
            results.append(result_dict)
            
            # Collect highlights
            if request.include_highlights and search_result.highlights:
                highlights[search_result.bill_id] = search_result.highlights
        
        # Step 5: Get additional metadata
        suggestions = search_response.suggestions if request.include_suggestions else []
        facets = search_response.facets if request.include_facets else {}
        
        # Step 6: Get statistics if requested
        statistics = {}
        if request.include_statistics:
            statistics = self._get_search_statistics(request)
        
        return IntegratedSearchResponse(
            results=results,
            total_count=search_response.total_count,
            query_time_ms=search_response.query_time_ms,
            search_mode=request.search_mode.value,
            has_text_search=True,
            has_filters=True,
            suggestions=suggestions,
            highlights=highlights,
            facets=facets,
            statistics=statistics,
            debug_info=search_response.debug_info
        )
    
    def _text_search_only(self, request: IntegratedSearchRequest) -> IntegratedSearchResponse:
        """Perform full-text search only"""
        
        # Create search query
        search_query = SearchQuery(
            query=request.text_query,
            mode=request.search_mode,
            fields=request.search_fields,
            limit=min(request.limit, self.config['max_results']),
            offset=request.offset,
            sort_by=self._convert_sort_to_search_sort(request.sort),
            use_morphological_analysis=request.use_morphological_analysis,
            enable_reading_search=request.enable_reading_search
        )
        
        # Execute search
        search_response = self.full_text_engine.search(search_query)
        
        # Convert results
        results = []
        highlights = {}
        
        for search_result in search_response.results:
            result_dict = {
                'bill_id': search_result.bill_id,
                'title': search_result.title,
                'relevance_score': search_result.relevance_score,
                'matched_fields': search_result.matched_fields,
                'snippet': search_result.snippet,
                'metadata': search_result.metadata
            }
            results.append(result_dict)
            
            if request.include_highlights and search_result.highlights:
                highlights[search_result.bill_id] = search_result.highlights
        
        # Get metadata
        suggestions = search_response.suggestions if request.include_suggestions else []
        facets = search_response.facets if request.include_facets else {}
        statistics = self._get_search_statistics(request) if request.include_statistics else {}
        
        return IntegratedSearchResponse(
            results=results,
            total_count=search_response.total_count,
            query_time_ms=search_response.query_time_ms,
            search_mode=request.search_mode.value,
            has_text_search=True,
            has_filters=False,
            suggestions=suggestions,
            highlights=highlights,
            facets=facets,
            statistics=statistics,
            debug_info=search_response.debug_info
        )
    
    def _filter_search_only(self, request: IntegratedSearchRequest) -> IntegratedSearchResponse:
        """Perform filtering only"""
        
        # Create filter query
        filter_query = FilterQuery(
            filters=request.filters,
            sort=request.sort,
            limit=min(request.limit, self.config['max_results']),
            offset=request.offset,
            include_count=True
        )
        
        # Execute filtering
        filter_result = self.filter_engine.apply_filters(filter_query)
        
        # Convert results
        results = []
        for data_dict in filter_result.data:
            # Add basic metadata for consistency
            result_dict = {
                'bill_id': data_dict.get('bill_id'),
                'title': data_dict.get('title'),
                'relevance_score': 1.0,  # No relevance for filter-only
                'matched_fields': [],
                'snippet': data_dict.get('bill_outline', data_dict.get('summary', ''))[:self.config['snippet_length']],
                'metadata': {
                    'submitter': data_dict.get('submitter'),
                    'category': data_dict.get('category'),
                    'status': data_dict.get('status'),
                    'diet_session': data_dict.get('diet_session'),
                    'house_of_origin': data_dict.get('house_of_origin'),
                    'submitted_date': data_dict.get('submitted_date')
                }
            }
            results.append(result_dict)
        
        # Get facets if requested
        facets = {}
        if request.include_facets:
            facets = self._get_filter_facets(request.filters)
        
        # Get statistics if requested
        statistics = self._get_search_statistics(request) if request.include_statistics else {}
        
        return IntegratedSearchResponse(
            results=results,
            total_count=filter_result.total_count or len(results),
            query_time_ms=filter_result.query_time_ms,
            search_mode=request.search_mode.value,
            has_text_search=False,
            has_filters=True,
            suggestions=[],
            highlights={},
            facets=facets,
            statistics=statistics,
            debug_info={'sql_query': filter_result.sql_query, 'parameters': filter_result.parameters}
        )
    
    def _browse_all(self, request: IntegratedSearchRequest) -> IntegratedSearchResponse:
        """Browse all bills with sorting and pagination"""
        
        # Create filter query with no filters
        filter_query = FilterQuery(
            filters=None,
            sort=request.sort if request.sort else [SortCriteria('submitted_date', SortOrder.DESC)],
            limit=min(request.limit, self.config['max_results']),
            offset=request.offset,
            include_count=True
        )
        
        # Execute query
        filter_result = self.filter_engine.apply_filters(filter_query)
        
        # Convert results
        results = []
        for data_dict in filter_result.data:
            result_dict = {
                'bill_id': data_dict.get('bill_id'),
                'title': data_dict.get('title'),
                'relevance_score': 1.0,
                'matched_fields': [],
                'snippet': data_dict.get('bill_outline', data_dict.get('summary', ''))[:self.config['snippet_length']],
                'metadata': {
                    'submitter': data_dict.get('submitter'),
                    'category': data_dict.get('category'),
                    'status': data_dict.get('status'),
                    'diet_session': data_dict.get('diet_session'),
                    'house_of_origin': data_dict.get('house_of_origin'),
                    'submitted_date': data_dict.get('submitted_date')
                }
            }
            results.append(result_dict)
        
        # Get facets if requested
        facets = {}
        if request.include_facets:
            facets = self._get_filter_facets(None)
        
        # Get statistics if requested
        statistics = self._get_search_statistics(request) if request.include_statistics else {}
        
        return IntegratedSearchResponse(
            results=results,
            total_count=filter_result.total_count or len(results),
            query_time_ms=filter_result.query_time_ms,
            search_mode=request.search_mode.value,
            has_text_search=False,
            has_filters=False,
            suggestions=[],
            highlights={},
            facets=facets,
            statistics=statistics,
            debug_info={'sql_query': filter_result.sql_query, 'parameters': filter_result.parameters}
        )
    
    def _convert_filters_to_search_filters(self, filters: Optional[FilterGroup]) -> Dict[str, Any]:
        """Convert filter group to search filters format"""
        search_filters = {}
        
        if not filters:
            return search_filters
        
        # Extract simple filters that can be used in full-text search
        for condition in filters.conditions:
            if isinstance(condition, FilterCondition):
                if condition.operator == FilterOperator.EQUALS:
                    if condition.field == 'category':
                        search_filters['category'] = condition.value
                    elif condition.field == 'status':
                        search_filters['status'] = condition.value
                    elif condition.field == 'submitter':
                        search_filters['submitter'] = condition.value
                    elif condition.field == 'session':
                        search_filters['diet_session'] = condition.value
                    elif condition.field == 'house':
                        search_filters['house_of_origin'] = condition.value
        
        return search_filters
    
    def _convert_sort_to_search_sort(self, sort_criteria: List[SortCriteria]) -> str:
        """Convert sort criteria to search sort format"""
        if not sort_criteria:
            return "relevance"
        
        # Use the first sort criterion
        first_sort = sort_criteria[0]
        
        if first_sort.field in ['submitted_date', 'vote_date', 'implementation_date']:
            return "date"
        elif first_sort.field == 'title':
            return "title"
        else:
            return "relevance"
    
    def _get_filter_facets(self, filters: Optional[FilterGroup]) -> Dict[str, Dict[str, int]]:
        """Get facets for filtering"""
        facets = {}
        
        try:
            # Get facets from filter engine
            for field in ['category', 'status', 'submitter', 'house']:
                stats = self.filter_engine.get_field_statistics(field)
                if 'top_values' in stats:
                    facets[field] = {
                        item['value']: item['count'] 
                        for item in stats['top_values'][:self.config['max_facet_values']]
                    }
        except Exception as e:
            self.logger.error(f"Error getting facets: {e}")
        
        return facets
    
    def _get_search_statistics(self, request: IntegratedSearchRequest) -> Dict[str, Any]:
        """Get search statistics"""
        statistics = {}
        
        try:
            # Get full-text search statistics
            ft_stats = self.full_text_engine.get_search_statistics()
            statistics['full_text_search'] = ft_stats
            
            # Get field statistics for key fields
            field_stats = {}
            for field in ['category', 'status', 'submitter', 'house']:
                field_stats[field] = self.filter_engine.get_field_statistics(field)
            
            statistics['field_statistics'] = field_stats
            
        except Exception as e:
            self.logger.error(f"Error getting search statistics: {e}")
            statistics['error'] = str(e)
        
        return statistics
    
    def _generate_cache_key(self, request: IntegratedSearchRequest) -> str:
        """Generate cache key for search request"""
        # Create a hash of the request parameters
        import hashlib
        request_str = json.dumps({
            'text_query': request.text_query,
            'search_mode': request.search_mode.value,
            'search_fields': [f.value for f in request.search_fields],
            'filters': self._serialize_filters(request.filters),
            'sort': [(s.field, s.order.value) for s in request.sort],
            'limit': request.limit,
            'offset': request.offset,
        }, sort_keys=True)
        
        return hashlib.md5(request_str.encode()).hexdigest()
    
    def _serialize_filters(self, filters: Optional[FilterGroup]) -> Optional[Dict[str, Any]]:
        """Serialize filters for cache key generation"""
        if not filters:
            return None
        
        serialized = {
            'operator': filters.operator.value,
            'conditions': []
        }
        
        for condition in filters.conditions:
            if isinstance(condition, FilterCondition):
                serialized['conditions'].append({
                    'field': condition.field,
                    'operator': condition.operator.value,
                    'value': condition.value,
                    'case_sensitive': condition.case_sensitive
                })
            elif isinstance(condition, FilterGroup):
                serialized['conditions'].append(self._serialize_filters(condition))
        
        return serialized
    
    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions for partial query"""
        suggestions = []
        
        try:
            # Get suggestions from different sources
            
            # 1. Popular search terms (could be from search logs)
            popular_terms = ['デジタル', '予算', '税制', '社会保障', '環境', '教育', '医療', '年金']
            matching_popular = [term for term in popular_terms if partial_query in term]
            suggestions.extend(matching_popular)
            
            # 2. Bill titles containing the query
            filter_query = FilterQuery(
                filters=FilterGroup(
                    conditions=[
                        FilterCondition(
                            field='title',
                            operator=FilterOperator.CONTAINS,
                            value=partial_query
                        )
                    ]
                ),
                sort=[SortCriteria('submitted_date', SortOrder.DESC)],
                limit=5
            )
            
            filter_result = self.filter_engine.apply_filters(filter_query)
            for result in filter_result.data:
                title = result.get('title', '')
                if title and title not in suggestions:
                    suggestions.append(title)
            
        except Exception as e:
            self.logger.error(f"Error getting search suggestions: {e}")
        
        return suggestions[:limit]
    
    def get_field_suggestions(self, field: str, partial_value: str = "", limit: int = 10) -> List[str]:
        """Get field value suggestions"""
        return self.filter_engine.get_filter_suggestions(field, partial_value, limit)
    
    def validate_search_request(self, request: IntegratedSearchRequest) -> List[str]:
        """Validate search request"""
        errors = []
        
        # Validate text query
        if request.text_query:
            if len(request.text_query.strip()) < 2:
                errors.append("Text query must be at least 2 characters long")
            elif len(request.text_query) > 1000:
                errors.append("Text query is too long (max 1000 characters)")
        
        # Validate search fields
        if not request.search_fields:
            errors.append("At least one search field must be specified")
        
        # Validate filters
        if request.filters:
            # Create a dummy filter query to validate
            filter_query = FilterQuery(filters=request.filters)
            filter_errors = self.filter_engine.validate_filter_query(filter_query)
            errors.extend(filter_errors)
        
        # Validate pagination
        if request.limit <= 0:
            errors.append("Limit must be positive")
        elif request.limit > self.config['max_results']:
            errors.append(f"Limit cannot exceed {self.config['max_results']}")
        
        if request.offset < 0:
            errors.append("Offset must be non-negative")
        
        return errors
    
    def clear_cache(self):
        """Clear search cache"""
        self._cache.clear()
        self._cache_timestamps.clear()
        self.logger.info("Search cache cleared")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self._cache),
            'cache_entries': list(self._cache.keys()),
            'oldest_entry': min(self._cache_timestamps.values()) if self._cache_timestamps else None,
            'newest_entry': max(self._cache_timestamps.values()) if self._cache_timestamps else None
        }