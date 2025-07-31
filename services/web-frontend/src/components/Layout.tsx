import React from "react";
import Head from "next/head";
import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import DebugInfo from "./DebugInfo";

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
}

export default function Layout({
  children,
  title = "政治ウォッチ！",
  description = "国会で議論されていることをAIによって分析・整理し、社会課題をわかりやすく届けます。",
}: LayoutProps) {
  // Furigana state - feature disabled for initial release
  // To enable: Set NEXT_PUBLIC_ENABLE_FURIGANA=true in .env.local
  const [furiganaEnabled, setFuriganaEnabled] = useState(false);

  return (
    <>
      <Head>
        <title>{title}</title>
        <meta name="description" content={description} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#27AE60" />
        <link rel="icon" href="/favicon.png" />

        {/* PWA Meta Tags */}
        <link rel="manifest" href="/manifest.json" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />

        {/* Open Graph Meta Tags */}
        <meta property="og:type" content="website" />
        <meta property="og:title" content={title} />
        <meta property="og:description" content={description} />
        <meta property="og:site_name" content="政治ウォッチ！" />

        {/* Accessibility */}
        <meta name="color-scheme" content="light" />
      </Head>

      <div
        className={`min-h-screen bg-gray-50 ${furiganaEnabled ? "furigana-enabled" : ""}`}
      >
        {/* Header */}
        <header
          className="bg-white shadow-sm border-b border-gray-200 fixed top-0 left-0 right-0 z-50 backdrop-blur-md"
          style={{
            background:
              "linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 249, 250, 0.98) 100%)",
          }}
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              {/* Logo and title */}
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Link href="/" className="flex items-center">
                    <Image
                      src="/logo.svg"
                      alt="政治ウォッチ！"
                      width={32}
                      height={32}
                      className="h-8 w-auto"
                    />
                  </Link>
                </div>

                {/* Navigation */}
                <nav className="ml-8 hidden md:flex space-x-8">
                  <Link
                    href="/"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                  >
                    法案検索
                  </Link>
                  <Link
                    href="/speeches"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                  >
                    発言検索
                  </Link>
                  <Link
                    href="/members"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                  >
                    議員一覧
                  </Link>
                  <Link
                    href="/issues/categories"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                  >
                    政策分野
                  </Link>
                  <Link
                    href="/issues"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                  >
                    イシュー
                  </Link>

                  {/* Legal dropdown */}
                  <div className="relative group">
                    <button
                      type="button"
                      className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium inline-flex items-center"
                      aria-expanded="false"
                      aria-haspopup="true"
                    >
                      法的情報
                      <svg
                        className="ml-1 h-4 w-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </button>

                    <div className="absolute left-0 mt-1 w-48 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                      <div className="bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5">
                        <div className="py-1">
                          <Link
                            href="/terms"
                            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                          >
                            利用規約
                          </Link>
                          <Link
                            href="/privacy"
                            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                          >
                            プライバシーポリシー
                          </Link>
                        </div>
                      </div>
                    </div>
                  </div>
                </nav>
              </div>

              {/* Accessibility controls */}
              <div className="flex items-center space-x-4">
                {/* Furigana toggle - disabled for initial release */}
                {process.env.NEXT_PUBLIC_ENABLE_FURIGANA === "true" && (
                  <button
                    type="button"
                    onClick={() => setFuriganaEnabled(!furiganaEnabled)}
                    className={`px-3 py-1 text-sm rounded-md transition-colors ${
                      furiganaEnabled
                        ? "bg-primary-green text-white"
                        : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                    }`}
                    aria-label={`ふりがな表示を${furiganaEnabled ? "オフ" : "オン"}にする`}
                  >
                    ふりがな
                  </button>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-4 sm:py-8 pt-18 sm:pt-24">
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-gray-50 border-t border-gray-200 mt-12 sm:mt-16">
          <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-6 sm:py-8">
            {/* Header with Logo */}
            <div className="flex items-center mb-6">
              <div className="flex items-center">
                <Image
                  src="/logo.svg"
                  alt="政治ウォッチ！"
                  width={24}
                  height={24}
                  className="h-6 w-auto"
                />
              </div>
            </div>

            {/* Navigation Links */}
            <div className="mb-6">
              <nav className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                <Link
                  href="/"
                  className="text-blue-600 hover:text-blue-800 transition-colors"
                >
                  法案検索
                </Link>
                <span className="text-gray-300">|</span>
                <Link
                  href="/speeches"
                  className="text-blue-600 hover:text-blue-800 transition-colors"
                >
                  発言検索
                </Link>
                <span className="text-gray-300">|</span>
                <Link
                  href="/members"
                  className="text-blue-600 hover:text-blue-800 transition-colors"
                >
                  議員一覧
                </Link>
                <span className="text-gray-300">|</span>
                <Link
                  href="/issues/categories"
                  className="text-blue-600 hover:text-blue-800 transition-colors"
                >
                  政策分野
                </Link>
                <span className="text-gray-300">|</span>
                <Link
                  href="/issues"
                  className="text-blue-600 hover:text-blue-800 transition-colors"
                >
                  イシュー
                </Link>
                <span className="text-gray-300">|</span>
                <Link
                  href="/terms"
                  className="text-blue-600 hover:text-blue-800 transition-colors"
                >
                  利用規約
                </Link>
                <span className="text-gray-300">|</span>
                <Link
                  href="/privacy"
                  className="text-blue-600 hover:text-blue-800 transition-colors"
                >
                  プライバシーポリシー
                </Link>
                <span className="text-gray-300">|</span>
                <Link
                  href="/about-data"
                  className="text-blue-600 hover:text-blue-800 transition-colors"
                >
                  データについて
                </Link>
              </nav>
            </div>

            {/* Description */}
            <div className="mb-6">
              <p className="text-sm text-gray-600 leading-relaxed max-w-4xl">
                政治ウォッチは、国会議案の透明性向上と市民の政治参加促進を目的とした情報プラットフォームです。
                <br />
                正確で詳細な政治情報をわかりやすく提供し、民主主義の発展に貢献します。
                <br />
                システムに関するお問い合わせ、改善要望は、{" "}
                <Link
                  href="mailto:contact@politics-watch.jp"
                  className="text-blue-600 hover:text-blue-800 transition-colors"
                >
                  contact@politics-watch.jp
                </Link>{" "}
                までお願いします。
              </p>
            </div>
          </div>
        </footer>
        <DebugInfo />
      </div>
    </>
  );
}
