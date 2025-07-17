import React from 'react';
import { CalendarIcon } from '@heroicons/react/24/outline';

// Types
export interface KanbanIssue {
  id: string;
  title: string;
  stage: string;
  schedule: {
    from: string;
    to: string;
  };
  tags: string[];
  related_bills: Array<{
    bill_id: string;
    title: string;
    stage: string;
    bill_number: string;
  }>;
  updated_at: string;
}

// Stage configuration
const STAGE_CONFIG = {
  審議前: {
    label: '審議前',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    description: '未審議・タグ付け済み'
  },
  審議中: {
    label: '審議中',
    bgColor: 'bg-indigo-50',
    textColor: 'text-indigo-700', 
    description: '委員会・本会議審議中'
  },
  採決待ち: {
    label: '採決待ち',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-700',
    description: '審議完了・採決日程待ち'
  },
  成立: {
    label: '成立',
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    description: '可決成立・否決完了'
  }
};

// Category tag colors
const TAG_COLORS = [
  'bg-purple-50 text-purple-700',
  'bg-blue-50 text-blue-700',
  'bg-green-50 text-green-700',
  'bg-orange-50 text-orange-700',
  'bg-pink-50 text-pink-700',
  'bg-indigo-50 text-indigo-700'
];

interface IssueCardProps {
  issue: KanbanIssue;
  onCardClick: (issue: KanbanIssue) => void;
  onCardHover?: (issue: KanbanIssue) => void;
}

const IssueCard = React.memo(function IssueCard({ issue, onCardClick, onCardHover }: IssueCardProps) {
  const stageConfig = STAGE_CONFIG[issue.stage as keyof typeof STAGE_CONFIG];

  // Format schedule display
  const formatSchedule = (schedule: { from: string; to: string }) => {
    const fromDate = new Date(schedule.from);
    const toDate = new Date(schedule.to);
    
    const formatDate = (date: Date) => {
      return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
    };
    
    if (schedule.from === schedule.to) {
      return formatDate(fromDate);
    }
    
    return `${formatDate(fromDate)}〜${formatDate(toDate)}`;
  };

  // Get tag color by index
  const getTagColor = (index: number) => {
    return TAG_COLORS[index % TAG_COLORS.length];
  };


  return (
    <article 
      className="bg-white rounded-xl shadow-sm p-4 w-full space-y-3 cursor-pointer transition-all duration-200 hover:shadow-md hover:scale-[1.02] border border-gray-100"
      role="listitem"
      onClick={() => onCardClick(issue)}
      onMouseEnter={() => onCardHover?.(issue)}
      aria-labelledby={`issue-${issue.id}-title`}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onCardClick(issue);
        }
      }}
    >
      {/* Header: Title + Stage Badge */}
      <div className="flex items-start justify-between gap-2">
        <h3 
          id={`issue-${issue.id}-title`}
          className="font-medium text-sm leading-snug line-clamp-2 flex-1"
          title={issue.title}
        >
          {issue.title}
        </h3>
        <span 
          className={`px-2 py-0.5 text-xs rounded-full flex-shrink-0 font-medium ${stageConfig?.bgColor} ${stageConfig?.textColor}`}
          aria-label={`ステージ: ${issue.stage}`}
        >
          {issue.stage}
        </span>
      </div>

      {/* Schedule Chip */}
      <div className="flex items-center gap-2 text-xs text-gray-600 bg-gray-50 p-2 rounded-lg">
        <CalendarIcon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
        <span className="truncate">{formatSchedule(issue.schedule)}</span>
      </div>

      {/* Category Tags */}
      {issue.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {issue.tags.slice(0, 3).map((tag, index) => (
            <span 
              key={index}
              className={`px-2 py-1 text-xs rounded-full font-medium ${getTagColor(index)}`}
              title={tag}
            >
              {tag}
            </span>
          ))}
          {issue.tags.length > 3 && (
            <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600">
              +{issue.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Related Bills */}
      {issue.related_bills.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-gray-500 flex items-center gap-1">
            関連法案
            <span className="bg-gray-200 text-gray-700 px-1.5 py-0.5 rounded-full text-xs">
              {issue.related_bills.length}
            </span>
          </h4>
          <div className="space-y-1">
            {issue.related_bills.slice(0, 2).map((bill, index) => (
              <div 
                key={index}
                className="p-2 text-xs border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  // Handle bill click if needed
                }}
              >
                <div className="line-clamp-2 text-gray-800 mb-1" title={bill.title}>
                  {bill.title}
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500 text-xs">
                    {bill.bill_number}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-xs ${
                    STAGE_CONFIG[bill.stage as keyof typeof STAGE_CONFIG]?.bgColor || 'bg-gray-100'
                  } ${
                    STAGE_CONFIG[bill.stage as keyof typeof STAGE_CONFIG]?.textColor || 'text-gray-700'
                  }`}>
                    {bill.stage}
                  </span>
                </div>
              </div>
            ))}
            {issue.related_bills.length > 2 && (
              <div className="text-xs text-gray-500 text-center py-2 bg-gray-50 rounded-lg">
                他 {issue.related_bills.length - 2}件の関連法案
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex justify-between items-center text-xs text-gray-500 pt-2 border-t border-gray-100">
        <time dateTime={issue.updated_at} className="flex items-center gap-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
          最終更新: {issue.updated_at}
        </time>
        <span className="text-primary hover:underline font-medium transition-colors">
          詳細を見る →
        </span>
      </div>
    </article>
  );
});

export default IssueCard;