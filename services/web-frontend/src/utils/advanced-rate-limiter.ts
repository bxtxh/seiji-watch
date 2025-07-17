/**
 * Advanced Rate Limiting with multiple strategies and monitoring
 */

export interface RateLimitRule {
  windowMs: number;
  maxRequests: number;
  blockDurationMs?: number;
  skipSuccessfulRequests?: boolean;
  skipFailedRequests?: boolean;
}

export interface RateLimitInfo {
  limit: number;
  remaining: number;
  resetTime: number;
  retryAfter?: number;
  blocked: boolean;
}

export interface RateLimitConfig {
  // Different rules for different types of requests
  search: RateLimitRule;
  api: RateLimitRule;
  auth: RateLimitRule;
  general: RateLimitRule;
}

export class AdvancedRateLimiter {
  private requests: Map<
    string,
    Array<{ timestamp: number; success: boolean }>
  > = new Map();
  private blockedUntil: Map<string, number> = new Map();
  protected config: RateLimitConfig;

  constructor(config?: Partial<RateLimitConfig>) {
    this.config = {
      search: {
        windowMs: 60 * 1000, // 1 minute
        maxRequests: 10,
        blockDurationMs: 5 * 60 * 1000, // 5 minutes block
        skipSuccessfulRequests: false,
        skipFailedRequests: false,
      },
      api: {
        windowMs: 60 * 1000, // 1 minute
        maxRequests: 30,
        blockDurationMs: 10 * 60 * 1000, // 10 minutes block
        skipSuccessfulRequests: false,
        skipFailedRequests: true, // Don't count failed requests
      },
      auth: {
        windowMs: 15 * 60 * 1000, // 15 minutes
        maxRequests: 5, // Very strict for auth
        blockDurationMs: 30 * 60 * 1000, // 30 minutes block
        skipSuccessfulRequests: true,
        skipFailedRequests: false,
      },
      general: {
        windowMs: 60 * 1000, // 1 minute
        maxRequests: 20,
        blockDurationMs: 2 * 60 * 1000, // 2 minutes block
        skipSuccessfulRequests: false,
        skipFailedRequests: false,
      },
      ...config,
    };
  }

  /**
   * Check if a request is allowed
   */
  isAllowed(
    identifier: string,
    type: keyof RateLimitConfig = "general",
    requestInfo?: { userAgent?: string; ip?: string },
  ): RateLimitInfo {
    const rule = this.config[type];
    const now = Date.now();
    const key = `${type}:${identifier}`;

    // Check if currently blocked
    const blockedUntil = this.blockedUntil.get(key);
    if (blockedUntil && now < blockedUntil) {
      return {
        limit: rule.maxRequests,
        remaining: 0,
        resetTime: blockedUntil,
        retryAfter: Math.ceil((blockedUntil - now) / 1000),
        blocked: true,
      };
    }

    // Clear expired block
    if (blockedUntil && now >= blockedUntil) {
      this.blockedUntil.delete(key);
    }

    // Get request history
    const requests = this.requests.get(key) || [];
    const windowStart = now - rule.windowMs;

    // Filter requests in current window
    const recentRequests = requests.filter((req) => {
      if (req.timestamp <= windowStart) return false;
      if (rule.skipSuccessfulRequests && req.success) return false;
      if (rule.skipFailedRequests && !req.success) return false;
      return true;
    });

    const remaining = Math.max(0, rule.maxRequests - recentRequests.length);
    const resetTime =
      Math.max(...recentRequests.map((r) => r.timestamp), now - rule.windowMs) +
      rule.windowMs;

    // Check if over limit
    if (recentRequests.length >= rule.maxRequests) {
      // Block if configured
      if (rule.blockDurationMs) {
        this.blockedUntil.set(key, now + rule.blockDurationMs);
      }

      return {
        limit: rule.maxRequests,
        remaining: 0,
        resetTime,
        retryAfter: rule.blockDurationMs
          ? Math.ceil(rule.blockDurationMs / 1000)
          : Math.ceil((resetTime - now) / 1000),
        blocked: true,
      };
    }

    return {
      limit: rule.maxRequests,
      remaining,
      resetTime,
      blocked: false,
    };
  }

  /**
   * Record a request
   */
  recordRequest(
    identifier: string,
    type: keyof RateLimitConfig = "general",
    success: boolean = true,
  ): void {
    const key = `${type}:${identifier}`;
    const now = Date.now();
    const requests = this.requests.get(key) || [];

    // Add current request
    requests.push({ timestamp: now, success });

    // Clean old requests
    const rule = this.config[type];
    const windowStart = now - rule.windowMs;
    const filteredRequests = requests.filter(
      (req) => req.timestamp > windowStart,
    );

    this.requests.set(key, filteredRequests);
  }

