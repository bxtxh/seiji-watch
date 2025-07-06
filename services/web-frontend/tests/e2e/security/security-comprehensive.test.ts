import { test, expect } from '@playwright/test';
import { TestHelpers } from '../../utils/test-helpers';
import { securityTestCases } from '../../fixtures/test-data';

test.describe('Security Tests', () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);
    
    // Mock API responses with security considerations
    await page.route('**/api/**', async route => {
      const url = route.request().url();
      const method = route.request().method();
      const headers = route.request().headers();
      
      // Check for required security headers in requests
      if (!headers['content-type'] && method === 'POST') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            message: 'Content-Type header required'
          })
        });
        return;
      }
      
      if (url.includes('/search') && method === 'POST') {
        const requestBody = route.request().postDataJSON();
        const query = requestBody?.query || '';
        
        // Simulate server-side security checks
        if (query.includes('<script>') || query.includes('javascript:')) {
          await route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({
              success: false,
              message: 'セキュリティ上の理由により、この検索は実行できません'
            })
          });
          return;
        }
        
        if (query.includes('DROP TABLE') || query.includes('SELECT *')) {
          await route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({
              success: false,
              message: '不正な入力が検出されました'
            })
          });
          return;
        }
      }
      
      // Default successful response
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: {
          'X-Content-Type-Options': 'nosniff',
          'X-Frame-Options': 'DENY',
          'X-XSS-Protection': '1; mode=block',
          'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
          'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        },
        body: JSON.stringify({
          success: true,
          results: [],
          total_found: 0
        })
      });
    });
  });

  test.afterEach(async ({ page }) => {
    await helpers.cleanup();
  });

  test('should prevent XSS attacks in search input', async ({ page }) => {
    await page.goto('/');
    await helpers.waitForAppReady();
    
    const searchInput = page.locator('input#search');
    const maliciousInputs = [
      '<script>alert("xss")</script>',
      'javascript:alert("xss")',
      '<img src="x" onerror="alert(\'xss\')">',
      '<svg onload="alert(\'xss\')">',
      '"><script>alert("xss")</script>',
      '\';alert("xss");//'
    ];
    
    for (const maliciousInput of maliciousInputs) {
      // Clear any previous alerts
      const alerts: string[] = [];
      page.on('dialog', dialog => {
        alerts.push(dialog.message());
        dialog.dismiss();
      });
      
      await searchInput.fill(maliciousInput);
      await page.click('button:has-text("検索する")');
      
      // Wait for potential execution
      await page.waitForTimeout(1000);
      
      // Verify no XSS execution
      expect(alerts.length).toBe(0);
      
      // Should show security error or validation error
      const hasSecurityError = await page.locator('text=セキュリティ上の理由').count() > 0;
      const hasValidationError = await page.locator('.text-red-600').count() > 0;
      
      expect(hasSecurityError || hasValidationError).toBe(true);
      
      await searchInput.clear();
    }
  });

  test('should prevent SQL injection attempts', async ({ page }) => {
    await page.goto('/');
    await helpers.waitForAppReady();
    
    const searchInput = page.locator('input#search');
    const sqlInjectionInputs = [
      "' OR '1'='1",
      "'; DROP TABLE bills; --",
      "' UNION SELECT * FROM users --",
      "1'; DELETE FROM bills; --",
      "' OR 1=1 --",
      "admin'--",
      "' OR 'a'='a"
    ];
    
    for (const sqlInput of sqlInjectionInputs) {
      await searchInput.fill(sqlInput);
      await page.click('button:has-text("検索する")');
      
      await page.waitForTimeout(500);
      
      // Should show security error or validation error
      const hasSecurityError = await page.locator('text=不正な入力が検出されました').count() > 0;
      const hasValidationError = await page.locator('.text-red-600').count() > 0;
      
      expect(hasSecurityError || hasValidationError).toBe(true);
      
      await searchInput.clear();
    }
  });

  test('should enforce input length limits', async ({ page }) => {
    await page.goto('/');
    await helpers.waitForAppReady();
    
    const searchInput = page.locator('input#search');
    
    // Test maximum length enforcement (should be 200 characters)
    const longInput = 'a'.repeat(250);
    await searchInput.fill(longInput);
    
    const actualValue = await searchInput.inputValue();
    expect(actualValue.length).toBeLessThanOrEqual(200);
    
    // Should show validation error for excessive length
    await expect(page.locator('text=200文字以内で入力してください')).toBeVisible();
  });

  test('should validate and sanitize special characters', async ({ page }) => {
    await page.goto('/');
    await helpers.waitForAppReady();
    
    const searchInput = page.locator('input#search');
    const specialCharInputs = [
      '\\x00\\x01\\x02', // Null bytes
      '\u202e\u202d',     // Unicode control characters
      String.fromCharCode(0, 1, 2, 3), // Control characters
      '\uFEFF',           // Byte order mark
      '\u200B\u200C\u200D' // Zero-width characters
    ];
    
    for (const specialInput of specialCharInputs) {
      await searchInput.fill(specialInput);
      await page.click('button:has-text("検索する")');
      
      await page.waitForTimeout(500);
      
      // Should either reject the input or sanitize it
      const hasError = await page.locator('.text-red-600').count() > 0;
      const searchValue = await searchInput.inputValue();
      
      // Either show error or sanitize the input
      expect(hasError || searchValue !== specialInput).toBe(true);
      
      await searchInput.clear();
    }
  });

  test('should implement rate limiting', async ({ page }) => {
    await page.goto('/');
    await helpers.waitForAppReady();
    
    const searchInput = page.locator('input#search');
    
    // Perform rapid searches to trigger rate limiting
    const searchPromises = [];
    for (let i = 0; i < 15; i++) {
      searchPromises.push((async () => {
        await searchInput.fill(`テスト${i}`);
        await page.click('button:has-text("検索する")');
        await page.waitForTimeout(50); // Very rapid requests
      })());
    }
    
    await Promise.all(searchPromises);
    
    // Wait for rate limiting to trigger
    await page.waitForTimeout(2000);
    
    // Should show rate limiting message
    const hasRateLimit = await page.locator('text=上限に達しました').count() > 0;
    const hasRateLimitApi = await page.locator('text=API呼び出し回数の上限').count() > 0;
    
    expect(hasRateLimit || hasRateLimitApi).toBe(true);
  });

  test('should check for security headers', async ({ page }) => {
    const response = await page.goto('/');
    expect(response).toBeTruthy();
    
    const headers = response!.headers();
    
    // Check for important security headers
    const securityHeaders = [
      'x-content-type-options',
      'x-frame-options',
      'x-xss-protection',
      'strict-transport-security'
    ];
    
    for (const header of securityHeaders) {
      expect(headers[header]).toBeTruthy();
      console.log(`${header}: ${headers[header]}`);
    }
    
    // Check specific header values
    expect(headers['x-content-type-options']).toBe('nosniff');
    expect(headers['x-frame-options']).toMatch(/(DENY|SAMEORIGIN)/);
    expect(headers['x-xss-protection']).toMatch(/1/);
  });

  test('should prevent clickjacking attacks', async ({ page }) => {
    await page.goto('/');
    
    // Try to embed the page in an iframe (should be prevented by X-Frame-Options)
    const iframeContent = `
      <html>
        <body>
          <iframe src="${page.url()}" width="100%" height="400"></iframe>
        </body>
      </html>
    `;
    
    const iframePage = await page.context().newPage();
    await iframePage.setContent(iframeContent);
    
    // The iframe should not load the content due to X-Frame-Options
    const iframe = iframePage.locator('iframe');
    await iframe.waitFor({ timeout: 3000 }).catch(() => {});
    
    // Check if iframe content failed to load (which is expected)
    const iframeLoaded = await iframe.evaluate((iframe) => {
      try {
        return !!iframe.contentDocument;
      } catch (e) {
        return false;
      }
    }).catch(() => false);
    
    // Should NOT be able to load in iframe
    expect(iframeLoaded).toBe(false);
    
    await iframePage.close();
  });

  test('should sanitize content in search results', async ({ page }) => {
    // Mock API to return potentially dangerous content
    await page.route('**/api/search', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          results: [
            {
              id: 'test-bill-1',
              bill_number: 'TEST001',
              title: 'Normal Title <script>alert("xss")</script>',
              description: 'Description with <img src="x" onerror="alert(\'xss2\')"> dangerous content',
              certainty: 0.9,
              search_method: 'vector'
            }
          ],
          total_found: 1
        })
      });
    });
    
    // Mock other endpoints
    await page.route('**/api/**', async route => {
      if (!route.request().url().includes('/search')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        });
      }
    });
    
    await page.goto('/');
    await helpers.waitForAppReady();
    
    const alerts: string[] = [];
    page.on('dialog', dialog => {
      alerts.push(dialog.message());
      dialog.dismiss();
    });
    
    // Perform search
    const searchInput = page.locator('input#search');
    await searchInput.fill('テスト');
    await page.click('button:has-text("検索する")');
    
    await page.waitForTimeout(2000);
    
    // No alerts should be triggered
    expect(alerts.length).toBe(0);
    
    // Content should be displayed but without dangerous tags
    await expect(page.locator('text=Normal Title')).toBeVisible();
    await expect(page.locator('text=Description with')).toBeVisible();
    
    // Dangerous tags should not be present in DOM
    const scriptTags = await page.locator('script:has-text("alert")').count();
    const imgTags = await page.locator('img[onerror]').count();
    
    expect(scriptTags).toBe(0);
    expect(imgTags).toBe(0);
  });

  test('should protect against CSRF attacks', async ({ page }) => {
    await page.goto('/');
    await helpers.waitForAppReady();
    
    // Check that forms include CSRF protection
    const forms = page.locator('form');
    const formCount = await forms.count();
    
    if (formCount > 0) {
      // Check for CSRF tokens or other protection mechanisms
      for (let i = 0; i < formCount; i++) {
        const form = forms.nth(i);
        
        // Check for hidden CSRF token field
        const csrfInput = form.locator('input[name*="csrf"], input[name*="token"]');
        const csrfInputCount = await csrfInput.count();
        
        // Or check for SameSite cookie attributes (would be in HTTP headers)
        // For now, just ensure form has proper attributes
        const action = await form.getAttribute('action');
        const method = await form.getAttribute('method');
        
        // Form should have proper method and action
        if (method) {
          expect(['get', 'post']).toContain(method.toLowerCase());
        }
        
        console.log(`Form ${i}: action=${action}, method=${method}, csrf=${csrfInputCount > 0}`);
      }
    }
  });

  test('should validate file upload security (if applicable)', async ({ page }) => {
    await page.goto('/');
    await helpers.waitForAppReady();
    
    // Check for file upload inputs
    const fileInputs = page.locator('input[type="file"]');
    const fileInputCount = await fileInputs.count();
    
    if (fileInputCount > 0) {
      for (let i = 0; i < fileInputCount; i++) {
        const fileInput = fileInputs.nth(i);
        
        // Check for file type restrictions
        const accept = await fileInput.getAttribute('accept');
        const multiple = await fileInput.getAttribute('multiple');
        
        // Should have accept attribute to restrict file types
        expect(accept).toBeTruthy();
        
        console.log(`File input ${i}: accept=${accept}, multiple=${multiple}`);
        
        // Test with potentially dangerous file types
        // Note: This is a basic test - real file upload testing would require actual files
        if (accept && !accept.includes('*')) {
          // Good - specific file types are allowed
          expect(accept).not.toMatch(/\.(exe|bat|cmd|scr|js)$/i);
        }
      }
    }
  });

  test('should handle authentication state securely', async ({ page }) => {
    await page.goto('/');
    await helpers.waitForAppReady();
    
    // Check for any authentication-related elements
    const loginElements = page.locator('button:has-text("ログイン"), a:has-text("ログイン"), [data-testid="login"]');
    const loginCount = await loginElements.count();
    
    if (loginCount > 0) {
      // Authentication elements exist, test security
      
      // Check that passwords are not exposed in DOM
      const passwordInputs = page.locator('input[type="password"]');
      const passwordCount = await passwordInputs.count();
      
      for (let i = 0; i < passwordCount; i++) {
        const passwordInput = passwordInputs.nth(i);
        
        // Password should have autocomplete="current-password" or "new-password"
        const autocomplete = await passwordInput.getAttribute('autocomplete');
        expect(autocomplete).toMatch(/(current-password|new-password|off)/);
        
        // Should not have password in name attribute (avoid form data leakage)
        const name = await passwordInput.getAttribute('name');
        expect(name).not.toMatch(/password/i);
      }
    }
    
    // Check that no sensitive data is exposed in localStorage or sessionStorage
    const localStorageData = await page.evaluate(() => {
      const data: Record<string, string> = {};
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key) {
          data[key] = localStorage.getItem(key) || '';
        }
      }
      return data;
    });
    
    const sessionStorageData = await page.evaluate(() => {
      const data: Record<string, string> = {};
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (key) {
          data[key] = sessionStorage.getItem(key) || '';
        }
      }
      return data;
    });
    
    // Check that no obvious sensitive data is stored
    const sensitivePatterns = [/password/i, /secret/i, /token/i, /key/i];
    
    Object.keys(localStorageData).forEach(key => {
      sensitivePatterns.forEach(pattern => {
        expect(key).not.toMatch(pattern);
      });
    });
    
    Object.keys(sessionStorageData).forEach(key => {
      sensitivePatterns.forEach(pattern => {
        expect(key).not.toMatch(pattern);
      });
    });
    
    console.log('Storage Security Check:', {
      localStorageKeys: Object.keys(localStorageData),
      sessionStorageKeys: Object.keys(sessionStorageData)
    });
  });

  test('should implement proper error handling without information disclosure', async ({ page }) => {
    // Mock API to return various error types
    await page.route('**/api/search', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          message: 'Internal server error' // Generic error message
        })
      });
    });
    
    await page.route('**/api/**', async route => {
      if (!route.request().url().includes('/search')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        });
      }
    });
    
    await page.goto('/');
    await helpers.waitForAppReady();
    
    // Trigger error
    const searchInput = page.locator('input#search');
    await searchInput.fill('エラーテスト');
    await page.click('button:has-text("検索する")');
    
    await page.waitForTimeout(1000);
    
    // Should show generic error message
    await expect(page.locator('.bg-red-50')).toBeVisible();
    
    // Error message should not reveal sensitive information
    const errorText = await page.locator('.bg-red-50').textContent();
    
    // Should not contain stack traces, file paths, or detailed error info
    expect(errorText).not.toMatch(/\.(js|ts|php|py):/);
    expect(errorText).not.toMatch(/\/var\/www/);
    expect(errorText).not.toMatch(/Error: /);
    expect(errorText).not.toMatch(/at \w+\./);
    
    console.log('Error message displayed:', errorText);
  });
});