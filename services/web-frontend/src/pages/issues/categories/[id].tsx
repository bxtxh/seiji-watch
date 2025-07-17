import React, { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import Layout from "@/components/Layout";
import BillCard from "@/components/BillCard";
import { Bill } from "@/types";

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

interface BillRecord {
  id: string;
  fields: {
    Bill_Number: string;
    Title: string;
    Status: string;
    Category?: string;
    Diet_Session?: string;
    Submitted_Date?: string;
    Summary?: string;
  };
}

const CategoryDetailPage = () => {
  const [category, setCategory] = useState<IssueCategory | null>(null);
  const [parentCategory, setParentCategory] = useState<IssueCategory | null>(
    null,
  );
  const [childCategories, setChildCategories] = useState<IssueCategory[]>([]);
  const [relatedBills, setRelatedBills] = useState<BillRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const { id } = router.query;

  useEffect(() => {
    if (id) {
      fetchCategoryData(id as string);
    }
  }, [id]);

  const fetchCategoryData = async (categoryId: string) => {
    try {
      setLoading(true);
      const apiBaseUrl =
        process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8081";

      // Fetch category details
      const categoryResponse = await fetch(
        `${apiBaseUrl}/api/issues/categories/${categoryId}`,
      );
      if (!categoryResponse.ok) {
        throw new Error("Category not found");
      }
      const categoryData = await categoryResponse.json();
      setCategory(categoryData);

      // Fetch parent category if this is L2
      if (
        categoryData.fields.Parent_Category &&
        categoryData.fields.Parent_Category.length > 0
      ) {
        const parentId = categoryData.fields.Parent_Category[0];
        try {
          const parentResponse = await fetch(
            `${apiBaseUrl}/api/issues/categories/${parentId}`,
          );
          if (parentResponse.ok) {
            const parentData = await parentResponse.json();
            setParentCategory(parentData);
          }
        } catch (err) {
          console.warn("Failed to fetch parent category:", err);
        }
      }

      // Fetch child categories
      try {
        const childrenResponse = await fetch(
          `${apiBaseUrl}/api/issues/categories/${categoryId}/children`,
        );
        if (childrenResponse.ok) {
          const childrenData = await childrenResponse.json();
          setChildCategories(childrenData);
        }
      } catch (err) {
        console.warn("Failed to fetch child categories:", err);
      }

      // Fetch related bills (mock for now - would need to implement bill-category relationship)
      try {
        const billsResponse = await fetch(
          `${apiBaseUrl}/api/bills?max_records=10`,
        );
        if (billsResponse.ok) {
          const billsData = await billsResponse.json();
          // Filter bills by category (simplified logic)
          const filtered = billsData.filter(
            (bill: BillRecord) =>
              bill.fields.Category &&
              bill.fields.Category.includes(categoryData.fields.Title_JA),
          );
          setRelatedBills(filtered.slice(0, 6)); // Limit to 6 bills
        }
      } catch (err) {
        console.warn("Failed to fetch related bills:", err);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const getCategoryIcon = (capCode: string): string => {
    const iconMap: { [key: string]: string } = {
      "1": "💰",
      "2": "⚖️",
      "3": "🏥",
      "4": "🌾",
      "5": "👷",
      "6": "📚",
      "7": "🌱",
      "8": "⚡",
      "10": "🚗",
      "12": "🏛️",
      "13": "🤝",
      "14": "🏙️",
      "15": "🏦",
      "16": "🛡️",
      "17": "🚀",
      "18": "🌏",
      "19": "🌍",
      "20": "🏢",
      "21": "🌲",
      "23": "🎭",
      "99": "📋",
    };
    return iconMap[capCode] || "📋";
  };

  const convertBillRecordToBill = (billRecord: BillRecord): Bill => {
    return {
      id: billRecord.id,
      bill_number: billRecord.fields.Bill_Number || "",
      title: billRecord.fields.Title || "",
      summary: billRecord.fields.Summary || "",
      category: billRecord.fields.Category || "",
      status: billRecord.fields.Status || "",
      diet_url: "", // Not available in this interface
    };
  };

  const getBreadcrumbs = () => {
    const breadcrumbs = [
      { label: "ホーム", href: "/" },
      { label: "政策分野", href: "/issues/categories" },
    ];

    if (parentCategory) {
      breadcrumbs.push({
        label: parentCategory.fields.Title_JA,
        href: `/issues/categories/${parentCategory.id}`,
      });
    }

    if (category) {
      breadcrumbs.push({
        label: category.fields.Title_JA,
        href: `/issues/categories/${category.id}`,
      });
    }

    return breadcrumbs;
  };

  if (loading) {
    return (
      <Layout title="カテゴリ詳細">
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
          <div className="container mx-auto px-4 py-8">
            <div className="flex justify-center items-center py-16">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-lg text-gray-600">
                カテゴリを読み込み中...
              </span>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !category) {
    return (
      <Layout title="カテゴリ詳細">
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
          <div className="container mx-auto px-4 py-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-red-800 mb-2">
                エラーが発生しました
              </h2>
              <p className="text-red-700">
                {error || "カテゴリが見つかりません"}
              </p>
              <Link
                href="/issues/categories"
                className="mt-4 inline-block bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
              >
                カテゴリ一覧に戻る
              </Link>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  const breadcrumbs = getBreadcrumbs();

  return (
    <Layout title={`${category.fields.Title_JA} - 政策分野`}>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
        <div className="container mx-auto px-4 py-8">
          {/* Breadcrumbs */}
          <nav className="flex mb-8" aria-label="Breadcrumb">
            <ol className="inline-flex items-center space-x-1 md:space-x-3">
              {breadcrumbs.map((breadcrumb, index) => (
                <li key={index} className="inline-flex items-center">
                  {index > 0 && (
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
                  )}
                  {index === breadcrumbs.length - 1 ? (
                    <span className="text-gray-500 text-sm font-medium">
                      {breadcrumb.label}
                    </span>
                  ) : (
                    <Link
                      href={breadcrumb.href}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                    >
                      {breadcrumb.label}
                    </Link>
                  )}
                </li>
              ))}
            </ol>
          </nav>

          {/* Category Header */}
          <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
            <div className="flex items-start justify-between">
              <div className="flex items-center">
                <span className="text-4xl mr-4">
                  {getCategoryIcon(category.fields.CAP_Code)}
                </span>
                <div>
                  <div className="flex items-center mb-2">
                    <h1 className="text-3xl font-bold text-gray-800 mr-4">
                      {category.fields.Title_JA}
                    </h1>
                    <span
                      className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                        category.fields.Layer === "L1"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-green-100 text-green-800"
                      }`}
                    >
                      {category.fields.Layer === "L1"
                        ? "主要分野"
                        : "サブトピック"}
                    </span>
                  </div>
                  <p className="text-lg text-gray-600 mb-3">
                    {category.fields.Title_EN}
                  </p>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    CAP-{category.fields.CAP_Code}
                  </span>
                </div>
              </div>
            </div>

            {category.fields.Summary_150JA && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-700 leading-relaxed">
                  {category.fields.Summary_150JA}
                </p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Main Content */}
            <div className="lg:col-span-2 space-y-8">
              {/* Child Categories */}
              {childCategories.length > 0 && (
                <div className="bg-white rounded-xl shadow-md p-6">
                  <h2 className="text-2xl font-bold text-gray-800 mb-6">
                    サブトピック
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {childCategories.map((child) => (
                      <Link
                        key={child.id}
                        href={`/issues/categories/${child.id}`}
                        className="block p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-md transition-all"
                        data-testid="child-category"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold text-gray-800 mb-1">
                              {child.fields.Title_JA}
                            </h3>
                            <p className="text-sm text-gray-600">
                              {child.fields.Title_EN}
                            </p>
                          </div>
                          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                            {child.fields.CAP_Code}
                          </span>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Related Bills */}
              <div className="bg-white rounded-xl shadow-md p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold text-gray-800">関連法案</h2>
                  {relatedBills.length > 0 && (
                    <Link
                      href={`/bills?category=${encodeURIComponent(category.fields.Title_JA)}`}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                    >
                      すべて見る →
                    </Link>
                  )}
                </div>

                {relatedBills.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {relatedBills.map((billRecord) => (
                      <BillCard
                        key={billRecord.id}
                        bill={convertBillRecordToBill(billRecord)}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <div className="text-gray-400 text-4xl mb-4">📋</div>
                    <p className="text-gray-600 text-lg font-medium mb-2">
                      関連法案が見つかりません
                    </p>
                    <p className="text-gray-500 text-sm">
                      このカテゴリに関連する法案がまだ登録されていません。
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Quick Stats */}
              <div className="bg-white rounded-xl shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  統計情報
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">関連法案</span>
                    <span className="font-semibold text-blue-600">
                      {relatedBills.length}件
                    </span>
                  </div>
                  {childCategories.length > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-600">サブトピック</span>
                      <span className="font-semibold text-green-600">
                        {childCategories.length}個
                      </span>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">分類コード</span>
                    <span className="font-semibold text-gray-800">
                      CAP-{category.fields.CAP_Code}
                    </span>
                  </div>
                </div>
              </div>

              {/* Navigation */}
              <div className="bg-white rounded-xl shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  ナビゲーション
                </h3>
                <div className="space-y-2">
                  <Link
                    href="/issues/categories"
                    className="block w-full text-left px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    すべての政策分野
                  </Link>
                  {parentCategory && (
                    <Link
                      href={`/issues/categories/${parentCategory.id}`}
                      className="block w-full text-left px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      {parentCategory.fields.Title_JA}
                    </Link>
                  )}
                  <Link
                    href={`/bills?policy_category_id=${category.id}`}
                    className="block w-full text-left px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    このカテゴリの法案一覧
                  </Link>
                  <Link
                    href="/bills"
                    className="block w-full text-left px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    すべての法案
                  </Link>
                </div>
              </div>

              {/* Help */}
              <div className="bg-blue-50 rounded-xl p-6 border border-blue-100">
                <h3 className="text-lg font-semibold text-blue-800 mb-3">
                  政策分類について
                </h3>
                <p className="text-sm text-blue-700 leading-relaxed">
                  この分類は国際的な政策研究プロジェクト（CAP）の基準に基づいており、
                  世界各国の政策と比較可能な形で整理されています。
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default CategoryDetailPage;
