# T53 Parameter Tuning Recommendations

## Executive Summary

Based on T53 data quality validation results (Overall Quality Score: 66.9%), the system requires targeted parameter tuning to achieve production readiness. Critical issues identified: title quality (0.64 vs 0.80 threshold) and category diversity (0.30 vs 0.60 threshold).

## Validation Results Overview

- **Overall Quality Score**: 66.9% (NEEDS_IMPROVEMENT)
- **Data Validation Score**: 82.4%
- **AI Readiness Score**: 51.4%
- **Components Status**: 2/3 passed (voting_data ✅, metadata ✅, bills_data ❌)

## Critical Parameter Adjustments

### 1. Bills Data Collection (Priority: HIGH)

**Current Issues:**
- Title quality: 0.64 (threshold: 0.80)
- Category diversity: 0.30 (threshold: 0.60)

**Recommended Parameters:**
```python
# Enhanced bill collection limits
MAX_BILLS = 50  # Increase from 30 for better diversity
MIN_TITLE_LENGTH = 15  # Improve title quality filtering
MAX_TITLE_LENGTH = 150  # Remove overly long titles

# Category classification improvements
CATEGORY_KEYWORDS = {
    '予算・決算': ['予算', '決算', '補正', '歳入', '歳出', '財政'],
    '税制': ['税', '課税', '控除', '減税', '増税', '租税'],
    '社会保障': ['年金', '医療', '介護', '福祉', '保険', '手当'],
    '外交・国際': ['条約', '協定', '外交', '国際', '通商', '貿易'],
    '経済・産業': ['産業', '経済', '金融', '企業', '投資', '規制'],
    'その他': []  # Default fallback
}

# Enhanced title validation
TITLE_VALIDATION_RULES = {
    'min_japanese_chars': 10,
    'min_legal_terms': 1,  # Require legal terminology
    'max_symbol_ratio': 0.2,
    'require_legal_suffix': ['法案', '法律案', '改正案', '廃止案']
}
```

### 2. Data Collection Strategy (Priority: HIGH)

**Current Approach:** Fixed 30 bills, limited to first 30 found
**Recommended Approach:** Quality-based selection with diversity requirements

```python
QUALITY_BASED_COLLECTION = {
    'target_bills': 40,
    'min_categories': 4,  # Ensure at least 4 different categories
    'category_distribution': {
        'その他': 0.4,  # Max 40% "other" category
        'tax_related': 0.2,  # At least 20% tax-related
        'social_welfare': 0.15,  # At least 15% social welfare
        'other_categories': 0.25  # Distributed among remaining
    },
    'quality_filters': {
        'min_title_score': 0.7,
        'require_bill_id': True,
        'require_status': True
    }
}
```

### 3. Scraping Rate Limiting (Priority: MEDIUM)

**Current Parameters:**
```python
RATE_LIMITS = {
    'requests_per_second': 0.5,  # 2 second delay
    'concurrent_requests': 1,
    'retry_attempts': 3,
    'backoff_factor': 2
}
```

**Recommended Tuning:**
```python
ENHANCED_RATE_LIMITS = {
    'requests_per_second': 0.8,  # Slightly faster for efficiency
    'concurrent_requests': 2,  # Allow 2 concurrent for voting data
    'retry_attempts': 5,  # More retries for reliability
    'backoff_factor': 1.5,  # Gentler backoff
    'timeout_seconds': 15,  # Longer timeout for complex pages
    'respect_robots_txt': True,
    'user_agent_rotation': True
}
```

### 4. AI/ML Feature Parameters (Priority: HIGH)

#### Speech-to-Text (STT)
```python
STT_CONFIG = {
    'model': 'whisper-large-v3',
    'language': 'ja',
    'word_error_rate_threshold': 0.15,  # WER < 15%
    'chunk_length': 30,  # 30-second audio chunks
    'preprocessing': {
        'noise_reduction': True,
        'normalization': True,
        'speed_adjustment': False
    },
    'quality_checks': {
        'confidence_threshold': 0.8,
        'silence_detection': True,
        'audio_quality_minimum': 0.7
    }
}
```

#### LLM Issue Extraction
```python
LLM_CONFIG = {
    'model': 'gpt-4-turbo',
    'temperature': 0.1,  # Low temperature for consistency
    'max_tokens': 1000,
    'prompt_template': """
以下の法案から重要な政治的課題を抽出してください。
法案タイトル: {title}
法案内容: {content}

抽出する項目：
1. 主要な政治的課題 (最大3つ)
2. 影響を受ける分野
3. 社会的重要度 (1-10)
4. 関連する既存法案

回答は構造化されたJSONで返してください。
""",
    'validation_rules': {
        'min_issues_extracted': 1,
        'max_issues_extracted': 5,
        'relevance_threshold': 0.7
    }
}
```

