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
}

export interface Speech {
  id: string;
  text: string;
  speaker: string;
  meeting_id: string;
  duration: number;
  language: string;
  quality_passed: boolean;
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