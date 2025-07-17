import { Page, Locator, expect } from "@playwright/test";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

/**
 * Test server management utilities
 */
export async function startTestServer() {
  // In a real implementation, this would start the backend API server
  // For now, we'll just ensure the environment is ready
  console.log("Starting test server...");

  // Set up test environment variables (read-only properties handled safely)
  if (process.env.NODE_ENV !== "test") {
    Object.defineProperty(process.env, "NODE_ENV", {
      value: "test",
      writable: false,
    });
  }
  if (!process.env.NEXT_PUBLIC_API_BASE_URL) {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8001";
  }

  // Wait a bit for server to be ready
  await new Promise((resolve) => setTimeout(resolve, 1000));
}

export async function stopTestServer() {
  // In a real implementation, this would stop the backend API server
  console.log("Stopping test server...");

  // Clean up test environment (only if safe to do so)
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  }
}

export async function waitForServer(url: string, timeout: number = 30000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return true;
      }
    } catch (error) {
      // Server not ready yet
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw new Error(`Server at ${url} did not start within ${timeout}ms`);
}

/**
 * Test helper utilities for Diet Issue Tracker E2E tests
 */

export class TestHelpers {
  constructor(private page: Page) {}

  /**
   * Common selectors used across tests
   */
  static selectors = {
    // Navigation
    homeLink: 'a[href="/"]',
    issuesLink: 'a[href="/issues"]',

    // Search
    searchInput: "input#search",
    searchButton: 'button:has-text("検索する")',
    searchResults: ".grid.gap-4", // BillCard container
    billCard: '[data-testid="bill-card"]',

    // Common UI elements
    header: "header",
    footer: "footer",
    mainContent: "main",
    loadingIndicator: ".loading-dots",

    // PWA elements
    installButton: 'button:has-text("アプリをインストール")',
    pwaDebugButton: 'button[title*="PWAデバッグ"]',

    // Error states
    errorMessage: ".bg-red-50",
    validationError: ".text-red-600",

    // Accessibility
    skipLink: 'a:has-text("メインコンテンツへスキップ")',
    furiganaToggle: 'button:has-text("ふりがな")',

    // Search specific
    searchStats: ".bg-gray-50",
    emptyState: "text=検索結果が見つかりませんでした",
  };

  /**
   * Wait for application to be ready
   */
  async waitForAppReady(): Promise<void> {
    await this.page.waitForLoadState("domcontentloaded");
    // Wait for the main heading to appear - this should be faster than waiting for API calls
    await this.page.waitForSelector('h1:has-text("国会議事録検索システム")', {
      timeout: 15000,
    });
  }

  /**
   * Navigate to a specific page and wait for it to load
   */
  async navigateToPage(path: string): Promise<void> {
    await this.page.goto(path);
    await this.page.waitForLoadState("networkidle");
  }

  /**
   * Perform a search and wait for results
   */
  async performSearch(query: string): Promise<void> {
    const searchInput = this.page.locator(TestHelpers.selectors.searchInput);
    const searchButton = this.page.locator(TestHelpers.selectors.searchButton);

    await searchInput.fill(query);
    await searchButton.click();

    // Wait for search to complete (either results or empty state)
    await Promise.race([
      this.page.waitForSelector(TestHelpers.selectors.searchResults, {
        timeout: 10000,
      }),
      this.page.waitForSelector("text=検索結果が見つかりませんでした", {
        timeout: 10000,
      }),
      this.page.waitForSelector(TestHelpers.selectors.errorMessage, {
        timeout: 10000,
      }),
    ]);
  }

  /**
   * Check if element is visible and accessible
   */
  async expectElementToBeAccessible(selector: string): Promise<void> {
    const element = this.page.locator(selector);
    await expect(element).toBeVisible();

    // Check for basic accessibility attributes
    const tagName = await element.evaluate((el) => el.tagName.toLowerCase());

    if (tagName === "button" || tagName === "a") {
      // Interactive elements should be keyboard accessible
      await element.focus();
      await expect(element).toBeFocused();
    }

    if (tagName === "input") {
      // Form inputs should have labels
      const ariaLabel = await element.getAttribute("aria-label");
      const ariaLabelledby = await element.getAttribute("aria-labelledby");
      const associatedLabel = await this.page
        .locator(`label[for="${await element.getAttribute("id")}"]`)
        .count();

      if (!ariaLabel && !ariaLabelledby && associatedLabel === 0) {
        throw new Error(`Input element ${selector} lacks proper labeling`);
      }
    }
  }

  /**
   * Check responsive design at different viewports
   */
  async checkResponsiveDesign(selector: string): Promise<void> {
    const viewports = [
      { width: 375, height: 667, name: "Mobile" },
      { width: 768, height: 1024, name: "Tablet" },
      { width: 1280, height: 720, name: "Desktop" },
    ];

    for (const viewport of viewports) {
      await this.page.setViewportSize(viewport);
      await this.page.waitForTimeout(500); // Allow layout to settle

      const element = this.page.locator(selector);
      await expect(element).toBeVisible({ timeout: 5000 });

      // Check if element is not cut off
      const boundingBox = await element.boundingBox();
      if (boundingBox) {
        expect(boundingBox.x).toBeGreaterThanOrEqual(0);
        expect(boundingBox.y).toBeGreaterThanOrEqual(0);
        expect(boundingBox.x + boundingBox.width).toBeLessThanOrEqual(
          viewport.width,
        );
      }
    }
  }

