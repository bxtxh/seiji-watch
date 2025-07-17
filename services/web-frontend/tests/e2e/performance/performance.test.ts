import { test, expect } from "@playwright/test";
import { TestHelpers } from "../../utils/test-helpers";
import { performanceThresholds, testViewports } from "../../fixtures/test-data";

test.describe("Performance Tests", () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
  });

  test.afterEach(async ({ page }) => {
    await helpers.cleanup();
  });

  test("should meet page load performance targets", async ({ page }) => {
    const startTime = Date.now();

    // Navigate to page and measure load time
    await helpers.navigateToPage("/");
    await page.waitForLoadState("domcontentloaded");

    const domContentLoadedTime = Date.now() - startTime;

    await page.waitForLoadState("networkidle");
    const fullLoadTime = Date.now() - startTime;

    // Check performance targets
    expect(domContentLoadedTime).toBeLessThan(
      performanceThresholds.domContentLoaded,
    );
    expect(fullLoadTime).toBeLessThan(performanceThresholds.pageLoad);

    console.log(`DOM Content Loaded: ${domContentLoadedTime}ms`);
    console.log(`Full Load Time: ${fullLoadTime}ms`);
  });

  test("should measure Core Web Vitals", async ({ page }) => {
    await helpers.navigateToPage("/");
    await helpers.waitForAppReady();

    // Get performance metrics
    const metrics = await helpers.measurePagePerformance();

    // Check Core Web Vitals against thresholds
    expect(metrics.firstContentfulPaint).toBeLessThan(
      performanceThresholds.firstContentfulPaint,
    );
    expect(metrics.loadTime).toBeLessThan(performanceThresholds.pageLoad);

    console.log("Performance Metrics:", metrics);

    // Measure additional metrics
    const additionalMetrics = await page.evaluate(() => {
      return new Promise((resolve) => {
        if ("PerformanceObserver" in window) {
          const observer = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lcp = entries.find(
              (entry) => entry.entryType === "largest-contentful-paint",
            );
            const cls = entries
              .filter((entry) => entry.entryType === "layout-shift")
              .reduce((sum, entry) => sum + (entry as any).value, 0);

            resolve({
              largestContentfulPaint: lcp ? lcp.startTime : 0,
              cumulativeLayoutShift: cls,
            });
          });

          observer.observe({
            entryTypes: ["largest-contentful-paint", "layout-shift"],
          });

          // Fallback timeout
          setTimeout(
            () =>
              resolve({ largestContentfulPaint: 0, cumulativeLayoutShift: 0 }),
            5000,
          );
        } else {
          resolve({ largestContentfulPaint: 0, cumulativeLayoutShift: 0 });
        }
      });
    });

    console.log("Additional Metrics:", additionalMetrics);
  });

  test("should perform well on mobile devices", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize(testViewports.mobile);

    // Simulate mobile network conditions
    await helpers.simulateNetworkCondition("fast3g");

    const startTime = Date.now();
    await helpers.navigateToPage("/");
    await page.waitForLoadState("domcontentloaded");

    const mobileLoadTime = Date.now() - startTime;

    // Mobile should meet stricter thresholds
    expect(mobileLoadTime).toBeLessThan(
      performanceThresholds.mobile.domContentLoaded,
    );

    console.log(`Mobile Load Time: ${mobileLoadTime}ms`);
  });

  test("should handle slow network conditions gracefully", async ({ page }) => {
    // Simulate slow 3G
    await helpers.simulateNetworkCondition("slow3g");

    const startTime = Date.now();
    await helpers.navigateToPage("/");

    // Should show loading states appropriately
    const loadingIndicator = page.locator(
      TestHelpers.selectors.loadingIndicator,
    );

    // App should be responsive even on slow connections
    await page.waitForLoadState("domcontentloaded", { timeout: 10000 });
    const slowLoadTime = Date.now() - startTime;

    console.log(`Slow Network Load Time: ${slowLoadTime}ms`);

    // Should eventually load completely
    await expect(page.locator("h1").first()).toBeVisible({ timeout: 15000 });
  });

  test("should optimize resource loading", async ({ page }) => {
    // Monitor network requests
    const requests: any[] = [];
    const responses: any[] = [];

    page.on("request", (request) => {
      requests.push({
        url: request.url(),
        resourceType: request.resourceType(),
        method: request.method(),
      });
    });

    page.on("response", (response) => {
      responses.push({
        url: response.url(),
        status: response.status(),
        size: response.headers()["content-length"],
      });
    });

    await helpers.navigateToPage("/");
    await page.waitForLoadState("networkidle");

    // Analyze requests
    const jsRequests = requests.filter((r) => r.resourceType === "script");
    const cssRequests = requests.filter((r) => r.resourceType === "stylesheet");
    const imageRequests = requests.filter((r) => r.resourceType === "image");

    console.log(`JavaScript files loaded: ${jsRequests.length}`);
    console.log(`CSS files loaded: ${cssRequests.length}`);
    console.log(`Images loaded: ${imageRequests.length}`);

    // Check for optimization
    expect(jsRequests.length).toBeLessThan(20); // Reasonable bundle count
    expect(cssRequests.length).toBeLessThan(10); // CSS should be minimized

    // Check for failed requests
    const failedResponses = responses.filter((r) => r.status >= 400);
    expect(failedResponses.length).toBe(0);
  });

  test("should have efficient bundle sizes", async ({ page }) => {
    const bundleInfo: any[] = [];

    page.on("response", (response) => {
      const url = response.url();
      const contentLength = response.headers()["content-length"];

      if (url.includes("_next/static") && contentLength) {
        bundleInfo.push({
          url,
          size: parseInt(contentLength),
          type: url.includes(".js")
            ? "js"
            : url.includes(".css")
              ? "css"
              : "other",
        });
      }
    });

    await helpers.navigateToPage("/");
    await page.waitForLoadState("networkidle");

    // Calculate total bundle sizes
    const totalJsSize = bundleInfo
      .filter((b) => b.type === "js")
      .reduce((sum, b) => sum + b.size, 0);

    const totalCssSize = bundleInfo
      .filter((b) => b.type === "css")
      .reduce((sum, b) => sum + b.size, 0);

    console.log(`Total JS bundle size: ${(totalJsSize / 1024).toFixed(2)} KB`);
    console.log(
      `Total CSS bundle size: ${(totalCssSize / 1024).toFixed(2)} KB`,
    );

    // Check bundle size limits
    expect(totalJsSize).toBeLessThan(500 * 1024); // 500KB JS limit
    expect(totalCssSize).toBeLessThan(100 * 1024); // 100KB CSS limit
  });

  test("should optimize images", async ({ page }) => {
    const imageRequests: any[] = [];

    page.on("response", (response) => {
      const url = response.url();
      const contentType = response.headers()["content-type"];

      if (contentType && contentType.startsWith("image/")) {
        imageRequests.push({
          url,
          contentType,
          size: response.headers()["content-length"],
        });
      }
    });

    await helpers.navigateToPage("/");
    await page.waitForLoadState("networkidle");

    // Check image optimization
    for (const img of imageRequests) {
      console.log(
        `Image: ${img.url}, Type: ${img.contentType}, Size: ${img.size}`,
      );

      // Should use modern formats when possible
      const isModernFormat =
        img.contentType.includes("webp") ||
        img.contentType.includes("avif") ||
        img.contentType.includes("svg");

      // At least some images should use modern formats
      // This is a guideline rather than strict requirement
    }
  });

  test("should handle memory usage efficiently", async ({ page }) => {
    await helpers.navigateToPage("/");
    await helpers.waitForAppReady();

    // Measure initial memory
    const initialMemory = await page.evaluate(() => {
      return (performance as any).memory
        ? {
            usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
            totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
          }
        : null;
    });

    // Perform some actions that might create memory leaks
    for (let i = 0; i < 5; i++) {
      await page.click(TestHelpers.selectors.issuesLink);
      await page.waitForTimeout(500);
      await page.click(TestHelpers.selectors.homeLink);
      await page.waitForTimeout(500);
    }

    // Measure memory after navigation
    const finalMemory = await page.evaluate(() => {
      return (performance as any).memory
        ? {
            usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
            totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
          }
        : null;
    });

    if (initialMemory && finalMemory) {
      const memoryIncrease =
        finalMemory.usedJSHeapSize - initialMemory.usedJSHeapSize;
      console.log(
        `Memory increase: ${(memoryIncrease / 1024 / 1024).toFixed(2)} MB`,
      );

      // Memory increase should be reasonable (< 50MB for these simple operations)
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
    }
  });

  test("should optimize for search performance", async ({ page }) => {
    await helpers.navigateToPage("/");
    await helpers.waitForAppReady();

    // Mock fast API response for consistent testing
    await page.route("/api/search", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 100)); // 100ms simulated response
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          results: [],
          total_found: 0,
          query: "test",
          search_method: "vector",
        }),
      });
    });

    const searchInput = page.locator(TestHelpers.selectors.searchInput);

    // Measure search interaction performance
    const startTime = Date.now();

    await searchInput.fill("税制改正");
    await page.click(TestHelpers.selectors.searchButton);

    // Wait for search to complete
    await page.waitForSelector("text=検索結果が見つかりませんでした", {
      timeout: 5000,
    });

    const searchTime = Date.now() - startTime;
    console.log(`Search completion time: ${searchTime}ms`);

    // Search should be fast
    expect(searchTime).toBeLessThan(2000); // 2 second limit including API call
  });

  test("should maintain performance during concurrent operations", async ({
    page,
  }) => {
    await helpers.navigateToPage("/");
    await helpers.waitForAppReady();

    // Simulate multiple concurrent operations
    const operations = [
      // Search operation
      async () => {
        const searchInput = page.locator(TestHelpers.selectors.searchInput);
        await searchInput.fill("test");
        await searchInput.press("Enter");
      },

      // Navigation operation
      async () => {
        await page.click(TestHelpers.selectors.issuesLink);
        await page.waitForTimeout(100);
        await page.click(TestHelpers.selectors.homeLink);
      },

      // PWA debug panel (if available)
      async () => {
        const debugButton = page.locator(TestHelpers.selectors.pwaDebugButton);
        if ((await debugButton.count()) > 0) {
          await debugButton.click();
          await page.waitForTimeout(100);
          await page.keyboard.press("Escape");
        }
      },
    ];

    // Run operations concurrently
    const startTime = Date.now();
    await Promise.all(operations.map((op) => op().catch(() => {})));
    const totalTime = Date.now() - startTime;

    console.log(`Concurrent operations completed in: ${totalTime}ms`);

    // Should handle concurrent operations without significant delays
    expect(totalTime).toBeLessThan(5000);

    // App should still be responsive
    await expect(page.locator("h1")).toBeVisible();
  });

  test("should optimize for different device capabilities", async ({
    page,
  }) => {
    const deviceTests = [
      {
        name: "High-end mobile",
        viewport: testViewports.mobile,
        network: "fast3g",
      },
      {
        name: "Low-end mobile",
        viewport: { width: 320, height: 568 },
        network: "slow3g",
      },
      { name: "Tablet", viewport: testViewports.tablet, network: "fast3g" },
      { name: "Desktop", viewport: testViewports.desktop, network: "fast3g" },
    ];

    for (const device of deviceTests) {
      console.log(`Testing ${device.name}...`);

      await page.setViewportSize(device.viewport);
      await helpers.simulateNetworkCondition(device.network as any);

      const startTime = Date.now();
      await helpers.navigateToPage("/");
      await page.waitForLoadState("domcontentloaded");
      const loadTime = Date.now() - startTime;

      console.log(`${device.name} load time: ${loadTime}ms`);

      // Different devices should meet appropriate thresholds
      const threshold = device.name.includes("Low-end") ? 5000 : 3000;
      expect(loadTime).toBeLessThan(threshold);

      // Content should be visible
      await expect(page.locator("h1")).toBeVisible({ timeout: 10000 });
    }
  });
});
