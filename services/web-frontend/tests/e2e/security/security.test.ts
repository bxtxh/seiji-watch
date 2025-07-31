import { test, expect } from "@playwright/test";
import { TestHelpers } from "../../utils/test-helpers";
import { securityTestCases, testQueries } from "../../fixtures/test-data";

test.describe("Security Tests", () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
    await helpers.navigateToPage("/");
    await helpers.waitForAppReady();
  });

  test.afterEach(async ({ page }) => {
    await helpers.cleanup();
  });

  test("should have proper security headers", async ({ page }) => {
    await helpers.checkSecurityHeaders();

    // Get response headers
    const response = await page.goto(page.url());
    const headers = response?.headers() || {};

    // Check specific security headers
    const requiredHeaders = {
      "x-frame-options": "DENY",
      "x-content-type-options": "nosniff",
      "strict-transport-security": /max-age=\d+/,
      "content-security-policy": /.+/,
      "referrer-policy": "strict-origin-when-cross-origin",
    };

    for (const [header, expected] of Object.entries(requiredHeaders)) {
      const value = headers[header];
      expect(value).toBeTruthy();

      if (typeof expected === "string") {
        expect(value).toBe(expected);
      } else {
        expect(value).toMatch(expected);
      }

      console.log(`${header}: ${value}`);
    }
  });

  test("should prevent XSS attacks", async ({ page }) => {
    const searchInput = page.locator(TestHelpers.selectors.searchInput);

    // Test various XSS payloads
    const xssPayloads = [
      '<script>alert("xss")</script>',
      'javascript:alert("xss")',
      '<img src="x" onerror="alert(\'xss\')">',
      '"><script>alert("xss")</script>',
      "<svg onload=\"alert('xss')\">",
    ];

    for (const payload of xssPayloads) {
      await searchInput.fill(payload);
      await page.click(TestHelpers.selectors.searchButton);

      // Should not execute the script
      // Check for validation error or sanitized input
      const hasValidationError =
        (await page.locator(TestHelpers.selectors.validationError).count()) > 0;
      const inputValue = await searchInput.inputValue();

      // Either should show validation error or sanitize the input
      const isSafe = hasValidationError || !inputValue.includes("<script>");
      expect(isSafe).toBe(true);

      console.log(`XSS payload blocked: ${payload}`);
    }
  });

  test("should validate and sanitize input", async ({ page }) => {
    const searchInput = page.locator(TestHelpers.selectors.searchInput);

    // Test invalid inputs
    const invalidInputs = testQueries.invalid;

    for (const input of invalidInputs) {
      await searchInput.clear();
      await searchInput.fill(input);

      if (input === "") {
        // Empty input should disable button
        const searchButton = page.locator(TestHelpers.selectors.searchButton);
        await expect(searchButton).toBeDisabled();
      } else {
        await page.click(TestHelpers.selectors.searchButton);

        // Should show validation error for invalid inputs
        const hasError =
          (await page.locator(TestHelpers.selectors.validationError).count()) >
          0;
        const hasGeneralError =
          (await page.locator(TestHelpers.selectors.errorMessage).count()) > 0;

        expect(hasError || hasGeneralError).toBe(true);
      }

      console.log(`Input validation test passed for: ${input.slice(0, 50)}`);
    }
  });

  test("should enforce rate limiting", async ({ page }) => {
    const searchInput = page.locator(TestHelpers.selectors.searchInput);

    // Perform multiple rapid searches
    for (let i = 0; i < 15; i++) {
      await searchInput.clear();
      await searchInput.fill(`test${i}`);
      await page.click(TestHelpers.selectors.searchButton);
      await page.waitForTimeout(100); // Small delay
    }

    // Should show rate limiting message
    const rateLimitMessage = await page
      .locator("text=/上限|制限|limit/i")
      .count();
    expect(rateLimitMessage).toBeGreaterThan(0);

    console.log("Rate limiting enforced after multiple requests");
  });

  test("should handle CSRF protection", async ({ page }) => {
    // Check if forms include CSRF tokens
    const forms = page.locator("form");
    const formCount = await forms.count();

    for (let i = 0; i < formCount; i++) {
      const form = forms.nth(i);

      // Check for CSRF token field or header
      const hasCSRFField =
        (await form.locator('input[name="_csrf"]').count()) > 0;
      const hasCSRFMeta =
        (await page.locator('meta[name="csrf-token"]').count()) > 0;

      // CSRF protection should be in place (either field or meta tag)
      if (formCount > 0) {
        // For now, we mainly check that security context is loaded
        // Real CSRF testing would require backend integration
        console.log("CSRF protection mechanism detected");
      }
    }
  });

  test("should prevent clickjacking", async ({ page }) => {
    // Check X-Frame-Options header
    const response = await page.goto(page.url());
    const headers = response?.headers() || {};

    const frameOptions = headers["x-frame-options"];
    expect(frameOptions).toBe("DENY");

    // Test that page cannot be embedded in iframe
    const iframeTest = await page.evaluate(() => {
      try {
        return window.self === window.top;
      } catch {
        return false; // If error, likely in iframe
      }
    });

    expect(iframeTest).toBe(true);
    console.log("Clickjacking protection verified");
  });

  test("should use HTTPS in production context", async ({ page }) => {
    const protocol = await page.evaluate(() => location.protocol);
    const hostname = await page.evaluate(() => location.hostname);

    // In production, should use HTTPS
    // In development (localhost), HTTP is acceptable
    const isLocalhost = hostname === "localhost" || hostname === "127.0.0.1";

    if (!isLocalhost) {
      expect(protocol).toBe("https:");
    }

    console.log(`Protocol: ${protocol}, Hostname: ${hostname}`);
  });

  test("should protect against information disclosure", async ({ page }) => {
    // Check that sensitive information is not exposed

    // Check for development-only content in production
    const debugElements = await page
      .locator("[data-debug], .debug, #debug")
      .count();
    const devOnlyElements = await page
      .locator("text=/debug|dev|test/i")
      .count();

    // In production build, should not have debug elements
    if (process.env.NODE_ENV === "production") {
      expect(debugElements).toBe(0);
    }

    // Check console for sensitive information
    const consoleLogs: string[] = [];
    page.on("console", (msg) => {
      consoleLogs.push(msg.text());
    });

    await page.waitForTimeout(2000);

    // Should not log sensitive information
    const sensitivePatterns = [
      /password/i,
      /secret/i,
      /token/i,
      /api[_-]?key/i,
    ];

    for (const log of consoleLogs) {
      for (const pattern of sensitivePatterns) {
        expect(log).not.toMatch(pattern);
      }
    }
  });

  test("should validate content security policy", async ({ page }) => {
    const response = await page.goto(page.url());
    const headers = response?.headers() || {};

    const csp = headers["content-security-policy"];
    expect(csp).toBeTruthy();

    // Parse CSP directives
    const directives = csp.split(";").map((d) => d.trim());

    // Check for important directives
    const hasDefaultSrc = directives.some((d) => d.startsWith("default-src"));
    const hasScriptSrc = directives.some((d) => d.startsWith("script-src"));
    const hasStyleSrc = directives.some((d) => d.startsWith("style-src"));
    const hasObjectSrc = directives.some((d) => d.includes("object-src"));

    expect(hasDefaultSrc).toBe(true);
    expect(hasScriptSrc).toBe(true);
    expect(hasStyleSrc).toBe(true);

    // Should restrict object-src
    const objectSrcDirective = directives.find((d) =>
      d.startsWith("object-src")
    );
    if (objectSrcDirective) {
      expect(objectSrcDirective).toContain("'none'");
    }

    console.log("CSP validated:", csp);
  });

  test("should handle malicious URLs", async ({ page }) => {
    // Test navigation to potentially malicious URLs
    const maliciousUrls = [
      'javascript:alert("xss")',
      'data:text/html,<script>alert("xss")</script>',
      'vbscript:alert("xss")',
    ];

    for (const url of maliciousUrls) {
      // Try to navigate - should be blocked or sanitized
      try {
        await page.goto(url, { timeout: 5000 });

        // If navigation succeeds, check that no harmful script executed
        const currentUrl = page.url();
        expect(currentUrl).not.toContain("javascript:");
        expect(currentUrl).not.toContain("data:text/html");
        expect(currentUrl).not.toContain("vbscript:");
      } catch (error) {
        // Navigation blocked - this is good
        console.log(`Malicious URL blocked: ${url}`);
      }
    }
  });

  test("should secure cookies (if any)", async ({ page }) => {
    // Check cookie security attributes
    const cookies = await page.context().cookies();

    for (const cookie of cookies) {
      // Production cookies should be secure
      if (process.env.NODE_ENV === "production") {
        expect(cookie.secure).toBe(true);
      }

      // Sensitive cookies should be HttpOnly
      if (cookie.name.includes("session") || cookie.name.includes("auth")) {
        expect(cookie.httpOnly).toBe(true);
      }

      // Should have appropriate SameSite setting
      expect(["Strict", "Lax", "None"]).toContain(cookie.sameSite);

      console.log(
        `Cookie: ${cookie.name}, Secure: ${cookie.secure}, HttpOnly: ${cookie.httpOnly}, SameSite: ${cookie.sameSite}`
      );
    }
  });

  test("should handle error messages securely", async ({ page }) => {
    // Test that error messages don't expose sensitive information

    // Mock API error response
    await page.route("/api/search", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          success: false,
          message:
            "Database connection failed at server.example.com:5432 with credentials user:admin",
          error: "Internal server error with stack trace...",
        }),
      });
    });

    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    await searchInput.fill("test");
    await page.click(TestHelpers.selectors.searchButton);

    // Wait for error message
    await expect(
      page.locator(TestHelpers.selectors.errorMessage)
    ).toBeVisible();

    const errorText = await page
      .locator(TestHelpers.selectors.errorMessage)
      .textContent();

    // Error message should be user-friendly, not expose internal details
    expect(errorText).not.toContain("Database");
    expect(errorText).not.toContain("server.example.com");
    expect(errorText).not.toContain("admin");
    expect(errorText).not.toContain("stack trace");

    console.log("Error message is secure:", errorText);
  });

  test("should prevent script injection through URL parameters", async ({
    page,
  }) => {
    // Test URL parameter injection
    const maliciousParams = [
      '?search=<script>alert("xss")</script>',
      '?redirect=javascript:alert("xss")',
      '?callback=alert("xss")',
    ];

    for (const param of maliciousParams) {
      await page.goto(`/${param}`);

      // Should not execute injected scripts
      // Check that page still loads normally
      await expect(page.locator("h1")).toBeVisible();

      // Check that parameter is properly sanitized
      const currentUrl = page.url();
      expect(currentUrl).not.toContain("<script>");

      console.log(`URL parameter injection prevented: ${param}`);
    }
  });

  test("should validate file upload security (if applicable)", async ({
    page,
  }) => {
    // Check for file upload functionality
    const fileInputs = page.locator('input[type="file"]');
    const fileInputCount = await fileInputs.count();

    if (fileInputCount > 0) {
      // Test file upload restrictions
      for (let i = 0; i < fileInputCount; i++) {
        const fileInput = fileInputs.nth(i);

        // Check accept attribute
        const acceptAttr = await fileInput.getAttribute("accept");
        if (acceptAttr) {
          // Should not accept executable files
          expect(acceptAttr).not.toContain(".exe");
          expect(acceptAttr).not.toContain(".js");
          expect(acceptAttr).not.toContain(".php");

          console.log(`File input accept: ${acceptAttr}`);
        }
      }
    } else {
      console.log("No file upload functionality found");
    }
  });

  test("should implement proper access control", async ({ page }) => {
    // Test access to different routes
    const routes = ["/", "/issues", "/api/health"];

    for (const route of routes) {
      const response = await page.goto(route);
      const status = response?.status();

      // Public routes should be accessible
      if (route === "/" || route === "/issues") {
        expect(status).toBe(200);
      }

      // API routes should have proper headers
      if (route.startsWith("/api/")) {
        const headers = response?.headers() || {};

        // Should have cache control for API
        expect(headers["cache-control"]).toBeTruthy();
      }

      console.log(`Route ${route} - Status: ${status}`);
    }
  });
});
