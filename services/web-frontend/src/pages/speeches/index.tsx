import React from "react";
import Head from "next/head";
import Layout from "@/components/Layout";
import SpeechSearchInterface from "@/components/SpeechSearchInterface";

export default function SpeechesPage() {
  return (
    <>
      <Head>
        <title>発言検索 - Diet Issue Tracker</title>
        <meta
          name="description"
          content="国会での発言をAI要約とトピック分析で検索できます。議員の質問、答弁、討論を効率的に探せます。"
        />
        <meta
          name="keywords"
          content="国会,発言,検索,AI要約,トピック,質問,答弁,討論,議事録"
        />
        <meta property="og:title" content="発言検索 - Diet Issue Tracker" />
        <meta
          property="og:description"
          content="国会での発言をAI要約とトピック分析で検索できます。"
        />
        <meta property="og:type" content="website" />
        <link rel="canonical" href="/speeches" />
      </Head>

      <Layout>
        <div className="space-y-8">
          {/* Page Header */}
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl">
              国会発言検索
            </h1>
            <p className="mt-4 text-lg text-gray-600 max-w-3xl mx-auto">
              国会での議員の発言をAI技術で要約・分析し、効率的に検索できます。
              質問、答弁、討論の内容をトピック別に整理して表示します。
            </p>
          </div>

          {/* Search Interface */}
          <SpeechSearchInterface />

          {/* Key Features */}
          <div className="bg-gradient-to-r from-blue-50 to-green-50 rounded-lg p-6 md:p-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 text-center">
              AI-powered 発言分析機能
            </h2>
            <div className="grid md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                  <svg
                    className="w-6 h-6 text-blue-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">AI要約</h3>
                <p className="text-sm text-gray-600">
                  長い発言内容を1文で要約し、核心的な内容を素早く把握できます
                </p>
              </div>

              <div className="text-center">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                  <svg
                    className="w-6 h-6 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  トピック分析
                </h3>
                <p className="text-sm text-gray-600">
                  発言内容を自動分類し、関連するトピックでフィルタリング検索が可能
                </p>
              </div>

              <div className="text-center">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                  <svg
                    className="w-6 h-6 text-purple-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  スマート検索
                </h3>
                <p className="text-sm text-gray-600">
                  キーワード検索とトピック検索を組み合わせ、目的の発言を効率的に発見
                </p>
              </div>
            </div>
          </div>

          {/* Usage Guide */}
          <div className="bg-gray-50 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">使い方</h2>
            <div className="space-y-3 text-sm text-gray-600">
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold">
                  1
                </span>
                <p>
                  <strong>キーワード検索:</strong>{" "}
                  検索ボックスに関心のあるキーワードを入力してください
                </p>
              </div>
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold">
                  2
                </span>
                <p>
                  <strong>トピックフィルタ:</strong>{" "}
                  「トピックでフィルタ」を開いて関心のある分野を選択してください
                </p>
              </div>
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold">
                  3
                </span>
                <p>
                  <strong>詳細確認:</strong>{" "}
                  検索結果でAI要約を確認し、「続きを読む」で全文を表示できます
                </p>
              </div>
              <div className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold">
                  4
                </span>
                <p>
                  <strong>関連発言:</strong>{" "}
                  トピックタグをクリックして関連する他の発言を探すことができます
                </p>
              </div>
            </div>
          </div>

          {/* Technical Note */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-yellow-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-yellow-800">
                  ベータ版機能
                </h3>
                <p className="mt-1 text-sm text-yellow-700">
                  この発言検索機能はベータ版です。AI要約とトピック分析の精度向上のため、継続的に改善を行っています。
                  不正確な情報や分類がある場合がありますので、重要な判断の際は原文をご確認ください。
                </p>
              </div>
            </div>
          </div>
        </div>
      </Layout>
    </>
  );
}
