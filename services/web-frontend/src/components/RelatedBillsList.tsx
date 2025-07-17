import React, { useState, memo, useCallback, useMemo } from "react";
import {
  DocumentTextIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";
import { Bill } from "../types";
import BillDetailModal from "./BillDetailModal";

interface RelatedBillsListProps {
  bills: Bill[];
  loading?: boolean;
}

const RelatedBillsList: React.FC<RelatedBillsListProps> = ({
  bills,
  loading = false,
}) => {
  const [selectedBill, setSelectedBill] = useState<Bill | null>(null);
  const [showModal, setShowModal] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "passed":
      case "成立":
        return "bg-green-100 text-green-800 border-green-200";
      case "under_review":
      case "審議中":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "pending_vote":
      case "awaiting_vote":
      case "採決待ち":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "backlog":
      case "未審議":
        return "bg-gray-100 text-gray-800 border-gray-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getCategoryColor = (category: string | undefined) => {
    if (!category) return "bg-gray-50 text-gray-700";
    switch (category.toLowerCase()) {
      case "budget":
      case "予算・決算":
        return "bg-blue-50 text-blue-700";
      case "taxation":
      case "税制":
        return "bg-green-50 text-green-700";
      case "social_security":
      case "社会保障":
        return "bg-purple-50 text-purple-700";
      case "foreign_affairs":
      case "外交・国際":
        return "bg-red-50 text-red-700";
      case "economy":
      case "経済・産業":
        return "bg-yellow-50 text-yellow-700";
      default:
        return "bg-gray-50 text-gray-700";
    }
  };

  const formatStatus = (status: string) => {
    const statusMap: { [key: string]: string } = {
      passed: "成立",
      under_review: "審議中",
      pending_vote: "採決待ち",
      awaiting_vote: "採決待ち",
      backlog: "未審議",
    };
    return statusMap[status.toLowerCase()] || status;
  };

  const formatCategory = (category: string | undefined) => {
    if (!category) return "その他";
    const categoryMap: { [key: string]: string } = {
      budget: "予算・決算",
      taxation: "税制",
      social_security: "社会保障",
      foreign_affairs: "外交・国際",
      economy: "経済・産業",
      other: "その他",
    };
    return categoryMap[category.toLowerCase()] || category;
  };

  const handleBillClick = useCallback((bill: Bill) => {
    setSelectedBill(bill);
    setShowModal(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setShowModal(false);
    setSelectedBill(null);
  }, []);

  if (loading) {
    return (
      <div
        className="space-y-4"
        aria-live="polite"
        aria-label="関連法案を読み込み中"
      >
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-white border border-gray-200 rounded-lg p-4 animate-pulse"
            aria-hidden="true"
          >
            <div className="flex justify-between items-start mb-3">
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
              <div className="flex gap-2">
                <div className="h-6 w-16 bg-gray-200 rounded"></div>
                <div className="h-6 w-16 bg-gray-200 rounded"></div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="h-3 bg-gray-200 rounded"></div>
              <div className="h-3 bg-gray-200 rounded w-5/6"></div>
            </div>
          </div>
        ))}
        <span className="sr-only">関連法案情報を読み込んでいます</span>
      </div>
    );
  }

  if (bills.length === 0) {
    return (
      <div className="text-center py-12">
        <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-lg font-medium text-gray-900">
          関連法案が見つかりません
        </h3>
        <p className="mt-2 text-gray-600">
          このイシューに関連する法案はまだ登録されていません。
        </p>
      </div>
    );
  }

  return (
    <section className="space-y-4" aria-labelledby="related-bills-heading">
      <header className="flex items-center justify-between">
        <h2
          id="related-bills-heading"
          className="text-lg font-semibold text-gray-900 flex items-center"
        >
          <DocumentTextIcon className="w-5 h-5 mr-2" aria-hidden="true" />
          関連法案
          <span
            className="ml-2 bg-gray-200 text-gray-700 px-2 py-1 rounded-full text-sm"
            aria-label={`${bills.length}件の関連法案`}
          >
            {bills.length}
          </span>
        </h2>
      </header>

      <div className="space-y-3" role="list" aria-label="関連法案一覧">
        {bills.map((bill) => (
          <article
            key={bill.id}
            role="listitem"
            className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            onClick={() => handleBillClick(bill)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleBillClick(bill);
              }
            }}
            tabIndex={0}
            aria-labelledby={`bill-title-${bill.id}`}
          >
            <div className="flex justify-between items-start mb-3">
              <div className="flex-1 min-w-0">
                <h3
                  id={`bill-title-${bill.id}`}
                  className="text-base font-semibold text-gray-900 line-clamp-2"
                >
                  {bill.title}
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  <span className="sr-only">法案番号:</span>
                  法案番号: {bill.bill_number}
                </p>
              </div>

              <div
                className="flex flex-col gap-2 ml-4"
                role="group"
                aria-label="法案ステータス"
              >
                <span
                  className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(bill.status)}`}
                  aria-label={`ステータス: ${formatStatus(bill.status)}`}
                >
                  {formatStatus(bill.status)}
                </span>
                <span
                  className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${getCategoryColor(bill.policy_category?.title_ja || bill.category)}`}
                  aria-label={`カテゴリ: ${formatCategory(bill.policy_category?.title_ja || bill.category || "その他")}`}
                >
                  {formatCategory(
                    bill.policy_category?.title_ja || bill.category || "その他",
                  )}
                </span>
              </div>
            </div>

            {bill.summary && (
              <p className="text-sm text-gray-700 line-clamp-3 mb-3">
                {bill.summary}
              </p>
            )}

            <div className="flex justify-between items-center pt-3 border-t border-gray-100">
              <div className="flex items-center gap-3 text-xs text-gray-500">
                {bill.relevance_score && (
                  <span>関連度: {Math.round(bill.relevance_score * 100)}%</span>
                )}
                {bill.search_method && (
                  <span>
                    {bill.search_method === "vector"
                      ? "AI検索"
                      : "キーワード検索"}
                  </span>
                )}
              </div>

              <button
                type="button"
                className="inline-flex items-center text-sm font-medium text-blue-600 hover:text-blue-500"
                onClick={(e) => {
                  e.stopPropagation();
                  handleBillClick(bill);
                }}
              >
                詳細を見る
                <ChevronRightIcon className="ml-1 w-4 h-4" />
              </button>
            </div>
          </article>
        ))}
      </div>

      {/* Bill Detail Modal */}
      {showModal && selectedBill && (
        <BillDetailModal
          bill={selectedBill}
          isOpen={showModal}
          onClose={handleCloseModal}
        />
      )}
    </section>
  );
};

export default memo(RelatedBillsList);
