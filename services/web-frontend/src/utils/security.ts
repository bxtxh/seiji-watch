/**
 * Security utility functions for input validation, sanitization, and protection
 */

// Input validation patterns
export const VALIDATION_PATTERNS = {
  // Japanese text with common punctuation
  JAPANESE_TEXT:
    /^[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u3400-\u4DBF\s\u3000-\u303F\uFF00-\uFFEF\u0020-\u007E]*$/,
  // Search query (alphanumeric, Japanese, common symbols)
  SEARCH_QUERY:
    /^[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u3400-\u4DBF\s\u3000-\u303F\uFF00-\uFFEF\u0020-\u007E\u002D\u005F\u002E\u003A\u003B\u0021\u003F\u0028\u0029\u005B\u005D\u007B\u007D]*$/,
  // URL validation (basic)
  URL: /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/,
  // Email validation
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
};

// Maximum input lengths
export const INPUT_LIMITS = {
  SEARCH_QUERY: 200,
  TEXTAREA: 1000,
  URL: 2048,
  GENERAL_TEXT: 500,
} as const;

/**
 * Sanitize HTML content to prevent XSS attacks
 */
export function sanitizeHtml(input: string): string {
  if (typeof input !== "string") {
    return "";
  }

  // Basic HTML entity encoding
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;")
    .replace(/\//g, "&#x2F;");
}

/**
 * Sanitize user input for safe processing
 */
export function sanitizeInput(
  input: string,
  maxLength: number = INPUT_LIMITS.GENERAL_TEXT,
): string {
  if (typeof input !== "string") {
    return "";
  }

  // Trim whitespace and limit length
  let sanitized = input.trim().slice(0, maxLength);

  // Remove potentially dangerous characters
  sanitized = sanitized
    .replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, "") // Control characters
    .replace(/javascript:/gi, "") // JavaScript protocol
    .replace(/data:/gi, "") // Data protocol
    .replace(/vbscript:/gi, "") // VBScript protocol
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, ""); // Script tags

  return sanitized;
}

/**
 * Validate search query input
 */
export function validateSearchQuery(query: string): {
  isValid: boolean;
  error?: string;
} {
  if (!query || typeof query !== "string") {
    return { isValid: false, error: "検索クエリが必要です" };
  }

  const trimmed = query.trim();

  if (trimmed.length === 0) {
    return { isValid: false, error: "検索クエリを入力してください" };
  }

  if (trimmed.length > INPUT_LIMITS.SEARCH_QUERY) {
    return {
      isValid: false,
      error: `検索クエリは${INPUT_LIMITS.SEARCH_QUERY}文字以内で入力してください`,
    };
  }

  if (!VALIDATION_PATTERNS.SEARCH_QUERY.test(trimmed)) {
    return { isValid: false, error: "無効な文字が含まれています" };
  }

  return { isValid: true };
}

/**
 * Validate URL input
 */
export function validateUrl(url: string): { isValid: boolean; error?: string } {
  if (!url || typeof url !== "string") {
    return { isValid: false, error: "URLが必要です" };
  }

  const trimmed = url.trim();

  if (trimmed.length > INPUT_LIMITS.URL) {
    return { isValid: false, error: "URLが長すぎます" };
  }

  if (!VALIDATION_PATTERNS.URL.test(trimmed)) {
    return { isValid: false, error: "有効なURLを入力してください" };
  }

  // Additional security: only allow specific domains
  const allowedDomains = [
    "www.sangiin.go.jp",
    "sangiin.go.jp",
    "localhost",
    "127.0.0.1",
    "0.0.0.0", // For Next.js development
  ];

  try {
    const urlObj = new URL(trimmed);
    const hostname = urlObj.hostname.toLowerCase();

    if (
      !allowedDomains.some(
        (domain) => hostname === domain || hostname.endsWith(`.${domain}`),
      )
    ) {
      return { isValid: false, error: "許可されていないドメインです" };
    }
  } catch {
    return { isValid: false, error: "無効なURL形式です" };
  }

  return { isValid: true };
}

/**
 * Rate limiting utility
 */
export class RateLimiter {
  private requests: Map<string, number[]> = new Map();
  private readonly windowMs: number;
  private readonly maxRequests: number;

  constructor(windowMs: number = 60000, maxRequests: number = 10) {
    this.windowMs = windowMs;
    this.maxRequests = maxRequests;
  }

