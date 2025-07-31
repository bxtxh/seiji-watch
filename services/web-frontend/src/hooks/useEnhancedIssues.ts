/**
 * Enhanced Issues Hook
 * Provides state management and API integration for dual-level policy issues
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { Issue } from "../components/issues/IssueCard";
import { SearchFilters } from "../components/issues/IssueSearch";

export interface IssueFilters {
  level?: 1 | 2;
  status: string;
  billId?: string;
  maxRecords: number;
}

export interface IssueStats {
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
  unique_bills_count: number;
}

export interface UseEnhancedIssuesOptions {
  initialFilters?: Partial<IssueFilters>;
  autoLoad?: boolean;
  pollingInterval?: number;
}

export interface UseEnhancedIssuesReturn {
  // Data state
  issues: Issue[];
  stats: IssueStats | null;

  // Loading states
  loading: boolean;
  error: string | null;

  // Filters
  filters: IssueFilters;
  setFilters: (filters: Partial<IssueFilters>) => void;

  // Actions
  loadIssues: () => Promise<void>;
  loadStats: () => Promise<void>;
  searchIssues: (searchFilters: SearchFilters) => Promise<Issue[]>;
  updateIssueStatus: (
    issueId: string,
    status: string,
    notes?: string
  ) => Promise<void>;
  extractIssuesFromBill: (billData: any) => Promise<any>;

  // Utilities
  refresh: () => Promise<void>;
  clearError: () => void;

  // Computed values
  filteredIssues: Issue[];
  hasNextPage: boolean;
  isEmpty: boolean;
}

const DEFAULT_FILTERS: IssueFilters = {
  status: "approved",
  maxRecords: 50,
};

export const useEnhancedIssues = (
  options: UseEnhancedIssuesOptions = {}
): UseEnhancedIssuesReturn => {
  const { initialFilters = {}, autoLoad = true, pollingInterval } = options;

  // State
  const [issues, setIssues] = useState<Issue[]>([]);
  const [stats, setStats] = useState<IssueStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFiltersState] = useState<IssueFilters>({
    ...DEFAULT_FILTERS,
    ...initialFilters,
  });

  // Filters management
  const setFilters = useCallback((newFilters: Partial<IssueFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...newFilters }));
  }, []);

  // Load issues
  const loadIssues = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();

      if (filters.level) params.append("level", filters.level.toString());
      if (filters.status) params.append("status", filters.status);
      if (filters.billId) params.append("bill_id", filters.billId);
      params.append("max_records", filters.maxRecords.toString());

      const response = await fetch(`/api/issues?${params.toString()}`);

      if (!response.ok) {
        throw new Error(
          `Failed to load issues: ${response.status} ${response.statusText}`
        );
      }

      const data = await response.json();
      setIssues(data.issues || []);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Unknown error occurred";
      setError(errorMessage);
      console.error("Failed to load issues:", err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Load statistics
  const loadStats = useCallback(async () => {
    try {
      const response = await fetch("/api/issues/statistics");

      if (!response.ok) {
        throw new Error("Failed to load statistics");
      }

      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error("Failed to load statistics:", err);
      // Don't set error state for stats failure as it's not critical
    }
  }, []);

  // Search issues
  const searchIssues = useCallback(
    async (searchFilters: SearchFilters): Promise<Issue[]> => {
      const searchBody = {
        query: searchFilters.query,
        level: searchFilters.level,
        status: searchFilters.status,
        max_records: searchFilters.maxRecords,
        ...(searchFilters.minConfidence > 0 && {
          min_confidence: searchFilters.minConfidence,
        }),
        ...(searchFilters.minQuality > 0 && {
          min_quality: searchFilters.minQuality,
        }),
        ...(searchFilters.billId && { bill_id: searchFilters.billId }),
        ...(searchFilters.dateFrom && { date_from: searchFilters.dateFrom }),
        ...(searchFilters.dateTo && { date_to: searchFilters.dateTo }),
      };

      const response = await fetch("/api/issues/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(searchBody),
      });

      if (!response.ok) {
        throw new Error(
          `Search failed: ${response.status} ${response.statusText}`
        );
      }

      const data = await response.json();
      return data.results || [];
    },
    []
  );

  // Update issue status
  const updateIssueStatus = useCallback(
    async (issueId: string, status: string, notes?: string) => {
      try {
        const response = await fetch(`/api/issues/${issueId}/status`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            status,
            reviewer_notes: notes || `Status changed to ${status}`,
          }),
        });

        if (!response.ok) {
          throw new Error(
            `Failed to update status: ${response.status} ${response.statusText}`
          );
        }

        // Update local state
        setIssues((prev) =>
          prev.map((issue) =>
            issue.record_id === issueId
              ? { ...issue, status: status as any, reviewer_notes: notes }
              : issue
          )
        );

        // Reload stats to reflect changes
        await loadStats();
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to update status";
        setError(errorMessage);
        throw err;
      }
    },
    [loadStats]
  );

  // Extract issues from bill
  const extractIssuesFromBill = useCallback(
    async (billData: any) => {
      try {
        const response = await fetch("/api/issues/extract", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(billData),
        });

        if (!response.ok) {
          throw new Error(
            `Failed to extract issues: ${response.status} ${response.statusText}`
          );
        }

        const data = await response.json();

        // Reload issues and stats to include new extractions
        await Promise.all([loadIssues(), loadStats()]);

        return data;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to extract issues";
        setError(errorMessage);
        throw err;
      }
    },
    [loadIssues, loadStats]
  );

  // Refresh all data
  const refresh = useCallback(async () => {
    await Promise.all([loadIssues(), loadStats()]);
  }, [loadIssues, loadStats]);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Computed values
  const filteredIssues = useMemo(() => {
    let filtered = [...issues];

    // Apply client-side filtering if needed
    if (filters.level) {
      filtered = filtered.filter((issue) => issue.level === filters.level);
    }

    return filtered;
  }, [issues, filters]);

  const hasNextPage = useMemo(() => {
    return issues.length === filters.maxRecords;
  }, [issues.length, filters.maxRecords]);

  const isEmpty = useMemo(() => {
    return !loading && filteredIssues.length === 0;
  }, [loading, filteredIssues.length]);

  // Auto-load on mount and filter changes
  useEffect(() => {
    if (autoLoad) {
      loadIssues();
    }
  }, [loadIssues, autoLoad]);

  // Load stats on mount
  useEffect(() => {
    if (autoLoad) {
      loadStats();
    }
  }, [loadStats, autoLoad]);

  // Polling
  useEffect(() => {
    if (pollingInterval && pollingInterval > 0) {
      const interval = setInterval(() => {
        refresh();
      }, pollingInterval);

      return () => clearInterval(interval);
    }
  }, [pollingInterval, refresh]);

  return {
    // Data state
    issues: filteredIssues,
    stats,

    // Loading states
    loading,
    error,

    // Filters
    filters,
    setFilters,

    // Actions
    loadIssues,
    loadStats,
    searchIssues,
    updateIssueStatus,
    extractIssuesFromBill,

    // Utilities
    refresh,
    clearError,

    // Computed values
    filteredIssues,
    hasNextPage,
    isEmpty,
  };
};

/**
 * Hook for managing issue tree data
 */
