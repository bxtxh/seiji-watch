import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '@/components/Layout';

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

interface CategoryTreeNode {
  id: string;
  title_ja: string;
  title_en?: string;
  cap_code: string;
  description?: string;
  children: CategoryTreeNode[];
}

interface CategoryTreeResponse {
  tree: CategoryTreeNode[];
  total_l1: number;
  total_l2: number;
}

const IssueCategoriesPage = () => {
  const [categoryTree, setCategoryTree] = useState<CategoryTreeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedL1, setSelectedL1] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const router = useRouter();

  useEffect(() => {
    fetchCategoryTree();
  }, []);

  // Helper functions
  const getCategoryIcon = (capCode: string) => {
    const icons: { [key: string]: string } = {
      '1': '🏥', // Social Welfare & Healthcare
      '2': '💼', // Economic & Industrial Policy
      '3': '🌏', // Foreign Affairs & International Relations
    };
    return icons[capCode] || '📋';
  };

  const handleCategoryClick = (category: CategoryTreeNode) => {
    router.push(`/issues/categories/${category.id}`);
  };

  const toggleCategory = (categoryId: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId);
    } else {
      newExpanded.add(categoryId);
    }
    setExpandedCategories(newExpanded);
  };

  const fetchCategoryTree = async () => {
    try {
      setLoading(true);
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8081';
      const response = await fetch(`${apiBaseUrl}/api/issues/categories/tree`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch category tree');
      }
      
      const data = await response.json();
      setCategoryTree(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };


  if (loading) {
    return (
      <Layout title="政策分野">
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
          <div className="container mx-auto px-4 py-8">
            <div className="flex justify-center items-center py-16">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-lg text-gray-600">カテゴリを読み込み中...</span>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout title="政策分野">
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
          <div className="container mx-auto px-4 py-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-red-800 mb-2">エラーが発生しました</h2>
              <p className="text-red-700">{error}</p>
              <button
                onClick={fetchCategoryTree}
                className="mt-4 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
              >
                再試行
              </button>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="政策分野">
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-gray-800 mb-4">
              政策分野から法案を探す
            </h1>
            <p className="text-lg text-gray-600 max-w-3xl mx-auto">
              CAP（Comparative Agendas Project）に基づく国際標準の政策分類で、
              関心のある分野の法案を効率的に見つけることができます。
            </p>
          </div>

          {/* Statistics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            <div className="bg-white rounded-xl p-6 shadow-md border border-gray-100">
              <div className="text-2xl font-bold text-blue-600 mb-2">
                {categoryTree?.total_l1 || 0}
              </div>
              <div className="text-gray-600">主要政策分野</div>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-md border border-gray-100">
              <div className="text-2xl font-bold text-green-600 mb-2">
                {categoryTree?.total_l2 || 0}
              </div>
              <div className="text-gray-600">サブトピック</div>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-md border border-gray-100">
              <div className="text-2xl font-bold text-purple-600 mb-2">
                {categoryTree ? categoryTree.total_l1 + categoryTree.total_l2 : 0}
              </div>
              <div className="text-gray-600">総カテゴリ数</div>
            </div>
          </div>

          {/* Category Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {categoryTree?.tree.map((l1Category) => {
              const isExpanded = expandedCategories.has(l1Category.id);
              const l2Children = l1Category.children;
              const childCount = l2Children.length;

              return (
                <div key={l1Category.id} className="bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden" data-testid="l1-category">
                  {/* L1 Category Header */}
                  <div 
                    className="p-6 cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => handleCategoryClick(l1Category)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center mb-3">
                          <span className="text-2xl mr-3">
                            {getCategoryIcon(l1Category.cap_code)}
                          </span>
                          <div>
                            <h3 className="text-lg font-semibold text-gray-800 leading-tight">
                              {l1Category.title_ja}
                            </h3>
                            <p className="text-sm text-gray-500 mt-1">
                              {l1Category.title_en}
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            CAP-{l1Category.cap_code}
                          </span>
                          {childCount > 0 && (
                            <span className="text-sm text-gray-500">
                              {childCount}個のサブトピック
                            </span>
                          )}
                        </div>
                      </div>
                      
                      {childCount > 0 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleCategory(l1Category.id);
                          }}
                          className="ml-4 p-2 rounded-lg hover:bg-gray-100 transition-colors"
                        >
                          <svg
                            className={`w-5 h-5 text-gray-500 transition-transform ${
                              isExpanded ? 'transform rotate-180' : ''
                            }`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* L2 Children (Expandable) */}
                  {childCount > 0 && isExpanded && (
                    <div className="border-t border-gray-100 bg-gray-50">
                      <div className="p-4 space-y-2">
                        {l2Children.map((l2Category) => (
                          <div
                            key={l2Category.id}
                            onClick={() => handleCategoryClick(l2Category)}
                            className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-sm cursor-pointer transition-all"
                            data-testid="l2-category"
                          >
                            <div className="flex-1">
                              <h4 className="text-sm font-medium text-gray-800">
                                {l2Category.title_ja}
                              </h4>
                              <p className="text-xs text-gray-500 mt-1">
                                {l2Category.title_en}
                              </p>
                            </div>
                            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800 ml-3">
                              {l2Category.cap_code}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Help Section */}
          <div className="mt-16 bg-blue-50 rounded-xl p-8 border border-blue-100">
            <h2 className="text-2xl font-bold text-blue-800 mb-4">政策分類について</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-blue-700">
              <div>
                <h3 className="font-semibold mb-2">CAP（Comparative Agendas Project）</h3>
                <p>
                  国際的な政策研究プロジェクトの分類基準を採用し、
                  世界各国の政策と比較可能な形で整理しています。
                </p>
              </div>
              <div>
                <h3 className="font-semibold mb-2">階層構造</h3>
                <p>
                  L1（主要分野）からL2（サブトピック）への2段階構造で、
                  大まかな分野から具体的なテーマまで段階的に絞り込めます。
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default IssueCategoriesPage;