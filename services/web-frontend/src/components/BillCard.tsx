import React, { useState } from 'react';
import { Bill } from '@/types';
import BillDetailModal from './BillDetailModal';

interface BillCardProps {
  bill: Bill;
}

export default function BillCard({ bill }: BillCardProps) {
  const [showDetail, setShowDetail] = useState(false);

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

          {/* Category and metadata */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-100">
            <div className="flex items-center space-x-2">
              <span className={`status-badge ${getCategoryBadgeClass(bill.category)}`}>
                {formatCategory(bill.category)}
              </span>
              
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