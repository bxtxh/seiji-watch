import React, { useEffect, useState } from "react";
import { Bill } from "@/types";
import VotingResults from "./VotingResults";
import EnhancedBillDetails from "./EnhancedBillDetails";
import LegislativeProgressBar from "./LegislativeProgressBar";
import CommitteeAssignments from "./CommitteeAssignments";

interface BillDetailModalProps {
  bill: Bill;
  isOpen: boolean;
  onClose: () => void;
}

export default function BillDetailModal({
  bill,
  isOpen,
  onClose,
}: BillDetailModalProps) {
  const [activeTab, setActiveTab] = useState<
    "overview" | "details" | "progress" | "committee"
  >("overview");
  // Handle escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

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

  const getStatusBadgeClass = (status: string) => {
    switch (status.toLowerCase()) {
      case "passed":
      case "成立":
        return "status-passed";
      case "under_review":
      case "審議中":
        return "status-under-review";
      case "pending_vote":
      case "awaiting_vote":
      case "採決待ち":
        return "status-pending";
      case "backlog":
      default:
        return "status-backlog";
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden animate-slide-up"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          {/* Header */}
          <div className="flex items-start justify-between p-6 border-b border-gray-200">
            <div className="flex-1 min-w-0">
              <h2
                id="modal-title"
                className="text-xl font-semibold text-gray-900 japanese-text"
              >
                {bill.title}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                法案番号: {bill.bill_number}
              </p>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="ml-4 rounded-md bg-white text-gray-400 hover:text-gray-600 focus:ring-2 focus:ring-primary-green"
              aria-label="閉じる"
            >
              <span className="sr-only">閉じる</span>
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Tab Navigation */}
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6" aria-label="タブ">
              {[
                { id: "overview", label: "概要", count: null },
                { id: "details", label: "詳細", count: null },
                {
                  id: "progress",
                  label: "進捗",
                  count: bill.legislative_stage?.milestones?.length,
                },
                {
                  id: "committee",
                  label: "委員会",
                  count: bill.committee_assignments?.length,
                },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                    activeTab === tab.id
                      ? "border-blue-500 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  }`}
                  aria-current={activeTab === tab.id ? "page" : undefined}
                >
                  {tab.label}
                  {tab.count != null && tab.count > 0 && (
                    <span className="ml-2 bg-gray-100 text-gray-900 py-0.5 px-2 rounded-full text-xs">
                      {tab.count}
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
            {activeTab === "overview" && (
              <div className="space-y-6">
                {/* Status and Category */}
                <div className="flex flex-wrap gap-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-700">
                      ステータス:
                    </span>
                    <span
                      className={`status-badge ${getStatusBadgeClass(bill.status)}`}
                    >
                      {formatStatus(bill.status)}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-700">
                      カテゴリ:
                    </span>
                    <span className="status-badge bg-blue-100 text-blue-800">
                      {formatCategory(bill.category)}
                    </span>
                  </div>

                  {bill.relevance_score && (
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium text-gray-700">
                        関連度:
                      </span>
                      <span className="text-sm text-gray-600">
                        {Math.round(bill.relevance_score * 100)}%
                      </span>
                    </div>
                  )}
                </div>

                {/* Progress Bar - Compact */}
                {bill.legislative_stage && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <LegislativeProgressBar
                      stage={bill.legislative_stage}
                      compact={true}
                    />
                  </div>
                )}

                {/* Summary */}
                {bill.summary && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-3">
                      概要
                    </h3>
                    <p className="text-gray-700 japanese-text leading-relaxed">
                      {bill.summary}
                    </p>
                  </div>
                )}

                {/* Voting Results */}
                <VotingResults billNumber={bill.bill_number} />

                {/* Actions */}
                <div className="border-t border-gray-200 pt-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-3">
                    関連リンク
                  </h3>
                  <div className="space-y-3">
                    {bill.diet_url && (
                      <a
                        href={bill.diet_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-4 py-2 text-sm font-medium text-primary-green bg-green-50 hover:bg-green-100 rounded-md transition-colors"
                      >
                        <svg
                          className="w-4 h-4 mr-2"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                          />
                        </svg>
                        参議院ウェブサイトで詳細を見る
                      </a>
                    )}
                  </div>
                </div>

                {/* Search metadata */}
                {bill.search_method && (
                  <div className="bg-gray-50 rounded-md p-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">
                      検索情報
                    </h3>
                    <div className="text-sm text-gray-600 space-y-1">
                      <p>
                        検索方法:{" "}
                        {bill.search_method === "vector"
                          ? "AI検索（ベクトル類似度）"
                          : "キーワード検索"}
                      </p>
                      {bill.relevance_score && (
                        <p>スコア: {bill.relevance_score.toFixed(3)}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "details" && <EnhancedBillDetails bill={bill} />}

            {activeTab === "progress" && (
              <div className="space-y-6">
                {bill.legislative_stage ? (
                  <LegislativeProgressBar stage={bill.legislative_stage} />
                ) : (
                  <div className="text-center py-12">
                    <svg
                      className="mx-auto h-12 w-12 text-gray-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <h3 className="mt-4 text-lg font-medium text-gray-900">
                      進捗情報が利用できません
                    </h3>
                    <p className="mt-2 text-gray-600">
                      この法案の立法進捗情報はまだ取得されていません。
                    </p>
                  </div>
                )}
              </div>
            )}

            {activeTab === "committee" && (
              <div className="space-y-6">
                {bill.committee_assignments &&
                bill.committee_assignments.length > 0 ? (
                  <CommitteeAssignments
                    assignments={bill.committee_assignments}
                  />
                ) : (
                  <div className="text-center py-12">
                    <svg
                      className="mx-auto h-12 w-12 text-gray-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                      />
                    </svg>
                    <h3 className="mt-4 text-lg font-medium text-gray-900">
                      委員会情報が利用できません
                    </h3>
                    <p className="mt-2 text-gray-600">
                      この法案の委員会付託情報はまだ取得されていません。
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
            <button type="button" onClick={onClose} className="btn-secondary">
              閉じる
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
