import { test, expect } from '@playwright/test';
import { startTestServer, stopTestServer } from '../utils/test-helpers';

test.describe('Member List - T64 Implementation', () => {
  test.beforeAll(async () => {
    await startTestServer();
  });

  test.afterAll(async () => {
    await stopTestServer();
  });

  test('displays member list with virtualization', async ({ page }) => {
    await page.goto('/members');
    
    // Wait for page to load
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // Check if header is present
    await expect(page.locator('h1')).toContainText('国会議員一覧');
    
    // Check if member count is displayed
    await expect(page.locator('text=/\d+名の議員が登録されています/')).toBeVisible();
    
    // Check if search box is present
    await expect(page.locator('input[placeholder*="tanaka"]')).toBeVisible();
    
    // Check if filters are present
    await expect(page.locator('select[id="house"]')).toBeVisible();
    await expect(page.locator('select[id="party"]')).toBeVisible();
  });

  test('Japanese text search functionality', async ({ page }) => {
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    const searchInput = page.locator('input[id="search"]');
    
    // Test romaji to hiragana conversion
    await searchInput.fill('tanaka');
    await page.waitForTimeout(500); // Wait for search debounce
    
    // Should show conversion indicator
    await expect(page.locator('text=ローマ字入力')).toBeVisible();
    await expect(page.locator('text=たなか')).toBeVisible();
    
    // Should show search results
    await expect(page.locator('text=/検索結果: \d+名/')).toBeVisible();
    
    // Clear and test hiragana search
    await searchInput.clear();
    await searchInput.fill('たなか');
    await page.waitForTimeout(500);
    
    // Should show results for 田中
    await expect(page.locator('text=/検索結果: \d+名/')).toBeVisible();
    
    // Clear and test kanji search
    await searchInput.clear();
    await searchInput.fill('田中');
    await page.waitForTimeout(500);
    
    // Should show results
    await expect(page.locator('text=/検索結果: \d+名/')).toBeVisible();
  });

  test('filtering functionality', async ({ page }) => {
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // Test house filter
    await page.selectOption('select[id="house"]', 'house_of_representatives');
    await page.waitForTimeout(500);
    
    // Should show filtered results
    await expect(page.locator('text=/\d+名が条件に一致/')).toBeVisible();
    
    // Test party filter
    await page.selectOption('select[id="party"]', '自由民主党');
    await page.waitForTimeout(500);
    
    // Should show further filtered results
    await expect(page.locator('text=/\d+名が条件に一致/')).toBeVisible();
    
    // Reset filters
    await page.selectOption('select[id="house"]', '');
    await page.selectOption('select[id="party"]', '');
    await page.waitForTimeout(500);
  });

  test('virtual scrolling performance', async ({ page }) => {
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // Check virtual scrolling indicator
    await expect(page.locator('text=/仮想スクロール: \d+名中 \d+名を表示中/')).toBeVisible();
    
    // Test scrolling performance
    const scrollContainer = page.locator('[data-testid="virtual-scroll-container"]');
    
    // Scroll down multiple times
    for (let i = 0; i < 10; i++) {
      await scrollContainer.evaluate(el => el.scrollTop += 1000);
      await page.waitForTimeout(100);
    }
    
    // Should still show virtual scrolling indicator
    await expect(page.locator('text=/仮想スクロール: \d+名中 \d+名を表示中/')).toBeVisible();
    
    // Should maintain performance (no frozen UI)
    await expect(page.locator('h1')).toContainText('国会議員一覧');
  });

  test('member navigation', async ({ page }) => {
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // Click on first member
    await page.locator('[data-testid="member-card"]').first().click();
    
    // Should navigate to member detail page
    await expect(page).toHaveURL(/\/members\/member_\d+/);
    
    // Should show member details
    await expect(page.locator('h1')).toContainText(/田中|佐藤|鈴木|高橋|伊藤|渡辺|山本|中村|小林|加藤|吉田|山田|佐々木|山口|松本|井上|木村|林|斎藤|清水|山崎|森|池田|橋本|阿部|石川|前田|藤原|後藤|近藤/);
  });

  test('accessibility compliance', async ({ page }) => {
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // Check for proper ARIA labels
    await expect(page.locator('label[for="search"]')).toBeVisible();
    await expect(page.locator('label[for="house"]')).toBeVisible();
    await expect(page.locator('label[for="party"]')).toBeVisible();
    
    // Check keyboard navigation
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    // Search input should be focusable
    await expect(page.locator('input[id="search"]')).toBeFocused();
    
    // Test keyboard navigation to first member
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    // Should be able to navigate to member cards
    const memberCard = page.locator('[data-testid="member-card"]').first();
    await memberCard.focus();
    await page.keyboard.press('Enter');
    
    // Should navigate to member page
    await expect(page).toHaveURL(/\/members\/member_\d+/);
  });

  test('responsive design', async ({ page }) => {
    // Test desktop view
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // Check grid layout
    const filterGrid = page.locator('.grid-cols-1.md\\:grid-cols-2');
    await expect(filterGrid).toBeVisible();
    
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await page.reload();
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // Should still be usable on mobile
    await expect(page.locator('h1')).toContainText('国会議員一覧');
    await expect(page.locator('input[id="search"]')).toBeVisible();
    
    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.reload();
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // Should adapt to tablet layout
    await expect(page.locator('h1')).toContainText('国会議員一覧');
  });

  test('error handling', async ({ page }) => {
    // Test with API unavailable
    await page.route('**/api/members', route => route.abort());
    
    await page.goto('/members');
    await page.waitForTimeout(2000);
    
    // Should show fallback to mock data or error message
    await expect(page.locator('h1')).toContainText('国会議員一覧');
    
    // Should still show some data (mock fallback)
    await expect(page.locator('text=/\d+名の議員が登録されています/')).toBeVisible();
  });
});