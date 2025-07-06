// Diet Issue Tracker - Frontend Types

export interface Bill {
  bill_number: string;
  title: string;
  summary: string;
  category: string;
  status: string;
  diet_url: string;
  relevance_score?: number;
  search_method?: string;
  related_issues?: string[];
  issue_tags?: string[];
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
}

export interface Issue {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  status: 'active' | 'reviewed' | 'archived';
  related_bills?: string[];
  issue_tags?: string[];
  created_at?: string;
  updated_at?: string;
  extraction_confidence?: number;
  review_notes?: string;
  is_llm_generated?: boolean;
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
  vote_result: 'yes' | 'no' | 'abstain' | 'absent' | 'present';
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