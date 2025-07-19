/**
 * Enhanced Issues Page
 * Main page for browsing and managing dual-level policy issues
 */

import React, { useState, useEffect, useCallback } from "react";
import { NextPage } from "next";
import Head from "next/head";
import { 
  Bars3Icon,
  ListBulletIcon,
  FunnelIcon,
  ArrowPathIcon,
  ChartBarIcon
} from "@heroicons/react/24/outline";

import { DualLevelToggle, useDualLevel } from "../../components/issues/DualLevelToggle";
import { IssueCard, CompactIssueCard, Issue } from "../../components/issues/IssueCard";
import { IssueTreeView, useIssueTree } from "../../components/issues/IssueTreeView";
import { IssueSearch, useIssueSearch, SearchFilters } from "../../components/issues/IssueSearch";

type ViewMode = "list" | "tree" | "search";

interface IssueStats {
  total_issues: number;
  approved_count: number;
  pending_count: number;
  rejected_count: number;
  failed_validation_count: number;
  by_level: {
    lv1: number;
    lv2: number;
  };
  average_confidence: number;
  average_quality_score: number;
}

const EnhancedIssuesPage: NextPage = () => {
  const { level, setLevel } = useDualLevel(1);
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<IssueStats | null>(null);
  const [statusFilter, setStatusFilter] = useState("approved");
  const [maxRecords, setMaxRecords] = useState(50);

  // Hooks for different view modes
  const { treeData, loading: treeLoading, loadTreeData } = useIssueTree();
  const { search, isLoading: searchLoading } = useIssueSearch();

  // Load issues for list view
  const loadIssues = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        level: level.toString(),
        status: statusFilter,
        max_records: maxRecords.toString()
      });

      const response = await fetch(`/api/issues?${params.toString()}`);
      
      if (!response.ok) {
        throw new Error("Failed to load issues");
      }

      const data = await response.json();
      setIssues(data.issues || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [level, statusFilter, maxRecords]);

  // Load statistics
  const loadStats = useCallback(async () => {
    try {
      const response = await fetch("/api/issues/statistics");
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to load statistics:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadIssues();
    loadStats();
  }, [loadIssues, loadStats]);

  // Load tree data when switching to tree view
  useEffect(() => {
    if (viewMode === 'tree') {
      loadTreeData(statusFilter);
    }
  }, [viewMode, statusFilter, loadTreeData]);

  // Handle issue status change
  const handleStatusChange = useCallback(async (issueId: string, newStatus: string) => {
    try {
      const response = await fetch(`/api/issues/${issueId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          status: newStatus,
          reviewer_notes: `Status changed to ${newStatus}`
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update status');
      }

      // Refresh data
      if (viewMode === 'list') {
        await loadIssues();
      } else if (viewMode === 'tree') {
        await loadTreeData(statusFilter);
      }
      
      await loadStats();
    } catch (err) {
      console.error('Failed to update status:', err);
      alert('ステータスの更新に失敗しました');
    }
  }, [viewMode, loadIssues, loadTreeData, statusFilter, loadStats]);

  // Handle search
  const handleSearch = useCallback(async (filters: SearchFilters): Promise<Issue[]> => {
    return await search(filters);
  }, [search]);

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    if (viewMode === 'list') {
      await loadIssues();
    } else if (viewMode === 'tree') {
      await loadTreeData(statusFilter);
    }
    await loadStats();
  }, [viewMode, loadIssues, loadTreeData, statusFilter, loadStats]);

  const isAnyLoading = loading || treeLoading || searchLoading;

  return (
    <>
      <Head>
        <title>政策課題一覧（強化版） - Seiji Watch</title>
        <meta name="description" content="抽出された政策課題を閲覧・管理します。高校生向けと一般読者向けの2レベルで表示できます。" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Page Header */}
          <div className="mb-8">
            <div className="md:flex md:items-center md:justify-between">
              <div className="flex-1 min-w-0">
                <h1 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
                  政策課題一覧（強化版）
                </h1>
                <div className="mt-1 flex flex-col sm:flex-row sm:flex-wrap sm:mt-0 sm:space-x-6">
                  <div className="mt-2 flex items-center text-sm text-gray-500">
                    <ChartBarIcon className="flex-shrink-0 mr-1.5 h-5 w-5 text-gray-400" />
                    {stats && `総数: ${stats.total_issues}件`}
                  </div>
                  {stats && (
                    <>
                      <div className="mt-2 flex items-center text-sm text-green-600">
                        承認: {stats.approved_count}件
                      </div>
                      <div className="mt-2 flex items-center text-sm text-yellow-600">
                        審査中: {stats.pending_count}件
                      </div>
                      {stats.rejected_count > 0 && (
                        <div className="mt-2 flex items-center text-sm text-red-600">
                          却下: {stats.rejected_count}件
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
              <div className="mt-4 flex md:mt-0 md:ml-4">
                <button
                  onClick={handleRefresh}
                  disabled={isAnyLoading}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  <ArrowPathIcon className={`-ml-1 mr-2 h-5 w-5 ${isAnyLoading ? 'animate-spin' : ''}`} />
                  更新
                </button>
              </div>
            </div>
          </div>

          {/* Controls */}
          <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
              {/* View Mode Selector */}
              <div className="flex items-center space-x-3">
                <span className="text-sm font-medium text-gray-700">表示方法:</span>
                <div className="flex bg-gray-100 rounded-lg p-1">
                  <button
                    onClick={() => setViewMode('list')}
                    className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors duration-150 ${
                      viewMode === 'list'
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <ListBulletIcon className="w-4 h-4 mr-2" />
                    リスト
                  </button>
                  <button
                    onClick={() => setViewMode('tree')}
                    className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors duration-150 ${
                      viewMode === 'tree'
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <Bars3Icon className="w-4 h-4 mr-2" />
                    ツリー
                  </button>
                  <button
                    onClick={() => setViewMode('search')}
                    className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors duration-150 ${
                      viewMode === 'search'
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <FunnelIcon className="w-4 h-4 mr-2" />
                    検索
                  </button>
                </div>
              </div>

              {/* Level Toggle and Filters */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center space-y-3 sm:space-y-0 sm:space-x-4">
                {/* Status Filter */}
                {viewMode !== 'search' && (
                  <div className="flex items-center space-x-2">
                    <label className="text-sm font-medium text-gray-700">状態:</label>
                    <select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="approved">承認済み</option>
                      <option value="pending">審査中</option>
                      <option value="rejected">却下</option>
                      <option value="">すべて</option>
                    </select>
                  </div>
                )}

                {/* Max Records */}
                {viewMode === 'list' && (
                  <div className="flex items-center space-x-2">
                    <label className="text-sm font-medium text-gray-700">件数:</label>
                    <select
                      value={maxRecords}
                      onChange={(e) => setMaxRecords(parseInt(e.target.value))}
                      className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value={25}>25件</option>
                      <option value={50}>50件</option>
                      <option value={100}>100件</option>
                      <option value={200}>200件</option>
                    </select>
                  </div>
                )}

                {/* Level Toggle */}
                {viewMode !== 'search' && (
                  <DualLevelToggle
                    currentLevel={level}
                    onLevelChange={setLevel}
                  />
                )}
              </div>
            </div>
          </div>

          {/* Content Area */}
          <div className="space-y-6">
            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <div className="flex">
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">エラーが発生しました</h3>
                    <div className="mt-2 text-sm text-red-700">{error}</div>
                  </div>
                </div>
              </div>
            )}

            {/* List View */}
            {viewMode === 'list' && (
              <div className="space-y-4">
                {loading ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent mx-auto mb-4"></div>
                    <p className="text-gray-600">読み込み中...</p>
                  </div>
                ) : issues.length === 0 ? (
                  <div className="text-center py-12">
                    <ListBulletIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">政策課題がありません</h3>
                    <p className="text-gray-600">指定された条件に一致する課題が見つかりませんでした。</p>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between">
                      <h2 className="text-lg font-medium text-gray-900">
                        {issues.length}件の政策課題
                      </h2>
                      <div className="text-sm text-gray-600">
                        レベル{level} ({level === 1 ? '高校生向け' : '一般読者向け'})
                      </div>
                    </div>
                    
                    {issues.map((issue) => (
                      <IssueCard
                        key={issue.issue_id}
                        issue={issue}
                        currentLevel={level}
                        onStatusChange={handleStatusChange}
                        className="transition-all duration-200 hover:shadow-md"
                      />
                    ))}
                  </>
                )}
              </div>
            )}

            {/* Tree View */}
            {viewMode === 'tree' && (
              <IssueTreeView
                treeData={treeData}
                currentLevel={level}
                onLevelChange={setLevel}
                onStatusChange={handleStatusChange}
                expandAll={false}
                showCompact={false}
              />
            )}

            {/* Search View */}
            {viewMode === 'search' && (
              <IssueSearch
                onSearch={handleSearch}
                initialFilters={{ level, status: statusFilter }}
                showAdvancedFilters={true}
              />
            )}
          </div>

          {/* Statistics Panel */}
          {stats && (
            <div className="mt-8 bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">統計情報</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{stats.by_level.lv1}</div>
                  <div className="text-sm text-gray-600">レベル1課題</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{stats.by_level.lv2}</div>
                  <div className="text-sm text-gray-600">レベル2課題</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {Math.round(stats.average_confidence * 100)}%
                  </div>
                  <div className="text-sm text-gray-600">平均信頼度</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {Math.round(stats.average_quality_score * 100)}%
                  </div>
                  <div className="text-sm text-gray-600">平均品質</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default EnhancedIssuesPage;