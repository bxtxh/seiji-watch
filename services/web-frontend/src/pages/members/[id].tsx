import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import { GetServerSideProps } from "next";
import Image from "next/image";
import Layout from "@/components/Layout";
import { useObservability } from "@/lib/observability";
import { apiClient } from "@/lib/api";

interface Member {
  id: string;
  name: string;
  name_kana: string;
  house: "house_of_representatives" | "house_of_councillors";
  party: string;
  constituency: string;
  terms_served: number;
  committees: string[];
  profile_image?: string;
  official_url?: string;
  elected_date?: string;
  birth_date?: string;
  education?: string;
  career?: string;
}

interface PolicyPosition {
  issue_tag: string;
  issue_name: string;
  stance: string;
  confidence: number;
  vote_count: number;
  supporting_evidence: string[];
  last_updated: string;
}

interface PolicyAnalysis {
  member_id: string;
  analysis_timestamp: string;
  overall_activity_level: number;
  party_alignment_rate: number;
  data_completeness: number;
  stance_distribution: Record<string, number>;
  strongest_positions: PolicyPosition[];
  total_issues_analyzed: number;
}

interface VotingStats {
  total_votes: number;
  attendance_rate: number;
  party_alignment_rate: number;
  voting_pattern: {
    yes_votes: number;
    no_votes: number;
    abstentions: number;
    absences: number;
  };
}

interface MemberPageProps {
  member: Member | null;
  initialPolicyAnalysis: PolicyAnalysis | null;
  initialVotingStats: VotingStats | null;
}

