import { test, expect } from '@playwright/test';

test.describe('Issue Categories Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the homepage first
    await page.goto('/');
  });

  test('should navigate to categories page from main navigation', async ({ page }) => {
    // Click on "政策分野" in the main navigation
    await page.click('nav a[href="/issues/categories"]');
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
    
    // Check that we're on the categories page
    await expect(page).toHaveURL('/issues/categories');
    
    // Check page title
    await expect(page).toHaveTitle(/政策分野/);
    
    // Check main heading
    await expect(page.locator('h1')).toContainText('政策分野から法案を探す');
  });

  test('should display category tree and statistics', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Check statistics cards are present
    await expect(page.locator('text=主要政策分野')).toBeVisible();
    await expect(page.locator('text=サブトピック')).toBeVisible();
    await expect(page.locator('text=総カテゴリ数')).toBeVisible();
    
    // Check at least some L1 categories are displayed
    await expect(page.locator('[data-testid="l1-category"]').first()).toBeVisible();
    
    // Check CAP code badges are present
    await expect(page.locator('text=/CAP-\\d+/')).toBeVisible();
  });

  test('should expand and collapse L1 categories', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Find an L1 category with children (look for expand button)
    const expandButton = page.locator('button:has(svg)').first();
    
    if (await expandButton.isVisible()) {
      // Click to expand
      await expandButton.click();
      
      // Check that L2 children are now visible
      await expect(page.locator('[data-testid="l2-category"]').first()).toBeVisible();
      
      // Click to collapse
      await expandButton.click();
      
      // Check that L2 children are hidden
      await expect(page.locator('[data-testid="l2-category"]').first()).toBeHidden();
    }
  });

  test('should navigate to category detail page', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Click on the first L1 category
    const firstCategory = page.locator('[data-testid="l1-category"]').first();
    await firstCategory.click();
    
    // Wait for navigation
    await page.waitForLoadState('networkidle');
    
    // Check that we're on a category detail page
    await expect(page.url()).toMatch(/\/issues\/categories\/[^\/]+$/);
    
    // Check breadcrumbs are present
    await expect(page.locator('nav[aria-label="Breadcrumb"]')).toBeVisible();
    
    // Check category header is present
    await expect(page.locator('h1')).toBeVisible();
  });

  test('should display breadcrumbs on category detail page', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Click on first category
    const firstCategory = page.locator('[data-testid="l1-category"]').first();
    await firstCategory.click();
    await page.waitForLoadState('networkidle');
    
    // Check breadcrumbs
    const breadcrumb = page.locator('nav[aria-label="Breadcrumb"]');
    await expect(breadcrumb).toBeVisible();
    await expect(breadcrumb.locator('text=ホーム')).toBeVisible();
    await expect(breadcrumb.locator('text=政策分野')).toBeVisible();
  });

  test('should show child categories on L1 detail page', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Click on first category
    const firstCategory = page.locator('[data-testid="l1-category"]').first();
    await firstCategory.click();
    await page.waitForLoadState('networkidle');
    
    // Check if sub-topics section exists
    const subTopicsSection = page.locator('text=サブトピック').first();
    if (await subTopicsSection.isVisible()) {
      // Check that sub-topics are displayed
      await expect(page.locator('[data-testid="child-category"]').first()).toBeVisible();
    }
  });

  test('should navigate back to categories from detail page', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Click on first category
    const firstCategory = page.locator('[data-testid="l1-category"]').first();
    await firstCategory.click();
    await page.waitForLoadState('networkidle');
    
    // Click on "政策分野" breadcrumb
    await page.locator('nav[aria-label="Breadcrumb"] a[href="/issues/categories"]').click();
    await page.waitForLoadState('networkidle');
    
    // Check that we're back on the categories page
    await expect(page).toHaveURL('/issues/categories');
    await expect(page.locator('h1')).toContainText('政策分野から法案を探す');
  });

  test('should show navigation sidebar on detail page', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Click on first category
    const firstCategory = page.locator('[data-testid="l1-category"]').first();
    await firstCategory.click();
    await page.waitForLoadState('networkidle');
    
    // Check sidebar navigation
    await expect(page.locator('text=ナビゲーション')).toBeVisible();
    await expect(page.locator('a[href="/issues/categories"]:has-text("すべての政策分野")')).toBeVisible();
    await expect(page.locator('a[href="/bills"]:has-text("法案一覧")')).toBeVisible();
  });

  test('should show statistics on detail page', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Click on first category
    const firstCategory = page.locator('[data-testid="l1-category"]').first();
    await firstCategory.click();
    await page.waitForLoadState('networkidle');
    
    // Check statistics sidebar
    await expect(page.locator('text=統計情報')).toBeVisible();
    await expect(page.locator('text=関連法案')).toBeVisible();
  });

  test('should handle category without children gracefully', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Look for a category without expand button (no children)
    const categoryWithoutChildren = page.locator('[data-testid="l1-category"]:not(:has(button))').first();
    
    if (await categoryWithoutChildren.isVisible()) {
      await categoryWithoutChildren.click();
      await page.waitForLoadState('networkidle');
      
      // Should still show the detail page properly
      await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('text=統計情報')).toBeVisible();
    }
  });
});

