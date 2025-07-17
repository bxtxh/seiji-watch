import { FullConfig } from "@playwright/test";

/**
 * Global teardown for Playwright tests
 * Runs once after all tests
 */
async function globalTeardown(config: FullConfig) {
  console.log("🧹 Starting global test teardown...");

  try {
    // Clean up any global resources
    // For example: clear test databases, clean up files, etc.

    // Log test completion
    console.log("📊 Test run completed");

    // Optional: Generate summary report
    console.log("📈 Generating test summary...");

    console.log("✅ Global teardown completed successfully");
  } catch (error) {
    console.error("❌ Global teardown failed:", error);
    // Don't throw error to avoid masking test failures
  }
}

export default globalTeardown;
