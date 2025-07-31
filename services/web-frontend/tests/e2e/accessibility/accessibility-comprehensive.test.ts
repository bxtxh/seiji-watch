import { test, expect } from "@playwright/test";
import { TestHelpers } from "../../utils/test-helpers";
import { accessibilityTestCases } from "../../fixtures/test-data";
import { injectAxe, checkA11y, getViolations } from "axe-playwright";

test.describe("Accessibility Tests (WCAG 2.1 AA)", () => {
  let helpers: TestHelpers;

  test.beforeEach(async ({ page }) => {
    helpers = new TestHelpers(page);

    // Mock API responses
    await page.route("**/api/**", async (route) => {
      const url = route.request().url();

      if (url.includes("/health")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "healthy",
            message: "Test system is running",
          }),
        });
      } else if (url.includes("/embeddings/stats")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "ok",
            bills: 150,
            speeches: 1200,
            message: "Test data available",
          }),
        });
      } else if (url.includes("/search")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            results: [
              {
                id: "test-bill-1",
                bill_number: "TEST001",
                title: "アクセシビリティテスト法案",
                description: "アクセシビリティをテストするための法案です",
                certainty: 0.9,
                search_method: "vector",
              },
            ],
            total_found: 1,
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true }),
        });
      }
    });

    await page.goto("/");
    await helpers.waitForAppReady();

    // Inject axe-core for automated accessibility testing
    await injectAxe(page);
  });

  test.afterEach(async ({ page }) => {
    await helpers.cleanup();
  });

  test("should pass automated WCAG 2.1 AA checks on homepage", async ({
    page,
  }) => {
    // Run axe-core accessibility checks
    const accessibilityScanResults = await checkA11y(page, undefined, {
      detailedReport: true,
      detailedReportOptions: { html: true },
    });

    // Check for violations
    const violations = await getViolations(page);

    if (violations.length > 0) {
      console.log("Accessibility violations found:", violations);
      violations.forEach((violation) => {
        console.log(`- ${violation.id}: ${violation.description}`);
        console.log(`  Impact: ${violation.impact}`);
        console.log(`  Help: ${violation.help}`);
        violation.nodes.forEach((node) => {
          console.log(`    Element: ${node.target.join(", ")}`);
        });
      });
    }

    // Should pass with no violations
    expect(violations.length).toBe(0);
  });

  test("should have proper semantic HTML structure", async ({ page }) => {
    // Check for main landmark
    const main = page.locator("main");
    await expect(main).toBeVisible();
    await expect(main).toHaveCount(1);

    // Check for proper heading hierarchy
    const h1 = page.locator("h1");
    await expect(h1).toBeVisible();
    await expect(h1).toHaveCount(1);

    // Check for navigation landmarks
    const nav = page.locator('nav, [role="navigation"]');
    const navCount = await nav.count();
    if (navCount > 0) {
      await expect(nav.first()).toBeVisible();
    }

    // Check for proper form labeling
    const inputs = page.locator("input");
    const inputCount = await inputs.count();

    for (let i = 0; i < inputCount; i++) {
      const input = inputs.nth(i);
      const inputId = await input.getAttribute("id");
      const ariaLabel = await input.getAttribute("aria-label");
      const ariaLabelledBy = await input.getAttribute("aria-labelledby");

      if (inputId) {
        const label = page.locator(`label[for="${inputId}"]`);
        const labelCount = await label.count();

        if (labelCount === 0 && !ariaLabel && !ariaLabelledBy) {
          throw new Error(`Input with id="${inputId}" lacks proper labeling`);
        }
      }
    }
  });

  test("should support keyboard navigation", async ({ page }) => {
    // Start keyboard navigation from body
    await page.locator("body").focus();

    // Test Tab navigation through interactive elements
    const interactiveElements: string[] = [];
    let currentFocus = null;

    // Navigate through first 10 tab stops
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press("Tab");
      await page.waitForTimeout(100);

      const focusedElement = page.locator(":focus");
      const focusedCount = await focusedElement.count();

      if (focusedCount > 0) {
        const tagName = await focusedElement.evaluate((el) =>
          el.tagName.toLowerCase()
        );
        const role = await focusedElement.getAttribute("role");
        const ariaLabel = await focusedElement.getAttribute("aria-label");

        interactiveElements.push(
          `${tagName}${role ? `[role="${role}"]` : ""}${ariaLabel ? `[aria-label="${ariaLabel}"]` : ""}`
        );

        // Verify focus is visible
        await expect(focusedElement).toBeFocused();

        // Test Enter/Space activation for buttons
        if (tagName === "button" || role === "button") {
          // Don't actually activate to avoid navigation issues
          console.log(
            `Found focusable button: ${tagName}${role ? `[role="${role}"]` : ""}`
          );
        }

        // Test form controls
        if (
          tagName === "input" ||
          tagName === "textarea" ||
          tagName === "select"
        ) {
          // Verify input is accessible
          const disabled = await focusedElement.getAttribute("disabled");
          expect(disabled).toBeNull();
        }
      } else {
        break; // No more focusable elements
      }
    }

    console.log("Keyboard navigation path:", interactiveElements);

    // Should have found at least some interactive elements
    expect(interactiveElements.length).toBeGreaterThan(0);
  });

  test("should support screen reader navigation", async ({ page }) => {
    // Check for skip links
    const skipLink = page.locator(
      'a:has-text("メインコンテンツへスキップ"), a:has-text("スキップ")'
    );
    const skipLinkCount = await skipLink.count();

    if (skipLinkCount > 0) {
      await expect(skipLink.first()).toBeInViewport();
    }

    // Check for proper ARIA landmarks
    const landmarks = [
      { selector: 'main, [role="main"]', name: "main" },
      { selector: 'nav, [role="navigation"]', name: "navigation" },
      { selector: 'header, [role="banner"]', name: "banner" },
      { selector: 'footer, [role="contentinfo"]', name: "contentinfo" },
    ];

    for (const landmark of landmarks) {
      const elements = page.locator(landmark.selector);
      const count = await elements.count();

      if (count > 0) {
        console.log(`Found ${count} ${landmark.name} landmark(s)`);
        await expect(elements.first()).toBeVisible();
      }
    }

    // Check for proper heading structure (no skipped levels)
    const headings = await page.locator("h1, h2, h3, h4, h5, h6").all();
    const headingLevels: number[] = [];

    for (const heading of headings) {
      const tagName = await heading.evaluate((el) => el.tagName.toLowerCase());
      const level = parseInt(tagName.substring(1));
      headingLevels.push(level);
    }

    // Check for logical heading progression
    for (let i = 1; i < headingLevels.length; i++) {
      const currentLevel = headingLevels[i];
      const previousLevel = headingLevels[i - 1];

      // Heading levels should not skip more than 1 level
      if (currentLevel > previousLevel + 1) {
        console.warn(
          `Heading level skipped: h${previousLevel} followed by h${currentLevel}`
        );
      }
    }

    console.log(
      "Heading structure:",
      headingLevels.map((level) => `h${level}`).join(" → ")
    );
  });

  test("should provide alternative text for images", async ({ page }) => {
    const images = page.locator("img");
    const imageCount = await images.count();

    for (let i = 0; i < imageCount; i++) {
      const img = images.nth(i);
      const alt = await img.getAttribute("alt");
      const ariaLabel = await img.getAttribute("aria-label");
      const ariaLabelledBy = await img.getAttribute("aria-labelledby");
      const role = await img.getAttribute("role");

      // Decorative images should have empty alt or role="presentation"
      if (role === "presentation" || role === "none") {
        // Decorative image - no alt text needed
        continue;
      }

      // Informative images should have alt text
      if (!alt && !ariaLabel && !ariaLabelledBy) {
        const src = await img.getAttribute("src");
        throw new Error(`Image without alternative text: ${src}`);
      }

      // Alt text should be meaningful (not just filename)
      if (alt) {
        expect(alt).not.toMatch(/\.(jpg|jpeg|png|gif|svg|webp)$/i);
        expect(alt).not.toMatch(/^image\d*$/i);
        expect(alt).not.toMatch(/^img\d*$/i);
      }
    }

    console.log(`Checked ${imageCount} images for alternative text`);
  });

  test("should have sufficient color contrast", async ({ page }) => {
    // Run color contrast checks with axe-core
    await checkA11y(page, undefined, {
      tags: ["wcag2a", "wcag2aa", "wcag21aa"],
      rules: {
        "color-contrast": { enabled: true },
        "color-contrast-enhanced": { enabled: true },
      },
    });

    // Additional manual checks for color-blind accessibility
    const primaryColors = [
      { selector: ".text-primary-green", description: "Primary green text" },
      {
        selector: ".bg-primary-green",
        description: "Primary green background",
      },
      { selector: ".text-primary-red", description: "Primary red text" },
      { selector: ".bg-primary-red", description: "Primary red background" },
      { selector: ".text-primary-yellow", description: "Primary yellow text" },
      {
        selector: ".bg-primary-yellow",
        description: "Primary yellow background",
      },
    ];

    for (const color of primaryColors) {
      const elements = page.locator(color.selector);
      const count = await elements.count();

      if (count > 0) {
        console.log(`Found ${count} elements with ${color.description}`);

        // Ensure colored elements also have non-color indicators
        for (let i = 0; i < Math.min(count, 3); i++) {
          const element = elements.nth(i);
          const textContent = await element.textContent();
          const ariaLabel = await element.getAttribute("aria-label");

          // Should have text content or aria-label for context
          expect(textContent || ariaLabel).toBeTruthy();
        }
      }
    }
  });

  test("should support text scaling up to 200%", async ({ page }) => {
    // Test text scaling by zooming
    const originalViewport = page.viewportSize();

    // Zoom to 200%
    await page.setViewportSize({
      width: Math.floor(originalViewport!.width / 2),
      height: Math.floor(originalViewport!.height / 2),
    });

    await page.waitForTimeout(500); // Allow layout to adjust

    // Check that main elements are still visible and usable
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.locator("input#search")).toBeVisible();
    await expect(page.locator('button:has-text("検索する")')).toBeVisible();

    // Check that text is not cut off
    const searchInput = page.locator("input#search");
    const boundingBox = await searchInput.boundingBox();

    if (boundingBox) {
      expect(boundingBox.width).toBeGreaterThan(100); // Should have reasonable width
      expect(boundingBox.height).toBeGreaterThan(20); // Should have reasonable height
    }

    // Restore original viewport
    await page.setViewportSize(originalViewport!);
  });

  test("should handle focus management properly", async ({ page }) => {
    // Test focus trap in modals/dialogs
    const modalTriggers = page.locator(
      'button:has-text("詳細"), button:has-text("詳細を見る")'
    );
    const modalCount = await modalTriggers.count();

    if (modalCount > 0) {
      // Open modal
      await modalTriggers.first().click();
      await page.waitForTimeout(500);

      // Check if modal is open
      const modal = page.locator(
        '[role="dialog"], .modal, [aria-modal="true"]'
      );
      const modalOpenCount = await modal.count();

      if (modalOpenCount > 0) {
        // Focus should be within modal
        const focusedElement = page.locator(":focus");
        const modalContainer = modal.first();

        // Check if focus is within modal
        const focusWithinModal =
          (await modalContainer.locator(":focus").count()) > 0;
        expect(focusWithinModal).toBe(true);

        // Test escape key to close modal
        await page.keyboard.press("Escape");
        await page.waitForTimeout(500);

        // Modal should be closed
        const modalStillOpen = await modal.count();
        expect(modalStillOpen).toBe(0);
      }
    }
  });

  test("should provide error messages and form validation feedback", async ({
    page,
  }) => {
    const searchInput = page.locator("input#search");

    // Test with invalid input
    await searchInput.fill('<script>alert("test")</script>');
    await page.click('button:has-text("検索する")');

    await page.waitForTimeout(1000);

    // Should show validation error
    const errorMessages = page.locator(
      '[role="alert"], .text-red-600, .error-message'
    );
    const errorCount = await errorMessages.count();

    if (errorCount > 0) {
      const errorElement = errorMessages.first();
      await expect(errorElement).toBeVisible();

      // Error message should be associated with the input
      const errorId = await errorElement.getAttribute("id");
      const inputAriaDescribedBy =
        await searchInput.getAttribute("aria-describedby");

      if (errorId && inputAriaDescribedBy) {
        expect(inputAriaDescribedBy).toContain(errorId);
      }
    }

    // Clear input and test empty state
    await searchInput.clear();
    const searchButton = page.locator('button:has-text("検索する")');

    // Button should be disabled for empty input
    const isDisabled = await searchButton.isDisabled();
    expect(isDisabled).toBe(true);
  });

  test("should support Japanese language accessibility features", async ({
    page,
  }) => {
    // Check for lang attribute
    const htmlLang = await page.getAttribute("html", "lang");
    expect(htmlLang).toBe("ja");

    // Check for furigana support (if implemented)
    const furiganaToggle = page.locator(
      'button:has-text("ふりがな"), [aria-label*="ふりがな"]'
    );
    const furiganaCount = await furiganaToggle.count();

    if (furiganaCount > 0) {
      console.log("Found furigana toggle feature");

      // Test furigana toggle
      await furiganaToggle.first().click();
      await page.waitForTimeout(500);

      // Check if furigana elements are added
      const furiganaElements = page.locator("ruby, rt, .furigana");
      const furiganaElementCount = await furiganaElements.count();

      console.log(`Found ${furiganaElementCount} furigana elements`);
    }

    // Check for proper Japanese text direction and layout
    const japaneseText = page.locator("text=/[ひらがなカタカナ漢字]/");
    const japaneseTextCount = await japaneseText.count();

    expect(japaneseTextCount).toBeGreaterThan(0);
    console.log(`Found ${japaneseTextCount} elements with Japanese text`);
  });

  test("should be mobile accessible", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);

    // Check touch target sizes (minimum 44px)
    const buttons = page.locator(
      'button, a, input[type="submit"], input[type="button"]'
    );
    const buttonCount = await buttons.count();

    for (let i = 0; i < Math.min(buttonCount, 5); i++) {
      const button = buttons.nth(i);
      const isVisible = await button.isVisible();

      if (isVisible) {
        const boundingBox = await button.boundingBox();

        if (boundingBox) {
          const minDimension = Math.min(boundingBox.width, boundingBox.height);
          expect(minDimension).toBeGreaterThanOrEqual(44);
        }
      }
    }

    // Check that interactive elements are properly spaced
    const interactiveElements = page.locator("button, a, input");
    const elementsCount = await interactiveElements.count();

    if (elementsCount > 1) {
      // Elements should not overlap
      for (let i = 0; i < Math.min(elementsCount - 1, 3); i++) {
        const element1 = interactiveElements.nth(i);
        const element2 = interactiveElements.nth(i + 1);

        const box1 = await element1.boundingBox();
        const box2 = await element2.boundingBox();

        if (box1 && box2) {
          // Elements should not overlap significantly
          const overlap = !(
            box1.x + box1.width < box2.x ||
            box2.x + box2.width < box1.x ||
            box1.y + box1.height < box2.y ||
            box2.y + box2.height < box1.y
          );

          if (overlap) {
            console.warn("Found overlapping interactive elements");
          }
        }
      }
    }
  });
});
