import { test, expect } from '@playwright/test';
import { TestHelpers, DietTrackerAssertions } from '../../utils/test-helpers';

test.describe('Basic Navigation', () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
    await helpers.navigateToPage('/');
    await helpers.waitForAppReady();
  });

  test.afterEach(async ({ page }) => {
    await helpers.cleanup();
  });

  test('should navigate between home and issues pages', async ({ page }) => {
    // Verify we're on the home page
    await expect(page).toHaveURL('/');
    await expect(page.locator('h1')).toContainText('国会議事録検索システム');

    // Navigate to issues page
    await page.click(TestHelpers.selectors.issuesLink);
    await expect(page).toHaveURL('/issues');
    await expect(page.locator('h1')).toContainText('政策イシューボード');

    // Navigate back to home
    await page.click(TestHelpers.selectors.homeLink);
    await expect(page).toHaveURL('/');
    await expect(page.locator('h1')).toContainText('国会議事録検索システム');
  });

  test('should maintain navigation state on page refresh', async ({ page }) => {
    // Navigate to issues page
    await page.click(TestHelpers.selectors.issuesLink);
    await expect(page).toHaveURL('/issues');

    // Refresh the page
    await page.reload();
    await helpers.waitForAppReady();

    // Should still be on issues page
    await expect(page).toHaveURL('/issues');
    await expect(page.locator('h1')).toContainText('政策イシューボード');
  });

  test('should handle browser back and forward buttons', async ({ page }) => {
    // Navigate to issues page
    await page.click(TestHelpers.selectors.issuesLink);
    await expect(page).toHaveURL('/issues');

    // Use browser back button
    await page.goBack();
    await expect(page).toHaveURL('/');

    // Use browser forward button
    await page.goForward();
    await expect(page).toHaveURL('/issues');
  });

  test('should display header and footer on all pages', async ({ page }) => {
    const pages = ['/', '/issues'];

    for (const path of pages) {
      await helpers.navigateToPage(path);
      
      // Check header is present
      await expect(page.locator(TestHelpers.selectors.header)).toBeVisible();
      
      // Check footer is present
      await expect(page.locator(TestHelpers.selectors.footer)).toBeVisible();
      
      // Check main content is present
      await expect(page.locator(TestHelpers.selectors.mainContent)).toBeVisible();
    }
  });

  test('should handle 404 pages gracefully', async ({ page }) => {
    // Navigate to non-existent page
    const response = await page.goto('/non-existent-page');
    
    // Should return 404 status
    expect(response?.status()).toBe(404);
    
    // Should show user-friendly 404 page
    await expect(page.locator('h1')).toContainText(/404|見つかりません/);
  });

  test('should be keyboard navigable', async ({ page }) => {
    // Test tab navigation
    await page.keyboard.press('Tab');
    
    // Should focus on first interactive element
    const firstFocusedElement = page.locator(':focus');
    await expect(firstFocusedElement).toBeVisible();
    
    // Continue tabbing to navigate
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    // Test keyboard activation
    await helpers.testKeyboardNavigation();
  });

  test('should display Japanese content correctly', async ({ page }) => {
    // Check main heading
    await DietTrackerAssertions.expectValidJapaneseContent(page, 'h1');
    
    // Check navigation links
    await DietTrackerAssertions.expectValidJapaneseContent(page, 'nav');
    
    // Check footer content
    await DietTrackerAssertions.expectValidJapaneseContent(page, 'footer');
  });

  test('should have proper meta tags', async ({ page }) => {
    // Check viewport meta tag for mobile
    const viewportMeta = page.locator('meta[name="viewport"]');
    await expect(viewportMeta).toHaveAttribute('content', /width=device-width/);
    
    // Check language attribute
    const htmlElement = page.locator('html');
    await expect(htmlElement).toHaveAttribute('lang', 'ja');
    
    // Check title
    await expect(page).toHaveTitle(/国会議事録検索システム/);
  });

  test('should load without console errors', async ({ page }) => {
    await helpers.expectNoConsoleErrors();
  });

  test('should be mobile-friendly', async ({ page }) => {
    await DietTrackerAssertions.expectMobileFriendly(page);
  });

  test('should have accessible navigation', async ({ page }) => {
    // Check navigation landmarks
    const nav = page.locator('nav');
    await expect(nav).toBeVisible();
    
    // Check navigation links are accessible
    await helpers.expectElementToBeAccessible(TestHelpers.selectors.homeLink);
    await helpers.expectElementToBeAccessible(TestHelpers.selectors.issuesLink);
  });
});