import React, { useEffect, useState } from 'react';
import Layout from '@/components/Layout';
import SearchInterface from '@/components/SearchInterface';
import KanbanBoard from '@/components/KanbanBoard';

export default function Home() {
  const [systemStatus, setSystemStatus] = useState<{
    isHealthy: boolean;
    message: string;
    stats?: {
      bills: number;
      speeches: number;
    };
  }>({ isHealthy: true, message: 'システムは正常に動作しています' });

  return (
    <Layout>
      <div className="space-y-8">
        {/* Hero Section */}
        <div className="hero-section text-center rounded-2xl p-8 mb-8 fade-in-up">
          <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl japanese-heading animate-slide-down">
            国会議事録検索システム
          </h1>
          <p className="mt-4 text-lg text-gray-600 max-w-3xl mx-auto japanese-body animate-fade-in" style={{animationDelay: '0.2s'}}>
            国会の法案や議事録をAIとキーワード検索で素早く見つけることができます。
            アクセシブルで使いやすいインターフェースで、重要な政治情報にアクセスできます。
          </p>
        </div>

        {/* System Status */}
        <div className={`card-elevated ${systemStatus.isHealthy ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'}`}>
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3 flex-1">
              <p className="text-sm font-medium text-green-800">
                {systemStatus.message}
              </p>
            </div>
          </div>
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
      </div>
    </Layout>
  );
}