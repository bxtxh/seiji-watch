/**
 * Enhanced Issue Card Component
 * Displays policy issues with dual-level support and hierarchical relationships
 */

import React, { useState, useCallback } from "react";
import {
  ChevronDownIcon,
  ChevronRightIcon,
  TagIcon,
  CalendarIcon,
  UserIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
} from "@heroicons/react/24/outline";

export interface Issue {
  issue_id: string;
  record_id: string;
  label_lv1?: string;
  label_lv2?: string;
  parent_id?: string | null;
  confidence: number;
  quality_score: number;
  status: "pending" | "approved" | "rejected" | "failed_validation";
  source_bill_id: string;
  created_at: string;
  valid_from?: string;
  valid_to?: string | null;
  level: 1 | 2;
  children?: Issue[];
  bill_title?: string;
  bill_category?: string;
  reviewer_notes?: string;
}

export interface IssueCardProps {
  issue: Issue;
  currentLevel: 1 | 2;
  showHierarchy?: boolean;
  showDetails?: boolean;
  onStatusChange?: (issueId: string, status: string) => void;
  onToggleDetails?: (issueId: string) => void;
  className?: string;
}

export const IssueCard: React.FC<IssueCardProps> = ({
  issue,
  currentLevel,
  showHierarchy = false,
  showDetails = false,
  onStatusChange,
  onToggleDetails,
  className = "",
}) => {
  const [isExpanded, setIsExpanded] = useState(showDetails);

  const handleToggleExpanded = useCallback(() => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    if (onToggleDetails) {
      onToggleDetails(issue.issue_id);
    }
  }, [isExpanded, onToggleDetails, issue.issue_id]);

  const getStatusInfo = (status: string) => {
    switch (status) {
      case "approved":
        return {
          icon: CheckCircleIcon,
          label: "承認済み",
          color: "text-green-600",
          bgColor: "bg-green-50",
          borderColor: "border-green-200",
        };
      case "pending":
        return {
          icon: ClockIcon,
          label: "審査中",
          color: "text-yellow-600",
          bgColor: "bg-yellow-50",
          borderColor: "border-yellow-200",
        };
      case "rejected":
        return {
          icon: ExclamationTriangleIcon,
          label: "却下",
          color: "text-red-600",
          bgColor: "bg-red-50",
          borderColor: "border-red-200",
        };
      case "failed_validation":
        return {
          icon: ExclamationTriangleIcon,
          label: "検証失敗",
          color: "text-red-600",
          bgColor: "bg-red-50",
          borderColor: "border-red-200",
        };
      default:
        return {
          icon: ClockIcon,
          label: "不明",
          color: "text-gray-600",
          bgColor: "bg-gray-50",
          borderColor: "border-gray-200",
        };
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "text-green-600";
    if (confidence >= 0.6) return "text-yellow-600";
    return "text-red-600";
  };

  const getQualityColor = (quality: number) => {
    if (quality >= 0.8) return "text-green-600";
    if (quality >= 0.6) return "text-yellow-600";
    return "text-red-600";
  };

  const statusInfo = getStatusInfo(issue.status);
  const issueLabel = currentLevel === 1 ? issue.label_lv1 : issue.label_lv2;
  const hasChildren = issue.children && issue.children.length > 0;

  return (
    <div
      className={`bg-white rounded-lg border shadow-sm transition-shadow duration-200 hover:shadow-md ${className}`}
    >
      {/* Main Card Content */}
      <div className="p-6">
        {/* Header with Status and Toggle */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            {/* Status Badge */}
            <div
              className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${statusInfo.color} ${statusInfo.bgColor}`}
            >
              <statusInfo.icon className="w-4 h-4 mr-1" />
              {statusInfo.label}
            </div>

            {/* Level Indicator */}
            <div
              className={`px-2 py-1 rounded text-xs font-medium ${
                currentLevel === 1
                  ? "text-blue-600 bg-blue-50"
                  : "text-green-600 bg-green-50"
              }`}
            >
              レベル{currentLevel}
            </div>
          </div>

          {/* Expand/Collapse Button */}
          <button
            onClick={handleToggleExpanded}
            className="text-gray-400 hover:text-gray-600 transition-colors duration-150"
            aria-label={isExpanded ? "詳細を閉じる" : "詳細を開く"}
          >
            {isExpanded ? (
              <ChevronDownIcon className="w-5 h-5" />
            ) : (
              <ChevronRightIcon className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Issue Label */}
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          {issueLabel || "（ラベルなし）"}
        </h3>

        {/* Quick Info */}
        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 mb-4">
          {/* Confidence Score */}
          <div className="flex items-center space-x-1">
            <ChartBarIcon className="w-4 h-4" />
            <span>信頼度:</span>
            <span
              className={`font-medium ${getConfidenceColor(issue.confidence)}`}
            >
              {Math.round(issue.confidence * 100)}%
            </span>
          </div>

          {/* Quality Score */}
          <div className="flex items-center space-x-1">
            <TagIcon className="w-4 h-4" />
            <span>品質:</span>
            <span
              className={`font-medium ${getQualityColor(issue.quality_score)}`}
            >
              {Math.round(issue.quality_score * 100)}%
            </span>
          </div>

          {/* Source Bill */}
          {issue.bill_title && (
            <div className="flex items-center space-x-1">
              <UserIcon className="w-4 h-4" />
              <span className="truncate max-w-48">{issue.bill_title}</span>
            </div>
          )}
        </div>

        {/* Expanded Details */}
        {isExpanded && (
          <div className="border-t border-gray-100 pt-4 space-y-4">
            {/* Both Level Labels */}
            {issue.label_lv1 && issue.label_lv2 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-blue-600">
                    高校生向け (レベル1)
                  </h4>
                  <p className="text-sm text-gray-700 bg-blue-50 p-3 rounded-md">
                    {issue.label_lv1}
                  </p>
                </div>
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-green-600">
                    一般読者向け (レベル2)
                  </h4>
                  <p className="text-sm text-gray-700 bg-green-50 p-3 rounded-md">
                    {issue.label_lv2}
                  </p>
                </div>
              </div>
            )}

            {/* Metadata */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-600">作成日:</span>
                <div className="text-gray-900">
                  {new Date(issue.created_at).toLocaleDateString("ja-JP")}
                </div>
              </div>
              <div>
                <span className="font-medium text-gray-600">課題ID:</span>
                <div className="text-gray-900 font-mono text-xs">
                  {issue.issue_id}
                </div>
              </div>
              <div>
                <span className="font-medium text-gray-600">法案ID:</span>
                <div className="text-gray-900 font-mono text-xs">
                  {issue.source_bill_id}
                </div>
              </div>
              <div>
                <span className="font-medium text-gray-600">レコードID:</span>
                <div className="text-gray-900 font-mono text-xs">
                  {issue.record_id}
                </div>
              </div>
            </div>

            {/* Validity Period */}
            {issue.valid_from && (
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <CalendarIcon className="w-4 h-4" />
                <span>有効期間:</span>
                <span>{issue.valid_from}</span>
                {issue.valid_to && (
                  <>
                    <span>〜</span>
                    <span>{issue.valid_to}</span>
                  </>
                )}
                {!issue.valid_to && <span>〜 現在</span>}
              </div>
            )}

            {/* Reviewer Notes */}
            {issue.reviewer_notes && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-gray-600">
                  審査者コメント
                </h4>
                <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded-md">
                  {issue.reviewer_notes}
                </div>
              </div>
            )}

            {/* Bill Category */}
            {issue.bill_category && (
              <div className="flex items-center space-x-2 text-sm">
                <TagIcon className="w-4 h-4 text-gray-400" />
                <span className="font-medium text-gray-600">カテゴリ:</span>
                <span className="px-2 py-1 bg-gray-100 rounded text-gray-700">
                  {issue.bill_category}
                </span>
              </div>
            )}

            {/* Status Change Actions (for pending issues) */}
            {issue.status === "pending" && onStatusChange && (
              <div className="flex space-x-2 pt-2">
                <button
                  onClick={() => onStatusChange(issue.record_id, "approved")}
                  className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 transition-colors duration-150"
                >
                  承認
                </button>
                <button
                  onClick={() => onStatusChange(issue.record_id, "rejected")}
                  className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 transition-colors duration-150"
                >
                  却下
                </button>
              </div>
            )}
          </div>
        )}

        {/* Children (Hierarchical View) */}
        {showHierarchy && hasChildren && (
          <div className="mt-4 border-t border-gray-100 pt-4">
            <h4 className="text-sm font-medium text-gray-600 mb-3">
              関連する詳細課題
            </h4>
            <div className="space-y-2">
              {issue.children!.map((child) => (
                <IssueCard
                  key={child.issue_id}
                  issue={child}
                  currentLevel={currentLevel}
                  showHierarchy={false}
                  showDetails={false}
                  onStatusChange={onStatusChange}
                  onToggleDetails={onToggleDetails}
                  className="border-l-4 border-gray-200 ml-4 shadow-sm"
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Compact Issue Card for list views
 */
export const CompactIssueCard: React.FC<IssueCardProps> = ({
  issue,
  currentLevel,
  onToggleDetails,
  className = "",
}) => {
  const statusInfo = getStatusInfo(issue.status);
  const issueLabel = currentLevel === 1 ? issue.label_lv1 : issue.label_lv2;

  return (
    <div
      onClick={() => onToggleDetails?.(issue.issue_id)}
      className={`
        bg-white border rounded-lg p-4 cursor-pointer
        transition-all duration-200 hover:shadow-md hover:border-gray-300
        ${className}
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-2">
            <div
              className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${statusInfo.color} ${statusInfo.bgColor}`}
            >
              <statusInfo.icon className="w-3 h-3 mr-1" />
              {statusInfo.label}
            </div>
            <div
              className={`px-2 py-1 rounded text-xs font-medium ${
                currentLevel === 1
                  ? "text-blue-600 bg-blue-50"
                  : "text-green-600 bg-green-50"
              }`}
            >
              Lv.{currentLevel}
            </div>
          </div>

          <h3 className="text-sm font-medium text-gray-900 truncate mb-1">
            {issueLabel || "（ラベルなし）"}
          </h3>

          <div className="flex items-center space-x-3 text-xs text-gray-500">
            <span>信頼度: {Math.round(issue.confidence * 100)}%</span>
            <span>品質: {Math.round(issue.quality_score * 100)}%</span>
            {issue.bill_title && (
              <span className="truncate">{issue.bill_title}</span>
            )}
          </div>
        </div>

        <ChevronRightIcon className="w-4 h-4 text-gray-400 flex-shrink-0" />
      </div>
    </div>
  );
};

// Helper function for status info (also used in CompactIssueCard)
const getStatusInfo = (status: string) => {
  switch (status) {
    case "approved":
      return {
        icon: CheckCircleIcon,
        label: "承認済み",
        color: "text-green-600",
        bgColor: "bg-green-50",
        borderColor: "border-green-200",
      };
    case "pending":
      return {
        icon: ClockIcon,
        label: "審査中",
        color: "text-yellow-600",
        bgColor: "bg-yellow-50",
        borderColor: "border-yellow-200",
      };
    case "rejected":
      return {
        icon: ExclamationTriangleIcon,
        label: "却下",
        color: "text-red-600",
        bgColor: "bg-red-50",
        borderColor: "border-red-200",
      };
    case "failed_validation":
      return {
        icon: ExclamationTriangleIcon,
        label: "検証失敗",
        color: "text-red-600",
        bgColor: "bg-red-50",
        borderColor: "border-red-200",
      };
    default:
      return {
        icon: ClockIcon,
        label: "不明",
        color: "text-gray-600",
        bgColor: "bg-gray-50",
        borderColor: "border-gray-200",
      };
  }
};

export default IssueCard;
