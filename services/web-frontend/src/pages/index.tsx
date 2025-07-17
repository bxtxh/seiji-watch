import React, { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import SearchInterface from "@/components/SearchInterface";
import KanbanBoard from "@/components/KanbanBoard";

export default function Home() {
  const [showSystemError, setShowSystemError] = useState(false);

  const handleSearchButtonClick = () => {
    const searchInput = document.getElementById("search");
    if (searchInput) {
      searchInput.focus();
      searchInput.scrollIntoView({ behavior: "smooth" });
    }
  };

  useEffect(() => {
    const checkSystemHealth = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/health`,
          {
            method: "GET",
            headers: { "Content-Type": "application/json" },
          },
        );

        if (!response.ok) {
          setShowSystemError(true);
        }
      } catch (error) {
        console.error("System health check failed:", error);
        setShowSystemError(true);
      }
    };

    checkSystemHealth();
    const interval = setInterval(checkSystemHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Layout>
      <div className="space-y-8">
        {/* Hero Section */}
        <div className="hero-section text-center py-8 sm:py-16 px-4 sm:px-8 mb-6 sm:mb-8 fade-in-up">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 japanese-heading animate-slide-down leading-tight">
            国はいま、何を話しているんだろう？
          </h1>
          <p
            className="mt-3 sm:mt-4 text-sm sm:text-base lg:text-lg text-gray-600 max-w-3xl mx-auto japanese-body animate-fade-in leading-relaxed"
            style={{ animationDelay: "0.2s" }}
          >
            国会で審議される法案を簡単に検索・追跡できるシステムです。いま、国が取り扱っている議論や課題を誰の目にもわかりやすく届けます。
          </p>

          <div className="mt-4 sm:mt-6 flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center items-center px-2 sm:px-4">
            <button
              onClick={handleSearchButtonClick}
              className="w-full sm:w-auto sm:min-w-44 bg-blue-600 text-white px-4 sm:px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors text-sm sm:text-base text-center"
            >
              法案を検索する
            </button>
            <a
              href="/speeches"
              className="w-full sm:w-auto sm:min-w-44 bg-white text-blue-600 px-4 sm:px-6 py-3 rounded-lg font-medium border border-blue-600 hover:bg-blue-50 transition-colors text-sm sm:text-base text-center"
            >
              最新の議論をみる
            </a>
          </div>
        </div>

        {/* Kanban Board Section */}
        <div className="space-y-4 sm:space-y-6">
          <KanbanBoard className="animate-fade-in" />
        </div>

        {/* Main Search Interface */}
        <SearchInterface />

        {/* Features Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-6 sm:mb-8 stagger-children">
          <div className="card-interactive text-center p-4 sm:p-6">
            <div className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 sm:mb-4 bg-primary-green bg-opacity-10 rounded-lg flex items-center justify-center interactive-scale">
              <svg
                className="w-5 h-5 sm:w-6 sm:h-6 text-primary-green"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v6a2 2 0 002 2h6a2 2 0 002-2V9a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                />
              </svg>
            </div>
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-2">
              論点を抽出
            </h3>
            <p className="text-xs sm:text-sm text-gray-600 japanese-text leading-relaxed">
              政治の場で扱われている法案を基に論点を可視化します
            </p>
          </div>

          <div className="card-interactive text-center p-4 sm:p-6">
            <div className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 sm:mb-4 bg-primary-green bg-opacity-10 rounded-lg flex items-center justify-center interactive-scale">
              <svg
                className="w-5 h-5 sm:w-6 sm:h-6 text-primary-green"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-2">
              リアルタイム更新
            </h3>
            <p className="text-xs sm:text-sm text-gray-600 japanese-text leading-relaxed">
              法案の審議状況や進捗をリアルタイム（日次）で更新します。
            </p>
          </div>

          <div className="card-interactive text-center p-4 sm:p-6 sm:col-span-2 lg:col-span-1">
            <div className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 sm:mb-4 bg-primary-green bg-opacity-10 rounded-lg flex items-center justify-center interactive-scale">
              <svg
                className="w-5 h-5 sm:w-6 sm:h-6 text-primary-green"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 17h5l-5 5-5-5h5v-5a7.5 7.5 0 00-15 0v5h5l-5 5-5-5h5v-5a9.5 9.5 0 0119 0v5z"
                />
              </svg>
            </div>
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-2">
              論点をウォッチ！
            </h3>
            <p className="text-xs sm:text-sm text-gray-600 japanese-text leading-relaxed">
              論点や議案に動きがあった時には、更新内容が通知されます
            </p>
          </div>
        </div>

        {/* Usage Instructions */}
        <div className="card bg-gray-50 border-gray-200 overflow-hidden p-4 sm:p-6">
          <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-3 sm:mb-4">
            使い方
          </h2>
          <div className="space-y-3 sm:space-y-4 text-xs sm:text-sm text-gray-700 japanese-text">
            <div className="flex items-start">
              <span className="flex-shrink-0 w-5 h-5 sm:w-6 sm:h-6 bg-primary-green text-white rounded-full flex items-center justify-center text-xs font-medium mr-2 sm:mr-3 mt-0.5">
                1
              </span>
              <div className="flex-1 min-w-0">
                <p className="leading-relaxed break-words overflow-wrap-anywhere">
                  上の検索ボックスに探したいキーワードを入力してください。例:
                  「税制改正」「社会保障」「予算」
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <span className="flex-shrink-0 w-5 h-5 sm:w-6 sm:h-6 bg-primary-green text-white rounded-full flex items-center justify-center text-xs font-medium mr-2 sm:mr-3 mt-0.5">
                2
              </span>
              <div className="flex-1 min-w-0">
                <p className="leading-relaxed break-words overflow-wrap-anywhere">
                  検索結果から興味のある法案をクリックして詳細情報を確認できます。
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <span className="flex-shrink-0 w-5 h-5 sm:w-6 sm:h-6 bg-primary-green text-white rounded-full flex items-center justify-center text-xs font-medium mr-2 sm:mr-3 mt-0.5">
                3
              </span>
              <div className="flex-1 min-w-0">
                <p className="leading-relaxed break-words overflow-wrap-anywhere">
                  「詳細を見る」をクリックすると、法案の詳細や参議院ウェブサイトへのリンクが表示されます。
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* System Error Popup */}
        {showSystemError && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg p-4 sm:p-6 max-w-md w-full mx-4 shadow-xl">
              <div className="flex items-center mb-3 sm:mb-4">
                <svg
                  className="h-5 w-5 sm:h-6 sm:w-6 text-red-500 mr-2 sm:mr-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.966-.833-2.736 0L3.077 16.5c-.77.833.192 2.5 1.732 2.5z"
                  />
                </svg>
                <h3 className="text-base sm:text-lg font-semibold text-gray-900">
                  システム通知
                </h3>
              </div>
              <p className="text-sm sm:text-base text-gray-700 mb-4 leading-relaxed">
                システムが一時的に動作しておりません。しばらく時間をおいてから再度お試しください。
              </p>
              <div className="flex flex-col sm:flex-row justify-end space-y-2 sm:space-y-0 sm:space-x-3">
                <button
                  onClick={() => setShowSystemError(false)}
                  className="w-full sm:w-auto px-4 py-2 text-sm sm:text-base text-gray-600 hover:text-gray-800 transition-colors"
                >
                  閉じる
                </button>
                <button
                  onClick={() => window.location.reload()}
                  className="w-full sm:w-auto px-4 py-2 text-sm sm:text-base bg-primary-green text-white rounded-lg hover:bg-green-600 transition-colors"
                >
                  再読み込み
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