  /**
   * Get rate limit statistics
   */
  getStats(identifier: string, type: keyof RateLimitConfig = "general") {
    const key = `${type}:${identifier}`;
    const requests = this.requests.get(key) || [];
    const rule = this.config[type];
    const now = Date.now();
    const windowStart = now - rule.windowMs;

    const recentRequests = requests.filter(
      (req) => req.timestamp > windowStart,
    );
    const successfulRequests = recentRequests.filter((req) => req.success);
    const failedRequests = recentRequests.filter((req) => !req.success);

    return {
      totalRequests: recentRequests.length,
      successfulRequests: successfulRequests.length,
      failedRequests: failedRequests.length,
      isBlocked:
        this.blockedUntil.has(key) && now < (this.blockedUntil.get(key) || 0),
      limit: rule.maxRequests,
      remaining: Math.max(0, rule.maxRequests - recentRequests.length),
    };
  }

  /**
   * Reset rate limit for identifier
   */
  reset(identifier: string, type?: keyof RateLimitConfig): void {
    if (type) {
      const key = `${type}:${identifier}`;
      this.requests.delete(key);
      this.blockedUntil.delete(key);
    } else {
      // Reset all types for this identifier
      Object.keys(this.config).forEach((t) => {
        const key = `${t}:${identifier}`;
        this.requests.delete(key);
        this.blockedUntil.delete(key);
      });
    }
  }

  /**
   * Clean up old data
   */
  cleanup(): void {
    const now = Date.now();

    // Clean up old requests
    for (const [key, requests] of this.requests.entries()) {
      const type = key.split(":")[0] as keyof RateLimitConfig;
      const rule = this.config[type];
      if (!rule) continue;

      const windowStart = now - rule.windowMs;
      const filteredRequests = requests.filter(
        (req) => req.timestamp > windowStart,
      );

      if (filteredRequests.length === 0) {
        this.requests.delete(key);
      } else {
        this.requests.set(key, filteredRequests);
      }
    }

    // Clean up expired blocks
    for (const [key, blockedUntil] of this.blockedUntil.entries()) {
      if (now >= blockedUntil) {
        this.blockedUntil.delete(key);
      }
    }
  }

  /**
   * Get all active rate limits
   */
  getAllStats(): { [key: string]: any } {
    const stats: { [key: string]: any } = {};

    for (const [key] of this.requests.entries()) {
      const [type, identifier] = key.split(":");
      if (!stats[identifier]) {
        stats[identifier] = {};
      }
      stats[identifier][type] = this.getStats(
        identifier,
        type as keyof RateLimitConfig,
      );
    }

    return stats;
  }
}

// Singleton instance
export const globalRateLimiter = new AdvancedRateLimiter();

// Auto cleanup every 5 minutes
if (typeof window !== "undefined") {
  setInterval(
    () => {
      globalRateLimiter.cleanup();
    },
    5 * 60 * 1000,
  );
}

/**
 * Adaptive rate limiter that adjusts limits based on system load
 */
export class AdaptiveRateLimiter extends AdvancedRateLimiter {
  private systemLoad: number = 0;
  private errorRate: number = 0;
  private adaptiveMultiplier: number = 1;

  updateSystemMetrics(load: number, errorRate: number): void {
    this.systemLoad = Math.min(Math.max(load, 0), 1); // 0-1
    this.errorRate = Math.min(Math.max(errorRate, 0), 1); // 0-1

    // Adjust rate limits based on system health
    if (this.systemLoad > 0.8 || this.errorRate > 0.1) {
      // System under stress, reduce limits
      this.adaptiveMultiplier = 0.5;
    } else if (this.systemLoad < 0.3 && this.errorRate < 0.02) {
      // System healthy, allow more requests
      this.adaptiveMultiplier = 1.5;
    } else {
      // Normal operation
      this.adaptiveMultiplier = 1;
    }
  }

  isAllowed(
    identifier: string,
    type: keyof RateLimitConfig = "general",
    requestInfo?: any,
  ): RateLimitInfo {
    // Temporarily modify config based on adaptive multiplier
    const originalRule = this.config[type];
    const adaptedRule = {
      ...originalRule,
      maxRequests: Math.floor(
        originalRule.maxRequests * this.adaptiveMultiplier,
      ),
    };

    // Temporarily replace config
    const originalConfig = this.config[type];
    this.config[type] = adaptedRule;

    const result = super.isAllowed(identifier, type, requestInfo);

    // Restore original config
    this.config[type] = originalConfig;

    return result;
  }
}

/**
 * Rate limit middleware for components
 */
export function useRateLimit(type: keyof RateLimitConfig = "general") {
  const getIdentifier = (): string => {
    if (typeof window === "undefined") return "server";

    // Create identifier from multiple factors
    const factors = [
      window.location.hostname,
      navigator.userAgent ? btoa(navigator.userAgent).slice(0, 10) : "unknown",
      sessionStorage.getItem("session_id") ||
        localStorage.getItem("user_id") ||
        "anonymous",
    ];

    return factors.join("_");
  };

  const checkLimit = (): RateLimitInfo => {
    return globalRateLimiter.isAllowed(getIdentifier(), type);
  };

  const recordRequest = (success: boolean = true): void => {
    globalRateLimiter.recordRequest(getIdentifier(), type, success);
  };

  const getStats = () => {
    return globalRateLimiter.getStats(getIdentifier(), type);
  };

  return {
    checkLimit,
    recordRequest,
    getStats,
    reset: () => globalRateLimiter.reset(getIdentifier(), type),
  };
}
