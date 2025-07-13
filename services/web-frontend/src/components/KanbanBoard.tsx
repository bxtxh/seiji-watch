import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/router';
import IssueCard, { KanbanIssue } from './IssueCard';
import StageColumn from './StageColumn';
import { useIntersectionObserver } from '../hooks/useIntersectionObserver';

// Types for Kanban data
interface KanbanData {
  metadata: {
    total_issues: number;
    last_updated: string;
    date_range: {
      from: string;
      to: string;
    };
  };
  stages: {
    審議前: KanbanIssue[];
    審議中: KanbanIssue[];
    採決待ち: KanbanIssue[];
    成立: KanbanIssue[];
  };
}

// Skeleton Loading Component
function KanbanSkeleton() {
  return (
    <div className="grid grid-flow-col auto-cols-[300px] gap-6 overflow-x-auto pb-4">
      {[1, 2, 3, 4].map((stage) => (
        <div key={stage} className="space-y-4">
          <div className="h-6 bg-gray-200 rounded animate-pulse"></div>
          {[1, 2, 3].map((card) => (
            <div key={card} className="bg-white rounded-xl p-4 space-y-3 shadow-sm">
              <div className="h-4 bg-gray-200 rounded animate-pulse"></div>
              <div className="h-3 bg-gray-200 rounded animate-pulse w-3/4"></div>
              <div className="flex gap-2">
                <div className="h-5 w-12 bg-gray-200 rounded animate-pulse"></div>
                <div className="h-5 w-12 bg-gray-200 rounded animate-pulse"></div>
              </div>
              <div className="space-y-2">
                <div className="h-8 bg-gray-100 rounded animate-pulse"></div>
                <div className="h-8 bg-gray-100 rounded animate-pulse"></div>
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// Main Kanban Board Component
interface KanbanBoardProps {
  className?: string;
}

export default function KanbanBoard({ className = '' }: KanbanBoardProps) {
  const [kanbanData, setKanbanData] = useState<KanbanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { ref: kanbanRef, hasIntersected } = useIntersectionObserver({
    threshold: 0.1,
    rootMargin: '100px'
  });

  // Fetch Kanban data only when component becomes visible
  useEffect(() => {
    if (!hasIntersected) return;

    const fetchKanbanData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch('http://localhost:8000/api/issues/kanban?range=30d&max_per_stage=8');
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        setKanbanData(data);
        
      } catch (err) {
        console.error('Failed to fetch Kanban data:', err);
        setError(err instanceof Error ? err.message : 'データの取得に失敗しました');
      } finally {
        setLoading(false);
      }
    };

    fetchKanbanData();
  }, [hasIntersected]);

  const router = useRouter();

  // Handle card click with prefetching
  const handleCardClick = useCallback((issue: KanbanIssue) => {
    // Navigate to issue detail page using Next.js router
    router.push(`/issues/${issue.id}`);
  }, [router]);

  // Prefetch issue details on hover
  const handleCardHover = useCallback((issue: KanbanIssue) => {
    // Prefetch issue detail page using Next.js router
    router.prefetch(`/issues/${issue.id}`);
  }, [router]);

  // Memoize stage columns rendering - always call this hook
  const stageColumns = useMemo(() => {
    if (!kanbanData) return null;
    
    return Object.keys(kanbanData.stages).map((stageKey) => (
      <StageColumn
        key={stageKey}
        stageKey={stageKey}
        issues={kanbanData.stages[stageKey as keyof typeof kanbanData.stages] || []}
        onCardClick={handleCardClick}
        onCardHover={handleCardHover}
      />
    ));
  }, [kanbanData, handleCardClick, handleCardHover]);

  if (error) {
    return (
      <div className={`${className}`}>
        <div className="text-center py-8">
          <div className="text-red-600 text-sm mb-2">エラーが発生しました</div>
          <div className="text-gray-600 text-sm">{error}</div>
          <button 
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark text-sm"
          >
            再読み込み
          </button>
        </div>
      </div>
    );
  }

  return (
    <section ref={kanbanRef} className={`${className}`} aria-label="国会イシュー Kanban ボード">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">直近1ヶ月の議論</h2>
          <p className="text-sm text-gray-600 mt-1">
            {kanbanData ? `${kanbanData.metadata.total_issues}件のイシューを表示中` : '読み込み中...'}
          </p>
        </div>
        <span className="text-sm text-gray-500 hidden md:block">
          ← 横スクロールで確認 →
        </span>
      </div>

      {/* Kanban Board */}
      <div className="overflow-x-auto pb-8" role="list" aria-label="ステージ別イシュー一覧">
        {loading ? (
          <KanbanSkeleton />
        ) : stageColumns ? (
          <div className="grid grid-flow-col auto-cols-[300px] md:auto-cols-[320px] gap-6 snap-x snap-mandatory">
            {stageColumns}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            データが見つかりませんでした
          </div>
        )}
      </div>

      {/* Metadata */}
      {kanbanData && (
        <div className="mt-4 text-xs text-gray-500 text-center">
          最終更新: {new Date(kanbanData.metadata.last_updated).toLocaleString('ja-JP')} |{' '}
          対象期間: {kanbanData.metadata.date_range.from} 〜 {kanbanData.metadata.date_range.to}
        </div>
      )}
    </section>
  );
}