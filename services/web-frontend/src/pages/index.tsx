import React, { useEffect, useState } from 'react';
import Layout from '@/components/Layout';
import SearchInterface from '@/components/SearchInterface';
import KanbanBoard from '@/components/KanbanBoard';

export default function Home() {
  const [showSystemError, setShowSystemError] = useState(false);

  useEffect(() => {
    const checkSystemHealth = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/health', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
          setShowSystemError(true);
        }
      } catch (error) {
        console.error('System health check failed:', error);
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
        <div className="hero-section text-center rounded-2xl p-8 mb-8 fade-in-up">
          <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl japanese-heading animate-slide-down">
            政治ウォッチ！
          </h1>
          <h3 className="mt-3 text-xl font-semibold text-gray-700 japanese-heading animate-fade-in" style={{animationDelay: '0.1s'}}>
            <em>国会で議論されていることを見つめる</em>
          </h3>
          <p className="mt-4 text-lg text-gray-600 max-w-3xl mx-auto japanese-body animate-fade-in" style={{animationDelay: '0.2s'}}>
            国会で議論されていることをAIによって分析・整理します。いま、国が取り扱っている社会課題（イシュー）を誰の目にもわかりやすく届けます。
          </p>
        </div>



        {/* Features Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 stagger-children">
          <div className="card-interactive text-center">
            <div className="w-12 h-12 mx-auto mb-4 bg-primary-green bg-opacity-10 rounded-lg flex items-center justify-center interactive-scale">
              <svg className="w-6 h-6 text-primary-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">AI検索</h3>
            <p className="text-sm text-gray-600 japanese-text">
              ベクトル類似度を使用した高度な検索機能で、関連する法案を的確に見つけます。
            </p>
          </div>

          <div className="card-interactive text-center">
            <div className="w-12 h-12 mx-auto mb-4 bg-primary-green bg-opacity-10 rounded-lg flex items-center justify-center interactive-scale">
              <svg className="w-6 h-6 text-primary-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">モバイル対応</h3>
            <p className="text-sm text-gray-600 japanese-text">
              スマートフォンやタブレットでも快適に利用できるレスポンシブデザインです。
            </p>
          </div>

          <div className="card-interactive text-center">
            <div className="w-12 h-12 mx-auto mb-4 bg-primary-green bg-opacity-10 rounded-lg flex items-center justify-center interactive-scale">
              <svg className="w-6 h-6 text-primary-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              <a href="/issues/categories" className="hover:text-primary-green transition-colors">
                政策分野
              </a>
            </h3>
            <p className="text-sm text-gray-600 japanese-text">
              CAP基準の国際標準政策分類で、関心のある分野から法案を効率的に探せます。
            </p>
          </div>

          <div className="card-interactive text-center">
            <div className="w-12 h-12 mx-auto mb-4 bg-primary-green bg-opacity-10 rounded-lg flex items-center justify-center interactive-scale">
              <svg className="w-6 h-6 text-primary-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">アクセシブル</h3>
            <p className="text-sm text-gray-600 japanese-text">
              色覚バリアフリー対応、ふりがな表示、キーボード操作対応などの配慮があります。
            </p>
          </div>
        </div>

        {/* Kanban Board Section */}
        <div className="space-y-6">
          <KanbanBoard className="animate-fade-in" />
        </div>

        {/* Main Search Interface */}
        <SearchInterface />

        {/* Usage Instructions */}
        <div className="card bg-gray-50 border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">使い方</h2>
          <div className="space-y-3 text-sm text-gray-700 japanese-text">
            <div className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-primary-green text-white rounded-full flex items-center justify-center text-xs font-medium mr-3 mt-0.5">
                1
              </span>
              <p>
                上の検索ボックスに探したいキーワードを入力してください。例: 「税制改正」「社会保障」「予算」
              </p>
            </div>
            <div className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-primary-green text-white rounded-full flex items-center justify-center text-xs font-medium mr-3 mt-0.5">
                2
              </span>
              <p>
                検索結果から興味のある法案をクリックして詳細情報を確認できます。
              </p>
            </div>
            <div className="flex items-start">
              <span className="flex-shrink-0 w-6 h-6 bg-primary-green text-white rounded-full flex items-center justify-center text-xs font-medium mr-3 mt-0.5">
                3
              </span>
              <p>
                「詳細を見る」をクリックすると、法案の詳細や参議院ウェブサイトへのリンクが表示されます。
              </p>
            </div>
          </div>
        </div>

        {/* System Error Popup */}
        {showSystemError && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md mx-4 shadow-xl">
              <div className="flex items-center mb-4">
                <svg className="h-6 w-6 text-red-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.966-.833-2.736 0L3.077 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <h3 className="text-lg font-semibold text-gray-900">システム通知</h3>
              </div>
              <p className="text-gray-700 mb-4">
                システムが一時的に動作しておりません。しばらく時間をおいてから再度お試しください。
              </p>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowSystemError(false)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                >
                  閉じる
                </button>
                <button
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-primary-green text-white rounded-lg hover:bg-green-600 transition-colors"
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