test.describe('Issue Categories API Integration', () => {
  test('should load categories from API', async ({ page }) => {
    // Intercept API calls
    await page.route('/api/issues/categories/tree', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          L1: [
            {
              id: 'test-l1-1',
              fields: {
                CAP_Code: '1',
                Layer: 'L1',
                Title_JA: 'テスト政策分野',
                Title_EN: 'Test Policy Area',
                Is_Seed: true
              }
            }
          ],
          L2: [
            {
              id: 'test-l2-1',
              fields: {
                CAP_Code: '101',
                Layer: 'L2',
                Title_JA: 'テストサブトピック',
                Title_EN: 'Test Sub-topic',
                Parent_Category: ['test-l1-1'],
                Is_Seed: true
              }
            }
          ],
          L3: []
        })
      });
    });
    
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Check that test data is displayed
    await expect(page.locator('text=テスト政策分野')).toBeVisible();
    await expect(page.locator('text=CAP-1')).toBeVisible();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Intercept API calls and return error
    await page.route('/api/issues/categories/tree', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Server error' })
      });
    });
    
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Check error message is displayed
    await expect(page.locator('text=エラーが発生しました')).toBeVisible();
    await expect(page.locator('button:has-text("再試行")')).toBeVisible();
  });
});

test.describe('Issue Categories Accessibility', () => {
  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Test tab navigation
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab'); // Navigate to first category
    
    // Test Enter key to click
    await page.keyboard.press('Enter');
    await page.waitForLoadState('networkidle');
    
    // Should navigate to detail page
    await expect(page.url()).toMatch(/\/issues\/categories\/[^\/]+$/);
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Check heading structure
    const h1 = page.locator('h1');
    await expect(h1).toHaveCount(1);
    await expect(h1).toContainText('政策分野から法案を探す');
    
    // Check h2 headings for sections
    await expect(page.locator('h2')).toHaveCount(1); // Should have help section h2
  });

  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Check for navigation landmarks
    await expect(page.locator('nav')).toBeVisible();
    
    // Check for main content
    await expect(page.locator('main, [role="main"]')).toBeVisible();
  });
});

test.describe('Issue Categories Mobile Responsiveness', () => {
  test.use({ viewport: { width: 375, height: 667 } }); // iPhone SE size
  
  test('should display properly on mobile', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Check mobile layout
    await expect(page.locator('h1')).toBeVisible();
    
    // Check grid adjusts for mobile
    const categoryGrid = page.locator('.grid').first();
    await expect(categoryGrid).toBeVisible();
    
    // Test mobile navigation
    await expect(page.locator('nav a[href="/issues/categories"]')).toBeVisible();
  });

  test('should handle touch interactions', async ({ page }) => {
    await page.goto('/issues/categories');
    await page.waitForLoadState('networkidle');
    
    // Test tap on category
    const firstCategory = page.locator('[data-testid="l1-category"]').first();
    if (await firstCategory.isVisible()) {
      await firstCategory.tap();
      await page.waitForLoadState('networkidle');
      
      // Should navigate to detail page
      await expect(page.url()).toMatch(/\/issues\/categories\/[^\/]+$/);
    }
  });
});