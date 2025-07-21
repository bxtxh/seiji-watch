import React from "react";
import Link from "next/link";
import Layout from "@/components/Layout";

export default function Privacy() {
  return (
    <Layout
      title="プライバシーポリシー - 政治ウォッチ！"
      description="政治ウォッチ！のプライバシーポリシーです。個人情報の取扱いについて説明しています。"
    >
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 japanese-heading mb-4">
            プライバシーポリシー
          </h1>
          <p className="text-gray-600 japanese-text">最終更新: 2025年7月11日</p>
        </div>

        {/* Table of Contents */}
        <nav
          className="bg-gray-50 rounded-lg p-6 mb-8"
          aria-labelledby="toc-heading"
        >
          <h2
            id="toc-heading"
            className="text-lg font-semibold text-gray-900 mb-4"
          >
            目次
          </h2>
          <ol className="space-y-2 text-sm">
            <li>
              <a
                href="#section-1"
                className="text-primary-green hover:underline"
              >
                1. 適用範囲
              </a>
            </li>
            <li>
              <a
                href="#section-2"
                className="text-primary-green hover:underline"
              >
                2. 取得する情報
              </a>
            </li>
            <li>
              <a
                href="#section-3"
                className="text-primary-green hover:underline"
              >
                3. 利用目的
              </a>
            </li>
            <li>
              <a
                href="#section-4"
                className="text-primary-green hover:underline"
              >
                4. アクセス解析（Google Analytics 4）
              </a>
            </li>
            <li>
              <a
                href="#section-5"
                className="text-primary-green hover:underline"
              >
                5. 第三者提供
              </a>
            </li>
            <li>
              <a
                href="#section-6"
                className="text-primary-green hover:underline"
              >
                6. 管理体制・安全管理措置
              </a>
            </li>
            <li>
              <a
                href="#section-7"
                className="text-primary-green hover:underline"
              >
                7. 利用者の権利
              </a>
            </li>
            <li>
              <a
                href="#section-8"
                className="text-primary-green hover:underline"
              >
                8. プライバシーポリシーの変更
              </a>
            </li>
            <li>
              <a
                href="#section-9"
                className="text-primary-green hover:underline"
              >
                9. お問い合わせ窓口
              </a>
            </li>
          </ol>
        </nav>

        {/* Privacy Policy Content */}
        <div className="prose prose-lg max-w-none japanese-text">
          <section id="section-1" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              1. 適用範囲
            </h2>
            <p>
              本ポリシーは、政治ウォッチ！プロジェクトチーム（以下「当団体」）が提供するウェブサイト
              politwatch.jp（以下「本サイト」）において取得する利用者情報の取扱いについて定める。
            </p>
          </section>

          <section id="section-2" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              2. 取得する情報
            </h2>
            <p className="mb-4">本サイトは、現時点で次の情報のみを取得する。</p>
            <ol className="space-y-3 list-decimal list-inside">
              <li>
                <strong>アクセスログ</strong> — IP
                アドレス、ブラウザ種別、リファラー、閲覧日時等。
              </li>
              <li>
                <strong>Cookie 等</strong> — Google Analytics
                4（以下「GA4」）が発行する Client ID
                など。氏名・メールアドレス等の直接識別子は含まない。
              </li>
              <li>
                <strong>お問い合わせメール</strong> —
                利用者が当団体宛に送信するメール本文・送信元アドレス。
              </li>
            </ol>
            <div className="mt-4 p-4 bg-blue-50 border-l-4 border-blue-400 rounded">
              <p className="text-sm text-blue-800">
                <strong>将来の機能追加について：</strong>
                将来の機能追加（例:
                お問い合わせフォーム）により新たな情報を取得する場合、本ポリシーを改定して告知します。
              </p>
            </div>
          </section>

          <section id="section-3" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              3. 利用目的
            </h2>
            <p className="mb-3">取得した情報は次の目的で利用する。</p>
            <ul className="space-y-2 list-disc list-inside">
              <li>サイト利用状況の解析およびコンテンツ改善</li>
              <li>システム障害・不正アクセスの検知と防止</li>
              <li>利用者からの問い合わせ対応</li>
            </ul>
          </section>

          <section id="section-4" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              4. アクセス解析（Google Analytics 4）
            </h2>
            <ol className="space-y-3 list-decimal list-inside">
              <li>
                本サイトは GA4 を用いてトラフィックデータを収集・解析する。
              </li>
              <li>
                GA4 では IP 匿名化(Anonymize IP)
                オプションを有効化しており、収集した IP
                アドレスの末尾は即時にマスクされる。
              </li>
              <li>
                収集データは Google LLC
                のプライバシーポリシーに基づき米国など国外サーバーへ転送・保管される場合がある。
              </li>
              <li>
                利用者はブラウザ設定で Cookie を拒否、または
                <a
                  href="https://adssettings.google.com/authenticated"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-green hover:underline"
                >
                  Google の広告設定ページ
                </a>
                から収集をオプトアウトできる。
              </li>
              <li>
                <strong>データ保持期間は 14 か月。</strong>
              </li>
            </ol>
          </section>

          <section id="section-5" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              5. 第三者提供
            </h2>
            <p className="mb-3">
              当団体は、以下の場合を除き利用者情報を第三者へ提供しない。
            </p>
            <ul className="space-y-2 list-disc list-inside">
              <li>法令に基づく開示要請がある場合</li>
              <li>人の生命・身体・財産の保護に必要で本人同意が困難な場合</li>
              <li>
                アクセス統計を個人を識別できない形に加工した上で公開または共有する場合
              </li>
            </ul>
          </section>

          <section id="section-6" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              6. 管理体制・安全管理措置
            </h2>
            <ul className="space-y-2 list-disc list-inside">
              <li>通信は TLS で暗号化</li>
              <li>
                アクセスログは権限管理された環境に保管し、90 日経過後に自動削除
              </li>
              <li>
                個人情報データベースへのアクセスは最小権限・多要素認証を適用
              </li>
              <li>
                セキュリティ詳細（ファイアウォール設定等）は公開しませんが、適切な技術的・組織的対策を継続的に実施します。
              </li>
            </ul>
          </section>

          <section id="section-7" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              7. 利用者の権利
            </h2>
            <p className="mb-3">
              利用者は、個人情報保護法に基づき次の請求ができる。
            </p>
            <ul className="space-y-2 list-disc list-inside mb-4">
              <li>開示・訂正・追加・削除</li>
              <li>利用停止・第三者提供停止</li>
            </ul>
            <p>請求は「9. お問い合わせ窓口」までメールで行うものとする。</p>
          </section>

          <section id="section-8" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              8. プライバシーポリシーの変更
            </h2>
            <p>
              当団体は本ポリシーを改定する場合、効力発生日より前に本サイト上で告知する。改定後に利用者が本サイトを利用した場合、改定後のポリシーに同意したものとみなす。
            </p>
          </section>

          <section id="section-9" className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">
              9. お問い合わせ窓口
            </h2>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="font-semibold">政治ウォッチ！プロジェクトチーム</p>
              <p>所在地: 東京都渋谷区（詳細はお問い合わせ時に開示）</p>
              <p>
                Email:
                <a
                  href="mailto:privacy@politwatch.jp"
                  className="text-primary-green hover:underline"
                >
                  privacy@politwatch.jp
                </a>
              </p>
            </div>
          </section>
        </div>

        {/* Privacy Notice */}
        <div className="mt-8 p-4 bg-green-50 border border-green-200 rounded-lg">
          <h3 className="text-lg font-semibold text-green-800 mb-2">
            個人情報保護について
          </h3>
          <p className="text-green-700 text-sm">
            当サイトでは、個人情報保護法に基づき、利用者の個人情報を適切に管理し、
            プライバシーの保護に努めています。ご不明な点がございましたら、
            お気軽にお問い合わせください。
          </p>
        </div>

        {/* Navigation Links */}
        <div className="mt-12 pt-8 border-t border-gray-200">
          <div className="flex justify-between items-center">
            <Link href="/terms/" className="text-primary-green hover:underline">
              ← 利用規約
            </Link>
            <Link
              href="/"
              className="bg-primary-green text-white px-4 py-2 rounded-lg hover:bg-green-600 transition-colors"
            >
              ホームに戻る
            </Link>
          </div>
        </div>
      </div>
    </Layout>
  );
}
