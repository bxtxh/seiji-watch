import { test, expect } from '@playwright/test';
import { startTestServer, stopTestServer } from '../utils/test-helpers';

test.describe('Member Features Performance Tests', () => {
  test.beforeAll(async () => {
    await startTestServer();
  });

  test.afterAll(async () => {
    await stopTestServer();
  });

  test('member list virtual scrolling performance', async ({ page }) => {
    // Start performance measurement
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // Measure initial load time
    const loadStartTime = Date.now();
    await page.waitForSelector('[data-testid="virtual-scroll-container"]');
    const loadEndTime = Date.now();
    const loadTime = loadEndTime - loadStartTime;
    
    // Should load within 2 seconds
    expect(loadTime).toBeLessThan(2000);
    
    // Measure scroll performance
    const scrollContainer = page.locator('[data-testid="virtual-scroll-container"]');
    const scrollStartTime = Date.now();
    
    // Perform heavy scrolling
    for (let i = 0; i < 50; i++) {
      await scrollContainer.evaluate(el => el.scrollTop += 500);
      await page.waitForTimeout(10);
    }
    
    const scrollEndTime = Date.now();
    const scrollTime = scrollEndTime - scrollStartTime;
    
    // Should maintain smooth scrolling
    expect(scrollTime).toBeLessThan(5000);
    
    // Check if virtual scrolling is working (limited DOM elements)
    const memberCards = page.locator('[data-testid="member-card"]');
    const cardCount = await memberCards.count();
    
    // Should not render all 723 members at once
    expect(cardCount).toBeLessThan(100);
  });

  test('search performance with large dataset', async ({ page }) => {
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    const searchInput = page.locator('input[id="search"]');
    
    // Measure search response time
    const searchStartTime = Date.now();
    await searchInput.fill('田中');
    
    // Wait for search results
    await page.waitForSelector('text=/検索結果: \d+名/', { timeout: 5000 });
    
    const searchEndTime = Date.now();
    const searchTime = searchEndTime - searchStartTime;
    
    // Should respond within 1 second
    expect(searchTime).toBeLessThan(1000);
    
    // Test rapid typing performance
    await searchInput.clear();
    
    const rapidTypingStartTime = Date.now();
    
    // Simulate rapid typing
    const searchTerm = 'さとう';
    for (let i = 0; i < searchTerm.length; i++) {
      await searchInput.type(searchTerm[i]);
      await page.waitForTimeout(50);
    }
    
    await page.waitForSelector('text=/検索結果: \d+名/', { timeout: 5000 });
    
    const rapidTypingEndTime = Date.now();
    const rapidTypingTime = rapidTypingEndTime - rapidTypingStartTime;
    
    // Should handle rapid typing smoothly
    expect(rapidTypingTime).toBeLessThan(2000);
  });

  test('member detail page load performance', async ({ page }) => {
    // Measure page load time
    const startTime = Date.now();
    
    await page.goto('/members/member_001');
    await page.waitForSelector('[data-testid="member-profile"]', { timeout: 10000 });
    
    const endTime = Date.now();
    const loadTime = endTime - startTime;
    
    // Should load within 2 seconds
    expect(loadTime).toBeLessThan(2000);
    
    // Test tab switching performance
    const tabSwitchStartTime = Date.now();
    
    // Switch through all tabs
    await page.locator('button:has-text("政策立場")').click();
    await page.waitForSelector('text=政策立場分析');
    
    await page.locator('button:has-text("投票履歴")').click();
    await page.waitForSelector('text=投票履歴');
    
    await page.locator('button:has-text("活動記録")').click();
    await page.waitForSelector('text=活動記録');
    
    await page.locator('button:has-text("概要")').click();
    await page.waitForSelector('text=活動概要');
    
    const tabSwitchEndTime = Date.now();
    const tabSwitchTime = tabSwitchEndTime - tabSwitchStartTime;
    
    // Tab switching should be immediate
    expect(tabSwitchTime).toBeLessThan(1000);
  });

  test('Japanese text conversion performance', async ({ page }) => {
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    const searchInput = page.locator('input[id="search"]');
    
    // Test romaji to hiragana conversion speed
    const conversionStartTime = Date.now();
    
    await searchInput.fill('tanaka');
    
    // Wait for conversion indicator
    await page.waitForSelector('text=ローマ字入力', { timeout: 2000 });
    await page.waitForSelector('text=たなか', { timeout: 2000 });
    
    const conversionEndTime = Date.now();
    const conversionTime = conversionEndTime - conversionStartTime;
    
    // Should convert within 500ms
    expect(conversionTime).toBeLessThan(500);
    
    // Test multiple rapid conversions
    const rapidConversionStartTime = Date.now();
    
    const testInputs = ['yamada', 'suzuki', 'takahashi', 'watanabe'];
    
    for (const input of testInputs) {
      await searchInput.clear();
      await searchInput.fill(input);
      await page.waitForTimeout(100);
    }
    
    const rapidConversionEndTime = Date.now();
    const rapidConversionTime = rapidConversionEndTime - rapidConversionStartTime;
    
    // Should handle rapid conversions smoothly
    expect(rapidConversionTime).toBeLessThan(2000);
  });

  test('memory usage during virtual scrolling', async ({ page }) => {
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    const scrollContainer = page.locator('[data-testid="virtual-scroll-container"]');
    
    // Get initial memory usage
    const initialMetrics = await page.evaluate(() => {
      return {
        usedJSHeapSize: (performance as any).memory?.usedJSHeapSize || 0,
        totalJSHeapSize: (performance as any).memory?.totalJSHeapSize || 0,
      };
    });
    
    // Perform extensive scrolling
    for (let i = 0; i < 100; i++) {
      await scrollContainer.evaluate(el => el.scrollTop += 200);
      await page.waitForTimeout(10);
    }
    
    // Get final memory usage
    const finalMetrics = await page.evaluate(() => {
      return {
        usedJSHeapSize: (performance as any).memory?.usedJSHeapSize || 0,
        totalJSHeapSize: (performance as any).memory?.totalJSHeapSize || 0,
      };
    });
    
    // Memory usage should not increase dramatically
    const memoryIncrease = finalMetrics.usedJSHeapSize - initialMetrics.usedJSHeapSize;
    const memoryIncreasePercentage = (memoryIncrease / initialMetrics.usedJSHeapSize) * 100;
    
    // Should not increase memory usage by more than 50%
    expect(memoryIncreasePercentage).toBeLessThan(50);
  });

  test('API response time monitoring', async ({ page }) => {
    // Monitor API response times
    let apiResponseTime = 0;
    
    page.on('response', response => {
      if (response.url().includes('/api/members')) {
        apiResponseTime = response.timing().responseEnd - response.timing().requestStart;
      }
    });
    
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // API should respond within 1 second
    expect(apiResponseTime).toBeLessThan(1000);
  });

  test('lighthouse performance score', async ({ page }) => {
    await page.goto('/members');
    await page.waitForSelector('[data-testid="member-list"]', { timeout: 10000 });
    
    // Run basic performance checks
    const performanceMetrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        loadTime: navigation.loadEventEnd - navigation.loadEventStart,
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0,
      };
    });
    
    // Performance thresholds
    expect(performanceMetrics.loadTime).toBeLessThan(2000);
    expect(performanceMetrics.domContentLoaded).toBeLessThan(1000);
    expect(performanceMetrics.firstContentfulPaint).toBeLessThan(1500);
  });
});