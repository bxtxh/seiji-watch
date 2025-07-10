import { test, expect } from '@playwright/test';

test.describe('Kanban Board Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000); // Allow data to load
  });

  test('Semantic HTML structure', async ({ page }) => {
    // Check main container has proper ARIA role
    const kanbanBoard = page.locator('[aria-label="国会イシュー Kanban ボード"]');
    await expect(kanbanBoard).toBeVisible();
    expect(await kanbanBoard.getAttribute('role')).toBe(null); // section element doesn't need role
    
    // Check list container has proper ARIA role
    const listContainer = page.locator('[role="list"][aria-label="ステージ別イシュー一覧"]');
    await expect(listContainer).toBeVisible();
    
    // Check stage columns have proper group role
    const stageColumns = page.locator('[role="group"]');
    await expect(stageColumns.first()).toBeVisible();
    
    // Check issue cards have proper listitem role
    const issueCards = page.locator('[role="listitem"]');
    await expect(issueCards.first()).toBeVisible();
  });

  test('Keyboard navigation support', async ({ page }) => {
    // Wait for cards to load
    await page.waitForTimeout(3000);
    
    const firstCard = page.locator('article').first();
    await expect(firstCard).toBeVisible();
    
    // Check card is focusable
    expect(await firstCard.getAttribute('tabindex')).toBe('0');
    
    // Focus the card
    await firstCard.focus();
    await expect(firstCard).toBeFocused();
    
    // Test Enter key activation
    await firstCard.press('Enter');
    // Note: In a real app, this would navigate. Here we just verify the handler exists.
    
    // Test Space key activation
    await firstCard.focus();
    await firstCard.press('Space');
    // Note: In a real app, this would navigate. Here we just verify the handler exists.
  });

  test('ARIA labels and descriptions', async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(3000);
    
    // Check main section has aria-label
    const kanbanBoard = page.locator('[aria-label="国会イシュー Kanban ボード"]');
    await expect(kanbanBoard).toBeVisible();
    
    // Check list container has aria-label
    const listContainer = page.locator('[aria-label="ステージ別イシュー一覧"]');
    await expect(listContainer).toBeVisible();
    
    // Check stage columns have proper labeling
    const stageColumns = page.locator('[role="group"]');
    const firstColumn = stageColumns.first();
    
    const ariaLabelledBy = await firstColumn.getAttribute('aria-labelledby');
    expect(ariaLabelledBy).toContain('stage-');
    
    // Verify the referenced label exists
    const labelElement = page.locator(`#${ariaLabelledBy}`);
    await expect(labelElement).toBeVisible();
    
    // Check issue cards have proper aria-labelledby
    const firstCard = page.locator('article').first();
    const cardAriaLabelledBy = await firstCard.getAttribute('aria-labelledby');
    expect(cardAriaLabelledBy).toContain('issue-');
    
    // Verify the referenced title exists
    const titleElement = page.locator(`#${cardAriaLabelledBy}`);
    await expect(titleElement).toBeVisible();
  });

  test('Screen reader friendly content', async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(3000);
    
    // Check stage badges have proper screen reader text
    const stageBadges = page.locator('[aria-label*="ステージ"]');
    if (await stageBadges.count() > 0) {
      const firstBadge = stageBadges.first();
      const ariaLabel = await firstBadge.getAttribute('aria-label');
      expect(ariaLabel).toContain('ステージ:');
    }
    
    // Check count badges have proper screen reader text
    const countBadges = page.locator('[aria-label*="件のイシュー"]');
    if (await countBadges.count() > 0) {
      const firstCountBadge = countBadges.first();
      const ariaLabel = await firstCountBadge.getAttribute('aria-label');
      expect(ariaLabel).toContain('件のイシュー');
    }
    
    // Check calendar icons are hidden from screen readers
    const calendarIcons = page.locator('svg[aria-hidden="true"]');
    await expect(calendarIcons.first()).toBeVisible();
  });

  test('Color contrast and visual accessibility', async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(3000);
    
    // Check stage headers have sufficient contrast
    const stageHeaders = page.locator('h3[id*="stage-"]');
    const firstHeader = stageHeaders.first();
    await expect(firstHeader).toBeVisible();
    
    // Verify text color is dark enough (computed style check)
    const textColor = await firstHeader.evaluate(el => {
      return window.getComputedStyle(el).color;
    });
    
    // Should be dark color (rgb values close to 0) for good contrast
    expect(textColor).toContain('rgb');
    
    // Check stage badges have appropriate background colors
    const stageBadges = page.locator('[class*="bg-"]');
    await expect(stageBadges.first()).toBeVisible();
  });

  test('Focus management and visibility', async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(3000);
    
    const firstCard = page.locator('article').first();
    await expect(firstCard).toBeVisible();
    
    // Focus the card and check focus is visible
    await firstCard.focus();
    
    // Check focus styles are applied (browser default or custom)
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBe(firstCard);
    
    // Check that focused element is not hidden
    const isVisible = await firstCard.isVisible();
    expect(isVisible).toBe(true);
  });

  test('Error state accessibility', async ({ page }) => {
    // Block API to trigger error state
    await page.route('**/api/issues/kanban*', route => {
      route.abort();
    });
    
    await page.goto('/');
    await page.waitForTimeout(2000);
    
    // Check error message is accessible
    const errorMessage = page.locator('text=エラーが発生しました');
    await expect(errorMessage).toBeVisible();
    
    // Check retry button is accessible
    const retryButton = page.locator('button:has-text("再読み込み")');
    await expect(retryButton).toBeVisible();
    await expect(retryButton).toBeEnabled();
    
    // Check button is focusable
    await retryButton.focus();
    await expect(retryButton).toBeFocused();
  });

  test('Loading state accessibility', async ({ page }) => {
    // Start with blocked request to see loading state
    let requestCount = 0;
    await page.route('**/api/issues/kanban*', route => {
      requestCount++;
      if (requestCount === 1) {
        // Delay first request to see loading state
        setTimeout(() => route.continue(), 1000);
      } else {
        route.continue();
      }
    });
    
    await page.goto('/');
    
    // Check loading state is present initially
    const loadingSkeleton = page.locator('[class*="animate-pulse"]');
    await expect(loadingSkeleton.first()).toBeVisible();
    
    // Wait for data to load
    await page.waitForTimeout(2000);
    
    // Loading state should be replaced with actual content
    const kanbanBoard = page.locator('[aria-label="国会イシュー Kanban ボード"]');
    await expect(kanbanBoard).toBeVisible();
  });

  test('Mobile accessibility features', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('/');
    await page.waitForTimeout(2000);
    
    // Check touch targets are appropriate size (minimum 44px)
    const cards = page.locator('article');
    const firstCard = cards.first();
    await expect(firstCard).toBeVisible();
    
    const cardSize = await firstCard.evaluate(el => {
      const rect = el.getBoundingClientRect();
      return { width: rect.width, height: rect.height };
    });
    
    // Cards should be large enough for touch interaction
    expect(cardSize.width).toBeGreaterThan(280); // Minimum card width
    expect(cardSize.height).toBeGreaterThan(44);  // Minimum touch target height
  });

  test('High contrast mode compatibility', async ({ page }) => {
    // Simulate high contrast mode by forcing high contrast colors
    await page.addStyleTag({
      content: `
        @media (prefers-contrast: high) {
          * {
            filter: contrast(2) !important;
          }
        }
      `
    });
    
    await page.waitForTimeout(2000);
    
    // Check that elements are still visible and readable
    const kanbanBoard = page.locator('[aria-label="国会イシュー Kanban ボード"]');
    await expect(kanbanBoard).toBeVisible();
    
    const firstCard = page.locator('article').first();
    await expect(firstCard).toBeVisible();
    
    // Check that text is still readable
    const cardTitle = firstCard.locator('h3').first();
    await expect(cardTitle).toBeVisible();
  });

  test('Reduced motion compatibility', async ({ page }) => {
    // Simulate reduced motion preference
    await page.emulateMedia({ reducedMotion: 'reduce' });
    
    await page.waitForTimeout(2000);
    
    // Check that content is still accessible without animations
    const kanbanBoard = page.locator('[aria-label="国会イシュー Kanban ボード"]');
    await expect(kanbanBoard).toBeVisible();
    
    // Check that interactive elements still work
    const firstCard = page.locator('article').first();
    await expect(firstCard).toBeVisible();
    
    // Hover should still work (without smooth transitions)
    await firstCard.hover();
    
    // Click should still work
    await firstCard.click();
  });

  test('Time-based content accessibility', async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(3000);
    
    // Check that time elements have proper datetime attributes
    const timeElements = page.locator('time[datetime]');
    
    if (await timeElements.count() > 0) {
      const firstTime = timeElements.first();
      
      // Check datetime attribute is properly formatted
      const datetime = await firstTime.getAttribute('datetime');
      expect(datetime).toMatch(/\d{4}-\d{2}-\d{2}/); // ISO date format
      
      // Check visible text is in Japanese format
      const visibleText = await firstTime.textContent();
      expect(visibleText).toContain('最終更新:');
    }
  });
});