  /**
   * Check if request is allowed
   */
  isAllowed(identifier: string): boolean {
    const now = Date.now();
    const windowStart = now - this.windowMs;

    // Get existing requests for this identifier
    const requests = this.requests.get(identifier) || [];

    // Remove old requests outside the window
    const recentRequests = requests.filter(
      (timestamp) => timestamp > windowStart,
    );

    // Check if under the limit
    if (recentRequests.length >= this.maxRequests) {
      return false;
    }

    // Add current request
    recentRequests.push(now);
    this.requests.set(identifier, recentRequests);

    return true;
  }

  /**
   * Get remaining requests for identifier
   */
  getRemaining(identifier: string): number {
    const now = Date.now();
    const windowStart = now - this.windowMs;
    const requests = this.requests.get(identifier) || [];
    const recentRequests = requests.filter(
      (timestamp) => timestamp > windowStart,
    );

    return Math.max(0, this.maxRequests - recentRequests.length);
  }

  /**
   * Clear all rate limit data
   */
  clear(): void {
    this.requests.clear();
  }
}

/**
 * CSRF token generation and validation
 */
export class CSRFProtection {
  private static tokens: Set<string> = new Set();
  private static readonly TOKEN_LENGTH = 32;
  private static readonly TOKEN_LIFETIME = 3600000; // 1 hour

  /**
   * Generate a CSRF token
   */
  static generateToken(): string {
    const array = new Uint8Array(this.TOKEN_LENGTH);
    if (typeof window !== "undefined" && window.crypto) {
      window.crypto.getRandomValues(array);
    } else {
      // Fallback for server-side
      for (let i = 0; i < array.length; i++) {
        array[i] = Math.floor(Math.random() * 256);
      }
    }

    const token = Array.from(array, (byte) =>
      byte.toString(16).padStart(2, "0"),
    ).join("");
    this.tokens.add(token);

    // Clean up expired tokens after lifetime
    setTimeout(() => {
      this.tokens.delete(token);
    }, this.TOKEN_LIFETIME);

    return token;
  }

  /**
   * Validate a CSRF token
   */
  static validateToken(token: string): boolean {
    if (!token || typeof token !== "string") {
      return false;
    }

    return this.tokens.has(token);
  }

  /**
   * Remove a used token
   */
  static consumeToken(token: string): boolean {
    if (this.validateToken(token)) {
      this.tokens.delete(token);
      return true;
    }
    return false;
  }
}

/**
 * Secure random string generator
 */
export function generateSecureId(length: number = 16): string {
  const characters =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let result = "";

  if (typeof window !== "undefined" && window.crypto) {
    const array = new Uint8Array(length);
    window.crypto.getRandomValues(array);

    for (let i = 0; i < length; i++) {
      result += characters.charAt(array[i] % characters.length);
    }
  } else {
    // Fallback for server-side
    for (let i = 0; i < length; i++) {
      result += characters.charAt(
        Math.floor(Math.random() * characters.length),
      );
    }
  }

  return result;
}

/**
 * Content Security Policy nonce generator
 */
export function generateNonce(): string {
  return generateSecureId(24);
}

/**
 * Safe JSON parsing with error handling
 */
export function safeParse<T>(json: string, fallback: T): T {
  try {
    const parsed = JSON.parse(json);
    return parsed;
  } catch {
    return fallback;
  }
}

/**
 * Secure localStorage wrapper
 */
export const secureStorage = {
  setItem(key: string, value: any): void {
    if (typeof window === "undefined") return;

    try {
      const sanitizedKey = sanitizeInput(key, 100);
      const serialized = JSON.stringify(value);
      localStorage.setItem(sanitizedKey, serialized);
    } catch (error) {
      console.warn("Failed to save to localStorage:", error);
    }
  },

  getItem<T>(key: string, fallback: T): T {
    if (typeof window === "undefined") return fallback;

    try {
      const sanitizedKey = sanitizeInput(key, 100);
      const item = localStorage.getItem(sanitizedKey);
      if (item === null) return fallback;
      return safeParse(item, fallback);
    } catch (error) {
      console.warn("Failed to read from localStorage:", error);
      return fallback;
    }
  },

  removeItem(key: string): void {
    if (typeof window === "undefined") return;

    try {
      const sanitizedKey = sanitizeInput(key, 100);
      localStorage.removeItem(sanitizedKey);
    } catch (error) {
      console.warn("Failed to remove from localStorage:", error);
    }
  },
};

/**
 * Security middleware for API calls
 */
export function createSecureHeaders(): Headers {
  const headers = new Headers();

  // Add CSRF token
  const csrfToken = CSRFProtection.generateToken();
  headers.set("X-CSRF-Token", csrfToken);

  // Add content type
  headers.set("Content-Type", "application/json");

  // Add request ID for tracking
  const requestId = generateSecureId();
  headers.set("X-Request-ID", requestId);

  return headers;
}
