/**
 * Issue Search Component
 * Advanced search interface for dual-level policy issues
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { 
  MagnifyingGlassIcon,
  FunnelIcon,
  XMarkIcon,
  AdjustmentsHorizontalIcon,
  ChartBarIcon,
  CalendarIcon
} from '@heroicons/react/24/outline';
import { DualLevelToggle } from './DualLevelToggle';
import { IssueCard, Issue } from './IssueCard';

export interface SearchFilters {
  query: string;
  level?: 1 | 2;
  status: string;
  minConfidence: number;
  minQuality: number;
  billId?: string;
  dateFrom?: string;
  dateTo?: string;
  maxRecords: number;
}

export interface IssueSearchProps {
  onSearch: (filters: SearchFilters) => Promise<Issue[]>;
  initialFilters?: Partial<SearchFilters>;
  showAdvancedFilters?: boolean;
  className?: string;
}

const DEFAULT_FILTERS: SearchFilters = {
  query: '',
  status: 'approved',
  minConfidence: 0,
  minQuality: 0,
  maxRecords: 50
};

export const IssueSearch: React.FC<IssueSearchProps> = ({
  onSearch,
  initialFilters = {},
  showAdvancedFilters = false,
  className = ''
}) => {
  const [filters, setFilters] = useState<SearchFilters>({
    ...DEFAULT_FILTERS,
    ...initialFilters
  });
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(showAdvancedFilters);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<Issue[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Debounced search
  const [searchTimeout, setSearchTimeout] = useState<NodeJS.Timeout | null>(null);

  const handleFilterChange = useCallback(<K extends keyof SearchFilters>(
    key: K,
    value: SearchFilters[K]
  ) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const performSearch = useCallback(async (searchFilters: SearchFilters) => {
    if (!searchFilters.query.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    setSearchError(null);

    try {
      const results = await onSearch(searchFilters);
      setSearchResults(results);
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : '検索に失敗しました');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [onSearch]);

  // Debounced search trigger
  useEffect(() => {
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }

    const timeout = setTimeout(() => {
      if (filters.query.trim()) {
        performSearch(filters);
      }
    }, 500);

    setSearchTimeout(timeout);

    return () => {
      if (timeout) {
        clearTimeout(timeout);
      }
    };
  }, [filters, performSearch]);

  const handleClearFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
    setSearchResults([]);
    setSearchError(null);
  }, []);

  const handleToggleAdvanced = useCallback(() => {
    setIsAdvancedOpen(!isAdvancedOpen);
  }, [isAdvancedOpen]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.level) count++;
    if (filters.status !== 'approved') count++;
    if (filters.minConfidence > 0) count++;
    if (filters.minQuality > 0) count++;
    if (filters.billId) count++;
    if (filters.dateFrom) count++;
    if (filters.dateTo) count++;
    if (filters.maxRecords !== 50) count++;
    return count;
  }, [filters]);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Search Header */}
      <div className="bg-white rounded-lg border shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">政策課題検索</h2>
          
          <div className="flex items-center space-x-3">
            {/* Level Toggle */}
            {filters.level && (
              <DualLevelToggle
                currentLevel={filters.level}
                onLevelChange={(level) => handleFilterChange('level', level)}
              />
            )}
            
            {/* Advanced Filters Toggle */}
            <button
              onClick={handleToggleAdvanced}
              className={`
                flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors duration-150
                ${isAdvancedOpen 
                  ? 'text-blue-700 bg-blue-50 border border-blue-200' 
                  : 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'
                }
              `}
            >
              <AdjustmentsHorizontalIcon className="w-4 h-4 mr-2" />
              詳細フィルター
              {activeFilterCount > 0 && (
                <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                  {activeFilterCount}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Main Search Input */}
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={filters.query}
            onChange={(e) => handleFilterChange('query', e.target.value)}
            className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            placeholder="政策課題を検索（例：介護制度、環境保護、税制改革）"
          />
        </div>

        {/* Advanced Filters */}
        {isAdvancedOpen && (
          <div className="mt-6 border-t border-gray-100 pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Level Filter */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  表示レベル
                </label>
                <select
                  value={filters.level || ''}
                  onChange={(e) => handleFilterChange('level', e.target.value ? parseInt(e.target.value) as 1 | 2 : undefined)}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">すべて</option>
                  <option value="1">レベル1（高校生向け）</option>
                  <option value="2">レベル2（一般読者向け）</option>
                </select>
              </div>

              {/* Status Filter */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  承認状態
                </label>
                <select
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="approved">承認済み</option>
                  <option value="pending">審査中</option>
                  <option value="rejected">却下</option>
                  <option value="failed_validation">検証失敗</option>
                  <option value="">すべて</option>
                </select>
              </div>

              {/* Confidence Filter */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  最低信頼度 ({Math.round(filters.minConfidence * 100)}%)
                </label>
                <div className="flex items-center space-x-3">
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={filters.minConfidence}
                    onChange={(e) => handleFilterChange('minConfidence', parseFloat(e.target.value))}
                    className="flex-1"
                  />
                  <ChartBarIcon className="w-4 h-4 text-gray-400" />
                </div>
              </div>

              {/* Quality Filter */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  最低品質スコア ({Math.round(filters.minQuality * 100)}%)
                </label>
                <div className="flex items-center space-x-3">
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={filters.minQuality}
                    onChange={(e) => handleFilterChange('minQuality', parseFloat(e.target.value))}
                    className="flex-1"
                  />
                  <ChartBarIcon className="w-4 h-4 text-gray-400" />
                </div>
              </div>

              {/* Bill ID Filter */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  法案ID
                </label>
                <input
                  type="text"
                  value={filters.billId || ''}
                  onChange={(e) => handleFilterChange('billId', e.target.value || undefined)}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="例：bill_001"
                />
              </div>

              {/* Max Records */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  最大表示件数
                </label>
                <select
                  value={filters.maxRecords}
                  onChange={(e) => handleFilterChange('maxRecords', parseInt(e.target.value))}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value={10}>10件</option>
                  <option value={25}>25件</option>
                  <option value={50}>50件</option>
                  <option value={100}>100件</option>
                  <option value={200}>200件</option>
                </select>
              </div>
            </div>

            {/* Date Range Filters */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  作成日（開始）
                </label>
                <div className="relative">
                  <input
                    type="date"
                    value={filters.dateFrom || ''}
                    onChange={(e) => handleFilterChange('dateFrom', e.target.value || undefined)}
                    className="block w-full px-3 py-2 pl-10 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  <CalendarIcon className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  作成日（終了）
                </label>
                <div className="relative">
                  <input
                    type="date"
                    value={filters.dateTo || ''}
                    onChange={(e) => handleFilterChange('dateTo', e.target.value || undefined)}
                    className="block w-full px-3 py-2 pl-10 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  <CalendarIcon className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                </div>
              </div>
            </div>

            {/* Filter Actions */}
            <div className="mt-6 flex items-center justify-between">
              <button
                onClick={handleClearFilters}
                className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors duration-150"
              >
                <XMarkIcon className="w-4 h-4 mr-2" />
                フィルターをクリア
              </button>

              <div className="text-sm text-gray-600">
                {activeFilterCount > 0 && `${activeFilterCount}個のフィルターが適用中`}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Search Results */}
      <div className="space-y-4">
        {/* Results Header */}
        {(filters.query.trim() || searchResults.length > 0 || searchError) && (
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h3 className="text-lg font-medium text-gray-900">検索結果</h3>
              {isSearching && (
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent"></div>
                  <span>検索中...</span>
                </div>
              )}
            </div>
            
            {searchResults.length > 0 && (
              <div className="text-sm text-gray-600">
                {searchResults.length}件の課題が見つかりました
              </div>
            )}
          </div>
        )}

        {/* Error State */}
        {searchError && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <XMarkIcon className="h-5 w-5 text-red-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">検索エラー</h3>
                <div className="mt-2 text-sm text-red-700">{searchError}</div>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!isSearching && !searchError && filters.query.trim() && searchResults.length === 0 && (
          <div className="bg-gray-50 rounded-lg p-8 text-center">
            <MagnifyingGlassIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">検索結果がありません</h3>
            <p className="text-gray-600 mb-4">
              「{filters.query}」に一致する政策課題が見つかりませんでした。
            </p>
            <button
              onClick={handleClearFilters}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 transition-colors duration-150"
            >
              検索条件をリセット
            </button>
          </div>
        )}

        {/* Results List */}
        {searchResults.length > 0 && (
          <div className="space-y-4">
            {searchResults.map((issue) => (
              <IssueCard
                key={issue.issue_id}
                issue={issue}
                currentLevel={filters.level || 1}
                showDetails={false}
                className="transition-all duration-200 hover:shadow-md"
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Hook for search functionality
 */
export const useIssueSearch = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (filters: SearchFilters): Promise<Issue[]> => {
    setIsLoading(true);
    setError(null);

    try {
      const queryParams = new URLSearchParams();
      
      if (filters.query) queryParams.append('query', filters.query);
      if (filters.level) queryParams.append('level', filters.level.toString());
      if (filters.status) queryParams.append('status', filters.status);
      if (filters.minConfidence > 0) queryParams.append('min_confidence', filters.minConfidence.toString());
      if (filters.minQuality > 0) queryParams.append('min_quality', filters.minQuality.toString());
      if (filters.billId) queryParams.append('bill_id', filters.billId);
      if (filters.dateFrom) queryParams.append('date_from', filters.dateFrom);
      if (filters.dateTo) queryParams.append('date_to', filters.dateTo);
      queryParams.append('max_records', filters.maxRecords.toString());

      const response = await fetch(`/api/issues/search?${queryParams.toString()}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(filters),
      });

      if (!response.ok) {
        throw new Error('Search request failed');
      }

      const data = await response.json();
      return data.results || [];
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    search,
    isLoading,
    error,
    clearError: () => setError(null)
  };
};

export default IssueSearch;