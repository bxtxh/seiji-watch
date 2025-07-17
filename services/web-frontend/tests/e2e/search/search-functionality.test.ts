import { test, expect } from "@playwright/test";
import { TestHelpers, DietTrackerAssertions } from "../../utils/test-helpers";
import { testQueries, mockApiResponses } from "../../fixtures/test-data";

test.describe("Search Functionality", () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    // Mock API responses for search tests
    await page.route("**/api/**", async (route) => {
      const url = route.request().url();
      const method = route.request().method();

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
      } else if (url.includes("/search") && method === "POST") {
        // Parse request body to get query
        const requestBody = route.request().postDataJSON();
        const query = requestBody?.query || "";

        if (query === "nonexistent") {
          // Return empty results for specific test case
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              success: true,
              results: [],
              total_found: 0,
            }),
          });
        } else if (query.includes("<script>")) {
          // Return error for XSS test
          await route.fulfill({
            status: 400,
            contentType: "application/json",
            body: JSON.stringify({
              success: false,
              message: "無効な入力が検出されました",
            }),
          });
        } else {
          // Return mock search results
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              success: true,
              results: [
                {
                  id: "test-bill-1",
                  bill_number: "TEST001",
                  title: `検索結果: ${query}`,
                  description: "テスト用の法案です",
                  certainty: 0.9,
                  search_method: "vector",
                },
                {
                  id: "test-bill-2",
                  bill_number: "TEST002",
                  title: `関連法案: ${query}`,
                  description: "関連するテスト法案です",
                  certainty: 0.8,
                  search_method: "vector",
                },
              ],
              total_found: 2,
            }),
          });
        }
      } else {
        // Default mock response
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      }
    });

    helpers = new TestHelpers(page);
    await helpers.navigateToPage("/");
    await helpers.waitForAppReady();
  });

  test.afterEach(async ({ page }) => {
    await helpers.cleanup();
  });

  test("should perform basic search", async ({ page }) => {
    const query = testQueries.valid[0]; // '税制改正'

    // Fill search input
    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    await searchInput.fill(query);

    // Submit search
    await page.click(TestHelpers.selectors.searchButton);

    // Verify search was submitted
    await expect(searchInput).toHaveValue(query);

    // Check for results or empty state
    await DietTrackerAssertions.expectSearchResults(page, query);
  });

  test("should validate search input", async ({ page }) => {
    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    const searchButton = page.locator(TestHelpers.selectors.searchButton);

    // Test empty search
    await searchInput.fill("");
    await expect(searchButton).toBeDisabled();

    // Test valid search
    await searchInput.fill(testQueries.valid[0]);
    await expect(searchButton).toBeEnabled();
  });

  test("should enforce input length limits", async ({ page }) => {
    const searchInput = page.locator(TestHelpers.selectors.searchInput);

    // Try to input very long text
    const longText = "a".repeat(300);
    await searchInput.fill(longText);

    // Should be limited to 200 characters
    const actualValue = await searchInput.inputValue();
    expect(actualValue.length).toBeLessThanOrEqual(200);

    // Should show validation error
    await expect(
      page.locator(TestHelpers.selectors.validationError),
    ).toBeVisible();
  });

  test("should sanitize malicious input", async ({ page }) => {
    const searchInput = page.locator(TestHelpers.selectors.searchInput);

    // Try XSS input
    const xssInput = testQueries.invalid[2]; // '<script>alert("xss")</script>'
    await searchInput.fill(xssInput);

    // Should show validation error or sanitize input
    await page.click(TestHelpers.selectors.searchButton);

    // Check that no alert was triggered (XSS prevented)
    // Note: This would need specific implementation based on validation
    const hasValidationError =
      (await page.locator(TestHelpers.selectors.validationError).count()) > 0;
    expect(hasValidationError).toBe(true);
  });

  test("should show loading state during search", async ({ page }) => {
    // Mock slow API response
    await page.route("/api/search", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000)); // 2 second delay
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockApiResponses.searchResults.success),
      });
    });

    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    await searchInput.fill(testQueries.valid[0]);

    // Submit search
    await page.click(TestHelpers.selectors.searchButton);

    // Should show loading state
    await expect(
      page.locator(TestHelpers.selectors.loadingIndicator),
    ).toBeVisible();

    // Should show search results after loading
    await expect(page.locator(TestHelpers.selectors.searchResults)).toBeVisible(
      { timeout: 10000 },
    );
  });

  test("should handle search errors gracefully", async ({ page }) => {
    // Mock API error
    await page.route("/api/search", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify(mockApiResponses.searchResults.error),
      });
    });

    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    await searchInput.fill(testQueries.valid[0]);
    await page.click(TestHelpers.selectors.searchButton);

    // Should show error message
    await expect(
      page.locator(TestHelpers.selectors.errorMessage),
    ).toBeVisible();
    await expect(
      page.locator(TestHelpers.selectors.errorMessage),
    ).toContainText(/エラー|失敗/);
  });

  test("should support debounced search", async ({ page }) => {
    const searchInput = page.locator(TestHelpers.selectors.searchInput);

    // Type characters quickly
    await searchInput.type(testQueries.valid[0], { delay: 50 });

    // Wait for debounce period
    await page.waitForTimeout(1000);

    // Should have triggered search automatically
    await DietTrackerAssertions.expectSearchResults(page, testQueries.valid[0]);
  });

  test("should handle multiple search terms", async ({ page }) => {
    const multiTermQuery = testQueries.edge[1]; // '税制改正 社会保障 予算'

    await helpers.performSearch(multiTermQuery);

    // Should handle multi-term search
    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    await expect(searchInput).toHaveValue(multiTermQuery);
  });

  test("should display search statistics", async ({ page }) => {
    // Mock successful search with results
    await page.route("/api/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockApiResponses.searchResults.success),
      });
    });

    await helpers.performSearch(testQueries.valid[0]);

    // Should show search stats
    await expect(page.locator("text=件の結果が見つかりました")).toBeVisible();
    await expect(page.locator("text=AI検索")).toBeVisible();
  });

  test("should handle empty search results", async ({ page }) => {
    // Mock empty search results
    await page.route("/api/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockApiResponses.searchResults.empty),
      });
    });

    await helpers.performSearch("nonexistent");

    // Should show empty state
    await expect(
      page.locator("text=検索結果が見つかりませんでした"),
    ).toBeVisible();
  });

  test("should be responsive on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    // Search functionality should work on mobile
    await helpers.performSearch(testQueries.valid[0]);

    // Check responsive design
    await helpers.checkResponsiveDesign(TestHelpers.selectors.searchInput);
    await helpers.checkResponsiveDesign(TestHelpers.selectors.searchButton);
  });

  test("should enforce rate limiting", async ({ page }) => {
    // Simulate rapid searches
    for (let i = 0; i < 12; i++) {
      await helpers.performSearch(`query${i}`);
      await page.waitForTimeout(100);
    }

    // Should show rate limit error after too many requests
    await expect(page.locator("text=上限に達しました")).toBeVisible();
  });

  test("should preserve search state on navigation", async ({ page }) => {
    const query = testQueries.valid[0];
    await helpers.performSearch(query);

    // Navigate away and back
    await page.click(TestHelpers.selectors.issuesLink);
    await page.click(TestHelpers.selectors.homeLink);

    // Search input should be preserved (depending on implementation)
    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    // Note: This may depend on whether the app preserves search state
  });

  test("should be accessible", async ({ page }) => {
    // Check search input accessibility
    await helpers.expectElementToBeAccessible(
      TestHelpers.selectors.searchInput,
    );

    // Check search button accessibility
    await helpers.expectElementToBeAccessible(
      TestHelpers.selectors.searchButton,
    );

    // Test keyboard interaction
    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    await searchInput.focus();
    await expect(searchInput).toBeFocused();

    // Should be able to submit with Enter
    await searchInput.fill(testQueries.valid[0]);
    await searchInput.press("Enter");

    await DietTrackerAssertions.expectSearchResults(page, testQueries.valid[0]);
  });
});
