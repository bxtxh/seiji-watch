import React, { useEffect, useState } from 'react';
import Layout from '@/components/Layout';
import SearchInterface from '@/components/SearchInterface';
import PWADebugPanel from '@/components/PWADebugPanel';
import ObservabilityDashboard from '@/components/ObservabilityDashboard';
import { apiClient, handleApiError } from '@/lib/api';
import { useObservability } from '@/lib/observability';

export default function Home() {
  const [systemStatus, setSystemStatus] = useState<{
    isHealthy: boolean;
    message: string;
    stats?: {
      bills: number;
      speeches: number;
    };
  }>({ isHealthy: false, message: '接続確認中...' });
  
  const [showPWADebug, setShowPWADebug] = useState(false);
  const [showObservabilityDashboard, setShowObservabilityDashboard] = useState(false);
  
  // Observability hooks
  const { recordPageView, recordError, recordMetric, measureAsync } = useObservability();

  useEffect(() => {
    let abortController = new AbortController();
    let mounted = true;

    const checkSystemHealth = async () => {
      try {
        // Record page view only once
        recordPageView('home');
        
        // Check API health with abort signal
        const health = await apiClient.checkHealth();
        const stats = await apiClient.getEmbeddingStats();
        
        // Only update state if component is still mounted
        if (mounted && !abortController.signal.aborted) {
          setSystemStatus(prevStatus => {
            const newStatus = {
              isHealthy: true,
              message: 'システムは正常に動作しています',
              stats: {
                bills: stats.bills,
                speeches: stats.speeches,
              },
            };
            
            // Avoid unnecessary re-renders by comparing previous state
            if (prevStatus.isHealthy === newStatus.isHealthy && 
                prevStatus.message === newStatus.message &&
                prevStatus.stats?.bills === newStatus.stats?.bills &&
                prevStatus.stats?.speeches === newStatus.stats?.speeches) {
              return prevStatus;
            }
            
            return newStatus;
          });

          // Record successful health check
          recordMetric({
            name: 'system.health_check.success',
            value: 1,
            timestamp: Date.now(),
            tags: {
              bills_count: stats.bills.toString(),
              speeches_count: stats.speeches.toString()
            }
          });
        }

      } catch (error) {
        if (mounted && !abortController.signal.aborted) {
          console.error('System health check failed:', error);
          
          // Record health check failure
          recordError({
            error: error as Error,
            context: 'system_health_check',
            timestamp: Date.now()
          });
          
          setSystemStatus(prevStatus => {
            const newStatus = {
              isHealthy: false,
              message: 'システムへの接続に失敗しました',
            };
            
            // Avoid unnecessary re-renders
            if (prevStatus.isHealthy === false && prevStatus.message === newStatus.message) {
              return prevStatus;
            }
            
            return newStatus;
          });

          recordMetric({
            name: 'system.health_check.failure',
            value: 1,
            timestamp: Date.now(),
            tags: { error_type: 'connection_failed' }
          });
        }
      }
    };

    checkSystemHealth();

    // Cleanup function
    return () => {
      mounted = false;
      abortController.abort();
    };
  }, []); // Empty dependency array - run only once

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
              {systemStatus.isHealthy ? (
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <div className="ml-3 flex-1">
              <p className={`text-sm font-medium ${systemStatus.isHealthy ? 'text-green-800' : 'text-yellow-800'}`}>
                {systemStatus.message}
              </p>
              {systemStatus.stats && (
                <p className="mt-1 text-sm text-gray-600">
                  データベース: {systemStatus.stats.bills}件の法案、{systemStatus.stats.speeches}件の音声記録
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Features Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 stagger-children">
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
      
      {/* PWA Debug Panel */}
      <PWADebugPanel 
        isOpen={showPWADebug} 
        onClose={() => setShowPWADebug(false)} 
      />
      
      {/* Observability Dashboard */}
      <ObservabilityDashboard 
        isOpen={showObservabilityDashboard} 
        onClose={() => setShowObservabilityDashboard(false)} 
      />
      
      {/* Development Tools Buttons - Subtle styling */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 right-4 flex flex-col space-y-2 z-10 opacity-30 hover:opacity-100 transition-opacity duration-300">
          <button
            onClick={() => setShowPWADebug(true)}
            className="bg-gray-600 text-gray-300 p-2 rounded-md shadow-sm hover:bg-gray-500 hover:text-white transition-all duration-200 text-xs"
            title="PWAデバッグパネルを開く"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          <button
            onClick={() => setShowObservabilityDashboard(true)}
            className="bg-gray-600 text-gray-300 p-2 rounded-md shadow-sm hover:bg-gray-500 hover:text-white transition-all duration-200 text-xs"
            title="可観測性ダッシュボードを開く"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </button>
        </div>
      )}
    </Layout>
  );
}