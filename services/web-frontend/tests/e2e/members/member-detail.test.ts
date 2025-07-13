import { test, expect } from '@playwright/test';
import { startTestServer, stopTestServer } from '../utils/test-helpers';

test.describe('Member Detail Page - T63 Implementation', () => {
  test.beforeAll(async () => {
    await startTestServer();
  });

  test.afterAll(async () => {
    await stopTestServer();
  });

  test('displays member profile information', async ({ page }) => {
    await page.goto('/members/member_001');
    
    // Wait for page to load
    await page.waitForSelector('[data-testid="member-profile"]', { timeout: 10000 });
    
    // Check if member name is displayed
    await expect(page.locator('h1')).toContainText(/田中|佐藤|鈴木|高橋|伊藤|渡辺|山本|中村|小林|加藤|吉田|山田|佐々木|山口|松本|井上|木村|林|斎藤|清水|山崎|森|池田|橋本|阿部|石川|前田|藤原|後藤|近藤/);
    
    // Check if basic info is displayed
    await expect(page.locator('text=/衆議院|参議院/')).toBeVisible();
    await expect(page.locator('text=/自由民主党|立憲民主党|日本維新の会|公明党|日本共産党|国民民主党|れいわ新選組|社会民主党|無所属/')).toBeVisible();
    await expect(page.locator('text=/\d+期/')).toBeVisible();
    
    // Check if committees are displayed
    await expect(page.locator('text=所属委員会')).toBeVisible();
  });

  test('tab navigation functionality', async ({ page }) => {
    await page.goto('/members/member_001');
    await page.waitForSelector('[data-testid="member-profile"]', { timeout: 10000 });
    
    // Check initial tab (概要)
    await expect(page.locator('button[aria-selected="true"]')).toContainText('概要');
    
    // Click on 政策立場 tab
    await page.locator('button:has-text("政策立場")').click();
    
    // Should show policy tab content
    await expect(page.locator('h2')).toContainText('政策立場分析');
    await expect(page.locator('text=🚧 開発中')).toBeVisible();
    await expect(page.locator('text=開発中です')).toBeVisible();
    
    // Click on 投票履歴 tab
    await page.locator('button:has-text("投票履歴")').click();
    
    // Should show voting history tab content
    await expect(page.locator('h2')).toContainText('投票履歴');
    await expect(page.locator('text=投票パターン')).toBeVisible();
    
    // Click on 活動記録 tab
    await page.locator('button:has-text("活動記録")').click();
    
    // Should show activity tab content
    await expect(page.locator('h2')).toContainText('活動記録');
    await expect(page.locator('text=活動記録は準備中です')).toBeVisible();
  });

  test('policy analysis section with development notice', async ({ page }) => {
    await page.goto('/members/member_001');
    await page.waitForSelector('[data-testid="member-profile"]', { timeout: 10000 });
    
    // Navigate to policy tab
    await page.locator('button:has-text("政策立場")').click();
    
    // Should show development notice
    await expect(page.locator('span:has-text("🚧 開発中")')).toBeVisible();
    
    // Should show explanation banner
    await expect(page.locator('.bg-yellow-50')).toBeVisible();
    await expect(page.locator('text=政策立場分析機能について')).toBeVisible();
    await expect(page.locator('text=より精密な政策立場分析システムを開発中')).toBeVisible();
    
    // Should show sample data notice
    await expect(page.locator('text=※ 以下はMVP版のサンプルデータです')).toBeVisible();
    
    // Should show sample policy positions with reduced opacity
    await expect(page.locator('.opacity-75')).toBeVisible();
  });

  test('voting statistics visualization', async ({ page }) => {
    await page.goto('/members/member_001');
    await page.waitForSelector('[data-testid="member-profile"]', { timeout: 10000 });
    
    // Navigate to voting tab
    await page.locator('button:has-text("投票履歴")').click();
    
    // Should show voting pattern grid
    await expect(page.locator('text=投票パターン')).toBeVisible();
    
    // Should show voting statistics
    await expect(page.locator('text=賛成')).toBeVisible();
    await expect(page.locator('text=反対')).toBeVisible();
    await expect(page.locator('text=棄権')).toBeVisible();
    await expect(page.locator('text=欠席')).toBeVisible();
    
    // Should show numerical values
    await expect(page.locator('text=/\d+/')).toBeVisible();
  });

  test('overview section metrics', async ({ page }) => {
    await page.goto('/members/member_001');
    await page.waitForSelector('[data-testid="member-profile"]', { timeout: 10000 });
    
    // Should be on overview tab by default
    await expect(page.locator('text=活動概要')).toBeVisible();
    
    // Should show activity metrics
    await expect(page.locator('text=活動度')).toBeVisible();
    await expect(page.locator('text=党方針一致率')).toBeVisible();
    await expect(page.locator('text=データ完全性')).toBeVisible();
    
    // Should show percentage values
    await expect(page.locator('text=/\d+%/')).toBeVisible();
    
    // Should show voting statistics summary
    await expect(page.locator('text=投票統計')).toBeVisible();
    await expect(page.locator('text=総投票数')).toBeVisible();
    await expect(page.locator('text=出席率')).toBeVisible();
  });

  test('member navigation back to list', async ({ page }) => {
    await page.goto('/members/member_001');
    await page.waitForSelector('[data-testid="member-profile"]', { timeout: 10000 });
    
    // Navigate back using browser
    await page.goBack();
    
    // Should go back to member list
    await expect(page).toHaveURL('/members');
    await expect(page.locator('h1')).toContainText('国会議員一覧');
  });

  test('accessibility compliance', async ({ page }) => {
    await page.goto('/members/member_001');
    await page.waitForSelector('[data-testid="member-profile"]', { timeout: 10000 });
    
    // Check tab navigation with keyboard
    await page.keyboard.press('Tab');
    
    // Should be able to navigate through tabs
    const tabs = page.locator('nav[aria-label="タブ"] button');
    await expect(tabs).toHaveCount(4);
    
    // Test keyboard navigation
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Enter');
    
    // Should switch to next tab
    await expect(page.locator('button[aria-selected="true"]')).toContainText('政策立場');
    
    // Check for proper ARIA labels
    await expect(page.locator('nav[aria-label="タブ"]')).toBeVisible();
  });

  test('responsive design', async ({ page }) => {
    // Test desktop view
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto('/members/member_001');
    await page.waitForSelector('[data-testid="member-profile"]', { timeout: 10000 });
    
    // Should show proper layout
    await expect(page.locator('.grid-cols-1.lg\\:grid-cols-3')).toBeVisible();
    
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await page.reload();
    await page.waitForSelector('[data-testid="member-profile"]', { timeout: 10000 });
    
    // Should adapt to mobile layout
    await expect(page.locator('h1')).toBeVisible();
    
    // Tabs should still be accessible
    await expect(page.locator('nav[aria-label="タブ"]')).toBeVisible();
  });

  test('error handling for non-existent member', async ({ page }) => {
    await page.goto('/members/nonexistent_member');
    await page.waitForTimeout(2000);
    
    // Should show error message
    await expect(page.locator('text=エラー')).toBeVisible();
    await expect(page.locator('text=議員情報が見つかりません')).toBeVisible();
    
    // Should show return to list button
    await expect(page.locator('text=議員一覧に戻る')).toBeVisible();
  });

  test('API integration error handling', async ({ page }) => {
    // Mock API failure
    await page.route('**/api/members/**', route => route.abort());
    
    await page.goto('/members/member_001');
    await page.waitForTimeout(2000);
    
    // Should show fallback data or error
    await expect(page.locator('h1')).toContainText('田中太郎');
    
    // Should show mock data fallback
    await expect(page.locator('text=/衆議院|参議院/')).toBeVisible();
  });
});