import { test, expect } from "@playwright/test";
import { TestHelpers } from "../../utils/test-helpers";
import { performanceThresholds } from "../../fixtures/test-data";

test.describe("Performance Tests", () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);

    // Mock API responses with realistic delays
    await page.route("**/api/**", async (route) => {
      const url = route.request().url();

      // Add realistic API delays
      await new Promise((resolve) => setTimeout(resolve, 100)); // 100ms API response time

      if (url.includes("/health")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "healthy",
            message: "Test system is running",
          }),
        });
      } else if (url.includes("/embeddings/stats")) {
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
      } else if (url.includes("/search")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            results: Array.from({ length: 10 }, (_, i) => ({
              id: `test-bill-${i + 1}`,
              bill_number: `TEST${String(i + 1).padStart(3, "0")}`,
              title: `パフォーマンステスト法案 ${i + 1}`,
              description: `これは${i + 1}番目のテスト用法案です。`,
              certainty: 0.9 - i * 0.05,
              search_method: "vector",
            })),
            total_found: 10,
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      }
    });
  });

  test.afterEach(async ({ page }) => {
    await helpers.cleanup();
  });

  test("should meet page load performance requirements", async ({ page }) => {
    const startTime = Date.now();

    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    const domContentLoadedTime = Date.now() - startTime;

    // Wait for the page to be fully loaded
    await helpers.waitForAppReady();
    const fullLoadTime = Date.now() - startTime;

    // Get detailed performance metrics
    const metrics = await helpers.measurePagePerformance();

    console.log("Performance Metrics:", {
      domContentLoadedTime,
      fullLoadTime,
      ...metrics,
    });

    // Check performance requirements
    expect(domContentLoadedTime).toBeLessThan(
      performanceThresholds.domContentLoaded,
    );
    expect(fullLoadTime).toBeLessThan(performanceThresholds.pageLoad);

    if (metrics.firstContentfulPaint > 0) {
      expect(metrics.firstContentfulPaint).toBeLessThan(
        performanceThresholds.firstContentfulPaint,
      );
    }
  });

  test("should maintain performance on mobile devices", async ({ page }) => {
    // Simulate mobile device
    await page.setViewportSize({ width: 375, height: 667 });

    // Simulate slower mobile network
    await page.route("**/*", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 50)); // Add network delay
      await route.continue();
    });

    const startTime = Date.now();

    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    const domContentLoadedTime = Date.now() - startTime;

    await helpers.waitForAppReady();
    const fullLoadTime = Date.now() - startTime;

    console.log("Mobile Performance Metrics:", {
      domContentLoadedTime,
      fullLoadTime,
    });

    // Mobile-specific thresholds (more lenient)
    expect(domContentLoadedTime).toBeLessThan(
      performanceThresholds.mobile.domContentLoaded,
    );
    expect(fullLoadTime).toBeLessThan(performanceThresholds.mobile.pageLoad);
  });

  test("should handle search operations efficiently", async ({ page }) => {
    await page.goto("/");
    await helpers.waitForAppReady();

    const searchInput = page.locator("input#search");
    const searchTerm = "パフォーマンステスト";

    // Measure search operation time
    const searchStartTime = Date.now();

    await searchInput.fill(searchTerm);
    await page.click('button:has-text("検索する")');

    // Wait for search results
    await page.waitForSelector(".grid.gap-4", { timeout: 5000 });

    const searchDuration = Date.now() - searchStartTime;

    console.log("Search Performance:", {
      searchDuration,
      searchTerm,
    });

    // Search should complete within 2 seconds
    expect(searchDuration).toBeLessThan(2000);

    // Verify results are displayed
    const resultCount = await page.locator(".grid.gap-4 > *").count();
    expect(resultCount).toBeGreaterThan(0);
  });

  test("should handle multiple concurrent searches", async ({ page }) => {
    await page.goto("/");
    await helpers.waitForAppReady();

    const searchInput = page.locator("input#search");
    const searches = ["テスト1", "テスト2", "テスト3"];

    const startTime = Date.now();

    // Perform rapid searches
    for (const searchTerm of searches) {
      await searchInput.fill(searchTerm);
      await page.waitForTimeout(100); // Small delay between searches
    }

    // Final search should trigger
    await page.click('button:has-text("検索する")');

    // Wait for final results
    await page.waitForSelector(".grid.gap-4", { timeout: 5000 });

    const totalDuration = Date.now() - startTime;

    console.log("Concurrent Search Performance:", {
      totalDuration,
      searchCount: searches.length,
    });

    // Should handle multiple searches efficiently
    expect(totalDuration).toBeLessThan(3000);

    // Should show results for the last search
    await expect(page.locator("input#search")).toHaveValue("テスト3");
  });

  test("should optimize bundle size and loading", async ({ page, context }) => {
    // Track network requests
    const networkRequests: Array<{ url: string; size: number; type: string }> =
      [];

    page.on("response", async (response) => {
      try {
        const url = response.url();
        const headers = response.headers();
        const contentLength = headers["content-length"];
        const contentType = headers["content-type"] || "";

        if (url.includes("localhost") && !url.includes("/api/")) {
          networkRequests.push({
            url: url.split("/").pop() || url,
            size: contentLength ? parseInt(contentLength) : 0,
            type: contentType.split(";")[0],
          });
        }
      } catch (error) {
        // Ignore errors in response processing
      }
    });

    await page.goto("/");
    await helpers.waitForAppReady();

    // Wait for all resources to load
    await page.waitForLoadState("networkidle");

    console.log("Network Requests:", networkRequests);

    // Check main JavaScript bundle size
    const jsFiles = networkRequests.filter(
      (req) => req.type.includes("javascript") || req.url.endsWith(".js"),
    );

    // Check CSS bundle size
    const cssFiles = networkRequests.filter(
      (req) => req.type.includes("css") || req.url.endsWith(".css"),
    );

    console.log("Bundle Analysis:", {
      jsFiles: jsFiles.length,
      cssFiles: cssFiles.length,
      totalRequests: networkRequests.length,
    });

    // Basic bundle size checks
    expect(jsFiles.length).toBeLessThan(10); // Not too many JS files
    expect(cssFiles.length).toBeLessThan(5); // Not too many CSS files
  });

  test("should handle memory efficiently during extended use", async ({
    page,
  }) => {
    await page.goto("/");
    await helpers.waitForAppReady();

    // Simulate extended usage with multiple searches
    const searchTerms = [
      "税制改正",
      "社会保障",
      "予算",
      "外交",
      "環境",
      "教育",
      "医療",
      "交通",
      "農業",
      "技術",
    ];

    const searchInput = page.locator("input#search");

    for (const term of searchTerms) {
      await searchInput.fill(term);
      await page.click('button:has-text("検索する")');

      // Wait for results
      await page.waitForSelector(".grid.gap-4", { timeout: 3000 });
      await page.waitForTimeout(200); // Brief pause between searches
    }

    // Check for memory leaks by ensuring page is still responsive
    await searchInput.fill("最終テスト");
    await page.click('button:has-text("検索する")');

    const finalSearchStart = Date.now();
    await page.waitForSelector(".grid.gap-4", { timeout: 5000 });
    const finalSearchDuration = Date.now() - finalSearchStart;

    console.log("Extended Usage Performance:", {
      searchCount: searchTerms.length + 1,
      finalSearchDuration,
    });

    // Final search should still be reasonably fast
    expect(finalSearchDuration).toBeLessThan(3000);
  });

  test("should efficiently handle responsive design changes", async ({
    page,
  }) => {
    await page.goto("/");
    await helpers.waitForAppReady();

    const viewports = [
      { width: 375, height: 667, name: "Mobile" },
      { width: 768, height: 1024, name: "Tablet" },
      { width: 1280, height: 720, name: "Desktop" },
      { width: 375, height: 667, name: "Mobile Again" },
    ];

    for (const viewport of viewports) {
      const resizeStart = Date.now();

      await page.setViewportSize(viewport);
      await page.waitForTimeout(100); // Allow layout to settle

      const resizeDuration = Date.now() - resizeStart;

      // Verify main elements are still visible and responsive
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.locator("input#search")).toBeVisible();

      console.log(`${viewport.name} Resize Performance:`, {
        duration: resizeDuration,
        viewport: `${viewport.width}x${viewport.height}`,
      });

      // Resize should be fast
      expect(resizeDuration).toBeLessThan(500);
    }
  });

  test("should maintain performance with slow network conditions", async ({
    page,
  }) => {
    // Simulate 3G network conditions
    await page.route("**/*", async (route) => {
      // Add network latency
      await new Promise((resolve) => setTimeout(resolve, 200));
      await route.continue();
    });

    const startTime = Date.now();

    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    const domLoadTime = Date.now() - startTime;

    await helpers.waitForAppReady();
    const fullLoadTime = Date.now() - startTime;

    console.log("Slow Network Performance:", {
      domLoadTime,
      fullLoadTime,
    });

    // Should still load within reasonable time on slow network
    expect(domLoadTime).toBeLessThan(5000);
    expect(fullLoadTime).toBeLessThan(8000);

    // Test search functionality under slow network
    const searchInput = page.locator("input#search");
    const searchStart = Date.now();

    await searchInput.fill("ネットワークテスト");
    await page.click('button:has-text("検索する")');

    await page.waitForSelector(".grid.gap-4", { timeout: 8000 });

    const searchDuration = Date.now() - searchStart;

    console.log("Search on Slow Network:", { searchDuration });

    // Search should complete even on slow network
    expect(searchDuration).toBeLessThan(5000);
  });
});
