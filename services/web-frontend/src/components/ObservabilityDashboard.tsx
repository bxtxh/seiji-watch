import React, { useState, useEffect } from "react";
import { useObservability } from "@/lib/observability";

/**
 * Observability Dashboard Component
 *
 * Displays real-time monitoring data including:
 * - Core Web Vitals
 * - Performance metrics
 * - Error tracking
 * - User interactions
 * - Session information
 */

interface DashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ObservabilityDashboard({
  isOpen,
  onClose,
}: DashboardProps) {
  const { getWebVitals, getSessionSummary } = useObservability();
  const [webVitals, setWebVitals] = useState(getWebVitals());
  const [sessionSummary, setSessionSummary] = useState(getSessionSummary());
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(
    null,
  );

  useEffect(() => {
    if (isOpen) {
      // Update data immediately when opened
      updateData();

      // Set up auto-refresh every 5 seconds
      const interval = setInterval(updateData, 5000);
      setRefreshInterval(interval);

      return () => {
        if (interval) clearInterval(interval);
      };
    } else {
      if (refreshInterval) {
        clearInterval(refreshInterval);
        setRefreshInterval(null);
      }
    }
  }, [isOpen]);

  const updateData = () => {
    setWebVitals(getWebVitals());
    setSessionSummary(getSessionSummary());
  };

  const getVitalRating = (
    vital: string,
    value?: number,
  ): "good" | "needs-improvement" | "poor" | "unknown" => {
    if (value === undefined) return "unknown";

    const thresholds: Record<string, [number, number]> = {
      fcp: [1800, 3000],
      lcp: [2500, 4000],
      fid: [100, 300],
      cls: [0.1, 0.25],
      ttfb: [800, 1800],
    };

    const [good, poor] = thresholds[vital] || [0, 0];
    if (value <= good) return "good";
    if (value <= poor) return "needs-improvement";
    return "poor";
  };

  const formatValue = (vital: string, value?: number): string => {
    if (value === undefined) return "N/A";

    if (vital === "cls") {
      return value.toFixed(3);
    }
    return `${Math.round(value)}ms`;
  };

  const getRatingColor = (rating: string): string => {
    switch (rating) {
      case "good":
        return "text-green-600 bg-green-50";
      case "needs-improvement":
        return "text-yellow-600 bg-yellow-50";
      case "poor":
        return "text-red-600 bg-red-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            可観測性ダッシュボード
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="ダッシュボードを閉じる"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
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

        <div className="p-6 space-y-6">
          {/* Session Information */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-lg font-medium text-gray-900 mb-3">
              セッション情報
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">セッションID:</span>
                <p className="font-mono text-xs text-gray-900 mt-1 break-all">
                  {sessionSummary.sessionId}
                </p>
              </div>
              <div>
                <span className="text-gray-600">メトリクス:</span>
                <p className="text-lg font-semibold text-blue-600 mt-1">
                  {sessionSummary.metricsCount}
                </p>
              </div>
              <div>
                <span className="text-gray-600">エラー:</span>
                <p className="text-lg font-semibold text-red-600 mt-1">
                  {sessionSummary.errorsCount}
                </p>
              </div>
              <div>
                <span className="text-gray-600">インタラクション:</span>
                <p className="text-lg font-semibold text-green-600 mt-1">
                  {sessionSummary.interactionsCount}
                </p>
              </div>
            </div>
          </div>

          {/* Core Web Vitals */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">
              Core Web Vitals
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {Object.entries(webVitals).map(([vital, value]) => {
                const rating = getVitalRating(vital, value);
                const displayName =
                  {
                    fcp: "FCP",
                    lcp: "LCP",
                    fid: "FID",
                    cls: "CLS",
                    ttfb: "TTFB",
                  }[vital] || vital.toUpperCase();

                return (
                  <div
                    key={vital}
                    className="bg-white border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-600">
                        {displayName}
                      </span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${getRatingColor(rating)}`}
                      >
                        {rating === "unknown" ? "N/A" : rating}
                      </span>
                    </div>
                    <p className="text-lg font-semibold text-gray-900">
                      {formatValue(vital, value)}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {vital === "fcp" && "First Contentful Paint"}
                      {vital === "lcp" && "Largest Contentful Paint"}
                      {vital === "fid" && "First Input Delay"}
                      {vital === "cls" && "Cumulative Layout Shift"}
                      {vital === "ttfb" && "Time to First Byte"}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Performance Summary */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">
              パフォーマンス評価
            </h3>
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {
                      Object.values(webVitals).filter((v, i) => {
                        const vital = Object.keys(webVitals)[i];
                        return getVitalRating(vital, v) === "good";
                      }).length
                    }
                  </div>
                  <p className="text-sm text-gray-600">良好</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-yellow-600">
                    {
                      Object.values(webVitals).filter((v, i) => {
                        const vital = Object.keys(webVitals)[i];
                        return getVitalRating(vital, v) === "needs-improvement";
                      }).length
                    }
                  </div>
                  <p className="text-sm text-gray-600">要改善</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {
                      Object.values(webVitals).filter((v, i) => {
                        const vital = Object.keys(webVitals)[i];
                        return getVitalRating(vital, v) === "poor";
                      }).length
                    }
                  </div>
                  <p className="text-sm text-gray-600">不良</p>
                </div>
              </div>
            </div>
          </div>

          {/* Browser Information */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">
              ブラウザ情報
            </h3>
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">User Agent:</span>
                  <p className="font-mono text-xs text-gray-900 mt-1 break-all">
                    {typeof navigator !== "undefined"
                      ? navigator.userAgent
                      : "N/A"}
                  </p>
                </div>
                <div>
                  <span className="text-gray-600">画面サイズ:</span>
                  <p className="text-gray-900 mt-1">
                    {typeof window !== "undefined"
                      ? `${window.innerWidth} × ${window.innerHeight}`
                      : "N/A"}
                  </p>
                </div>
                <div>
                  <span className="text-gray-600">接続状態:</span>
                  <p className="text-gray-900 mt-1">
                    {typeof navigator !== "undefined" && navigator.onLine
                      ? "✅ オンライン"
                      : "❌ オフライン"}
                  </p>
                </div>
                <div>
                  <span className="text-gray-600">タイムゾーン:</span>
                  <p className="text-gray-900 mt-1">
                    {Intl.DateTimeFormat().resolvedOptions().timeZone}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Error Status */}
          {sessionSummary.errorsCount > 0 && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">
                エラー状況
              </h3>
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center">
                  <svg
                    className="w-5 h-5 text-red-400 mr-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <div>
                    <p className="text-sm font-medium text-red-800">
                      {sessionSummary.errorsCount} 件のエラーが検出されました
                    </p>
                    <p className="text-xs text-red-700 mt-1">
                      詳細はコンソールログを確認してください。
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Refresh Controls */}
          <div className="flex items-center justify-between pt-4 border-t border-gray-200">
            <button
              onClick={updateData}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
            >
              データを更新
            </button>
            <p className="text-xs text-gray-500">自動更新: 5秒ごと</p>
          </div>
        </div>
      </div>
    </div>
  );
}
