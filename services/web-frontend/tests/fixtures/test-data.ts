/**
 * Test data fixtures for Diet Issue Tracker E2E tests
 */

export const testQueries = {
  valid: ["税制改正", "社会保障", "予算", "外交", "環境"],
  invalid: [
    "", // Empty
    "a".repeat(201), // Too long
    '<script>alert("xss")</script>', // XSS attempt
    "SELECT * FROM bills", // SQL injection attempt
  ],
  edge: [
    "あ", // Single character
    "税制改正 社会保障 予算", // Multiple terms
    "①②③", // Special numbers
    "COVID-19", // Mixed languages
  ],
};

export const testUrls = {
  internal: ["/", "/issues"],
  external: ["https://www.sangiin.go.jp/"],
  invalid: [
    'javascript:alert("xss")',
    'data:text/html,<script>alert("xss")</script>',
    "http://malicious-site.com",
  ],
};

export const mockApiResponses = {
  healthCheck: {
    success: {
      status: "healthy",
      message: "API is running normally",
      timestamp: new Date().toISOString(),
    },
    error: {
      status: "error",
      message: "Service unavailable",
      timestamp: new Date().toISOString(),
    },
  },

  searchResults: {
    success: {
      success: true,
      results: [
        {
          bill_number: "Test-001",
          title: "テスト法案第1号",
          summary: "これはテスト用の法案です。",
          status: "審議中",
          category: "税制",
          submission_date: "2025-01-01",
          search_method: "vector",
          similarity_score: 0.95,
          url: "https://www.sangiin.go.jp/test-bill-001",
        },
        {
          bill_number: "Test-002",
          title: "テスト法案第2号",
          summary: "これは2番目のテスト法案です。",
          status: "成立",
          category: "社会保障",
          submission_date: "2025-01-02",
          search_method: "vector",
          similarity_score: 0.87,
          url: "https://www.sangiin.go.jp/test-bill-002",
        },
      ],
      total_found: 2,
      query: "テスト",
      search_method: "vector",
    },
    empty: {
      success: true,
      results: [],
      total_found: 0,
      query: "nonexistent",
      search_method: "vector",
    },
    error: {
      success: false,
      message: "Search service temporarily unavailable",
      results: [],
      total_found: 0,
    },
  },

  embeddingStats: {
    success: {
      status: "ready",
      bills: 1250,
      speeches: 4580,
      message: "Embedding service is operational",
    },
    error: {
      status: "error",
      bills: 0,
      speeches: 0,
      message: "Embedding service is unavailable",
    },
  },
};

export const testViewports = {
  mobile: { width: 375, height: 667 },
  mobileLandscape: { width: 667, height: 375 },
  tablet: { width: 768, height: 1024 },
  tabletLandscape: { width: 1024, height: 768 },
  desktop: { width: 1280, height: 720 },
  largeDesktop: { width: 1920, height: 1080 },
};

export const accessibilityTestCases = [
  {
    name: "Keyboard navigation",
    description: "All interactive elements should be keyboard accessible",
    selectors: ["button", "a", "input", "select"],
  },
  {
    name: "Focus management",
    description: "Focus should be visible and logical",
    selectors: [":focus"],
  },
  {
    name: "ARIA labels",
    description: "Interactive elements should have proper ARIA labels",
    selectors: ['[role="button"]', '[role="link"]', '[role="textbox"]'],
  },
  {
    name: "Color contrast",
    description: "Text should have sufficient color contrast",
    selectors: ["p", "h1", "h2", "h3", "button", "a"],
  },
];

export const performanceThresholds = {
  // Performance budget (in milliseconds)
  pageLoad: 2000,
  domContentLoaded: 1000,
  firstContentfulPaint: 1500,
  largestContentfulPaint: 2500,
  firstInputDelay: 100,
  cumulativeLayoutShift: 0.1,

  // Mobile-specific thresholds (stricter)
  mobile: {
    pageLoad: 3000,
    domContentLoaded: 1500,
    firstContentfulPaint: 2000,
  },
};

export const securityTestCases = [
  {
    name: "XSS Prevention",
    input: '<script>alert("xss")</script>',
    expectedBehavior: "Should be sanitized or rejected",
  },
  {
    name: "SQL Injection Prevention",
    input: "'; DROP TABLE bills; --",
    expectedBehavior: "Should be sanitized or rejected",
  },
  {
    name: "CSRF Protection",
    description: "Forms should include CSRF tokens",
    selectors: ["form"],
  },
  {
    name: "Content Security Policy",
    description: "CSP headers should be present",
    expectedHeaders: ["content-security-policy"],
  },
  {
    name: "HTTPS Enforcement",
    description: "HSTS headers should be present",
    expectedHeaders: ["strict-transport-security"],
  },
];

export const pwaTestScenarios = [
  {
    name: "Service Worker Registration",
    description: "Service worker should be registered",
    check: () => "serviceWorker" in navigator,
  },
  {
    name: "Manifest Presence",
    description: "Web app manifest should be present",
    selector: 'link[rel="manifest"]',
  },
  {
    name: "Install Prompt",
    description: "Install prompt should be available",
    selector: 'button:has-text("アプリをインストール")',
  },
  {
    name: "Offline Functionality",
    description: "App should work offline",
    scenario: "network-offline",
  },
];

export const errorScenarios = [
  {
    name: "Network Error",
    description: "Handle network failures gracefully",
    mockResponse: { status: 500, body: "Internal Server Error" },
  },
  {
    name: "API Timeout",
    description: "Handle API timeouts gracefully",
    mockResponse: { delay: 30000 },
  },
  {
    name: "Malformed Response",
    description: "Handle malformed API responses",
    mockResponse: { body: "invalid json{" },
  },
  {
    name: "Rate Limiting",
    description: "Handle rate limiting gracefully",
    mockResponse: { status: 429, body: "Too Many Requests" },
  },
];
