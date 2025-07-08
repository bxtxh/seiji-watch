import React from 'react';
import Head from 'next/head';
import { useState } from 'react';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
}

export default function Layout({
  children,
  title = '国会議事録検索システム',
  description = '国会の法案や議事録を簡単に検索・閲覧できるシステムです。',
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
        <link rel="icon" href="/favicon.ico" />
        
        {/* PWA Meta Tags */}
        <link rel="manifest" href="/manifest.json" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        
        {/* Open Graph Meta Tags */}
        <meta property="og:type" content="website" />
        <meta property="og:title" content={title} />
        <meta property="og:description" content={description} />
        <meta property="og:site_name" content="国会議事録検索システム" />
        
        {/* Accessibility */}
        <meta name="color-scheme" content="light" />
      </Head>

      <div className={`min-h-screen bg-gray-50 ${furiganaEnabled ? 'furigana-enabled' : ''}`}>
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200 relative backdrop-blur-md" style={{
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 249, 250, 0.98) 100%)'
        }}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              {/* Logo and title */}
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <h1 className="text-xl font-bold text-gray-900">
                    国会議事録検索
                  </h1>
                </div>
                
                {/* Navigation */}
                <nav className="ml-8 hidden md:flex space-x-8">
                  <a
                    href="/"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                  >
                    法案検索
                  </a>
                  <a
                    href="/speeches"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                  >
                    発言検索
                  </a>
                  <a
                    href="/issues"
                    className="text-gray-700 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                  >
                    イシュー
                  </a>
                </nav>
              </div>

              {/* Accessibility controls */}
              <div className="flex items-center space-x-4">
                {/* Furigana toggle - disabled for initial release */}
                {process.env.NEXT_PUBLIC_ENABLE_FURIGANA === 'true' && (
                  <button
                    type="button"
                    onClick={() => setFuriganaEnabled(!furiganaEnabled)}
                    className={`px-3 py-1 text-sm rounded-md transition-colors ${
                      furiganaEnabled
                        ? 'bg-primary-green text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                    aria-label={`ふりがな表示を${furiganaEnabled ? 'オフ' : 'オン'}にする`}
                  >
                    ふりがな
                  </button>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-white border-t border-gray-200 mt-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="text-center text-sm text-gray-600">
              <p>
                &copy; 2025 国会議事録検索システム. オープンソースプロジェクト.
              </p>
              <p className="mt-2">
                データは{' '}
                <a
                  href="https://www.sangiin.go.jp/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-green hover:underline"
                >
                  参議院ウェブサイト
                </a>{' '}
                から取得しています。
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}