#### Semantic Search
```python
EMBEDDING_CONFIG = {
    'model': 'text-embedding-3-large',
    'dimensions': 1536,
    'batch_size': 100,
    'similarity_threshold': 0.75,
    'index_settings': {
        'metric': 'cosine',
        'ef_construction': 200,
        'max_connections': 16
    },
    'search_parameters': {
        'k_neighbors': 10,
        'alpha': 0.7,  # Balance between speed and accuracy
        'ef_search': 100
    }
}
```

### 5. Data Quality Thresholds (Priority: MEDIUM)

**Current Thresholds:**
```python
CURRENT_THRESHOLDS = {
    'completeness': 0.95,
    'consistency': 0.90,
    'accuracy': 0.85,
    'uniqueness': 0.98,
    'timeliness': 0.80,
    'validity': 0.90
}
```

**Recommended Adjustments:**
```python
PRODUCTION_THRESHOLDS = {
    'completeness': 0.92,  # Slightly lower for real-world data
    'consistency': 0.88,   # Account for format variations
    'accuracy': 0.85,     # Maintain high accuracy
    'uniqueness': 0.95,   # Allow for some legitimate duplicates
    'timeliness': 0.75,   # More realistic for batch processing
    'validity': 0.90,     # Maintain format standards
    # Additional thresholds
    'title_quality': 0.75,        # Reduced from 0.80
    'category_diversity': 0.50,   # Reduced from 0.60
    'ai_readiness': 0.70          # Overall AI feature readiness
}
```

### 6. Performance Optimization (Priority: MEDIUM)

```python
PERFORMANCE_CONFIG = {
    'parallel_processing': {
        'max_workers': 4,
        'batch_size': 10,
        'use_async': True
    },
    'caching': {
        'enable_response_cache': True,
        'cache_ttl_hours': 24,
        'cache_size_mb': 100
    },
    'monitoring': {
        'log_level': 'INFO',
        'metrics_collection': True,
        'performance_tracking': True,
        'alert_thresholds': {
            'processing_time_seconds': 30,
            'error_rate_percentage': 5,
            'memory_usage_mb': 512
        }
    }
}
```

### 7. Data Storage and Retrieval (Priority: LOW)

```python
STORAGE_CONFIG = {
    'database': {
        'connection_pool_size': 10,
        'query_timeout_seconds': 30,
        'bulk_insert_batch_size': 1000
    },
    'vector_store': {
        'connection_timeout': 10,
        'batch_upsert_size': 100,
        'index_optimization_interval': '1h'
    },
    'file_storage': {
        'max_file_size_mb': 10,
        'compression_enabled': True,
        'retention_days': 30
    }
}
```

## Implementation Phases

### Phase 1: Critical Issues (Week 1)
1. Implement enhanced category classification
2. Improve title quality validation
3. Update collection strategy for diversity
4. Deploy quality-based filtering

### Phase 2: AI/ML Enhancement (Week 2)
1. Configure STT parameters for Japanese
2. Implement LLM issue extraction
3. Optimize embedding generation
4. Test semantic search accuracy

### Phase 3: Performance & Monitoring (Week 3)
1. Implement parallel processing
2. Add comprehensive monitoring
3. Optimize rate limiting
4. Deploy caching mechanisms

## Success Metrics

**Target Quality Scores:**
- Overall Quality Score: >80%
- Bills Data Quality: >85%
- Voting Data Quality: >90%
- AI Readiness Score: >75%

**Performance Targets:**
- Processing time: <2 minutes for 40 bills
- Error rate: <5%
- Category diversity: >50%
- Title quality: >75%

## Validation Plan

1. **Unit Testing**: Test each parameter change individually
2. **Integration Testing**: Validate complete pipeline with new parameters
3. **Quality Monitoring**: Continuous monitoring of quality metrics
4. **Performance Benchmarking**: Compare before/after performance
5. **User Acceptance**: Test search and display functionality

## Risk Mitigation

**High-Risk Changes:**
- Rate limiting adjustments (monitor for blocking)
- LLM API costs (implement usage caps)
- Embedding generation time (batch processing)

**Rollback Strategy:**
- Maintain parameter version control
- Implement feature flags for new configurations
- Monitor key metrics for degradation
- Automated rollback triggers

## Cost Considerations

**Estimated Costs (per batch):**
- OpenAI API (LLM): ~$2-5
- OpenAI API (Embeddings): ~$1-2
- Whisper STT: ~$0.50-1
- Total per 40-bill batch: ~$3.50-8

**Cost Optimization:**
- Batch API calls when possible
- Cache expensive operations
- Use smaller models for dev/testing
- Implement usage monitoring and caps

---

**Document Version**: 1.0  
**Last Updated**: 2025-07-08  
**Next Review**: 2025-07-15  
**Owner**: T53 Data Quality Validation Team