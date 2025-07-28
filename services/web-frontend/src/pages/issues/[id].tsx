import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/router";
import { GetServerSideProps } from "next";
import Layout from "../../components/Layout";
import IssueDetailCard from "../../components/IssueDetailCard";
import RelatedBillsList from "../../components/RelatedBillsList";
import DiscussionTimeline from "../../components/DiscussionTimeline";
import { Issue, IssueTag, Bill } from "../../types";
import {
  ArrowLeftIcon,
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  InformationCircleIcon,
  ExclamationTriangleIcon,
  TagIcon,
  CalendarIcon,
  ClockIcon,
} from "@heroicons/react/24/outline";

interface IssueDetailProps {
  issue: Issue | null;
  relatedBills: Bill[];
  issueTags: IssueTag[];
  error?: string;
}

interface ExtendedIssue extends Issue {
  category?: {
    id: string;
    title_ja: string;
    layer: string;
  };
  schedule?: {
    from: string;
    to: string;
  };
}

const IssueDetailPage = ({
  issue: initialIssue,
  relatedBills: initialRelatedBills,
  issueTags: initialIssueTags,
  error,
}: IssueDetailProps) => {
  const router = useRouter();
  const { id } = router.query;
  const [issue, setIssue] = useState<ExtendedIssue | null>(initialIssue);
  const [relatedBills, setRelatedBills] = useState<Bill[]>(
    initialRelatedBills || [],
  );
  const [issueTags, setIssueTags] = useState<IssueTag[]>(
    initialIssueTags || [],
  );
  const [loading, setLoading] = useState(!initialIssue && !error);
  const [activeTab, setActiveTab] = useState<
    "overview" | "bills" | "discussions"
  >("overview");
  const [billsLoading, setBillsLoading] = useState(false);
  const [discussionsLoading, setDiscussionsLoading] = useState(false);

  const fetchIssueDetails = useCallback(async () => {
    try {
      setLoading(true);
      const [issueResponse, billsResponse, tagsResponse] = await Promise.all([
        fetch(`/api/issues/${id}`),
        fetch(`/api/issues/${id}/bills`),
        fetch(`/api/issues/tags/`),
      ]);

      if (issueResponse.ok) {
        const issueData = await issueResponse.json();
        if (issueData.success && issueData.issue) {
          setIssue(transformIssueData(issueData.issue));
        }
      }

      if (billsResponse.ok) {
        const billsData = await billsResponse.json();
        if (billsData.success && billsData.bills) {
          setRelatedBills(billsData.bills);
        }
      }

      if (tagsResponse.ok) {
        const tagsData = await tagsResponse.json();
        if (tagsData.success && tagsData.tags) {
          // API returns tags as array of {name, count} objects
          const transformedTags = tagsData.tags.map((tag: any, index: number) => ({
            id: `tag-${index}`,
            name: tag.name || "",
            color_code: "#3B82F6",
            category: "",
            description: undefined,
          }));
          setIssueTags(transformedTags);
        }
      }
    } catch (error) {
      console.error("Failed to fetch issue details:", error);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!initialIssue && !error && id) {
      fetchIssueDetails();
    }
  }, [id, initialIssue, error, fetchIssueDetails]);

  const fetchRelatedBills = useCallback(async () => {
    try {
      setBillsLoading(true);
      const response = await fetch(`/api/issues/${id}/bills`);
      if (response.ok) {
        const billsData = await response.json();
        if (billsData.success && billsData.bills) {
          setRelatedBills(billsData.bills);
        }
      }
    } catch (error) {
      console.error("Failed to fetch related bills:", error);
    } finally {
      setBillsLoading(false);
    }
  }, [id]);

  // Mock discussions data - replace with real API call
  const mockDiscussions = useMemo(
    () => [
      {
        id: "1",
        date: "2025-01-15",
        title: "環境政策に関する委員会審議",
        speakers: ["田中太郎", "佐藤花子", "山田次郎"],
        summary:
          "カーボンニュートラル目標達成のための具体的政策について活発な議論が行われました。",
        committee: "環境委員会",
        session_type: "committee" as const,
        transcript_url: "#",
      },
      {
        id: "2",
        date: "2025-01-10",
        title: "本会議での環境関連法案審議",
        speakers: ["鈴木一郎", "高橋美子"],
        summary:
          "温室効果ガス削減に向けた新たな法的枠組みについて議論されました。",
        committee: "本会議",
        session_type: "plenary" as const,
        transcript_url: "#",
      },
    ],
    [],
  );

  const transformIssueData = (data: any): ExtendedIssue => ({
    id: data.id,
    title: data.title || "",
    description: data.description || "",
    priority: data.priority || "medium",
    status: data.status || "active",
    related_bills: data.related_bills || [],
    issue_tags: data.issue_tags || [],
    created_at: data.created_at,
    updated_at: data.updated_at,
    extraction_confidence: data.extraction_confidence,
    review_notes: data.review_notes,
    is_llm_generated: data.is_llm_generated || false,
    category: data.policy_category
      ? {
          id: data.policy_category.id,
          title_ja: data.policy_category.title_ja,
          layer: data.policy_category.layer,
        }
      : undefined,
    schedule: data.schedule || {
      from: new Date().toISOString(),
      to: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days from now
    },
  });

  const transformTagsData = (data: any[]): IssueTag[] => {
    return data.map((record: any) => ({
      id: record.id,
      name: record.fields?.Name || "",
      color_code: record.fields?.Color_Code || "#3B82F6",
      category: record.fields?.Category || "",
      description: record.fields?.Description,
    }));
  };

  const getTagsForIssue = (): IssueTag[] => {
    if (!issue?.issue_tags || !issueTags.length) return [];

    // Handle both string[] and IssueTag[] formats
    if (Array.isArray(issue.issue_tags) && issue.issue_tags.length > 0) {
      if (typeof issue.issue_tags[0] === "string") {
        // issue_tags is string[], filter by id
        const tagIds = issue.issue_tags as unknown as string[];
        return issueTags.filter((tag) => tagIds.includes(tag.id));
      } else {
        // issue_tags is already IssueTag[]
        return issue.issue_tags as IssueTag[];
      }
    }

    return [];
  };

  const getPriorityConfig = (priority: string) => {
    switch (priority) {
      case "high":
        return {
          label: "高優先度",
          bgColor: "bg-red-50",
          textColor: "text-red-700",
          borderColor: "border-red-200",
        };
      case "medium":
        return {
          label: "中優先度",
          bgColor: "bg-yellow-50",
          textColor: "text-yellow-700",
          borderColor: "border-yellow-200",
        };
      case "low":
        return {
          label: "低優先度",
          bgColor: "bg-green-50",
          textColor: "text-green-700",
          borderColor: "border-green-200",
        };
      default:
        return {
          label: "標準",
          bgColor: "bg-gray-50",
          textColor: "text-gray-700",
          borderColor: "border-gray-200",
        };
    }
  };

  const getStatusConfig = (status: string) => {
    switch (status) {
      case "active":
        return {
          label: "審議中",
          bgColor: "bg-blue-50",
          textColor: "text-blue-700",
          borderColor: "border-blue-200",
        };
      case "reviewed":
        return {
          label: "審議済み",
          bgColor: "bg-purple-50",
          textColor: "text-purple-700",
          borderColor: "border-purple-200",
        };
      case "archived":
        return {
          label: "完了",
          bgColor: "bg-gray-50",
          textColor: "text-gray-700",
          borderColor: "border-gray-200",
        };
      default:
        return {
          label: "不明",
          bgColor: "bg-gray-50",
          textColor: "text-gray-700",
          borderColor: "border-gray-200",
        };
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  useEffect(() => {
    if (activeTab === "bills" && !relatedBills.length && !billsLoading) {
      fetchRelatedBills();
    }
  }, [activeTab, relatedBills.length, billsLoading, fetchRelatedBills]);

  if (loading) {
    return (
      <Layout title="イシュー詳細 - 読み込み中">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded-md w-1/3 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded-md w-full mb-2"></div>
            <div className="h-4 bg-gray-200 rounded-md w-2/3 mb-8"></div>

            <div className="grid md:grid-cols-3 gap-6">
              <div className="md:col-span-2 space-y-6">
                <div className="h-64 bg-gray-200 rounded-xl"></div>
                <div className="h-32 bg-gray-200 rounded-xl"></div>
              </div>
              <div className="space-y-6">
                <div className="h-48 bg-gray-200 rounded-xl"></div>
                <div className="h-32 bg-gray-200 rounded-xl"></div>
              </div>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !issue) {
    return (
      <Layout title="イシュー詳細 - エラー">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-12">
            <ExclamationTriangleIcon className="mx-auto h-16 w-16 text-gray-400 mb-4" />
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              イシューが見つかりません
            </h1>
            <p className="text-gray-600 mb-6">
              {error ||
                "指定されたイシューが存在しないか、削除された可能性があります。"}
            </p>
            <button
              onClick={() => router.back()}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <ArrowLeftIcon className="h-4 w-4 mr-2" />
              戻る
            </button>
          </div>
        </div>
      </Layout>
    );
  }

  const priorityConfig = getPriorityConfig(issue.priority);
  const statusConfig = getStatusConfig(issue.status);
  const tags = getTagsForIssue();

  return (
    <Layout
      title={`${issue.title} - イシュー詳細`}
      description={issue.description}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4 transition-colors"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            戻る
          </button>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
              <div className="flex-1 min-w-0">
                <h1 className="text-2xl font-bold text-gray-900 mb-2 break-words">
                  {issue.title}
                </h1>
                <p className="text-gray-600 text-base leading-relaxed">
                  {issue.description}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <span
                  className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${statusConfig.bgColor} ${statusConfig.textColor} ${statusConfig.borderColor}`}
                >
                  {statusConfig.label}
                </span>
              </div>
            </div>

            {/* Tags */}
            {tags.length > 0 && (
              <div className="mb-4">
                <div className="flex flex-wrap gap-2">
                  {tags.map((tag) => (
                    <span
                      key={tag.id}
                      className="inline-flex items-center px-2 py-1 rounded-md text-sm font-medium border"
                      style={{
                        backgroundColor: tag.color_code + "20",
                        color: tag.color_code,
                        borderColor: tag.color_code + "40",
                      }}
                    >
                      <TagIcon className="h-3 w-3 mr-1" />
                      {tag.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata */}
            <div className="flex flex-wrap items-center gap-6 text-sm text-gray-500 pt-4 border-t border-gray-200">
              {issue.created_at && (
                <div className="flex items-center">
                  <CalendarIcon className="h-4 w-4 mr-1" />
                  作成: {formatDate(issue.created_at)}
                </div>
              )}
              {issue.updated_at && (
                <div className="flex items-center">
                  <ClockIcon className="h-4 w-4 mr-1" />
                  更新: {formatDate(issue.updated_at)}
                </div>
              )}
              {issue.is_llm_generated && (
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                  AI生成
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Content Tabs */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="border-b border-gray-200">
            <nav
              className="-mb-px flex space-x-8 px-6"
              role="tablist"
              aria-label="イシュー詳細タブ"
            >
              {[
                { id: "overview", label: "概要", icon: InformationCircleIcon },
                {
                  id: "bills",
                  label: `関連法案 (${relatedBills.length})`,
                  icon: DocumentTextIcon,
                },
                {
                  id: "discussions",
                  label: "議論履歴",
                  icon: ChatBubbleLeftRightIcon,
                },
              ].map((tab) => (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  aria-controls={`${tab.id}-panel`}
                  id={`${tab.id}-tab`}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`${
                    activeTab === tab.id
                      ? "border-blue-500 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
                >
                  <tab.icon className="h-4 w-4 mr-2" aria-hidden="true" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === "overview" && (
              <div
                role="tabpanel"
                id="overview-panel"
                aria-labelledby="overview-tab"
              >
                <IssueDetailCard issue={issue} issueTags={issueTags} />
              </div>
            )}

            {activeTab === "bills" && (
              <div role="tabpanel" id="bills-panel" aria-labelledby="bills-tab">
                <RelatedBillsList bills={relatedBills} loading={billsLoading} />
              </div>
            )}

            {activeTab === "discussions" && (
              <div
                role="tabpanel"
                id="discussions-panel"
                aria-labelledby="discussions-tab"
              >
                <DiscussionTimeline
                  discussions={mockDiscussions}
                  loading={discussionsLoading}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export const getServerSideProps: GetServerSideProps = async (context) => {
  const { id } = context.params!;

  try {
    // In a real implementation, you would fetch from your API here
    // For now, return props that will trigger client-side fetching
    return {
      props: {
        issue: null,
        relatedBills: [],
        issueTags: [],
      },
    };
  } catch (error) {
    console.error("Error fetching issue details:", error);
    return {
      props: {
        issue: null,
        relatedBills: [],
        issueTags: [],
        error: "イシューの詳細を取得できませんでした",
      },
    };
  }
};

export default IssueDetailPage;
