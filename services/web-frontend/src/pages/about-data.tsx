import React from 'react';
import Layout from '@/components/Layout';

export default function AboutData() {
  return (
    <Layout
      title="データについて - 政治ウォッチ"
      description="政治ウォッチで使用しているデータソースと収集方法について説明します。"
    >
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 japanese-heading mb-4">
            データについて
          </h1>
          <p className="text-gray-600 japanese-text">
            政治ウォッチで使用しているデータソースと収集方法
          </p>
        </div>

        {/* Data Sources */}
        <div className="space-y-8">
          <section className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              データソース
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* House of Representatives */}
              <div className="bg-blue-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                  <svg className="w-5 h-5 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                  衆議院
                </h3>
                <div className="space-y-2 text-sm">
                  <p>
                    <strong>公式サイト:</strong>{' '}
                    <a
                      href="https://www.shugiin.go.jp/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      www.shugiin.go.jp
                    </a>
                  </p>
                  <p><strong>収集データ:</strong></p>
                  <ul className="list-disc list-inside space-y-1 text-gray-600 ml-4">
                    <li>議員基本情報・所属政党</li>
                    <li>記名投票データ（PDF形式）</li>
                    <li>委員会投票記録</li>
                    <li>法案審議状況</li>
                  </ul>
                </div>
              </div>

              {/* House of Councillors */}
              <div className="bg-green-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                  <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                  参議院
                </h3>
                <div className="space-y-2 text-sm">
                  <p>
                    <strong>公式サイト:</strong>{' '}
                    <a
                      href="https://www.sangiin.go.jp/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-green-600 hover:underline"
                    >
                      www.sangiin.go.jp
                    </a>
                  </p>
                  <p><strong>収集データ:</strong></p>
                  <ul className="list-disc list-inside space-y-1 text-gray-600 ml-4">
                    <li>法案メタデータ・審議状況</li>
                    <li>議事録・会議録</li>
                    <li>議員投票記録</li>
                    <li>国会TV動画（HLS形式）</li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          {/* Data Collection Methods */}
          <section className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              データ収集方法
            </h2>
            
            <div className="space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">自動データ収集</h3>
                <p className="text-sm text-gray-600 mb-3">
                  両院の公式ウェブサイトから定期的にデータを自動収集しています。
                </p>
                <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                  <li>適切なレート制限（1-3秒間隔）を設けてサーバーに負荷をかけない配慮</li>
                  <li>robots.txt等のクローリングルールを遵守</li>
                  <li>エラー発生時の自動リトライ機能</li>
                  <li>データ整合性チェック機能</li>
                </ul>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">データ処理・正規化</h3>
                <p className="text-sm text-gray-600 mb-3">
                  収集したデータは統一的な形式に正規化し、検索・分析を容易にしています。
                </p>
                <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                  <li>HTML・PDF形式のデータを構造化</li>
                  <li>議員名・政党名の名寄せ処理</li>
                  <li>法案進捗状況の統一フォーマット化</li>
                  <li>AI・機械学習による内容分析</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Data Updates */}
          <section className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              データ更新頻度
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600 mb-2">1時間毎</div>
                <div className="text-sm text-gray-600">法案審議状況</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600 mb-2">6時間毎</div>
                <div className="text-sm text-gray-600">議員投票記録</div>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600 mb-2">24時間毎</div>
                <div className="text-sm text-gray-600">議員基本情報</div>
              </div>
            </div>
          </section>

          {/* Data Accuracy */}
          <section className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              データの正確性について
            </h2>
            
            <div className="space-y-4">
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-yellow-800">
                      重要な注意点
                    </h3>
                    <div className="mt-2 text-sm text-yellow-700">
                      <ul className="list-disc list-inside space-y-1">
                        <li>本サイトのデータは情報提供のみを目的とし、正確性・完全性・最新性を保証するものではありません</li>
                        <li>正式な情報については、必ず各院の公式ウェブサイトをご確認ください</li>
                        <li>データ処理過程でエラーや遅延が発生する可能性があります</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-blue-800">
                      データ品質向上への取り組み
                    </h3>
                    <div className="mt-2 text-sm text-blue-700">
                      <ul className="list-disc list-inside space-y-1">
                        <li>多段階の検証プロセスによるデータ品質チェック</li>
                        <li>ユーザーからのフィードバックによる継続的改善</li>
                        <li>定期的なデータソース整合性の確認</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Contact */}
          <section className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              お問い合わせ
            </h2>
            <p className="text-sm text-gray-600">
              データに関するご質問、エラーの報告、改善提案等がございましたら、
              <a
                href="mailto:contact@politics-watch.jp"
                className="text-blue-600 hover:underline ml-1"
              >
                contact@politics-watch.jp
              </a>
              までお気軽にお問い合わせください。
            </p>
          </section>
        </div>

        {/* Navigation Links */}
        <div className="mt-12 pt-8 border-t border-gray-200">
          <div className="flex justify-between items-center">
            <a 
              href="/privacy" 
              className="text-blue-600 hover:underline"
            >
              ← プライバシーポリシー
            </a>
            <a 
              href="/" 
              className="bg-primary-green text-white px-4 py-2 rounded-lg hover:bg-green-600 transition-colors"
            >
              ホームに戻る
            </a>
          </div>
        </div>
      </div>
    </Layout>
  );
}