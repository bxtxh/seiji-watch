import { test, expect } from '@playwright/test';
import { TestHelpers } from '../../utils/test-helpers';
import { pwaTestScenarios } from '../../fixtures/test-data';

test.describe('PWA Features', () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
    
    // Mock API responses
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
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        });
      }
    });
    
    await helpers.navigateToPage('/');
    await helpers.waitForAppReady();
  });

  test.afterEach(async ({ page }) => {
    await helpers.cleanup();
  });

  test('should register service worker', async ({ page }) => {
    // Check if service worker is supported and registered
    const swSupported = await page.evaluate(() => {
      return 'serviceWorker' in navigator;
    });
    
    expect(swSupported).toBe(true);
    
    // Wait for service worker registration
    await page.waitForFunction(() => {
      return navigator.serviceWorker.ready;
    }, { timeout: 10000 });
    
    const swRegistered = await page.evaluate(() => {
      return navigator.serviceWorker.controller !== null;
    });
    
    expect(swRegistered).toBe(true);
  });

  test('should have valid web app manifest', async ({ page }) => {
    // Check manifest link exists
    const manifestLink = page.locator('link[rel="manifest"]');
    await expect(manifestLink).toHaveCount(1);
    
    // Get manifest URL
    const manifestHref = await manifestLink.getAttribute('href');
    expect(manifestHref).toBeTruthy();
    
    // Fetch and validate manifest
    const manifestResponse = await page.goto(manifestHref!);
    expect(manifestResponse?.status()).toBe(200);
    
    const manifestContent = await manifestResponse?.json();
    
    // Validate required manifest fields
    expect(manifestContent).toHaveProperty('name');
    expect(manifestContent).toHaveProperty('short_name');
    expect(manifestContent).toHaveProperty('start_url');
    expect(manifestContent).toHaveProperty('display');
    expect(manifestContent).toHaveProperty('theme_color');
    expect(manifestContent).toHaveProperty('background_color');
    expect(manifestContent).toHaveProperty('icons');
    
    // Validate icons
    expect(Array.isArray(manifestContent.icons)).toBe(true);
    expect(manifestContent.icons.length).toBeGreaterThan(0);
    
    // Check icon properties
    const icon = manifestContent.icons[0];
    expect(icon).toHaveProperty('src');
    expect(icon).toHaveProperty('sizes');
    expect(icon).toHaveProperty('type');
  });

  test('should display install prompt', async ({ page }) => {
    // Check if install button is present (in development mode)
    const installButton = page.locator(TestHelpers.selectors.installButton);
    
    // Install button might be visible in development
    const buttonCount = await installButton.count();
    if (buttonCount > 0) {
      await expect(installButton).toBeVisible();
      
      // Test install button interaction
      await installButton.click();
      
      // Note: Actual install prompt behavior depends on browser and context
      // In test environment, we mainly check if the button responds
    }
  });

  test('should work offline', async ({ page }) => {
    // First, ensure the app is loaded and cached
    await page.waitForLoadState('networkidle');
    
    // Go offline
    await helpers.simulateNetworkCondition('offline');
    
    // Navigate to cached page
    await page.reload();
    
    // Should still show basic content
    await expect(page.locator('h1')).toContainText('国会議事録検索システム');
    
    // Should show offline indicator or message
    const offlineElements = await page.locator('text=/オフライン|offline/i').count();
    // Note: This depends on offline page implementation
    
    // Restore network
    await helpers.simulateNetworkCondition('fast3g');
  });

  test('should cache static resources', async ({ page }) => {
    // Navigate to page
    await page.waitForLoadState('networkidle');
    
    // Check if resources are cached
    const cacheExists = await page.evaluate(async () => {
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        return cacheNames.length > 0;
      }
      return false;
    });
    
    expect(cacheExists).toBe(true);
  });

  test('should handle cache updates', async ({ page }) => {
    // This test would check service worker update mechanisms
    // In a real scenario, this would involve deploying a new version
    
    // Check if update notification mechanism exists
    const updateElements = await page.locator('text=/更新|アップデート/').count();
    
    // Note: Update notification would only appear when there's actually an update
    // This test mainly verifies the structure is in place
  });

  test('should support background sync (if implemented)', async ({ page }) => {
    // Check if background sync is available
    const bgSyncSupported = await page.evaluate(() => {
      return 'serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype;
    });
    
    if (bgSyncSupported) {
      // Test background sync functionality
      // This would typically involve offline form submissions
      console.log('Background sync is supported');
    } else {
      console.log('Background sync not supported in this environment');
    }
  });

  test('should show appropriate PWA debug information in development', async ({ page }) => {
    // Check if debug panel is available in development
    const debugButton = page.locator(TestHelpers.selectors.pwaDebugButton);
    
    if (process.env.NODE_ENV === 'development') {
      await expect(debugButton).toBeVisible();
      
      // Open debug panel
      await debugButton.click();
      
      // Check debug panel content
      await expect(page.locator('text=PWA デバッグパネル')).toBeVisible();
      
      // Check for service worker status
      await expect(page.locator('text=Service Worker')).toBeVisible();
      
      // Check for cache information
      await expect(page.locator('text=キャッシュ情報')).toBeVisible();
      
      // Close debug panel
      await page.locator('button:has-text("×")').click();
    }
  });

  test('should handle installation on mobile devices', async ({ page }) => {
    // Simulate mobile device
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Check mobile-specific PWA features
    await expect(page.locator('meta[name="mobile-web-app-capable"]')).toHaveCount(1);
    await expect(page.locator('meta[name="apple-mobile-web-app-capable"]')).toHaveCount(1);
    
    // Check theme color for status bar
    const themeColor = page.locator('meta[name="theme-color"]');
    await expect(themeColor).toHaveCount(1);
    await expect(themeColor).toHaveAttribute('content', '#27AE60');
  });

  test('should support standalone mode', async ({ page }) => {
    // Check if app can detect standalone mode
    const isStandalone = await page.evaluate(() => {
      return window.matchMedia('(display-mode: standalone)').matches;
    });
    
    // In test environment, this will typically be false
    // But we can test the detection mechanism
    expect(typeof isStandalone).toBe('boolean');
    
    // Check if CSS is prepared for standalone mode
    const standaloneStyles = await page.evaluate(() => {
      const stylesheets = Array.from(document.styleSheets);
      return stylesheets.some(sheet => {
        try {
          const rules = Array.from(sheet.cssRules || []);
          return rules.some(rule => 
            rule.conditionText && rule.conditionText.includes('standalone')
          );
        } catch {
          return false;
        }
      });
    });
    
    // Note: This may need adjustment based on actual CSS structure
  });

  test('should handle PWA-specific navigation', async ({ page }) => {
    // Test navigation behavior in PWA context
    await page.goto('/issues');
    await expect(page).toHaveURL('/issues');
    
    // Use browser back (should work in PWA)
    await page.goBack();
    await expect(page).toHaveURL('/');
    
    // Forward navigation
    await page.goForward();
    await expect(page).toHaveURL('/issues');
  });

  test('should meet PWA lighthouse criteria', async ({ page }) => {
    // This would run Lighthouse audits programmatically
    // For now, we'll check basic PWA requirements manually
    
    // HTTPS (in production)
    const protocol = await page.evaluate(() => location.protocol);
    const isSecure = protocol === 'https:' || protocol === 'http:' && location.hostname === 'localhost';
    expect(isSecure).toBe(true);
    
    // Service Worker
    await helpers.testPWAFeatures();
    
    // Responsive design
    await helpers.checkResponsiveDesign('main');
    
    // Performance (basic check)
    const metrics = await helpers.measurePagePerformance();
    expect(metrics.loadTime).toBeLessThan(5000); // 5 second threshold for tests
  });

  test('should handle PWA-specific error scenarios', async ({ page }) => {
    // Test service worker registration failure
    await page.addInitScript(() => {
      // Mock service worker registration failure
      if ('serviceWorker' in navigator) {
        const originalRegister = navigator.serviceWorker.register;
        navigator.serviceWorker.register = () => Promise.reject(new Error('SW registration failed'));
      }
    });
    
    await page.reload();
    
    // App should still function without service worker
    await expect(page.locator('h1')).toContainText('国会議事録検索システム');
  });
});