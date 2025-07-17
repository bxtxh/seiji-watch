import React, { memo, useMemo } from "react";
import {
  ChatBubbleLeftRightIcon,
  CalendarIcon,
  UserIcon,
} from "@heroicons/react/24/outline";

interface DiscussionItem {
  id: string;
  date: string;
  title: string;
  speakers: string[];
  summary?: string;
  committee?: string;
  session_type: "committee" | "plenary" | "hearing";
  transcript_url?: string;
}

interface DiscussionTimelineProps {
  discussions: DiscussionItem[];
  loading?: boolean;
}

const DiscussionTimeline: React.FC<DiscussionTimelineProps> = ({
  discussions,
  loading = false,
}) => {
  const getSessionTypeColor = (type: string) => {
    switch (type) {
      case "committee":
        return "bg-blue-100 text-blue-800";
      case "plenary":
        return "bg-purple-100 text-purple-800";
      case "hearing":
        return "bg-green-100 text-green-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getSessionTypeLabel = (type: string) => {
    switch (type) {
      case "committee":
        return "委員会";
      case "plenary":
        return "本会議";
      case "hearing":
        return "公聴会";
      default:
        return "審議";
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: "short",
    });
  };

  if (loading) {
    return (
      <div
        className="space-y-6"
        aria-live="polite"
        aria-label="議論履歴を読み込み中"
      >
        {[1, 2, 3].map((i) => (
          <div key={i} className="relative" aria-hidden="true">
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-gray-200 rounded-full animate-pulse"></div>
              </div>
              <div className="flex-1 min-w-0 space-y-3">
                <div className="h-4 bg-gray-200 rounded w-1/4 animate-pulse"></div>
                <div className="h-5 bg-gray-200 rounded w-3/4 animate-pulse"></div>
                <div className="space-y-2">
                  <div className="h-3 bg-gray-200 rounded animate-pulse"></div>
                  <div className="h-3 bg-gray-200 rounded w-5/6 animate-pulse"></div>
                </div>
                <div className="flex gap-2">
                  <div className="h-6 w-16 bg-gray-200 rounded animate-pulse"></div>
                  <div className="h-6 w-20 bg-gray-200 rounded animate-pulse"></div>
                </div>
              </div>
            </div>
          </div>
        ))}
        <span className="sr-only">議論履歴情報を読み込んでいます</span>
      </div>
    );
  }

  if (discussions.length === 0) {
    return (
      <div className="text-center py-12">
        <ChatBubbleLeftRightIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-lg font-medium text-gray-900">
          議論の記録が見つかりません
        </h3>
        <p className="mt-2 text-gray-600">
          このイシューに関する国会での議論はまだ記録されていません。
        </p>
      </div>
    );
  }

  return (
    <section className="space-y-6" aria-labelledby="discussions-heading">
      <header className="flex items-center justify-between">
        <h2
          id="discussions-heading"
          className="text-lg font-semibold text-gray-900 flex items-center"
        >
          <ChatBubbleLeftRightIcon
            className="w-5 h-5 mr-2"
            aria-hidden="true"
          />
          国会での議論
          <span
            className="ml-2 bg-gray-200 text-gray-700 px-2 py-1 rounded-full text-sm"
            aria-label={`${discussions.length}件の議論`}
          >
            {discussions.length}
          </span>
        </h2>
      </header>

      <div className="relative" role="list" aria-label="議論履歴">
        {/* Timeline line */}
        <div
          className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200"
          aria-hidden="true"
        ></div>

        <div className="space-y-8">
          {discussions.map((discussion, index) => (
            <article
              key={discussion.id}
              className="relative flex items-start space-x-4"
              role="listitem"
            >
              {/* Timeline dot */}
              <div
                className="flex-shrink-0 w-10 h-10 bg-white border-2 border-blue-500 rounded-full flex items-center justify-center relative z-10"
                aria-hidden="true"
              >
                <CalendarIcon className="w-5 h-5 text-blue-500" />
              </div>

              {/* Content */}
              <div
                className="flex-1 min-w-0 bg-white border border-gray-200 rounded-lg p-4 shadow-sm"
                aria-labelledby={`discussion-title-${discussion.id}`}
              >
                <header className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
                      <time dateTime={discussion.date}>
                        {formatDate(discussion.date)}
                      </time>
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getSessionTypeColor(discussion.session_type)}`}
                        aria-label={`会議種別: ${getSessionTypeLabel(discussion.session_type)}`}
                      >
                        {getSessionTypeLabel(discussion.session_type)}
                      </span>
                      {discussion.committee && (
                        <span
                          className="text-gray-500"
                          aria-label={`委員会: ${discussion.committee}`}
                        >
                          {discussion.committee}
                        </span>
                      )}
                    </div>
                    <h3
                      id={`discussion-title-${discussion.id}`}
                      className="text-base font-semibold text-gray-900"
                    >
                      {discussion.title}
                    </h3>
                  </div>
                </header>

                {discussion.summary && (
                  <p className="text-sm text-gray-700 mb-4 leading-relaxed">
                    {discussion.summary}
                  </p>
                )}

                {/* Speakers */}
                {discussion.speakers.length > 0 && (
                  <div className="mb-4">
                    <div className="flex items-center gap-2 mb-2">
                      <UserIcon
                        className="w-4 h-4 text-gray-500"
                        aria-hidden="true"
                      />
                      <h4 className="text-sm font-medium text-gray-700">
                        発言者
                      </h4>
                    </div>
                    <div
                      className="flex flex-wrap gap-2"
                      role="list"
                      aria-label="発言者一覧"
                    >
                      {discussion.speakers
                        .slice(0, 5)
                        .map((speaker, speakerIndex) => (
                          <span
                            key={speakerIndex}
                            role="listitem"
                            className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-700"
                            aria-label={`発言者: ${speaker}`}
                          >
                            {speaker}
                          </span>
                        ))}
                      {discussion.speakers.length > 5 && (
                        <span
                          className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600"
                          aria-label={`他${discussion.speakers.length - 5}名の発言者`}
                        >
                          他{discussion.speakers.length - 5}名
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <footer className="flex justify-between items-center pt-3 border-t border-gray-100">
                  <div className="text-xs text-gray-500">
                    {index === 0 && (
                      <span className="font-medium">最新の議論</span>
                    )}
                  </div>

                  {discussion.transcript_url && (
                    <a
                      href={discussion.transcript_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-sm font-medium text-blue-600 hover:text-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded"
                      aria-label={`${discussion.title}の議事録を新しいタブで開く`}
                    >
                      議事録を見る
                      <svg
                        className="ml-1 w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                        />
                      </svg>
                    </a>
                  )}
                </footer>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

export default memo(DiscussionTimeline);
