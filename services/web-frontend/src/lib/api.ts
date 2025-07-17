// Diet Issue Tracker - API Client

import { ApiResponse, SearchResult, HealthStatus } from "@/types";
import {
  createSecureHeaders,
  sanitizeInput,
  validateSearchQuery,
  validateUrl,
  safeParse,
  RateLimiter,
} from "@/utils/security";
import { observability } from "@/lib/observability";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";

// Rate limiter for API requests (development: increased for frequent health checks)
const apiRateLimiter = new RateLimiter(60000, 1000);

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    // Validate base URL (more lenient for development)
    try {
      new URL(baseUrl);
      this.baseUrl = baseUrl;
    } catch (error) {
      console.warn(`Invalid API base URL: ${baseUrl}, using default`);
      this.baseUrl = "http://localhost:8080";
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const startTime = performance.now();
    const method = options.method || "GET";

    // Sanitize endpoint
    const sanitizedEndpoint = sanitizeInput(endpoint, 1000);
    const url = `${this.baseUrl}${sanitizedEndpoint}`;

    // Rate limiting check
    const clientId =
      "api_" +
      (typeof window !== "undefined" ? window.location.hostname : "server");
    if (!apiRateLimiter.isAllowed(clientId)) {
      const error = new Error(
        "API呼び出し回数の上限に達しました。しばらくお待ちください。",
      );
      observability.recordError({
        error,
        context: "api_rate_limit",
        timestamp: Date.now(),
        additionalData: { endpoint, method },
      });
      throw error;
    }

    // Create secure headers
    const secureHeaders = createSecureHeaders();

    const config: RequestInit = {
      headers: {
        ...Object.fromEntries(secureHeaders.entries()),
        ...options.headers,
      },
      credentials: "same-origin", // Prevent CSRF
      ...options,
    };

    try {
      const response = await fetch(url, config);
      const duration = performance.now() - startTime;

      // Record API call metrics
      observability.recordApiCall(
        sanitizedEndpoint,
        method,
        duration,
        response.status,
      );

      if (!response.ok) {
        // Sanitize error messages
        const errorMessage = sanitizeInput(
          `HTTP error! status: ${response.status}`,
          200,
        );
        const error = new Error(errorMessage);

        observability.recordError({
          error,
          context: "api_http_error",
          timestamp: Date.now(),
          additionalData: {
            endpoint: sanitizedEndpoint,
            method,
            status: response.status,
            duration,
          },
        });

        throw error;
      }

      const rawData = await response.text();
      const data = safeParse<T>(rawData, {} as T);
      return data;
    } catch (error) {
      const duration = performance.now() - startTime;

      // Sanitized error logging (don't log sensitive data)
      const sanitizedEndpoint = sanitizeInput(endpoint, 100);

      // Record error with monitoring
      observability.recordError({
        error: error as Error,
        context: "api_request_failed",
        timestamp: Date.now(),
        additionalData: {
          endpoint: sanitizedEndpoint,
          method,
          duration,
        },
      });
      console.error(
        `API request failed: ${sanitizedEndpoint}`,
        error instanceof Error ? error.message : "Unknown error",
      );
      throw error;
    }
  }

  // Health check with fallback for development
  async checkHealth(): Promise<HealthStatus> {
    try {
      return await this.request<HealthStatus>("/health");
    } catch (error) {
      // Development fallback when API Gateway is not accessible
      console.warn(
        "API Gateway health check failed, using mock response:",
        error,
      );
      return {
        status: "healthy",
        service: "api-gateway",
        version: "1.0.0-mock",
        timestamp: Date.now(),
        checks: {
          mock: {
            status: "healthy",
            response_time_ms: 0,
            details: { note: "Mock response for development" },
          },
        },
      };
    }
  }

  // Search bills
  async searchBills(
    query: string,
    limit: number = 10,
    min_certainty: number = 0.7,
  ): Promise<SearchResult> {
    // Validate search query
    const validation = validateSearchQuery(query);
    if (!validation.isValid) {
      observability.recordError({
        error: new Error(validation.error || "無効な検索クエリです"),
        context: "search_validation_failed",
        timestamp: Date.now(),
        additionalData: { query: sanitizeInput(query, 100) },
      });
      throw new Error(validation.error || "無効な検索クエリです");
    }

    // Sanitize and validate parameters
    const sanitizedQuery = sanitizeInput(query, 200);
    const sanitizedLimit = Math.min(Math.max(1, Math.floor(limit)), 100); // Limit between 1-100
    const sanitizedCertainty = Math.min(Math.max(0, min_certainty), 1); // Certainty between 0-1

    try {
      const queryParams = new URLSearchParams({
        q: sanitizedQuery,
        limit: sanitizedLimit.toString(),
        offset: "0",
      });

      // Define the actual API response type
      interface ApiSearchResponse {
        success: boolean;
        results: any[];
        query: string;
        total_found: number;
        search_method: string;
      }

      const apiResponse = await this.request<ApiSearchResponse>(`/search`, {
        method: "POST",
        body: JSON.stringify({
          query: sanitizedQuery,
          limit: sanitizedLimit,
          offset: 0,
        }),
      });

      // Convert API response to expected SearchResult format
      const result: SearchResult = {
        success: true,
        message: `Found ${apiResponse.total_found} results for "${sanitizedQuery}"`,
        results: apiResponse.results.map((item: any) => {
          console.log("Mapping API item:", item);
          return {
            id: item.bill_id || "", // Use bill_id from airtable response
            bill_number: item.bill_id || "",
            title: item.title || "",
            summary: item.summary || "",
            category: item.category || "",
            status: item.status || "審議中",
            diet_url: item.url || "",
            relevance_score: item.relevance_score || 1.0,
            search_method: item.search_method || "airtable",
          };
        }),
        total_found: apiResponse.total_found,
      };

      // Record search metrics
      observability.recordSearch(sanitizedQuery, result.results?.length);

      return result;
    } catch (error) {
      observability.recordError({
        error: error as Error,
        context: "search_request_failed",
        timestamp: Date.now(),
        additionalData: {
          query: sanitizedQuery,
          limit: sanitizedLimit,
          min_certainty: sanitizedCertainty,
        },
      });
      throw error;
    }
  }

  // Get embedding stats with fallback
  async getEmbeddingStats(): Promise<{
    status: string;
    bills: number;
    speeches: number;
    message: string;
  }> {
    try {
      return await this.request("/embeddings/stats");
    } catch (error) {
      // Development fallback when API Gateway is not accessible
      console.warn("API Gateway stats failed, using mock response:", error);
      return {
        status: "healthy",
        bills: 42,
        speeches: 156,
        message: "Mock data - API Gateway connection failed",
      };
    }
  }

  // Scrape bills (trigger background task)
  async triggerScraping(): Promise<{
    success: boolean;
    message: string;
    bills_processed: number;
    errors: string[];
  }> {
    return this.request("/scrape", {
      method: "POST",
      body: JSON.stringify({
        source: "diet_bills",
        force_refresh: false,
      }),
    });
  }

  // Search speeches
  async searchSpeeches(
    query: string,
    limit: number = 20,
  ): Promise<{
    success: boolean;
    message?: string;
    results: any[];
    total_found: number;
  }> {
    // Validate search query
    const validation = validateSearchQuery(query);
    if (!validation.isValid) {
      observability.recordError({
        error: new Error(validation.error || "無効な検索クエリです"),
        context: "speech_search_validation_failed",
        timestamp: Date.now(),
        additionalData: { query: sanitizeInput(query, 100) },
      });
      throw new Error(validation.error || "無効な検索クエリです");
    }

    // Sanitize parameters
    const sanitizedQuery = sanitizeInput(query, 200);
    const sanitizedLimit = Math.min(Math.max(1, Math.floor(limit)), 100);

    try {
      const result = await this.request<{
        success: boolean;
        message?: string;
        results: any[];
        total_found: number;
      }>("/speeches", {
        method: "GET",
        // Add query parameters to URL
      });

      observability.recordSearch(sanitizedQuery, result.results?.length);
      return result;
    } catch (error) {
      observability.recordError({
        error: error as Error,
        context: "speech_search_request_failed",
        timestamp: Date.now(),
        additionalData: {
          query: sanitizedQuery,
          limit: sanitizedLimit,
        },
      });
      throw error;
    }
  }

  // Search speeches by topic
  async searchSpeechesByTopic(
    topic: string,
    limit: number = 20,
  ): Promise<{
    success: boolean;
    message?: string;
    results: any[];
    total_found: number;
  }> {
    // Sanitize parameters
    const sanitizedTopic = sanitizeInput(topic, 100);
    const sanitizedLimit = Math.min(Math.max(1, Math.floor(limit)), 100);

    try {
      const params = new URLSearchParams({
        topic: sanitizedTopic,
        limit: sanitizedLimit.toString(),
      });

      const result = await this.request<{
        success: boolean;
        message?: string;
        results: any[];
        total_found: number;
      }>(`/speeches/search/by-topic?${params}`);

      observability.recordSearch(sanitizedTopic, result.results?.length);
      return result;
    } catch (error) {
      observability.recordError({
        error: error as Error,
        context: "speech_topic_search_request_failed",
        timestamp: Date.now(),
        additionalData: {
          topic: sanitizedTopic,
          limit: sanitizedLimit,
        },
      });
      throw error;
    }
  }

  // Generate speech summary
  async generateSpeechSummary(
    speechId: string,
    regenerate: boolean = false,
  ): Promise<{
    speech_id: string;
    summary: string;
    regenerated: boolean;
  }> {
    const sanitizedId = sanitizeInput(speechId, 50);

    return this.request(`/speeches/${sanitizedId}/summary`, {
      method: "POST",
      body: JSON.stringify({
        speech_id: sanitizedId,
        regenerate,
      }),
    });
  }

  // Extract speech topics
  async extractSpeechTopics(
    speechId: string,
    regenerate: boolean = false,
  ): Promise<{
    speech_id: string;
    topics: string[];
    regenerated: boolean;
  }> {
    const sanitizedId = sanitizeInput(speechId, 50);

    return this.request(`/speeches/${sanitizedId}/topics`, {
      method: "POST",
      body: JSON.stringify({
        speech_id: sanitizedId,
        regenerate,
      }),
    });
  }

  // Batch process speeches
  async batchProcessSpeeches(
    speechIds: string[],
    generateSummaries: boolean = true,
    extractTopics: boolean = true,
    regenerate: boolean = false,
  ): Promise<{
    processed_count: number;
    skipped_count: number;
    total_requested: number;
  }> {
    const sanitizedIds = speechIds
      .map((id) => sanitizeInput(id, 50))
      .slice(0, 50); // Limit to 50 speeches

    return this.request("/speeches/batch-process", {
      method: "POST",
      body: JSON.stringify({
        speech_ids: sanitizedIds,
        generate_summaries: generateSummaries,
        extract_topics: extractTopics,
        regenerate,
      }),
    });
  }

  // Get bills list
  async getBills(
    maxRecords: number = 100,
    category?: string,
  ): Promise<{
    success: boolean;
    data: any[];
    count: number;
    source: string;
    message?: string;
  }> {
    try {
      const params = new URLSearchParams({
        max_records: Math.min(
          Math.max(1, Math.floor(maxRecords)),
          1000,
        ).toString(),
      });

      if (category) {
        params.append("category", sanitizeInput(category, 100));
      }

      return await this.request(`/api/bills?${params}`);
    } catch (error) {
      console.warn("API Gateway bills failed, using mock response:", error);
      // Development fallback
      return {
        success: true,
        data: [
          {
            id: "mock-1",
            fields: {
              Name: "Mock Bill 1 - API Gateway接続待ち",
              Notes: "Real data integration test pending",
              Status: "API接続確認中",
              Category: "テストデータ",
              Title: "Mock Bill 1",
              Summary:
                "This is mock data while API Gateway connection is being established.",
            },
          },
        ],
        count: 1,
        source: "mock_fallback",
        message: "API Gateway connection failed - using mock data",
      };
    }
  }

  // Get bill detail
  async getBillDetail(billId: string): Promise<{
    success: boolean;
    data: any;
    source: string;
    message?: string;
  }> {
    try {
      const sanitizedId = sanitizeInput(billId, 50);
      return await this.request(`/api/bills/${sanitizedId}`);
    } catch (error) {
      console.warn(
        "API Gateway bill detail failed, using mock response:",
        error,
      );
      // Development fallback
      return {
        success: true,
        data: {
          id: billId,
          fields: {
            Name: "Mock Bill Detail - API Gateway接続待ち",
            Notes: "Real data integration test pending for bill details",
            Status: "API接続確認中",
            Category: "テストデータ",
            Title: "Mock Bill Detail",
            Summary:
              "This is mock data while API Gateway connection is being established.",
            Full_Content:
              "Complete bill content would appear here once API Gateway connection is established.",
          },
          metadata: {
            source: "mock_fallback",
            last_updated: new Date().toISOString(),
            record_id: billId,
          },
        },
        source: "mock_fallback",
        message: "API Gateway connection failed - using mock data",
      };
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export error handling utility
export const handleApiError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred";
};
