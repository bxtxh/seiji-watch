import React from 'react';
import IssueCard, { KanbanIssue } from './IssueCard';

// Stage configuration
const STAGE_CONFIG = {
  審議前: {
    label: '審議前',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    description: '未審議・タグ付け済み',
    icon: '📋'
  },
  審議中: {
    label: '審議中',
    bgColor: 'bg-indigo-50',
    textColor: 'text-indigo-700', 
    description: '委員会・本会議審議中',
    icon: '⚖️'
  },
  採決待ち: {
    label: '採決待ち',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-700',
    description: '審議完了・採決日程待ち',
    icon: '⏳'
  },
  成立: {
    label: '成立',
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    description: '可決成立・否決完了',
    icon: '✅'
  }
};

interface StageColumnProps {
  stageKey: string;
  issues: KanbanIssue[];
  onCardClick: (issue: KanbanIssue) => void;
  onCardHover?: (issue: KanbanIssue) => void;
  maxDisplayed?: number;
}

const StageColumn = React.memo(function StageColumn({ 
  stageKey, 
  issues, 
  onCardClick,
  onCardHover,
  maxDisplayed = 8 
}: StageColumnProps) {
  const config = STAGE_CONFIG[stageKey as keyof typeof STAGE_CONFIG];
  const displayedIssues = issues.slice(0, maxDisplayed);
  const hiddenCount = issues.length - maxDisplayed;
  
  if (!config) {
    return null;
  }

  return (
    <div 
      className="flex flex-col h-full snap-start min-w-[280px] md:min-w-[320px]" 
      role="group" 
      aria-labelledby={`stage-${stageKey}-label`}
    >
      {/* Column Header */}
      <div className="sticky top-0 bg-gray-50 z-10 py-3 px-1 rounded-t-lg border-b border-gray-200">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg" role="img" aria-label={config.label}>
            {config.icon}
          </span>
          <h3 
            id={`stage-${stageKey}-label`}
            className="text-sm font-bold text-gray-900"
          >
            {config.label}
          </h3>
          <span 
            className={`px-2 py-1 text-xs rounded-full font-medium ${config.bgColor} ${config.textColor}`}
            aria-label={`${issues.length}件のイシュー`}
          >
            {issues.length}
          </span>
        </div>
        <p className="text-xs text-gray-600 leading-relaxed">
          {config.description}
        </p>
      </div>

      {/* Issue Cards Container */}
      <div className="flex-1 space-y-3 p-1 min-h-[400px]">
        {displayedIssues.length > 0 ? (
          <>
            {/* Issue Cards */}
            {displayedIssues.map((issue) => (
              <IssueCard 
                key={issue.id} 
                issue={issue} 
                onCardClick={onCardClick}
                onCardHover={onCardHover}
              />
            ))}
            
            {/* More Items Indicator */}
            {hiddenCount > 0 && (
              <div className="bg-gradient-to-r from-gray-100 to-gray-200 rounded-xl p-4 text-center border-2 border-dashed border-gray-300">
                <div className="text-sm font-medium text-gray-700 mb-1">
                  さらに {hiddenCount}件のイシュー
                </div>
                <button 
                  className="text-xs text-primary hover:underline font-medium"
                  onClick={() => {
                    // Navigate to full stage view
                    window.location.href = `/issues?stage=${encodeURIComponent(stageKey)}`;
                  }}
                >
                  すべて表示 →
                </button>
              </div>
            )}
          </>
        ) : (
          /* Empty State */
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-3">
              <span className="text-2xl opacity-50" role="img" aria-label="空">
                {config.icon}
              </span>
            </div>
            <div className="text-sm text-gray-500 mb-1">
              現在{config.label}のイシューはありません
            </div>
            <div className="text-xs text-gray-400">
              新しいイシューが追加されると<br />
              ここに表示されます
            </div>
          </div>
        )}
      </div>
      
      {/* Column Footer */}
      <div className="px-1 py-2 border-t border-gray-200 bg-gray-50 rounded-b-lg">
        <div className="text-xs text-gray-500 text-center">
          {displayedIssues.length > 0 ? (
            `${displayedIssues.length}件表示中`
          ) : (
            '空のステージ'
          )}
        </div>
      </div>
    </div>
  );
});

export default StageColumn;