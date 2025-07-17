import React, { memo } from "react";
import {
  CalendarIcon,
  TagIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import { Issue, IssueTag } from "../types";

interface ExtendedIssue extends Issue {
  category?: {
    id: string;
    title_ja: string;
    layer: string;
  };
  schedule?: {
    from: string;
    to: string;
  };
}

interface IssueDetailCardProps {
  issue: ExtendedIssue;
  issueTags: IssueTag[];
}

const IssueDetailCard: React.FC<IssueDetailCardProps> = ({
  issue,
  issueTags,
}) => {
  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case "high":
        return <ExclamationTriangleIcon className="w-4 h-4 text-red-600" />;
      case "medium":
        return <ClockIcon className="w-4 h-4 text-yellow-600" />;
      case "low":
        return <ClockIcon className="w-4 h-4 text-green-600" />;
      default:
        return <ClockIcon className="w-4 h-4 text-gray-600" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "bg-red-100 text-red-800 border-red-200";
      case "medium":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "low":
        return "bg-green-100 text-green-800 border-green-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "reviewed":
        return "bg-purple-100 text-purple-800 border-purple-200";
      case "archived":
        return "bg-gray-100 text-gray-800 border-gray-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const formatStatus = (status: string) => {
    const statusMap: { [key: string]: string } = {
      active: "審議中",
      reviewed: "審議済み",
      archived: "完了",
    };
    return statusMap[status] || status;
  };

  const formatPriority = (priority: string) => {
    const priorityMap: { [key: string]: string } = {
      high: "高",
      medium: "中",
      low: "低",
    };
    return priorityMap[priority] || priority;
  };

  const formatSchedule = (schedule?: { from: string; to: string }) => {
    if (!schedule) return null;

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

  const getTagsForIssue = (issue: ExtendedIssue): IssueTag[] => {
    if (!issue.issue_tags) return [];

    // Handle both string[] and IssueTag[] formats
    if (Array.isArray(issue.issue_tags) && issue.issue_tags.length > 0) {
      if (typeof issue.issue_tags[0] === "string") {
        // issue_tags is string[], filter by id
        const tagIds = issue.issue_tags as unknown as string[];
        return issueTags.filter((tag) => tagIds.includes(tag.id));
      } else {
        // issue_tags is already IssueTag[]
        return issue.issue_tags as IssueTag[];
      }
    }

    return [];
  };

  const tags = getTagsForIssue(issue);

  return (
    <article
      className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-6"
      role="main"
      aria-labelledby="issue-title"
    >
      {/* Header */}
      <header className="flex items-start justify-between">
        <div className="flex-1">
          <h1
            id="issue-title"
            className="text-2xl font-bold text-gray-900 mb-2"
          >
            {issue.title}
          </h1>
          {issue.category && (
            <div className="text-sm text-gray-600">
              <span className="sr-only">カテゴリ:</span>
              カテゴリ: {issue.category.title_ja}
            </div>
          )}
        </div>

        <div
          className="flex gap-2 ml-4"
          role="group"
          aria-label="イシューのステータス"
        >
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(issue.status)}`}
            aria-label={`ステータス: ${formatStatus(issue.status)}`}
          >
            {formatStatus(issue.status)}
          </span>
        </div>
      </header>

      {/* Description */}
      {issue.description && (
        <section
          className="prose prose-sm max-w-none"
          aria-labelledby="description-heading"
        >
          <h2
            id="description-heading"
            className="text-lg font-semibold text-gray-900 mb-2"
          >
            概要
          </h2>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
            {issue.description}
          </p>
        </section>
      )}

      {/* Schedule */}
      {issue.schedule && (
        <section
          className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg"
          aria-labelledby="schedule-heading"
        >
          <CalendarIcon
            className="w-5 h-5 text-gray-600 flex-shrink-0"
            aria-hidden="true"
          />
          <div>
            <h3
              id="schedule-heading"
              className="text-sm font-medium text-gray-900"
            >
              審議スケジュール
            </h3>
            <time
              className="text-sm text-gray-600"
              dateTime={issue.schedule.from}
            >
              {formatSchedule(issue.schedule)}
            </time>
          </div>
        </section>
      )}

      {/* Issue Tags */}
      {tags.length > 0 && (
        <section aria-labelledby="tags-heading">
          <h2
            id="tags-heading"
            className="text-lg font-semibold text-gray-900 mb-3 flex items-center"
          >
            <TagIcon className="w-5 h-5 mr-2" aria-hidden="true" />
            イシュータグ
          </h2>
          <div
            className="flex flex-wrap gap-2"
            role="list"
            aria-label="イシュータグ一覧"
          >
            {tags.map((tag) => (
              <span
                key={tag.id}
                role="listitem"
                className="inline-flex items-center px-3 py-1 rounded-lg text-sm font-medium border"
                style={{
                  backgroundColor: tag.color_code + "20",
                  color: tag.color_code,
                  borderColor: tag.color_code + "40",
                }}
                aria-label={`タグ: ${tag.name}${tag.description ? `, ${tag.description}` : ""}`}
              >
                {tag.name}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Metadata */}
      <footer className="pt-4 border-t border-gray-200">
        <h2 className="sr-only">詳細情報</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="font-medium text-gray-900">作成日:</dt>
            <dd className="ml-2 text-gray-600">
              {issue.created_at ? (
                <time dateTime={issue.created_at}>
                  {new Date(issue.created_at).toLocaleDateString("ja-JP")}
                </time>
              ) : (
                "-"
              )}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-gray-900">最終更新:</dt>
            <dd className="ml-2 text-gray-600">
              {issue.updated_at ? (
                <time dateTime={issue.updated_at}>
                  {new Date(issue.updated_at).toLocaleDateString("ja-JP")}
                </time>
              ) : (
                "-"
              )}
            </dd>
          </div>
          {issue.extraction_confidence && (
            <div>
              <dt className="font-medium text-gray-900">抽出信頼度:</dt>
              <dd
                className="ml-2 text-gray-600"
                aria-label={`信頼度 ${Math.round(issue.extraction_confidence * 100)}パーセント`}
              >
                {Math.round(issue.extraction_confidence * 100)}%
              </dd>
            </div>
          )}
          {issue.is_llm_generated && (
            <div>
              <dt className="sr-only">生成方法:</dt>
              <dd>
                <span
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                  aria-label="このイシューはAIによって生成されました"
                >
                  AI生成
                </span>
              </dd>
            </div>
          )}
        </dl>

        {issue.review_notes && (
          <div
            className="mt-4 p-3 bg-blue-50 rounded-lg"
            role="note"
            aria-labelledby="review-notes-heading"
          >
            <h3
              id="review-notes-heading"
              className="text-sm font-medium text-blue-900 mb-1"
            >
              レビューノート
            </h3>
            <p className="text-sm text-blue-800">{issue.review_notes}</p>
          </div>
        )}
      </footer>
    </article>
  );
};

export default memo(IssueDetailCard);