export interface IssueTreeNode {
  record_id: string;
  issue_id: string;
  label_lv1: string;
  label_lv2?: string;
  confidence: number;
  source_bill_id: string;
  quality_score: number;
  status: string;
  created_at: string;
  children: IssueTreeNode[];
}

export const useIssueTree = () => {
  const [treeData, setTreeData] = useState<IssueTreeNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTreeData = useCallback(async (status: string = "approved") => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/issues/tree?status=${status}`);

      if (!response.ok) {
        throw new Error("Failed to load tree data");
      }

      const data = await response.json();
      setTreeData(data.tree || []);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load tree data";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    treeData,
    loading,
    error,
    loadTreeData,
    refresh: () => loadTreeData(),
  };
};

/**
 * Hook for issue extraction workflow
 */
export const useIssueExtraction = () => {
  const [extracting, setExtracting] = useState(false);
  const [extractionResults, setExtractionResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const extractSingle = useCallback(async (billData: any) => {
    setExtracting(true);
    setError(null);

    try {
      const response = await fetch("/api/issues/extract", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(billData),
      });

      if (!response.ok) {
        throw new Error("Extraction failed");
      }

      const result = await response.json();
      setExtractionResults(result);
      return result;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Extraction failed";
      setError(errorMessage);
      throw err;
    } finally {
      setExtracting(false);
    }
  }, []);

  const extractBatch = useCallback(async (billsData: any[]) => {
    setExtracting(true);
    setError(null);

    try {
      const response = await fetch("/api/issues/extract/batch", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(billsData),
      });

      if (!response.ok) {
        throw new Error("Batch extraction failed");
      }

      const result = await response.json();
      setExtractionResults(result);
      return result;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Batch extraction failed";
      setError(errorMessage);
      throw err;
    } finally {
      setExtracting(false);
    }
  }, []);

  return {
    extracting,
    extractionResults,
    error,
    extractSingle,
    extractBatch,
    clearResults: () => setExtractionResults(null),
    clearError: () => setError(null),
  };
};

export default useEnhancedIssues;