const MemberPage: React.FC<MemberPageProps> = ({
  member: initialMember,
  initialPolicyAnalysis,
  initialVotingStats,
}) => {
  const router = useRouter();
  const { id } = router.query;
  const { recordPageView, recordError, recordMetric } = useObservability();

  const [member, setMember] = useState<Member | null>(initialMember);
  const [policyAnalysis, setPolicyAnalysis] = useState<PolicyAnalysis | null>(
    initialPolicyAnalysis
  );
  const [votingStats, setVotingStats] = useState<VotingStats | null>(
    initialVotingStats
  );
  const [loading, setLoading] = useState(!initialMember);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<
    "overview" | "policy" | "voting" | "activity"
  >("overview");

  const fetchMemberData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch member profile
      const memberResponse = await fetch(`/api/members/${id}`);
      if (!memberResponse.ok) {
        throw new Error("Member not found");
      }
      const memberData = await memberResponse.json();

      // Transform Airtable response to match Member interface
      if (memberData.success && memberData.member) {
        const rawMember = memberData.member;
        const fields = rawMember.fields || {};

        const transformedMember: Member = {
          id: rawMember.id,
          name: fields.Name || "",
          name_kana: fields.Name_Kana || "",
          house:
            fields.House === "衆議院"
              ? "house_of_representatives"
              : "house_of_councillors",
          party: fields.Party_Name || "無所属",
          constituency: fields.Constituency || "",
          terms_served: fields.Terms_Served || 1,
          committees: fields.Committees || [],
          profile_image: fields.Profile_Image?.[0]?.url,
          official_url: fields.Official_URL,
          elected_date: fields.First_Elected,
          birth_date: fields.Birth_Date,
          education: fields.Education,
          career: fields.Career,
        };

        setMember(transformedMember);
      }

      // Fetch policy analysis
      const policyResponse = await fetch(`/api/policy/member/${id}/analysis`);
      if (policyResponse.ok) {
        const policyData = await policyResponse.json();
        setPolicyAnalysis(policyData.analysis);
      }

      // Fetch voting stats
      const votingResponse = await fetch(`/api/members/${id}/voting-stats`);
      if (votingResponse.ok) {
        const votingData = await votingResponse.json();
        setVotingStats(votingData.stats);
      }
    } catch (err) {
      console.error("Failed to fetch member data:", err);
      setError(
        err instanceof Error ? err.message : "Failed to load member data"
      );
      recordError({
        error: err as Error,
        context: "member_page_fetch",
        timestamp: Date.now(),
      });
    } finally {
      setLoading(false);
    }
  }, [id, recordError]);

  useEffect(() => {
    if (id) {
      recordPageView(`member/${id}`);
    }
  }, [id, recordPageView]);

  useEffect(() => {
    if (!initialMember && id) {
      fetchMemberData();
    }
  }, [id, initialMember, fetchMemberData]);

  const getHouseLabel = (house: string) => {
    return house === "house_of_representatives" ? "衆議院" : "参議院";
  };

  const getStanceColor = (stance: string) => {
    switch (stance) {
      case "strong_support":
        return "bg-green-100 text-green-800 border-green-300";
      case "support":
        return "bg-green-50 text-green-700 border-green-200";
      case "neutral":
        return "bg-gray-100 text-gray-700 border-gray-300";
      case "oppose":
        return "bg-red-50 text-red-700 border-red-200";
      case "strong_oppose":
        return "bg-red-100 text-red-800 border-red-300";
      default:
        return "bg-gray-100 text-gray-600 border-gray-300";
    }
  };

  const getStanceLabel = (stance: string) => {
    switch (stance) {
      case "strong_support":
        return "強く支持";
      case "support":
        return "支持";
      case "neutral":
        return "中立";
      case "oppose":
        return "反対";
      case "strong_oppose":
        return "強く反対";
      default:
        return "不明";
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto py-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-24 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !member) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto py-8 text-center">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h1 className="text-2xl font-bold text-red-800 mb-2">エラー</h1>
            <p className="text-red-700">
              {error || "議員情報が見つかりません"}
            </p>
            <button
              onClick={() => router.push("/members")}
              className="mt-4 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors"
            >
              議員一覧に戻る
            </button>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto py-8" data-testid="member-profile">
        {/* Header Section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-start space-x-6">
            <div className="flex-shrink-0">
              {member.profile_image ? (
                <Image
                  src={member.profile_image}
                  alt={`${member.name}の写真`}
                  width={96}
                  height={96}
                  className="w-24 h-24 rounded-lg object-cover"
                />
              ) : (
                <div className="w-24 h-24 bg-gray-200 rounded-lg flex items-center justify-center">
                  <svg
                    className="w-12 h-12 text-gray-400"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M24 20.993V24H0v-2.996A14.977 14.977 0 0112.004 15c4.904 0 9.26 2.354 11.996 5.993zM16.002 8.999a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                </div>
              )}
            </div>

            <div className="flex-1 min-w-0">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {member.name}
                {member.name_kana && (
                  <span className="text-lg font-normal text-gray-600 ml-2">
                    （{member.name_kana}）
                  </span>
                )}
              </h1>

              <div className="flex flex-wrap items-center space-x-4 text-sm text-gray-600 mb-4">
                <span className="flex items-center">
                  <svg
                    className="w-4 h-4 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                  {getHouseLabel(member.house)}
                </span>

                <span className="flex items-center">
                  <svg
                    className="w-4 h-4 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                    />
                  </svg>
                  {member.party}
                </span>

                <span className="flex items-center">
                  <svg
                    className="w-4 h-4 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                    />
                  </svg>
                  {member.constituency}
                </span>

                <span className="flex items-center">
                  <svg
                    className="w-4 h-4 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  {member.terms_served}期
                </span>
              </div>

              {member.committees && member.committees.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">
                    所属委員会
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {member.committees.map((committee, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                      >
                        {committee}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {member.official_url && (
                <a
                  href={member.official_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800"
                >
                  <svg
                    className="w-4 h-4 mr-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                  公式サイト
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="mb-6">
          <nav className="flex space-x-8" aria-label="タブ">
            {[
              { id: "overview", label: "概要", icon: "📊" },
              { id: "policy", label: "政策立場", icon: "📋" },
              { id: "voting", label: "投票履歴", icon: "🗳️" },
              { id: "activity", label: "活動記録", icon: "📈" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`flex items-center space-x-2 pb-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Activity Overview */}
              <div className="lg:col-span-2">
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    活動概要
                  </h2>

                  {policyAnalysis && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600">
                          {Math.round(
                            policyAnalysis.overall_activity_level * 100
                          )}
                          %
                        </div>
                        <div className="text-sm text-gray-600">活動度</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600">
                          {Math.round(
                            policyAnalysis.party_alignment_rate * 100
                          )}
                          %
                        </div>
                        <div className="text-sm text-gray-600">
                          党方針一致率
                        </div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-600">
                          {Math.round(policyAnalysis.data_completeness * 100)}%
                        </div>
                        <div className="text-sm text-gray-600">
                          データ完全性
                        </div>
                      </div>
                    </div>
                  )}

                  {member.career && (
                    <div className="mt-6">
                      <h3 className="font-medium text-gray-900 mb-2">経歴</h3>
                      <p className="text-gray-700 text-sm">{member.career}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Quick Stats */}
              <div className="space-y-4">
                {votingStats && (
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <h3 className="font-semibold text-gray-900 mb-4">
                      投票統計
                    </h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">総投票数</span>
                        <span className="text-sm font-medium">
                          {votingStats.total_votes}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">出席率</span>
                        <span className="text-sm font-medium">
                          {Math.round(votingStats.attendance_rate * 100)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">
                          党方針一致率
                        </span>
                        <span className="text-sm font-medium">
                          {Math.round(votingStats.party_alignment_rate * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "policy" && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-gray-900">
                  政策立場分析
                </h2>
                <span className="px-3 py-1 text-sm bg-yellow-100 text-yellow-800 rounded-full border border-yellow-300">
                  🚧 開発中
                </span>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                <div className="flex items-center">
                  <svg
                    className="w-5 h-5 text-yellow-600 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <div>
                    <h3 className="text-sm font-medium text-yellow-800">
                      政策立場分析機能について
                    </h3>
                    <p className="text-sm text-yellow-700 mt-1">
                      現在、より精密な政策立場分析システムを開発中です。実際の議事録データとLLMを活用した本格的な分析機能は、今後のリリースで提供予定です。
                    </p>
                  </div>
                </div>
              </div>

              {policyAnalysis && policyAnalysis.strongest_positions ? (
                <div className="space-y-4">
                  <div className="text-sm text-gray-600 mb-4">
                    <span className="font-medium">
                      ※ 以下はMVP版のサンプルデータです
                    </span>
                  </div>
                  {policyAnalysis.strongest_positions.map((position, index) => (
                    <div
                      key={index}
                      className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors opacity-75"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium text-gray-900">
                          {position.issue_name}
                        </h3>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium border ${getStanceColor(position.stance)}`}
                        >
                          {getStanceLabel(position.stance)}
                        </span>
                      </div>

                      <div className="flex items-center space-x-4 text-sm text-gray-600 mb-3">
                        <span>
                          確信度: {Math.round(position.confidence * 100)}%
                        </span>
                        <span>投票数: {position.vote_count}</span>
                        <span>
                          更新:{" "}
                          {new Date(position.last_updated).toLocaleDateString(
                            "ja-JP"
                          )}
                        </span>
                      </div>

                      {position.supporting_evidence &&
                        position.supporting_evidence.length > 0 && (
                          <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-2">
                              根拠:
                            </h4>
                            <ul className="text-sm text-gray-600 space-y-1">
                              {position.supporting_evidence.map(
                                (evidence, evidenceIndex) => (
                                  <li
                                    key={evidenceIndex}
                                    className="flex items-start"
                                  >
                                    <span className="flex-shrink-0 w-1 h-1 bg-gray-400 rounded-full mt-2 mr-2"></span>
                                    <span>{evidence}</span>
                                  </li>
                                )
                              )}
                            </ul>
                          </div>
                        )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <svg
                    className="w-12 h-12 mx-auto mb-4"
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
                  <p>政策立場分析データが読み込み中です...</p>
                </div>
              )}
            </div>
          )}

          {activeTab === "voting" && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">
                投票履歴
              </h2>

              {votingStats ? (
                <div className="space-y-6">
                  {/* Voting Pattern Chart */}
                  <div>
                    <h3 className="font-medium text-gray-900 mb-4">
                      投票パターン
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center p-4 bg-green-50 rounded-lg border border-green-200">
                        <div className="text-3xl font-bold text-green-600">
                          {votingStats.voting_pattern.yes_votes}
                        </div>
                        <div className="text-sm text-gray-600">賛成</div>
                        <div className="text-xs text-gray-500 mt-1">
                          {Math.round(
                            (votingStats.voting_pattern.yes_votes /
                              votingStats.total_votes) *
                              100
                          )}
                          %
                        </div>
                      </div>
                      <div className="text-center p-4 bg-red-50 rounded-lg border border-red-200">
                        <div className="text-3xl font-bold text-red-600">
                          {votingStats.voting_pattern.no_votes}
                        </div>
                        <div className="text-sm text-gray-600">反対</div>
                        <div className="text-xs text-gray-500 mt-1">
                          {Math.round(
                            (votingStats.voting_pattern.no_votes /
                              votingStats.total_votes) *
                              100
                          )}
                          %
                        </div>
                      </div>
                      <div className="text-center p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                        <div className="text-3xl font-bold text-yellow-600">
                          {votingStats.voting_pattern.abstentions}
                        </div>
                        <div className="text-sm text-gray-600">棄権</div>
                        <div className="text-xs text-gray-500 mt-1">
                          {Math.round(
                            (votingStats.voting_pattern.abstentions /
                              votingStats.total_votes) *
                              100
                          )}
                          %
                        </div>
                      </div>
                      <div className="text-center p-4 bg-gray-50 rounded-lg border border-gray-300">
                        <div className="text-3xl font-bold text-gray-600">
                          {votingStats.voting_pattern.absences}
                        </div>
                        <div className="text-sm text-gray-600">欠席</div>
                        <div className="text-xs text-gray-500 mt-1">
                          {Math.round(
                            (votingStats.voting_pattern.absences /
                              votingStats.total_votes) *
                              100
                          )}
                          %
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Overall Statistics */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="font-medium text-gray-900 mb-3">
                      統計サマリー
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">総投票数:</span>
                        <span className="text-sm font-medium">
                          {votingStats.total_votes}回
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">出席率:</span>
                        <span className="text-sm font-medium">
                          {Math.round(votingStats.attendance_rate * 100)}%
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">
                          党方針一致率:
                        </span>
                        <span className="text-sm font-medium">
                          {Math.round(votingStats.party_alignment_rate * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Voting History Placeholder */}
                  <div className="border-t pt-6">
                    <h3 className="font-medium text-gray-900 mb-4">
                      最近の投票記録
                    </h3>
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                      <div className="flex items-center">
                        <svg
                          className="w-5 h-5 text-yellow-600 mr-2"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        <div>
                          <h4 className="text-sm font-medium text-yellow-800">
                            投票履歴機能について
                          </h4>
                          <p className="text-sm text-yellow-700 mt-1">
                            個別の法案への投票記録は、今後のアップデートで追加予定です。現在は統計データのみ表示しています。
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <svg
                    className="w-12 h-12 mx-auto mb-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                  <p>投票データを読み込んでいます...</p>
                </div>
              )}
            </div>
          )}

          {activeTab === "activity" && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">
                活動記録
              </h2>

              <div className="text-center py-8 text-gray-500">
                <svg
                  className="w-12 h-12 mx-auto mb-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
                  />
                </svg>
                <p>活動記録は準備中です...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export const getServerSideProps: GetServerSideProps = async ({ params }) => {
  const { id } = params!;

  try {
    // In production, these would be actual API calls
    // For now, return mock data structure
    return {
      props: {
        member: null,
        initialPolicyAnalysis: null,
        initialVotingStats: null,
      },
    };
  } catch (error) {
    console.error("Failed to fetch member data:", error);
    return {
      props: {
        member: null,
        initialPolicyAnalysis: null,
        initialVotingStats: null,
      },
    };
  }
};

export default MemberPage;
