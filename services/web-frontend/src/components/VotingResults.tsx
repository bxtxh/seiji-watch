import React, { useState, useEffect } from "react";
import { VotingSession, VoteResult } from "@/types";

interface VotingResultsProps {
  billNumber: string;
}

export default function VotingResults({ billNumber }: VotingResultsProps) {
  const [votingData, setVotingData] = useState<VotingSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<VotingSession | null>(
    null,
  );

  useEffect(() => {
    fetchVotingData();
  }, [billNumber]);

  const fetchVotingData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Mock voting data for development
      // TODO: Replace with actual API call
      const mockVotingSession: VotingSession = {
        bill_number: billNumber,
        bill_title: "令和6年度補正予算案",
        vote_date: "2024-07-05",
        vote_type: "本会議",
        vote_stage: "最終",
        house: "参議院",
        total_votes: 20,
        yes_votes: 12,
        no_votes: 6,
        abstain_votes: 1,
        absent_votes: 1,
        is_final_vote: true,
        vote_records: [
          {
            member_name: "議員01",
            party_name: "自由民主党",
            constituency: "東京都",
            vote_result: "yes",
          },
          {
            member_name: "議員02",
            party_name: "立憲民主党",
            constituency: "大阪府",
            vote_result: "no",
          },
          {
            member_name: "議員03",
            party_name: "公明党",
            constituency: "神奈川県",
            vote_result: "yes",
          },
          {
            member_name: "議員04",
            party_name: "日本維新の会",
            constituency: "愛知県",
            vote_result: "yes",
          },
          {
            member_name: "議員05",
            party_name: "国民民主党",
            constituency: "埼玉県",
            vote_result: "abstain",
          },
        ],
      };

      setVotingData([mockVotingSession]);
      setLoading(false);
    } catch (err) {
      setError("投票データの取得に失敗しました");
      setLoading(false);
    }
  };

  const getVoteResultBadge = (result: string) => {
    const badgeClasses = {
      yes: "bg-green-100 text-green-800",
      no: "bg-red-100 text-red-800",
      abstain: "bg-yellow-100 text-yellow-800",
      absent: "bg-gray-100 text-gray-800",
      present: "bg-blue-100 text-blue-800",
    };

    const labels = {
      yes: "賛成",
      no: "反対",
      abstain: "棄権",
      absent: "欠席",
      present: "出席",
    };

    return (
      <span
        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${badgeClasses[result as keyof typeof badgeClasses] || "bg-gray-100 text-gray-800"}`}
      >
        {labels[result as keyof typeof labels] || result}
      </span>
    );
  };

  const calculatePercentage = (count: number, total: number) => {
    return total > 0 ? ((count / total) * 100).toFixed(1) : "0.0";
  };

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
        <div className="h-24 bg-gray-200 rounded"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-md">
        {error}
      </div>
    );
  }

  if (votingData.length === 0) {
    return (
      <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-md">
        この法案の投票記録はまだ記録されていません。
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900">投票記録</h3>

      {votingData.map((session, index) => (
        <div key={index} className="border border-gray-200 rounded-lg p-4">
          {/* Voting Session Header */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h4 className="font-medium text-gray-900">
                {session.vote_type}
                {session.vote_stage && ` - ${session.vote_stage}`}
                {session.is_final_vote && (
                  <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                    最終採決
                  </span>
                )}
              </h4>
              <p className="text-sm text-gray-600 mt-1">
                {session.vote_date} | {session.house}
                {session.committee_name && ` | ${session.committee_name}`}
              </p>
            </div>
          </div>

          {/* Vote Results Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center p-3 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                {session.yes_votes}
              </div>
              <div className="text-sm text-green-700">賛成</div>
              <div className="text-xs text-green-600">
                {calculatePercentage(session.yes_votes, session.total_votes)}%
              </div>
            </div>

            <div className="text-center p-3 bg-red-50 rounded-lg">
              <div className="text-2xl font-bold text-red-600">
                {session.no_votes}
              </div>
              <div className="text-sm text-red-700">反対</div>
              <div className="text-xs text-red-600">
                {calculatePercentage(session.no_votes, session.total_votes)}%
              </div>
            </div>

            <div className="text-center p-3 bg-yellow-50 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600">
                {session.abstain_votes}
              </div>
              <div className="text-sm text-yellow-700">棄権</div>
              <div className="text-xs text-yellow-600">
                {calculatePercentage(
                  session.abstain_votes,
                  session.total_votes,
                )}
                %
              </div>
            </div>

            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-600">
                {session.absent_votes}
              </div>
              <div className="text-sm text-gray-700">欠席</div>
              <div className="text-xs text-gray-600">
                {calculatePercentage(session.absent_votes, session.total_votes)}
                %
              </div>
            </div>
          </div>

          {/* Vote Result Visualization */}
          <div className="mb-4">
            <div className="flex rounded-lg overflow-hidden h-4 bg-gray-200">
              <div
                className="bg-green-500"
                style={{
                  width: `${calculatePercentage(session.yes_votes, session.total_votes)}%`,
                }}
              ></div>
              <div
                className="bg-red-500"
                style={{
                  width: `${calculatePercentage(session.no_votes, session.total_votes)}%`,
                }}
              ></div>
              <div
                className="bg-yellow-500"
                style={{
                  width: `${calculatePercentage(session.abstain_votes, session.total_votes)}%`,
                }}
              ></div>
              <div
                className="bg-gray-400"
                style={{
                  width: `${calculatePercentage(session.absent_votes, session.total_votes)}%`,
                }}
              ></div>
            </div>
            <div className="text-xs text-gray-600 mt-1 text-right">
              総投票数: {session.total_votes}票
            </div>
          </div>

          {/* Individual Vote Records */}
          {session.vote_records && session.vote_records.length > 0 && (
            <div className="border-t border-gray-200 pt-4">
              <button
                onClick={() =>
                  setSelectedSession(
                    selectedSession === session ? null : session,
                  )
                }
                className="text-sm text-blue-600 hover:text-blue-800 mb-3"
              >
                {selectedSession === session
                  ? "議員別投票記録を隠す"
                  : "議員別投票記録を表示"}
              </button>

              {selectedSession === session && (
                <div className="space-y-2">
                  <div className="grid gap-2">
                    {session.vote_records.map((vote, voteIndex) => (
                      <div
                        key={voteIndex}
                        className="flex items-center justify-between p-2 bg-gray-50 rounded"
                      >
                        <div className="flex items-center space-x-3">
                          <span className="font-medium text-gray-900">
                            {vote.member_name}
                          </span>
                          <span className="text-sm text-gray-600">
                            {vote.party_name}
                          </span>
                          <span className="text-xs text-gray-500">
                            {vote.constituency}
                          </span>
                        </div>
                        {getVoteResultBadge(vote.vote_result)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
