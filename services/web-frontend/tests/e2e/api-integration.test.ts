import { test, expect } from "@playwright/test";
import { TestHelpers } from "../utils/test-helpers";

test.describe("API Integration Tests", () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
  });

  test.afterEach(async ({ page }) => {
    await helpers.cleanup();
  });

  test("should handle API health check", async ({ page }) => {
    let healthCheckCalled = false;

    // Mock API health check
    await page.route("**/api/health", async (route) => {
      healthCheckCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "healthy",
          message: "API is running normally",
        }),
      });
    });

    // Mock other API endpoints
    await page.route("**/api/**", async (route) => {
      if (!route.request().url().includes("/health")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "ok",
            bills: 150,
            speeches: 1200,
            message: "Test data available",
          }),
        });
      }
    });

    await page.goto("/");
    await helpers.waitForAppReady();

    // Verify health check was called
    expect(healthCheckCalled).toBe(true);

    // Check system status indicator
    await expect(page.locator(".bg-green-50")).toBeVisible();
    await expect(
      page.locator("text=システムは正常に動作しています"),
    ).toBeVisible();
  });

  test("should handle API errors gracefully", async ({ page }) => {
    // Mock API error responses
    await page.route("**/api/health", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          status: "error",
          message: "Service unavailable",
        }),
      });
    });

    await page.route("**/api/**", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          success: false,
          message: "Service temporarily unavailable",
        }),
      });
    });

    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    // Should show error state
    await expect(page.locator(".bg-yellow-50")).toBeVisible();
    await expect(
      page.locator("text=システムへの接続に失敗しました"),
    ).toBeVisible();
  });

  test("should validate API request/response format", async ({ page }) => {
    let searchRequestBody: any = null;

    // Mock search API to capture request
    await page.route("**/api/search", async (route) => {
      const method = route.request().method();
      expect(method).toBe("POST");

      searchRequestBody = route.request().postDataJSON();

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          results: [
            {
              id: "test-bill-1",
              bill_number: "TEST001",
              title: "検索結果テスト",
              description: "テスト用の法案です",
              certainty: 0.9,
              search_method: "vector",
            },
          ],
          total_found: 1,
        }),
      });
    });

    // Mock other endpoints
    await page.route("**/api/**", async (route) => {
      if (!route.request().url().includes("/search")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      }
    });

    await page.goto("/");
    await helpers.waitForAppReady();

    // Perform search
    const searchInput = page.locator("input#search");
    await searchInput.fill("テスト検索");
    await page.click('button:has-text("検索する")');

    // Wait for API call
    await page.waitForTimeout(1000);

    // Validate request format
    expect(searchRequestBody).toBeTruthy();
    expect(searchRequestBody.query).toBe("テスト検索");
    expect(searchRequestBody.limit).toBeGreaterThan(0);
    expect(searchRequestBody.min_certainty).toBeGreaterThanOrEqual(0);
    expect(searchRequestBody.min_certainty).toBeLessThanOrEqual(1);

    // Validate response display
    await expect(page.locator("text=検索結果テスト")).toBeVisible();
    await expect(page.locator("text=1件の結果が見つかりました")).toBeVisible();
  });

  test("should handle rate limiting", async ({ page }) => {
    let requestCount = 0;

    // Mock rate limiting after 3 requests
    await page.route("**/api/search", async (route) => {
      requestCount++;

      if (requestCount > 3) {
        await route.fulfill({
          status: 429,
          contentType: "application/json",
          body: JSON.stringify({
            success: false,
            message:
              "API呼び出し回数の上限に達しました。しばらくお待ちください。",
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            results: [],
            total_found: 0,
          }),
        });
      }
    });

    // Mock other endpoints
    await page.route("**/api/**", async (route) => {
      if (!route.request().url().includes("/search")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      }
    });

    await page.goto("/");
    await helpers.waitForAppReady();

    const searchInput = page.locator("input#search");
    const searchButton = page.locator('button:has-text("検索する")');

    // Perform multiple searches to trigger rate limiting
    for (let i = 1; i <= 5; i++) {
      await searchInput.fill(`テスト${i}`);
      await searchButton.click();
      await page.waitForTimeout(200);
    }

    // Should show rate limit error
    await expect(page.locator("text=上限に達しました")).toBeVisible({
      timeout: 5000,
    });
  });

  test("should sanitize API responses", async ({ page }) => {
    // Mock API with potentially malicious content
    await page.route("**/api/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          results: [
            {
              id: "test-bill-1",
              bill_number: "TEST001",
              title: '<script>alert("xss")</script>危険なタイトル',
              description: '<img src="x" onerror="alert(\'xss\')">危険な説明',
              certainty: 0.9,
              search_method: "vector",
            },
          ],
          total_found: 1,
        }),
      });
    });

    // Mock other endpoints
    await page.route("**/api/**", async (route) => {
      if (!route.request().url().includes("/search")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      }
    });

    await page.goto("/");
    await helpers.waitForAppReady();

    // Perform search
    const searchInput = page.locator("input#search");
    await searchInput.fill("テスト");
    await page.click('button:has-text("検索する")');

    await page.waitForTimeout(1000);

    // Check that script tags are not executed
    const alerts = [];
    page.on("dialog", (dialog) => {
      alerts.push(dialog.message());
      dialog.dismiss();
    });

    await page.waitForTimeout(1000);
    expect(alerts.length).toBe(0);

    // Content should be displayed but sanitized
    await expect(page.locator("text=危険なタイトル")).toBeVisible();
    await expect(page.locator("text=危険な説明")).toBeVisible();
  });

  test("should timeout on slow API responses", async ({ page }) => {
    // Mock slow API response
    await page.route("**/api/search", async (route) => {
      // Simulate slow response (longer than typical timeout)
      await new Promise((resolve) => setTimeout(resolve, 5000));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          results: [],
          total_found: 0,
        }),
      });
    });

    // Mock other endpoints normally
    await page.route("**/api/**", async (route) => {
      if (!route.request().url().includes("/search")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      }
    });

    await page.goto("/");
    await helpers.waitForAppReady();

    // Perform search
    const searchInput = page.locator("input#search");
    await searchInput.fill("テスト");
    await page.click('button:has-text("検索する")');

    // Should show loading state initially
    await expect(page.locator(".loading-dots")).toBeVisible();

    // Should eventually show error or timeout message
    await expect(page.locator(".bg-red-50")).toBeVisible({ timeout: 10000 });
  });

  test("should handle malformed JSON responses", async ({ page }) => {
    // Mock malformed JSON response
    await page.route("**/api/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "invalid json{{",
      });
    });

    // Mock other endpoints normally
    await page.route("**/api/**", async (route) => {
      if (!route.request().url().includes("/search")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      }
    });

    await page.goto("/");
    await helpers.waitForAppReady();

    // Perform search
    const searchInput = page.locator("input#search");
    await searchInput.fill("テスト");
    await page.click('button:has-text("検索する")');

    await page.waitForTimeout(1000);

    // Should handle JSON parsing error gracefully
    await expect(page.locator(".bg-red-50")).toBeVisible();
  });
});
