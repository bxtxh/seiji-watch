import { test, expect, devices } from "@playwright/test";

test.describe("Kanban Board Performance Tests", () => {
  test("Core Web Vitals - LCP under 2.5s", async ({ page }) => {
    const startTime = Date.now();

    await page.goto("/");

    // Wait for Largest Contentful Paint (LCP) - should be the Kanban board
    await expect(
      page.locator('[aria-label="国会イシュー Kanban ボード"]')
    ).toBeVisible();
    await page.waitForLoadState("networkidle");

    const lcpTime = Date.now() - startTime;

    // LCP should be under 2.5 seconds (2500ms) for good performance
    expect(lcpTime).toBeLessThan(2500);

    console.log(`LCP Time: ${lcpTime}ms`);
  });

  test("First Input Delay (FID) simulation", async ({ page }) => {
    await page.goto("/");

    // Wait for page to load
    await page.waitForLoadState("networkidle");

    const startTime = Date.now();

    // Simulate user input - click on first issue card
    const firstCard = page.locator("article").first();
    await expect(firstCard).toBeVisible();
    await firstCard.click();

    const fidTime = Date.now() - startTime;

    // FID should be under 100ms for good performance
    expect(fidTime).toBeLessThan(100);

    console.log(`FID Time: ${fidTime}ms`);
  });

  test("Cumulative Layout Shift (CLS) - no layout shifts during load", async ({
    page,
  }) => {
    await page.goto("/");

    // Get initial viewport measurements
    const initialMetrics = await page.evaluate(() => {
      const kanban = document.querySelector(
        '[aria-label="国会イシュー Kanban ボード"]'
      );
      if (!kanban) return null;

      const rect = kanban.getBoundingClientRect();
      return {
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      };
    });

    // Wait for data to load
    await page.waitForTimeout(2000);

    // Get final measurements
    const finalMetrics = await page.evaluate(() => {
      const kanban = document.querySelector(
        '[aria-label="国会イシュー Kanban ボード"]'
      );
      if (!kanban) return null;

      const rect = kanban.getBoundingClientRect();
      return {
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      };
    });

    // Check for minimal layout shift
    if (initialMetrics && finalMetrics) {
      const topShift = Math.abs(finalMetrics.top - initialMetrics.top);
      const leftShift = Math.abs(finalMetrics.left - initialMetrics.left);

      // Layout shift should be minimal (< 10px)
      expect(topShift).toBeLessThan(10);
      expect(leftShift).toBeLessThan(10);

      console.log(`Layout shift - Top: ${topShift}px, Left: ${leftShift}px`);
    }
  });

  test("Memory usage during scroll interactions", async ({ page }) => {
    await page.goto("/");

    // Wait for initial load
    await page.waitForLoadState("networkidle");

    // Get initial memory usage
    const initialMemory = await page.evaluate(() => {
      if ("memory" in performance) {
        return performance.memory.usedJSHeapSize;
      }
      return null;
    });

    // Perform scroll interactions
    const scrollContainer = page.locator(
      '[role="list"][aria-label="ステージ別イシュー一覧"]'
    );
    await expect(scrollContainer).toBeVisible();

    // Scroll left and right multiple times
    for (let i = 0; i < 10; i++) {
      await scrollContainer.evaluate((el) => (el.scrollLeft += 200));
      await page.waitForTimeout(100);
      await scrollContainer.evaluate((el) => (el.scrollLeft -= 200));
      await page.waitForTimeout(100);
    }

    // Get final memory usage
    const finalMemory = await page.evaluate(() => {
      if ("memory" in performance) {
        return performance.memory.usedJSHeapSize;
      }
      return null;
    });

    if (initialMemory && finalMemory) {
      const memoryIncrease = finalMemory - initialMemory;
      const memoryIncreasePercent = (memoryIncrease / initialMemory) * 100;

      // Memory increase should be reasonable (< 50% increase)
      expect(memoryIncreasePercent).toBeLessThan(50);

      console.log(
        `Memory increase: ${memoryIncrease} bytes (${memoryIncreasePercent.toFixed(2)}%)`
      );
    }
  });

  test("Mobile performance - iPhone 12", async ({ browser }) => {
    const context = await browser.newContext({
      ...devices["iPhone 12"],
    });
    const page = await context.newPage();

    const startTime = Date.now();

    await page.goto("/");

    // Wait for Kanban board to be visible
    await expect(
      page.locator('[aria-label="国会イシュー Kanban ボード"]')
    ).toBeVisible();
    await page.waitForLoadState("networkidle");

    const loadTime = Date.now() - startTime;

    // Mobile load time should be under 3 seconds
    expect(loadTime).toBeLessThan(3000);

    // Check horizontal scroll works on mobile
    const scrollContainer = page.locator(
      '[role="list"][aria-label="ステージ別イシュー一覧"]'
    );

    // Perform touch scroll
    await scrollContainer.evaluate((el) => {
      el.scrollLeft = 200;
    });

    await page.waitForTimeout(500);

    const scrollLeft = await scrollContainer.evaluate((el) => el.scrollLeft);
    expect(scrollLeft).toBeGreaterThan(0);

    console.log(`Mobile load time: ${loadTime}ms`);

    await context.close();
  });

  test("API response caching effectiveness", async ({ page }) => {
    // Monitor network requests
    const apiRequests = [];
    page.on("request", (request) => {
      if (request.url().includes("/api/issues/kanban")) {
        apiRequests.push({
          url: request.url(),
          method: request.method(),
          timestamp: Date.now(),
        });
      }
    });

    // First page load
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const firstLoadRequestCount = apiRequests.length;
    expect(firstLoadRequestCount).toBeGreaterThan(0);

    // Navigate away and back
    await page.goto("/about");
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Should use cached data or minimal additional requests
    const totalRequests = apiRequests.length;
    const additionalRequests = totalRequests - firstLoadRequestCount;

    // Should not make excessive additional requests
    expect(additionalRequests).toBeLessThanOrEqual(1);

    console.log(
      `API requests - First load: ${firstLoadRequestCount}, Additional: ${additionalRequests}`
    );
  });

  test("Scroll performance - 60fps target", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    const scrollContainer = page.locator(
      '[role="list"][aria-label="ステージ別イシュー一覧"]'
    );
    await expect(scrollContainer).toBeVisible();

    // Start performance monitoring
    const performanceData = await page.evaluate(() => {
      const frames = [];
      let lastTime = performance.now();

      function measureFrame() {
        const currentTime = performance.now();
        const frameDuration = currentTime - lastTime;
        frames.push(frameDuration);
        lastTime = currentTime;

        if (frames.length < 60) {
          // Monitor for 60 frames
          requestAnimationFrame(measureFrame);
        }
      }

      requestAnimationFrame(measureFrame);

      return new Promise((resolve) => {
        setTimeout(() => {
          const avgFrameTime =
            frames.reduce((a, b) => a + b, 0) / frames.length;
          const fps = 1000 / avgFrameTime;
          resolve({ avgFrameTime, fps, frames: frames.length });
        }, 1000);
      });
    });

    // Perform scroll while monitoring
    for (let i = 0; i < 10; i++) {
      await scrollContainer.evaluate((el) => (el.scrollLeft += 50));
      await page.waitForTimeout(16); // ~60fps
    }

    const result = await performanceData;

    // Target 60fps (16.67ms per frame)
    expect(result.fps).toBeGreaterThan(45); // Allow some tolerance

    console.log(
      `Average FPS: ${result.fps.toFixed(2)}, Frame time: ${result.avgFrameTime.toFixed(2)}ms`
    );
  });

  test("Resource loading optimization", async ({ page }) => {
    const resourceSizes = [];

    page.on("response", (response) => {
      const contentLength = response.headers()["content-length"];
      if (contentLength && response.url().includes("localhost")) {
        resourceSizes.push({
          url: response.url(),
          size: parseInt(contentLength),
          contentType: response.headers()["content-type"],
        });
      }
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Check JavaScript bundle sizes
    const jsResources = resourceSizes.filter(
      (r) => r.contentType?.includes("javascript") || r.url.includes(".js")
    );

    const totalJSSize = jsResources.reduce((sum, r) => sum + r.size, 0);

    // JavaScript bundle should be reasonably sized (< 1MB)
    expect(totalJSSize).toBeLessThan(1024 * 1024);

    // Check CSS sizes
    const cssResources = resourceSizes.filter(
      (r) => r.contentType?.includes("css") || r.url.includes(".css")
    );

    const totalCSSSize = cssResources.reduce((sum, r) => sum + r.size, 0);

    // CSS should be optimized (< 500KB)
    expect(totalCSSSize).toBeLessThan(500 * 1024);

    console.log(`Total JS size: ${(totalJSSize / 1024).toFixed(2)}KB`);
    console.log(`Total CSS size: ${(totalCSSSize / 1024).toFixed(2)}KB`);
  });
});