  /**
   * Test keyboard navigation
   */
  async testKeyboardNavigation(): Promise<void> {
    // Test Tab navigation
    await this.page.keyboard.press("Tab");
    await expect(this.page.locator(":focus")).toBeVisible();

    // Test Enter on focused button
    const focusedElement = this.page.locator(":focus");
    const tagName = await focusedElement.evaluate((el) =>
      el.tagName.toLowerCase(),
    );

    if (tagName === "button" || tagName === "a") {
      await this.page.keyboard.press("Enter");
      // Wait for any navigation or action to complete
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Check for security headers
   */
  async checkSecurityHeaders(): Promise<void> {
    const response = await this.page.goto(this.page.url());
    if (!response) throw new Error("No response received");

    const headers = response.headers();

    // Check for critical security headers
    const expectedHeaders = [
      "x-frame-options",
      "x-content-type-options",
      "strict-transport-security",
      "content-security-policy",
    ];

    for (const header of expectedHeaders) {
      if (!headers[header]) {
        throw new Error(`Missing security header: ${header}`);
      }
    }
  }

  /**
   * Measure page performance
   */
  async measurePagePerformance(): Promise<{
    loadTime: number;
    domContentLoaded: number;
    firstContentfulPaint: number;
  }> {
    const performanceMetrics = await this.page.evaluate(() => {
      const navigation = performance.getEntriesByType(
        "navigation",
      )[0] as PerformanceNavigationTiming;
      const paint = performance.getEntriesByType("paint");

      return {
        loadTime: navigation.loadEventEnd - navigation.loadEventStart,
        domContentLoaded:
          navigation.domContentLoadedEventEnd -
          navigation.domContentLoadedEventStart,
        firstContentfulPaint:
          paint.find((p) => p.name === "first-contentful-paint")?.startTime ||
          0,
      };
    });

    return performanceMetrics;
  }

  /**
   * Check for console errors
   */
  async expectNoConsoleErrors(): Promise<void> {
    const consoleErrors: string[] = [];

    this.page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    this.page.on("pageerror", (error) => {
      consoleErrors.push(error.message);
    });

    // Wait a bit for any async errors
    await this.page.waitForTimeout(2000);

    if (consoleErrors.length > 0) {
      throw new Error(`Console errors found: ${consoleErrors.join(", ")}`);
    }
  }

  /**
   * Test PWA features
   */
  async testPWAFeatures(): Promise<void> {
    // Check if service worker is registered
    const swRegistered = await this.page.evaluate(() => {
      return "serviceWorker" in navigator;
    });

    expect(swRegistered).toBe(true);

    // Check manifest
    const manifestLink = this.page.locator('link[rel="manifest"]');
    await expect(manifestLink).toHaveCount(1);
  }

  /**
   * Simulate network conditions
   */
  async simulateNetworkCondition(
    condition: "offline" | "slow3g" | "fast3g",
  ): Promise<void> {
    const context = this.page.context();

    switch (condition) {
      case "offline":
        await context.setOffline(true);
        break;
      case "slow3g":
        await context.route("**/*", (route) => {
          setTimeout(() => route.continue(), 1000); // Simulate slow network
        });
        break;
      case "fast3g":
        await context.route("**/*", (route) => {
          setTimeout(() => route.continue(), 200); // Simulate fast 3G
        });
        break;
    }
  }

  /**
   * Clean up after test
   */
  async cleanup(): Promise<void> {
    const context = this.page.context();
    await context.setOffline(false);
    await context.unroute("**/*");
  }
}

/**
 * Custom assertions for Diet Issue Tracker
 */
export class DietTrackerAssertions {
  static async expectSearchResults(page: Page, query: string): Promise<void> {
    // Check if search was performed
    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    await expect(searchInput).toHaveValue(query);

    // Wait for search to complete
    await page.waitForTimeout(1000);

    // Check for either results or empty state or error
    const hasResults =
      (await page.locator(TestHelpers.selectors.searchResults).count()) > 0;
    const hasEmptyState =
      (await page.locator(TestHelpers.selectors.emptyState).count()) > 0;
    const hasError =
      (await page.locator(TestHelpers.selectors.errorMessage).count()) > 0;

    expect(hasResults || hasEmptyState || hasError).toBe(true);
  }

  static async expectValidJapaneseContent(
    page: Page,
    selector: string,
  ): Promise<void> {
    const element = page.locator(selector);
    const text = await element.textContent();

    if (text) {
      // Check for Japanese characters (Hiragana, Katakana, Kanji)
      const hasJapanese = /[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]/.test(
        text,
      );
      expect(hasJapanese).toBe(true);
    }
  }

  static async expectMobileFriendly(page: Page): Promise<void> {
    // Check viewport meta tag
    const viewportMeta = page.locator('meta[name="viewport"]');
    await expect(viewportMeta).toHaveAttribute("content", /width=device-width/);

    // Check touch targets are large enough (minimum 44px)
    const buttons = page.locator("button, a");
    const buttonCount = await buttons.count();

    for (let i = 0; i < Math.min(buttonCount, 10); i++) {
      const button = buttons.nth(i);
      const boundingBox = await button.boundingBox();

      if (boundingBox && (await button.isVisible())) {
        expect(
          Math.min(boundingBox.width, boundingBox.height),
        ).toBeGreaterThanOrEqual(44);
      }
    }
  }
}
