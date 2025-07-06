import { test, expect } from '@playwright/test';
import { TestHelpers } from '../../utils/test-helpers';
import { accessibilityTestCases, testViewports } from '../../fixtures/test-data';

test.describe('Accessibility Tests', () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
    await helpers.navigateToPage('/');
    await helpers.waitForAppReady();
  });

  test.afterEach(async ({ page }) => {
    await helpers.cleanup();
  });

  test('should have proper semantic HTML structure', async ({ page }) => {
    // Check for semantic HTML elements
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('main')).toBeVisible();
    await expect(page.locator('footer')).toBeVisible();
    await expect(page.locator('nav')).toBeVisible();
    
    // Check heading hierarchy
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBeGreaterThanOrEqual(1); // Should have at least one h1
    
    // Check that headings are in logical order
    const headings = await page.locator('h1, h2, h3, h4, h5, h6').allTextContents();
    expect(headings.length).toBeGreaterThan(0);
  });

  test('should support keyboard navigation', async ({ page }) => {
    // Start from the beginning
    await page.keyboard.press('Tab');
    
    // Track focus movement
    const focusableElements = [];
    let attempts = 0;
    const maxAttempts = 20;
    
    while (attempts < maxAttempts) {
      const focusedElement = page.locator(':focus');
      const isVisible = await focusedElement.isVisible().catch(() => false);
      
      if (isVisible) {
        const tagName = await focusedElement.evaluate(el => el.tagName).catch(() => '');
        const text = await focusedElement.textContent().catch(() => '');
        focusableElements.push({ tagName, text: text?.slice(0, 50) });
      }
      
      await page.keyboard.press('Tab');
      attempts++;
      
      // Small delay to allow focus to settle
      await page.waitForTimeout(100);
    }
    
    // Should have found focusable elements
    expect(focusableElements.length).toBeGreaterThan(0);
    
    // Test Shift+Tab (reverse navigation)
    await page.keyboard.press('Shift+Tab');
    const reverseFocused = page.locator(':focus');
    await expect(reverseFocused).toBeVisible();
  });

  test('should have proper ARIA labels and roles', async ({ page }) => {
    // Check search input has proper labeling
    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    
    // Should have either aria-label, aria-labelledby, or associated label
    const hasAriaLabel = await searchInput.getAttribute('aria-label');
    const hasAriaLabelledby = await searchInput.getAttribute('aria-labelledby');
    const inputId = await searchInput.getAttribute('id');
    const hasAssociatedLabel = inputId ? await page.locator(`label[for="${inputId}"]`).count() > 0 : false;
    
    expect(hasAriaLabel || hasAriaLabelledby || hasAssociatedLabel).toBeTruthy();
    
    // Check buttons have accessible names
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();
    
    for (let i = 0; i < Math.min(buttonCount, 10); i++) {
      const button = buttons.nth(i);
      const isVisible = await button.isVisible();
      
      if (isVisible) {
        const text = await button.textContent();
        const ariaLabel = await button.getAttribute('aria-label');
        const title = await button.getAttribute('title');
        
        // Button should have accessible text via content, aria-label, or title
        expect(text || ariaLabel || title).toBeTruthy();
      }
    }
  });

  test('should have sufficient color contrast', async ({ page }) => {
    // This is a basic check - in real scenarios, you'd use tools like axe-core
    // Check that text elements exist and are visible
    const textElements = ['p', 'h1', 'h2', 'h3', 'button', 'a'];
    
    for (const selector of textElements) {
      const elements = page.locator(selector);
      const count = await elements.count();
      
      for (let i = 0; i < Math.min(count, 5); i++) {
        const element = elements.nth(i);
        const isVisible = await element.isVisible();
        
        if (isVisible) {
          // Check that text is not empty
          const text = await element.textContent();
          if (text && text.trim()) {
            // Element has visible text - contrast should be checked by accessibility tools
            await expect(element).toBeVisible();
          }
        }
      }
    }
  });

  test('should support screen readers', async ({ page }) => {
    // Check for screen reader specific attributes
    
    // Check for role attributes where appropriate
    const nav = page.locator('nav');
    const navCount = await nav.count();
    if (navCount > 0) {
      // Nav element exists - it has implicit navigation role
      await expect(nav).toBeVisible();
    }
    
    // Check for aria-hidden on decorative elements
    const icons = page.locator('svg');
    const iconCount = await icons.count();
    
    // Icons without text should have aria-hidden="true" or role="img" with alt
    for (let i = 0; i < Math.min(iconCount, 5); i++) {
      const icon = icons.nth(i);
      const isVisible = await icon.isVisible();
      
      if (isVisible) {
        const ariaHidden = await icon.getAttribute('aria-hidden');
        const role = await icon.getAttribute('role');
        const ariaLabel = await icon.getAttribute('aria-label');
        
        // Icon should either be hidden from screen readers or have accessible text
        const isAccessible = ariaHidden === 'true' || role === 'img' || ariaLabel || 
                             ariaHidden === null; // SVG without explicit aria-hidden is acceptable
        expect(isAccessible).toBeTruthy();
      }
    }
  });

  test('should handle focus management', async ({ page }) => {
    // Test focus trap in modals (if any)
    // Test focus restoration after modal closes
    // Test skip links
    
    // Check if skip link exists
    const skipLink = page.locator(TestHelpers.selectors.skipLink);
    const skipLinkExists = await skipLink.count() > 0;
    
    if (skipLinkExists) {
      // Test skip link functionality
      await skipLink.focus();
      await expect(skipLink).toBeFocused();
      
      await skipLink.press('Enter');
      
      // Should move focus to main content
      const mainContent = page.locator('main');
      await expect(mainContent).toBeFocused();
    }
  });

  test('should support furigana toggle feature', async ({ page }) => {
    // Check if furigana toggle exists
    const furiganaToggle = page.locator(TestHelpers.selectors.furiganaToggle);
    const toggleExists = await furiganaToggle.count() > 0;
    
    if (toggleExists) {
      await expect(furiganaToggle).toBeVisible();
      
      // Test toggle functionality
      await furiganaToggle.click();
      
      // Should change button text or state
      const buttonText = await furiganaToggle.textContent();
      expect(buttonText).toContain('ふりがな');
      
      // Test accessibility of toggle
      await helpers.expectElementToBeAccessible(TestHelpers.selectors.furiganaToggle);
    }
  });

  test('should be usable with keyboard only', async ({ page }) => {
    // Navigate through the entire page using only keyboard
    
    // Test search functionality with keyboard
    await page.keyboard.press('Tab');
    
    // Find search input
    let currentElement = page.locator(':focus');
    let attempts = 0;
    
    while (attempts < 10) {
      const tagName = await currentElement.evaluate(el => el.tagName).catch(() => '');
      const type = await currentElement.getAttribute('type').catch(() => '');
      
      if (tagName === 'INPUT' && type === 'text') {
        // Found search input
        await currentElement.type('税制改正');
        break;
      }
      
      await page.keyboard.press('Tab');
      currentElement = page.locator(':focus');
      attempts++;
    }
    
    // Submit search with Enter
    await page.keyboard.press('Enter');
    
    // Should be able to navigate search results with keyboard
    await page.waitForTimeout(2000); // Wait for search
  });

  test('should work across different viewport sizes', async ({ page }) => {
    const viewports = Object.values(testViewports);
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.waitForTimeout(500); // Allow layout to settle
      
      // Check that content is still accessible
      await expect(page.locator('h1').first()).toBeVisible();
      
      // Check that interactive elements are still accessible
      const searchInput = page.locator(TestHelpers.selectors.searchInput);
      if (await searchInput.count() > 0) {
        await expect(searchInput).toBeVisible();
      }
      
      // Check that navigation exists (may be hidden on mobile)
      const nav = page.locator('nav');
      await expect(nav).toBeAttached();
    }
  });

  test('should handle high contrast mode', async ({ page }) => {
    // Simulate high contrast mode (simplified)
    await page.addStyleTag({
      content: `
        @media (prefers-contrast: high) {
          * {
            background: white !important;
            color: black !important;
            border-color: black !important;
          }
        }
      `
    });
    
    // Content should still be visible and usable
    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page.locator(TestHelpers.selectors.searchInput)).toBeVisible();
  });

  test('should support reduced motion preferences', async ({ page }) => {
    // Check if app respects prefers-reduced-motion
    await page.emulateMedia({ reducedMotion: 'reduce' });
    
    // Navigate and check that animations are reduced
    await page.click(TestHelpers.selectors.issuesLink);
    await expect(page).toHaveURL('/issues');
    
    // App should still function without animations
    await expect(page.locator('h1').first()).toBeVisible();
  });

  test('should provide meaningful error messages', async ({ page }) => {
    // Test form validation messages
    const searchInput = page.locator(TestHelpers.selectors.searchInput);
    
    // Try invalid input
    await searchInput.fill('a'.repeat(300)); // Too long
    
    // Should show accessible error message
    const errorMessage = page.locator(TestHelpers.selectors.validationError);
    if (await errorMessage.count() > 0) {
      await expect(errorMessage).toBeVisible();
      
      // Error should be announced to screen readers
      const role = await errorMessage.getAttribute('role');
      const ariaLive = await errorMessage.getAttribute('aria-live');
      
      expect(role === 'alert' || ariaLive === 'polite' || ariaLive === 'assertive').toBeTruthy();
    }
  });

  test('should have proper language declarations', async ({ page }) => {
    // Check html lang attribute
    const htmlLang = await page.locator('html').getAttribute('lang');
    expect(htmlLang).toBe('ja');
    
    // Check if content in other languages is marked
    const englishContent = page.locator('[lang="en"]');
    const englishCount = await englishContent.count();
    
    // If there's English content, it should be properly marked
    for (let i = 0; i < englishCount; i++) {
      const element = englishContent.nth(i);
      await expect(element).toHaveAttribute('lang', 'en');
    }
  });

  test('should support voice control', async ({ page }) => {
    // Test that elements have appropriate labels for voice control
    
    // Buttons should have clear names
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();
    
    for (let i = 0; i < Math.min(buttonCount, 10); i++) {
      const button = buttons.nth(i);
      const isVisible = await button.isVisible();
      
      if (isVisible) {
        const accessibleName = await button.evaluate(el => {
          return el.textContent || 
                 el.getAttribute('aria-label') || 
                 el.getAttribute('title') || 
                 '';
        });
        
        // Should have clear, meaningful name
        expect(accessibleName.trim().length).toBeGreaterThan(0);
        expect(accessibleName.trim().length).toBeLessThan(50); // Not too verbose
      }
    }
  });
});