import React, { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

interface ActiveIssue {
  id: string;
  title: string;
  summary: string;
  category: string;
  priority: string;
  stage: string;
  status: string;
  bill_number: string;
  last_updated: string;
  urgency: string;
  metadata: {
    source: string;
    record_id: string;
  };
}

interface ActiveIssuesResponse {
  success: boolean;
  data: ActiveIssue[];
  count: number;
  message: string;
  source: string;
}

const ActiveIssuesStrip: React.FC = () => {
  const [activeIssues, setActiveIssues] = useState<ActiveIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchActiveIssues = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          "http://localhost:8080/api/issues?status=in_view&limit=12",
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: ActiveIssuesResponse = await response.json();

        if (data.success) {
          setActiveIssues(data.data);
        } else {
          throw new Error("Failed to fetch active issues");
        }
      } catch (err) {
        console.error("Active issues fetch error:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchActiveIssues();
  }, []);

  const getPriorityColor = (urgency: string) => {
    switch (urgency) {
      case "high":
        return "border-red-500 bg-red-50";
      case "medium":
        return "border-yellow-500 bg-yellow-50";
      default:
        return "border-gray-300 bg-gray-50";
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case "deliberating":
        return "bg-blue-100 text-blue-800";
      case "vote_pending":
        return "bg-orange-100 text-orange-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          🔥 注目のイシュー
        </h2>
        <div className="flex space-x-4 overflow-x-auto pb-2">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="flex-shrink-0 w-80 h-32 bg-gray-200 rounded-lg animate-pulse"
            ></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          🔥 注目のイシュー
        </h2>
        <div className="text-red-600 text-sm">エラー: {error}</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">
          🔥 注目のイシュー
        </h2>
        <div className="text-sm text-gray-500">
          {activeIssues.length}件のアクティブな議題
        </div>
      </div>

      <div className="flex space-x-4 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
        {activeIssues.map((issue) => (
          <div
            key={issue.id}
            className={`flex-shrink-0 w-80 p-4 rounded-lg border-l-4 transition-all duration-200 hover:shadow-lg cursor-pointer ${getPriorityColor(issue.urgency)}`}
          >
            <div className="flex items-start justify-between mb-2">
              <div
                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeColor(issue.status)}`}
              >
                {issue.stage}
              </div>
              <div className="text-xs text-gray-500">{issue.category}</div>
            </div>

            <h3 className="font-semibold text-gray-900 text-sm mb-2 line-clamp-2">
              {issue.title}
            </h3>

            <p className="text-xs text-gray-600 line-clamp-3 mb-3">
              {issue.summary}
            </p>

            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>法案ID: {issue.bill_number.slice(0, 10)}...</span>
              <span>{issue.last_updated}</span>
            </div>
          </div>
        ))}
      </div>

      {activeIssues.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          現在アクティブなイシューはありません
        </div>
      )}
    </div>
  );
};

export default ActiveIssuesStrip;
