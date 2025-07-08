import React, { useState, useEffect } from 'react';
import { apiClient, handleApiError } from '@/lib/api';
import { Bill, SearchResult } from '@/types';
import BillCard from './BillCard';
import { 
  sanitizeInput, 
  validateSearchQuery, 
  RateLimiter,
  sanitizeHtml,
  INPUT_LIMITS 
} from '@/utils/security';
import { useSecureForm, useSecurityLogger } from '@/contexts/SecurityContext';
import { useObservability } from '@/lib/observability';

// Rate limiter for search requests (development: 100 requests per minute)
const searchRateLimiter = new RateLimiter(60000, 100);

export default function SearchInterface() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [searchStats, setSearchStats] = useState<{
    total: number;
    method: string;
    duration?: number;
  } | null>(null);

  // Security hooks
  const secureForm = useSecureForm();
  const { logSecurityEvent } = useSecurityLogger();
  
  // Observability hooks
  const { recordInteraction, recordError, recordMetric, startTimer } = useObservability();

  const handleSearch = async (searchQuery: string) => {
    const stopTimer = startTimer('search_operation');
    
    // Clear previous errors
    setError(null);
    setValidationError(null);

    if (!searchQuery.trim()) {
      setResults([]);
      setSearchStats(null);
      recordInteraction({ type: 'search', element: 'search_input', value: '' });
      return;
    }

    // Record search attempt
    recordInteraction({ type: 'search', element: 'search_input', value: searchQuery });

    // Sanitize input
    const sanitizedQuery = sanitizeInput(searchQuery, INPUT_LIMITS.SEARCH_QUERY);
    
    // Validate input
    const validation = validateSearchQuery(sanitizedQuery);
    if (!validation.isValid) {
      setValidationError(validation.error || '無効な検索クエリです');
      setResults([]);
      setSearchStats(null);
      logSecurityEvent('invalid_input', { query: sanitizedQuery, error: validation.error });
      
      // Record validation error
      recordError({
        error: new Error(validation.error || 'Invalid search query'),
        context: 'search_validation',
        timestamp: Date.now(),
        additionalData: { query: sanitizedQuery }
      });
      
      stopTimer();
      return;
    }

    // Rate limiting check
    const clientId = 'search_' + (typeof window !== 'undefined' ? window.location.hostname : 'server');
    if (!searchRateLimiter.isAllowed(clientId)) {
      setError('検索回数の上限に達しました。しばらくお待ちください。');
      logSecurityEvent('rate_limit_exceeded', { clientId });
      
      // Record rate limit event
      recordError({
        error: new Error('Search rate limit exceeded'),
        context: 'search_rate_limit',
        timestamp: Date.now(),
        additionalData: { clientId }
      });
      
      stopTimer();
      return;
    }

    // Security check: ensure secure form is ready
    if (!secureForm.isReady) {
      setError('セキュリティの初期化中です。しばらくお待ちください。');
      stopTimer();
      return;
    }

    setLoading(true);
    
    const startTime = Date.now();

    try {
      const response: SearchResult = await apiClient.searchBills(sanitizedQuery, 20);
      
      if (response.success) {
        const duration = Date.now() - startTime;
        setResults(response.results);
        setSearchStats({
          total: response.total_found,
          method: response.results[0]?.search_method || 'unknown',
          duration,
        });

        // Record successful search metrics
        recordMetric({
          name: 'search.success',
          value: duration,
          timestamp: Date.now(),
          tags: {
            result_count: response.total_found.toString(),
            has_results: (response.total_found > 0).toString(),
            search_method: response.results[0]?.search_method || 'unknown'
          }
        });

        recordMetric({
          name: 'search.result_count',
          value: response.total_found,
          timestamp: Date.now(),
          tags: {
            query_length: sanitizedQuery.length.toString()
          }
        });

      } else {
        setError(sanitizeHtml(response.message || '検索に失敗しました'));
        setResults([]);
        setSearchStats(null);
        
        // Record search failure
        recordError({
          error: new Error(response.message || 'Search failed'),
          context: 'search_api_failure',
          timestamp: Date.now(),
          additionalData: { 
            query: sanitizedQuery,
            response: response.message
          }
        });
      }
    } catch (err) {
      setError(sanitizeHtml(handleApiError(err)));
      setResults([]);
      setSearchStats(null);
      
      // Record search error
      recordError({
        error: err as Error,
        context: 'search_exception',
        timestamp: Date.now(),
        additionalData: { query: sanitizedQuery }
      });
    } finally {
      setLoading(false);
      stopTimer();
    }
  };

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (query) {
        handleSearch(query);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch(query);
  };

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-2">
              法案や議事録を検索
            </label>
            <div className="relative">
              <input
                id="search"
                type="text"
                value={query}
                onChange={(e) => {
                  const input = e.target.value;
                  // Basic client-side length limiting
                  if (input.length <= INPUT_LIMITS.SEARCH_QUERY) {
                    setQuery(input);
                    setValidationError(null);
                  } else {
                    setValidationError(`検索クエリは${INPUT_LIMITS.SEARCH_QUERY}文字以内で入力してください`);
                  }
                }}
                placeholder="検索キーワードを入力してください..."
                className={`search-input ${validationError ? 'border-red-300 focus:border-red-500' : ''}`}
                aria-describedby="search-help"
                autoComplete="off"
                maxLength={INPUT_LIMITS.SEARCH_QUERY}
              />
              {loading && (
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  <div className="loading-dots">
                    <div></div>
                    <div></div>
                    <div></div>
                  </div>
                </div>
              )}
            </div>
            {validationError ? (
              <p className="mt-2 text-sm text-red-600" role="alert">
                {validationError}
              </p>
            ) : (
              <p id="search-help" className="mt-2 text-sm text-gray-600">
                例: 「税制改正」「社会保障」「予算」など（{INPUT_LIMITS.SEARCH_QUERY}文字まで）
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || !query.trim() || !!validationError}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '検索中...' : '検索する'}
          </button>
        </form>

        {/* Search Stats */}
        {searchStats && (
          <div className="mt-4 p-3 bg-gray-50 rounded-md">
            <p className="text-sm text-gray-600">
              {searchStats.total}件の結果が見つかりました
              {searchStats.method && (
                <span className="ml-2 text-xs text-gray-500">
                  ({searchStats.method === 'vector' ? 'AI検索' : 'キーワード検索'})
                </span>
              )}
              {searchStats.duration && (
                <span className="ml-2 text-xs text-gray-500">
                  ({searchStats.duration}ms)
                </span>
              )}
            </p>
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="card bg-red-50 border-red-200">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                検索エラー
              </h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Search Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">検索結果</h2>
          
          <div className="grid gap-4">
            {results.map((bill, index) => (
              <BillCard 
                key={`${bill.bill_number}-${index}`} 
                bill={bill} 
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {query && !loading && results.length === 0 && !error && (
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">検索結果が見つかりませんでした</h3>
          <p className="mt-1 text-sm text-gray-500">
            別のキーワードで検索してみてください
          </p>
        </div>
      )}
    </div>
  );
}