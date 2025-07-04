import React, { useState, useEffect } from 'react';
import { Bill, IssueTag } from '@/types';
import BillDetailModal from './BillDetailModal';

interface BillCardProps {
  bill: Bill;
}

export default function BillCard({ bill }: BillCardProps) {
  const [showDetail, setShowDetail] = useState(false);
  const [issueTags, setIssueTags] = useState<IssueTag[]>([]);

  useEffect(() => {
    if (bill.issue_tags && bill.issue_tags.length > 0) {
      fetchIssueTags();
    }
  }, [bill.issue_tags]);

  const fetchIssueTags = async () => {
    try {
      const response = await fetch('/api/issues/tags/');
      const data = await response.json();
      
      const transformedTags: IssueTag[] = data.map((record: any) => ({
        id: record.id,
        name: record.fields?.Name || '',
        color_code: record.fields?.Color_Code || '#3B82F6',
        category: record.fields?.Category || '',
        description: record.fields?.Description
      }));
      
      // Filter tags that are associated with this bill
      const billTags = transformedTags.filter(tag => 
        bill.issue_tags?.includes(tag.id)
      );
      
      setIssueTags(billTags);
    } catch (error) {
      console.error('Failed to fetch issue tags:', error);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status.toLowerCase()) {
      case 'passed':
      case '成立':
        return 'status-passed';
      case 'under_review':
      case '審議中':
        return 'status-under-review';
      case 'pending_vote':
      case 'awaiting_vote':
      case '採決待ち':
        return 'status-pending';
      case 'backlog':
      default:
        return 'status-backlog';
    }
  };

  const getCategoryBadgeClass = (category: string) => {
    switch (category.toLowerCase()) {
      case 'budget':
      case '予算・決算':
        return 'bg-blue-100 text-blue-800';
      case 'taxation':
      case '税制':
        return 'bg-green-100 text-green-800';
      case 'social_security':
      case '社会保障':
        return 'bg-purple-100 text-purple-800';
      case 'foreign_affairs':
      case '外交・国際':
        return 'bg-red-100 text-red-800';
      case 'economy':
      case '経済・産業':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatStatus = (status: string) => {
    const statusMap: { [key: string]: string } = {
      'passed': '成立',
      'under_review': '審議中',
      'pending_vote': '採決待ち',
      'awaiting_vote': '採決待ち',
      'backlog': '未審議',
    };
    return statusMap[status.toLowerCase()] || status;
  };

  const formatCategory = (category: string) => {
    const categoryMap: { [key: string]: string } = {
      'budget': '予算・決算',
      'taxation': '税制',
      'social_security': '社会保障',
      'foreign_affairs': '外交・国際',
      'economy': '経済・産業',
      'other': 'その他',
    };
    return categoryMap[category.toLowerCase()] || category;
  };

  return (
    <>
      <div className="card hover:shadow-md transition-shadow duration-200 cursor-pointer">
        <div onClick={() => setShowDetail(true)} className="space-y-3">
          {/* Header with bill number and status */}
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-gray-900 japanese-text">
                {bill.title}
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                法案番号: {bill.bill_number}
              </p>
            </div>
            
            <div className="flex flex-col items-end space-y-2 ml-4">
              <span className={`status-badge ${getStatusBadgeClass(bill.status)}`}>
                {formatStatus(bill.status)}
              </span>
              
              {bill.relevance_score && (
                <div className="text-xs text-gray-500">
                  関連度: {Math.round(bill.relevance_score * 100)}%
                </div>
              )}
            </div>
          </div>

          {/* Summary */}
          {bill.summary && (
            <p className="text-sm text-gray-700 japanese-text line-clamp-3">
              {bill.summary}
            </p>
          )}

          {/* Issue Tags */}
          {issueTags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {issueTags.slice(0, 3).map((tag) => (
                <span
                  key={tag.id}
                  className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium"
                  style={{
                    backgroundColor: tag.color_code + '20',
                    color: tag.color_code
                  }}
                >
                  {tag.name}
                </span>
              ))}
              {issueTags.length > 3 && (
                <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
                  +{issueTags.length - 3} more
                </span>
              )}
            </div>
          )}

          {/* Category and metadata */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-100">
            <div className="flex items-center space-x-2 flex-wrap">
              <span className={`status-badge ${getCategoryBadgeClass(bill.category)}`}>
                {formatCategory(bill.category)}
              </span>
              
              {/* Voting Status Indicator */}
              {bill.status === 'PASSED' && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  採決済み
                </span>
              )}
              
              {bill.status === 'PENDING_VOTE' && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                  <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                  </svg>
                  採決予定
                </span>
              )}
              
              {bill.search_method && (
                <span className="text-xs text-gray-500">
                  {bill.search_method === 'vector' ? 'AI検索' : 'キーワード検索'}
                </span>
              )}
            </div>

            <button
              type="button"
              className="text-primary-green hover:text-green-600 text-sm font-medium"
              onClick={(e) => {
                e.stopPropagation();
                setShowDetail(true);
              }}
              aria-label={`${bill.title}の詳細を表示`}
            >
              詳細を見る →
            </button>
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {showDetail && (
        <BillDetailModal
          bill={bill}
          isOpen={showDetail}
          onClose={() => setShowDetail(false)}
        />
      )}
    </>
  );
}