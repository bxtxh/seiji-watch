import { chromium, FullConfig } from "@playwright/test";

/**
 * Global setup for Playwright tests
 * Runs once before all tests
 */
async function globalSetup(config: FullConfig) {
  console.log("🚀 Starting global test setup...");

  const baseURL = config.projects[0].use?.baseURL || "http://localhost:3000";

  // Launch browser for setup
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    console.log("🔍 Checking if application is ready...");

    // Mock API responses to avoid dependency on backend
    await page.route("**/api/**", async (route) => {
      const url = route.request().url();

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
            results: [
              {
                id: "test-bill-1",
                title: "テスト法案1",
                description: "テスト用の法案です",
                certainty: 0.9,
              },
            ],
            total_found: 1,
          }),
        });
      } else {
        // Default mock response
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      }
    });

    // Wait for the application to be ready (use domcontentloaded instead of networkidle to avoid API dependency)
    await page.goto(baseURL, { waitUntil: "domcontentloaded" });

    // Check if the main elements are present
    await page.waitForSelector('h1:has-text("国会議事録検索システム")', {
      timeout: 15000,
    });

    console.log("✅ Application is ready for testing");

    // Optional: Pre-warm the application
    console.log("🔥 Pre-warming application...");

    // Navigate to key pages to warm up
    await page.goto(`${baseURL}/issues`);
    await page.waitForLoadState("domcontentloaded");

    // Go back to home
    await page.goto(baseURL);
    await page.waitForLoadState("domcontentloaded");

    console.log("✅ Global setup completed successfully");
  } catch (error) {
    console.error("❌ Global setup failed:", error);
    throw error;
  } finally {
    await browser.close();
  }
}

export default globalSetup;
