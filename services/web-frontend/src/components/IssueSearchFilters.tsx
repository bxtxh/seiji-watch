import React from "react";
import {
  MagnifyingGlassIcon,
  Bars3Icon,
  ListBulletIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";

interface IssueSearchFiltersProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  selectedCategory: string;
  setSelectedCategory: (category: string) => void;
  selectedStatus: string;
  setSelectedStatus: (status: string) => void;
  selectedPriority: string;
  setSelectedPriority: (priority: string) => void;
  viewMode: "grid" | "list";
  setViewMode: (mode: "grid" | "list") => void;
  sortBy: string;
  setSortBy: (sort: string) => void;
  categories: string[];
  onClearFilters: () => void;
}

const IssueSearchFilters: React.FC<IssueSearchFiltersProps> = ({
  searchQuery,
  setSearchQuery,
  selectedCategory,
  setSelectedCategory,
  selectedStatus,
  setSelectedStatus,
  selectedPriority,
  setSelectedPriority,
  viewMode,
  setViewMode,
  sortBy,
  setSortBy,
  categories,
  onClearFilters,
}) => {
  const hasActiveFilters =
    selectedCategory || selectedStatus || selectedPriority;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
      {/* Search Bar */}
      <div className="mb-6">
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="イシュー名、説明、タグで検索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-lg text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
          />
        </div>
      </div>

      {/* View Toggle and Sort */}
      <div className="flex items-center justify-between mb-6">
        {/* View Toggle */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setViewMode("grid")}
            className={`p-2 rounded-md transition-colors ${
              viewMode === "grid"
                ? "bg-blue-500 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
            aria-label="グリッド表示"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <rect x="3" y="3" width="7" height="7" strokeWidth="2" rx="1" />
              <rect x="14" y="3" width="7" height="7" strokeWidth="2" rx="1" />
              <rect x="3" y="14" width="7" height="7" strokeWidth="2" rx="1" />
              <rect x="14" y="14" width="7" height="7" strokeWidth="2" rx="1" />
            </svg>
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={`p-2 rounded-md transition-colors ${
              viewMode === "list"
                ? "bg-blue-500 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
            aria-label="リスト表示"
          >
            <ListBulletIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Sort Dropdown */}
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-700">並び順:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          >
            <option value="updated_desc">更新日時</option>
            <option value="created_desc">作成日時</option>
            <option value="priority_desc">優先度</option>
            <option value="title_asc">タイトル</option>
          </select>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 items-end">
        {/* 審議状況 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            審議状況
          </label>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          >
            <option value="">すべて</option>
            <option value="active">アクティブ</option>
            <option value="reviewed">レビュー済み</option>
            <option value="archived">アーカイブ</option>
          </select>
        </div>

        {/* タグ (政策分野) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            タグ
          </label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          >
            <option value="">すべて</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>

        {/* 優先度 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            優先度
          </label>
          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          >
            <option value="">すべて</option>
            <option value="high">高</option>
            <option value="medium">中</option>
            <option value="low">低</option>
          </select>
        </div>

        {/* フィルタークリア */}
        <div className="flex justify-end">
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="flex items-center px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            >
              <XMarkIcon className="w-4 h-4 mr-2" />
              フィルタをクリア
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default IssueSearchFilters;
