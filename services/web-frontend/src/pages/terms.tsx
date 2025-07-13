import React from 'react';
import Layout from '@/components/Layout';

export default function Terms() {
  return (
    <Layout
      title="利用規約 - 政治ウォッチ！"
      description="政治ウォッチ！の利用規約です。ご利用前に必ずお読みください。"
    >
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 japanese-heading mb-4">
            利用規約
          </h1>
          <p className="text-gray-600 japanese-text">
            最終更新: 2025年7月11日
          </p>
        </div>

        {/* Table of Contents */}
        <nav className="bg-gray-50 rounded-lg p-6 mb-8" aria-labelledby="toc-heading">
          <h2 id="toc-heading" className="text-lg font-semibold text-gray-900 mb-4">
            目次
          </h2>
          <ol className="space-y-2 text-sm">
            <li><a href="#section-1" className="text-primary-green hover:underline">1. 総則</a></li>
            <li><a href="#section-2" className="text-primary-green hover:underline">2. 定義</a></li>
            <li><a href="#section-3" className="text-primary-green hover:underline">3. ライセンス</a></li>
            <li><a href="#section-4" className="text-primary-green hover:underline">4. 禁止事項</a></li>
            <li><a href="#section-5" className="text-primary-green hover:underline">5. 免責事項・責任制限</a></li>
            <li><a href="#section-6" className="text-primary-green hover:underline">6. 個人情報の取扱い</a></li>
            <li><a href="#section-7" className="text-primary-green hover:underline">7. 規約の改定</a></li>
            <li><a href="#section-8" className="text-primary-green hover:underline">8. 準拠法・管轄</a></li>
            <li><a href="#section-9" className="text-primary-green hover:underline">9. 問い合わせ</a></li>
          </ol>
        </nav>

        {/* Terms Content */}
        <div className="prose prose-lg max-w-none japanese-text">
          <section id="section-1" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              1. 総則
            </h2>
            <ol className="space-y-3 list-decimal list-inside">
              <li>
                本規約は、政治ウォッチ！（以下「本サービス」）の提供条件ならびに利用者と運営主体である政治ウォッチ！プロジェクトチーム（以下「当団体」）との間の権利義務関係を定める。
              </li>
              <li>
                利用者は本サービスを閲覧・利用した時点で本規約に同意したものとみなす。
              </li>
              <li>
                当団体が別途定めるプライバシーポリシーその他のポリシーは本規約の一部を構成する。
              </li>
            </ol>
          </section>

          <section id="section-2" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              2. 定義
            </h2>
            <ul className="space-y-3">
              <li>
                <strong>データ</strong> — 国会関連メタデータ、文字起こし、要約、メディアファイルその他本サービスが提供する情報資源。
              </li>
              <li>
                <strong>コード</strong> — 本サービスを構成するプログラム、スクリプト、設定ファイル。
              </li>
            </ul>
          </section>

          <section id="section-3" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              3. ライセンス
            </h2>
            <ol className="space-y-3 list-decimal list-inside">
              <li>
                データは、Creative Commons Attribution 4.0 International（CC BY 4.0）に従い、出典表示さえ行えば商用・非商用を問わず二次利用・改変・再配布を自由に行える。ただし、政府・国会その他公的機関が別途ライセンスを指定している場合は当該条件が優先する。
              </li>
              <li>
                コードは MIT ライセンスで公開する。
              </li>
              <li>
                サイト名、ロゴ、ドメインその他のブランド資産は当団体またはライセンサーが保有し、商標法等により保護される。
              </li>
            </ol>
          </section>

          <section id="section-4" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              4. 禁止事項
            </h2>
            <p className="mb-3">利用者は以下の行為を行わない。</p>
            <ul className="space-y-2 list-disc list-inside">
              <li>法令または公序良俗に反する行為</li>
              <li>本サービスの情報を虚偽の文脈で引用し、第三者に誤解を与える行為</li>
              <li>本サービスへ過度の負荷を与えるスクレイピング・自動化アクセス</li>
              <li>本サービスを妨害する行為および当団体が不適切と判断する行為</li>
            </ul>
          </section>

          <section id="section-5" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              5. 免責事項・責任制限
            </h2>
            <ol className="space-y-3 list-decimal list-inside">
              <li>
                本サービスは「現状有姿（AS IS）」で提供し、正確性・完全性・最新性を保証しない。
              </li>
              <li>
                当団体は、利用者が本サービスの情報を用いて行う一切の行為およびその結果について責任を負わない。
              </li>
              <li>
                当団体は、直接・間接を問わずいかなる損害に対しても賠償責任を負わない。
              </li>
            </ol>
          </section>

          <section id="section-6" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              6. 個人情報の取扱い
            </h2>
            <p>
              利用者のアクセスログ・Cookie 等の情報は、Google Analytics 4 などの解析ツールを通じて収集する場合がある。詳細は
              <a href="/privacy" className="text-primary-green hover:underline">プライバシーポリシー</a>
              に定める。
            </p>
          </section>

          <section id="section-7" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              7. 規約の改定
            </h2>
            <p>
              当団体は本規約を改定する場合、効力発生日より前に本サービス上で告知する。改定後に利用者が本サービスを利用した場合、改定後の規約に同意したものとみなす。
            </p>
          </section>

          <section id="section-8" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              8. 準拠法・管轄
            </h2>
            <p>
              本規約は日本法に準拠し、東京地方裁判所を第一審の専属的合意管轄裁判所とする。
            </p>
          </section>

          <section id="section-9" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              9. 問い合わせ
            </h2>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="font-semibold">政治ウォッチ！プロジェクトチーム</p>
              <p>所在地: 東京都渋谷区（詳細は問い合わせ時に開示）</p>
              <p>
                Email: 
                <a href="mailto:contact@politwatch.jp" className="text-primary-green hover:underline">
                  contact@politwatch.jp
                </a>
              </p>
            </div>
          </section>
        </div>

        {/* Navigation Links */}
        <div className="mt-12 pt-8 border-t border-gray-200">
          <div className="flex justify-between items-center">
            <a 
              href="/privacy" 
              className="text-primary-green hover:underline"
            >
              プライバシーポリシー →
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