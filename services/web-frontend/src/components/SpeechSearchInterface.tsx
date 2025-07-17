import React, { useState, useEffect } from "react";
import { apiClient, handleApiError } from "@/lib/api";
import { Speech } from "@/types";
import SpeechCard from "./SpeechCard";
import {
  sanitizeInput,
  validateSearchQuery,
  RateLimiter,
  sanitizeHtml,
  INPUT_LIMITS,
} from "@/utils/security";
import { useSecureForm, useSecurityLogger } from "@/contexts/SecurityContext";
import { useObservability } from "@/lib/observability";

// Rate limiter for speech search (10 requests per minute)
const speechSearchRateLimiter = new RateLimiter(60000, 10);

// Predefined topic categories for filtering
const TOPIC_CATEGORIES = [
  "予算・決算",
  "税制",
  "社会保障",
  "外交・国際",
  "経済・産業",
  "教育",
  "環境",
  "防衛",
  "法務",
  "労働",
  "農業",
  "医療・健康",
  "科学技術",
  "地方自治",
  "選挙制度",
  "憲法",
  "災害対策",
  "交通・インフラ",
  "文化・スポーツ",
  "その他",
];

interface SpeechSearchStats {
  total: number;
  processed: number;
  duration?: number;
}

export default function SpeechSearchInterface() {
  const [query, setQuery] = useState("");
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [results, setResults] = useState<Speech[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [searchStats, setSearchStats] = useState<SpeechSearchStats | null>(
    null,
  );
  const [showTopicFilter, setShowTopicFilter] = useState(false);

  // Security hooks
  const secureForm = useSecureForm();
  const { logSecurityEvent } = useSecurityLogger();

  // Observability hooks
  const { recordInteraction, recordError, recordMetric, startTimer } =
    useObservability();

  const handleSearch = async (searchQuery: string, topics: string[] = []) => {
    const stopTimer = startTimer("speech_search_operation");

    // Clear previous errors
    setError(null);
    setValidationError(null);

    if (!searchQuery.trim() && topics.length === 0) {
      setResults([]);
      setSearchStats(null);
      recordInteraction({ type: "search", element: "search_input", value: "" });
      stopTimer();
      return;
    }

    // Record search attempt
    recordInteraction({
      type: "search",
      element: "search_input",
      value: searchQuery,
    });

    // Sanitize input
    const sanitizedQuery = sanitizeInput(
      searchQuery,
      INPUT_LIMITS.SEARCH_QUERY,
    );

    // Validate input if query is not empty
    if (sanitizedQuery.trim()) {
      const validation = validateSearchQuery(sanitizedQuery);
      if (!validation.isValid) {
        setValidationError(validation.error || "無効な検索クエリです");
        setResults([]);
        setSearchStats(null);
        logSecurityEvent("invalid_input", {
          query: sanitizedQuery,
          error: validation.error,
        });

        recordError({
          error: new Error(validation.error || "Invalid search query"),
          context: "speech_search_validation",
          timestamp: Date.now(),
          additionalData: { query: sanitizedQuery },
        });

        stopTimer();
        return;
      }
    }

    // Rate limiting check
    const clientId =
      "speech_search_" +
      (typeof window !== "undefined" ? window.location.hostname : "server");
    if (!speechSearchRateLimiter.isAllowed(clientId)) {
      setError("検索回数の上限に達しました。しばらくお待ちください。");
      logSecurityEvent("rate_limit_exceeded", { clientId });

      recordError({
        error: new Error("Speech search rate limit exceeded"),
        context: "speech_search_rate_limit",
        timestamp: Date.now(),
        additionalData: { clientId },
      });

      stopTimer();
      return;
    }

    if (!secureForm.isReady) {
      setError("セキュリティの初期化中です。しばらくお待ちください。");
      stopTimer();
      return;
    }

    setLoading(true);
    const startTime = Date.now();

    try {
      let response;

      if (topics.length > 0 && !sanitizedQuery.trim()) {
        // Topic-only search
        response = await apiClient.searchSpeechesByTopic(topics[0], 50); // Use first topic for now
      } else {
        // Text search (implement when API is ready)
        response = await apiClient.searchSpeeches(sanitizedQuery, 50);
      }

      if (response.success) {
        const duration = Date.now() - startTime;
        const speeches = response.results || [];

        // Filter by additional topics if multiple are selected
        let filteredSpeeches = speeches;
        if (topics.length > 1) {
          filteredSpeeches = speeches.filter(
            (speech) =>
              speech.topics &&
              topics.every((topic: string) =>
                speech.topics!.some((speechTopic: string) =>
                  speechTopic.includes(topic),
                ),
              ),
          );
        }

        setResults(filteredSpeeches);
        setSearchStats({
          total: filteredSpeeches.length,
          processed: filteredSpeeches.filter((s) => s.is_processed).length,
          duration,
        });

        // Record successful search metrics
        recordMetric({
          name: "speech_search.success",
          value: duration,
          timestamp: Date.now(),
          tags: {
            result_count: filteredSpeeches.length.toString(),
            has_results: (filteredSpeeches.length > 0).toString(),
            has_topics: (topics.length > 0).toString(),
            has_query: (sanitizedQuery.trim().length > 0).toString(),
          },
        });
      } else {
        setError(sanitizeHtml(response.message || "検索に失敗しました"));
        setResults([]);
        setSearchStats(null);

        recordError({
          error: new Error(response.message || "Speech search failed"),
          context: "speech_search_api_failure",
          timestamp: Date.now(),
          additionalData: {
            query: sanitizedQuery,
            topics,
            response: response.message,
          },
        });
      }
    } catch (err) {
      setError(sanitizeHtml(handleApiError(err)));
      setResults([]);
      setSearchStats(null);

      recordError({
        error: err as Error,
        context: "speech_search_exception",
        timestamp: Date.now(),
        additionalData: { query: sanitizedQuery, topics },
      });
    } finally {
      setLoading(false);
      stopTimer();
    }
  };

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (query || selectedTopics.length > 0) {
        handleSearch(query, selectedTopics);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [query, selectedTopics]);

  const handleTopicToggle = (topic: string) => {
    setSelectedTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic],
    );
  };

  const handleTopicClick = (topic: string) => {
    if (!selectedTopics.includes(topic)) {
      setSelectedTopics((prev) => [...prev, topic]);
    }
  };

  const clearFilters = () => {
    setQuery("");
    setSelectedTopics([]);
    setResults([]);
    setSearchStats(null);
    setError(null);
    setValidationError(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch(query, selectedTopics);
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Search Form */}
      <div className="card p-4 sm:p-6">
        <form onSubmit={handleSubmit} className="space-y-3 sm:space-y-4">
          <div>
            <label
              htmlFor="speech-search"
              className="block text-sm sm:text-base font-medium text-gray-700 mb-2"
            >
              発言を検索
            </label>
            <div className="relative">
              <input
                id="speech-search"
                type="text"
                value={query}
                onChange={(e) => {
                  const input = e.target.value;
                  if (input.length <= INPUT_LIMITS.SEARCH_QUERY) {
                    setQuery(input);
                    setValidationError(null);
                  } else {
                    setValidationError(
                      `検索クエリは${INPUT_LIMITS.SEARCH_QUERY}文字以内で入力してください`,
                    );
                  }
                }}
                placeholder="発言内容を検索..."
                className={`search-input text-sm sm:text-base ${validationError ? "border-red-300 focus:border-red-500" : ""}`}
                aria-describedby="speech-search-help"
                autoComplete="off"
                maxLength={INPUT_LIMITS.SEARCH_QUERY}
              />
              {loading && (
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  <div className="loading-dots">
                    <div></div>
                    <div></div>
                    <div></div>
                  </div>
                </div>
              )}
            </div>
            {validationError ? (
              <p className="mt-2 text-xs sm:text-sm text-red-600" role="alert">
                {validationError}
              </p>
            ) : (
              <p
                id="speech-search-help"
                className="mt-2 text-xs sm:text-sm text-gray-600"
              >
                国会での発言内容を検索できます（{INPUT_LIMITS.SEARCH_QUERY}
                文字まで）
              </p>
            )}
          </div>

          {/* Topic Filter Toggle */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between space-y-2 sm:space-y-0">
            <button
              type="button"
              onClick={() => setShowTopicFilter(!showTopicFilter)}
              className="flex items-center space-x-2 text-xs sm:text-sm text-gray-600 hover:text-gray-900"
            >
              <svg
                className={`h-3 w-3 sm:h-4 sm:w-4 transition-transform ${showTopicFilter ? "rotate-90" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
              <span>トピックでフィルタ</span>
              {selectedTopics.length > 0 && (
                <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                  {selectedTopics.length}
                </span>
              )}
            </button>

            {(query || selectedTopics.length > 0) && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-xs sm:text-sm text-gray-500 hover:text-gray-700 self-start sm:self-auto"
              >
                フィルタをクリア
              </button>
            )}
          </div>

          {/* Topic Filter */}
          {showTopicFilter && (
            <div className="border-t pt-3 sm:pt-4">
              <p className="text-xs sm:text-sm font-medium text-gray-700 mb-3">
                トピックを選択
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 sm:gap-3">
                {TOPIC_CATEGORIES.map((topic) => (
                  <label
                    key={topic}
                    className="flex items-center space-x-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedTopics.includes(topic)}
                      onChange={() => handleTopicToggle(topic)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 w-3 h-3 sm:w-4 sm:h-4"
                    />
                    <span className="text-xs sm:text-sm text-gray-700">
                      {topic}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={
              loading ||
              (!query.trim() && selectedTopics.length === 0) ||
              !!validationError
            }
            className="w-full sm:w-auto btn-primary disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base"
          >
            {loading ? "検索中..." : "検索する"}
          </button>
        </form>

        {/* Search Stats */}
        {searchStats && (
          <div className="mt-3 sm:mt-4 p-3 bg-gray-50 rounded-md">
            <p className="text-xs sm:text-sm text-gray-600">
              {searchStats.total}件の発言が見つかりました
              <span className="ml-2 text-xs text-gray-500">
                (AI処理済み: {searchStats.processed}件)
              </span>
              {searchStats.duration && (
                <span className="ml-2 text-xs text-gray-500">
                  ({searchStats.duration}ms)
                </span>
              )}
            </p>
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="card bg-red-50 border-red-200 p-4 sm:p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg
                className="h-4 w-4 sm:h-5 sm:w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-2 sm:ml-3">
              <h3 className="text-sm sm:text-base font-medium text-red-800">
                検索エラー
              </h3>
              <p className="mt-1 text-xs sm:text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Search Results */}
      {results.length > 0 && (
        <div className="space-y-3 sm:space-y-4">
          <h2 className="text-base sm:text-lg font-semibold text-gray-900">
            発言検索結果
          </h2>

          <div className="grid gap-3 sm:gap-4">
            {results.map((speech, index) => (
              <SpeechCard
                key={`${speech.id}-${index}`}
                speech={speech}
                onTopicClick={handleTopicClick}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {(query || selectedTopics.length > 0) &&
        !loading &&
        results.length === 0 &&
        !error && (
          <div className="text-center py-8 sm:py-12">
            <svg
              className="mx-auto h-10 w-10 sm:h-12 sm:w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <h3 className="mt-2 text-sm sm:text-base font-medium text-gray-900">
              該当する発言が見つかりませんでした
            </h3>
            <p className="mt-1 text-xs sm:text-sm text-gray-500">
              別のキーワードやトピックで検索してみてください
            </p>
          </div>
        )}
    </div>
  );
}
