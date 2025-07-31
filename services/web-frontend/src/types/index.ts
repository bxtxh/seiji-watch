// Diet Issue Tracker - Frontend Types

export interface PolicyCategory {
  id: string;
  cap_code?: string;
  layer: string;
  title_ja: string;
  parent_category?: PolicyCategory;
}

export interface Bill {
  id: string;
  bill_number: string;
  title: string;
  summary: string;
  policy_category?: PolicyCategory; // PolicyCategory (政策分野) - CAP基準の政策分類
  status: string;
  diet_url: string;
  relevance_score?: number;
  search_method?: string;
  related_issues?: string[];
  issue_tags?: string[];

  // Enhanced detailed content fields
  bill_outline?: string; // 議案要旨相当の長文情報
  background_context?: string; // 提出背景・経緯
  expected_effects?: string; // 期待される効果
  key_provisions?: string[]; // 主要条項リスト
  related_laws?: string[]; // 関連法律リスト
  implementation_date?: string; // 施行予定日

  // Process tracking fields
  committee_assignments?: CommitteeAssignment[]; // 委員会付託情報
  voting_results?: VotingSession[]; // 採決結果
  amendments?: Amendment[]; // 修正内容
  inter_house_status?: string; // 両院間の状況
  legislative_stage?: LegislativeStage; // 立法段階情報

  // 後方互換性のため (段階的移行)
  category?: string;
}

export interface CommitteeAssignment {
  committee_name: string;
  assignment_date: string;
  status: "pending" | "in_progress" | "completed";
  house: "衆議院" | "参議院";
}

export interface Amendment {
  amendment_id: string;
  title: string;
  description: string;
  proposed_by: string;
  proposed_date: string;
  status: "proposed" | "adopted" | "rejected";
  amendment_text?: string;
}

export interface LegislativeStage {
  current_stage: "提出" | "審議中" | "委員会" | "採決待ち" | "成立" | "否決";
  stage_progress: number; // 0-100の進捗率
  next_scheduled_action?: string;
  next_action_date?: string;
  milestones: LegislativeMilestone[];
}

export interface LegislativeMilestone {
  stage: string;
  date: string;
  description: string;
  completed: boolean;
  house?: "衆議院" | "参議院";
}

export interface Speech {
  id: string;
  meeting_id: string;
  speaker_id?: string;
  related_bill_id?: string;
  speech_order: number;
  start_time?: string;
  end_time?: string;
  duration_seconds?: number;
  speaker_name?: string;
  speaker_title?: string;
  speaker_type: string;
  original_text: string;
  cleaned_text?: string;
  speech_type?: string;
  summary?: string;
  key_points?: string[];
  topics?: string[];
  sentiment?: string;
  stance?: string;
  word_count?: number;
  confidence_score?: string;
  is_interruption: boolean;
  is_processed: boolean;
  needs_review: boolean;
}

export interface SearchResult {
  success: boolean;
  message: string;
  results: Bill[];
  total_found: number;
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data?: T;
  error?: string;
}

export interface SearchFilters {
  category?: string;
  status?: string;
  limit?: number;
  min_certainty?: number;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  timestamp?: number;
  checks?: Record<string, any>;
  metrics_summary?: Record<string, any>;
}

export interface Issue {
  id: string;
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
  status: "active" | "reviewed" | "archived";
  stage?: string; // 審議ステージ (審議前, 審議中, 採決待ち, 成立)
  policy_category?: PolicyCategory; // PolicyCategory (政策分野) - CAP基準の政策分類
  issue_tags?: IssueTag[]; // IssueTag (イシュータグ) - Issue特有の分類タグ
  related_bills?: string[];
  related_bills_count?: number;
  extraction_confidence?: number;
  review_notes?: string;
  is_llm_generated?: boolean;
  created_at?: string;
  updated_at?: string;
  schedule?: {
    from: string;
    to: string;
  };
}

export interface IssueTag {
  id: string;
  name: string;
  color_code: string;
  category: string;
  description?: string;
}

export interface VoteResult {
  member_name: string;
  party_name: string;
  constituency: string;
  vote_result: "yes" | "no" | "abstain" | "absent" | "present";
}

export interface VotingSession {
  bill_number: string;
  bill_title: string;
  vote_date: string;
  vote_type: string;
  vote_stage?: string;
  committee_name?: string;
  house: string;
  total_votes: number;
  yes_votes: number;
  no_votes: number;
  abstain_votes: number;
  absent_votes: number;
  is_final_vote: boolean;
  vote_records?: VoteResult[];
}

export interface Member {
  id: string;
  name_ja: string;
  name_en?: string;
  party: string;
  house: string;
  district: string;
  profile?: string;
  photo_url?: string;
}
