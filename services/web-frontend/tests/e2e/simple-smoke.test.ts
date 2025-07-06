import { test, expect } from '@playwright/test';

test.describe('Simple Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses for each test
    await page.route('**/api/**', async route => {
      const url = route.request().url();
      
      if (url.includes('/health')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'healthy',
            message: 'Test system is running'
          })
        });
      } else if (url.includes('/embeddings/stats')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'ok',
            bills: 150,
            speeches: 1200,
            message: 'Test data available'
          })
        });
      } else {
        // Default mock response
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        });
      }
    });
  });

  test('should load the homepage', async ({ page }) => {
    await page.goto('/');
    
    // Wait for the page to load
    await page.waitForLoadState('domcontentloaded');
    
    // Check that the title contains expected text
    await expect(page).toHaveTitle(/国会議事録検索システム/);
    
    // Check that the main heading is present
    await expect(page.locator('h1:has-text("国会議事録検索システム")')).toBeVisible();
  });

  test('should navigate to issues page', async ({ page }) => {
    await page.goto('/');
    
    // Wait for the page to load
    await page.waitForLoadState('domcontentloaded');
    
    // Navigate to issues page
    await page.goto('/issues');
    
    // Check that we're on the issues page
    await expect(page).toHaveURL('/issues');
    
    // Check that the page has loaded
    await expect(page.locator('h1').first()).toBeVisible();
  });

  test('should be responsive', async ({ page }) => {
    await page.goto('/');
    
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('h1').first()).toBeVisible();
    
    // Test desktop viewport
    await page.setViewportSize({ width: 1024, height: 768 });
    await expect(page.locator('h1').first()).toBeVisible();
  });
});