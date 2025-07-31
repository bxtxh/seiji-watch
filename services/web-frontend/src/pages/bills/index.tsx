import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import Layout from "@/components/Layout";
import BillCard from "@/components/BillCard";
import { Bill } from "@/types";
import { api } from "@/lib/api-client";
import {
  transformBillRecordToBill,
  type BillRecord,
} from "@/utils/data-transformers";

// BillRecord interface is now imported from data-transformers

interface SearchResponse {
  success: boolean;
  results: BillRecord[];
  total_found: number;
  query?: string;
  filters: {
    status?: string;
    stage?: string;
    policy_category_ids?: string[];
    policy_category_layer?: string;
  };
}

interface IssueCategory {
  id: string;
  fields: {
    CAP_Code: string;
    Layer: string;
    Title_JA: string;
    Title_EN?: string;
    Summary_150JA?: string;
    Parent_Category?: string[];
    Is_Seed: boolean;
  };
}

const BillsPage = () => {
  const [bills, setBills] = useState<BillRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("");
  const [selectedStage, setSelectedStage] = useState<string>("");
  const [selectedCategory, setSelectedCategory] =
    useState<IssueCategory | null>(null);
  const [totalFound, setTotalFound] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(20);

  const router = useRouter();

  // Define fetchBills early to avoid hoisting issues
  const fetchBills = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Build search request
      const searchRequest = {
        query: searchQuery || undefined,
        status: selectedStatus || undefined,
        stage: selectedStage || undefined,
        policy_category_ids: selectedCategory
          ? [selectedCategory.id]
          : undefined,
        max_records: itemsPerPage * currentPage,
      };

      const data = (await api.bills.search(searchRequest)) as SearchResponse;

      if (data.success) {
        setBills(data.results);
        setTotalFound(data.total_found);
      } else {
        throw new Error("Failed to fetch bills");
      }
    } catch (err) {
      console.error("Failed to fetch bills:", err);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(
          "データの取得に失敗しました。APIサーバーが起動しているか確認してください。"
        );
      }
    } finally {
      setLoading(false);
    }
  }, [
    searchQuery,
    selectedStatus,
    selectedStage,
    selectedCategory,
    currentPage,
    itemsPerPage,
  ]);

  const fetchCategory = async (categoryId: string) => {
    try {
      const categoryData = (await api.categories.get(
        categoryId
      )) as IssueCategory;
      setSelectedCategory(categoryData);
    } catch (err) {
      console.error("Failed to fetch category:", err);
    }
  };

  // Get initial filters from URL parameters
  useEffect(() => {
    const { query, status, stage, policy_category_id } = router.query;

    if (query && typeof query === "string") {
      setSearchQuery(query);
    }

    if (status && typeof status === "string") {
      setSelectedStatus(status);
    }

    if (stage && typeof stage === "string") {
      setSelectedStage(stage);
    }

    if (policy_category_id && typeof policy_category_id === "string") {
      fetchCategory(policy_category_id);
    }
  }, [router.query]);

  // Fetch bills when filters change
  useEffect(() => {
    fetchBills();
  }, [
    searchQuery,
    selectedStatus,
    selectedStage,
    selectedCategory,
    currentPage,
    fetchBills,
  ]);

  // Data transformation is now handled by the imported utility function

  const clearFilters = () => {
    setSearchQuery("");
    setSelectedStatus("");
    setSelectedStage("");
    setSelectedCategory(null);
    setCurrentPage(1);

    // Update URL
    router.push("/bills", undefined, { shallow: true });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchBills();
  };

  const statusOptions = [
    { value: "", label: "すべて" },
    { value: "成立", label: "成立" },
    { value: "審議中", label: "審議中" },
    { value: "採決待ち", label: "採決待ち" },
    { value: "未審議", label: "未審議" },
  ];

  const stageOptions = [
    { value: "", label: "すべて" },
    { value: "審議前", label: "審議前" },
    { value: "審議中", label: "審議中" },
    { value: "採決待ち", label: "採決待ち" },
    { value: "成立", label: "成立" },
  ];

  const totalPages = Math.ceil(totalFound / itemsPerPage);

  return (
    <Layout title="法案一覧">
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-3xl font-bold text-gray-900">法案一覧</h1>
              <Link
                href="/issues/categories"
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                政策分野から探す →
              </Link>
            </div>

            {/* Breadcrumbs */}
            <nav className="flex mb-4" aria-label="Breadcrumb">
              <ol className="inline-flex items-center space-x-1 md:space-x-3">
                <li className="inline-flex items-center">
                  <Link
                    href="/"
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    ホーム
                  </Link>
                </li>
                <li>
                  <div className="flex items-center">
                    <svg
                      className="w-4 h-4 text-gray-400 mx-1"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {selectedCategory ? (
                      <Link
                        href={`/issues/categories/${selectedCategory.id}`}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        {selectedCategory.fields.Title_JA}
                      </Link>
                    ) : (
                      <span className="text-gray-500 text-sm font-medium">
                        法案一覧
                      </span>
                    )}
                  </div>
                </li>
                {selectedCategory && (
                  <li>
                    <div className="flex items-center">
                      <svg
                        className="w-4 h-4 text-gray-400 mx-1"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      <span className="text-gray-500 text-sm font-medium">
                        法案一覧
                      </span>
                    </div>
                  </li>
                )}
              </ol>
            </nav>
          </div>

          {/* Search and Filters */}
          <div className="bg-white rounded-xl shadow-md p-6 mb-8">
            <form onSubmit={handleSearch} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                {/* Search Query */}
                <div>
                  <label
                    htmlFor="search"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    検索キーワード
                  </label>
                  <input
                    id="search"
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="法案名、法案番号で検索..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Status Filter */}
                <div>
                  <label
                    htmlFor="status"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    ステータス
                  </label>
                  <select
                    id="status"
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {statusOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Stage Filter */}
                <div>
                  <label
                    htmlFor="stage"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    審議段階
                  </label>
                  <select
                    id="stage"
                    value={selectedStage}
                    onChange={(e) => setSelectedStage(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {stageOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Actions */}
                <div className="sm:col-span-2 lg:col-span-1 flex flex-col sm:flex-row items-end space-y-2 sm:space-y-0 sm:space-x-2">
                  <button
                    type="submit"
                    className="w-full sm:flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm sm:text-base"
                  >
                    検索
                  </button>
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="w-full sm:flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 text-sm sm:text-base"
                  >
                    クリア
                  </button>
                </div>
              </div>
            </form>

            {/* Active Filters */}
            {(selectedCategory ||
              searchQuery ||
              selectedStatus ||
              selectedStage) && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex items-center space-x-2 flex-wrap gap-2">
                  <span className="text-xs sm:text-sm text-gray-600">
                    フィルター:
                  </span>

                  {selectedCategory && (
                    <span className="inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm bg-blue-100 text-blue-800">
                      {selectedCategory.fields.Title_JA}
                      <button
                        type="button"
                        onClick={() => setSelectedCategory(null)}
                        className="ml-1 sm:ml-2 text-blue-600 hover:text-blue-800"
                      >
                        ×
                      </button>
                    </span>
                  )}

                  {searchQuery && (
                    <span className="inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm bg-green-100 text-green-800">
                      「{searchQuery}」
                      <button
                        type="button"
                        onClick={() => setSearchQuery("")}
                        className="ml-1 sm:ml-2 text-green-600 hover:text-green-800"
                      >
                        ×
                      </button>
                    </span>
                  )}

                  {selectedStatus && (
                    <span className="inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm bg-purple-100 text-purple-800">
                      {selectedStatus}
                      <button
                        type="button"
                        onClick={() => setSelectedStatus("")}
                        className="ml-1 sm:ml-2 text-purple-600 hover:text-purple-800"
                      >
                        ×
                      </button>
                    </span>
                  )}

                  {selectedStage && (
                    <span className="inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm bg-orange-100 text-orange-800">
                      {selectedStage}
                      <button
                        type="button"
                        onClick={() => setSelectedStage("")}
                        className="ml-1 sm:ml-2 text-orange-600 hover:text-orange-800"
                      >
                        ×
                      </button>
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Results */}
          <div className="bg-white rounded-xl shadow-md p-6">
            {/* Results Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 space-y-2 sm:space-y-0">
              <h2 className="text-lg sm:text-xl font-semibold text-gray-900">
                {loading
                  ? "検索中..."
                  : `${totalFound}件の法案が見つかりました`}
              </h2>
              {totalFound > 0 && (
                <div className="text-xs sm:text-sm text-gray-600">
                  {Math.min(itemsPerPage * (currentPage - 1) + 1, totalFound)} -{" "}
                  {Math.min(itemsPerPage * currentPage, totalFound)} 件目を表示
                </div>
              )}
            </div>

            {/* Loading State */}
            {loading && (
              <div className="flex justify-center items-center py-16">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-lg text-gray-600">
                  法案を読み込み中...
                </span>
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="text-center py-16">
                <div className="text-red-400 text-4xl mb-4">⚠️</div>
                <p className="text-red-600 text-lg font-medium mb-2">
                  法案の読み込みに失敗しました
                </p>
                <p className="text-red-500 text-sm mb-4">{error}</p>
                <button
                  onClick={fetchBills}
                  className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                >
                  再試行
                </button>
              </div>
            )}

            {/* Bills List */}
            {!loading && !error && bills.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                {bills.map((billRecord) => (
                  <BillCard
                    key={billRecord.id}
                    bill={transformBillRecordToBill(billRecord)}
                  />
                ))}
              </div>
            )}

            {/* Empty State */}
            {!loading && !error && bills.length === 0 && (
              <div className="text-center py-16">
                <div className="text-gray-400 text-4xl mb-4">📋</div>
                <p className="text-gray-600 text-lg font-medium mb-2">
                  条件に合う法案が見つかりませんでした
                </p>
                <p className="text-gray-500 text-sm">
                  検索条件を変更して再度お試しください
                </p>
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center mt-6 sm:mt-8">
                <nav className="flex items-center space-x-1 sm:space-x-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span className="hidden sm:inline">前のページ</span>
                    <span className="sm:hidden">前</span>
                  </button>

                  <div className="flex items-center space-x-1">
                    {[...Array(Math.min(5, totalPages))].map((_, i) => {
                      const page = i + 1;
                      return (
                        <button
                          key={page}
                          onClick={() => setCurrentPage(page)}
                          className={`px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium rounded-md ${
                            currentPage === page
                              ? "bg-blue-600 text-white"
                              : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                          }`}
                        >
                          {page}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={() =>
                      setCurrentPage(Math.min(totalPages, currentPage + 1))
                    }
                    disabled={currentPage === totalPages}
                    className="px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span className="hidden sm:inline">次のページ</span>
                    <span className="sm:hidden">次</span>
                  </button>
                </nav>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default BillsPage;
