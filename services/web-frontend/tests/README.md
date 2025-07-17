# E2E Testing Implementation (T40)

## Overview

This directory contains the comprehensive End-to-End (E2E) testing implementation for the Diet Issue Tracker web frontend. The testing framework is built with Playwright and provides extensive coverage across multiple browsers, devices, and testing scenarios.

## Test Structure

### Test Suites

1. **Navigation Tests** (`tests/e2e/navigation/`)
   - Basic navigation between pages
   - Browser back/forward functionality
   - URL routing validation
   - 404 error handling
   - Navigation state persistence

2. **Search Functionality Tests** (`tests/e2e/search/`)
   - Search input validation
   - Search result rendering
   - XSS prevention in search queries
   - Rate limiting protection
   - Search performance testing

3. **Accessibility Tests** (`tests/e2e/accessibility/`)
   - WCAG 2.1 AA compliance
   - Keyboard navigation support
   - Screen reader compatibility
   - ARIA labels and roles
   - Color contrast validation
   - Furigana toggle functionality
   - High contrast mode support

4. **Performance Tests** (`tests/e2e/performance/`)
   - Core Web Vitals measurement
   - Page load time optimization
   - Mobile performance testing
   - Network condition simulation
   - Resource loading optimization
   - Bundle size analysis

5. **Security Tests** (`tests/e2e/security/`)
   - XSS prevention validation
   - Content Security Policy (CSP) headers
   - Input sanitization testing
   - Rate limiting verification
   - Security header validation

6. **PWA Tests** (`tests/e2e/pwa/`)
   - Service Worker registration
   - Manifest file validation
   - Offline functionality testing
   - Cache management
   - Install prompt testing

### Test Infrastructure

- **Configuration**: `playwright.config.ts` - Multi-browser, multi-device setup
- **Global Setup**: `tests/setup/global-setup.ts` - Application readiness verification
- **Test Helpers**: `tests/utils/test-helpers.ts` - Comprehensive utility functions
- **Test Data**: `tests/fixtures/test-data.ts` - Mock data and test fixtures
- **Test Runner**: `tests/run-e2e-tests.js` - Custom test execution script

## Browser and Device Coverage

### Desktop Browsers

- **Chromium**: Latest stable version
- **Firefox**: Latest stable version
- **WebKit**: Safari engine testing

### Mobile Devices

- **Mobile Chrome**: Pixel 5 simulation
- **Mobile Safari**: iPhone 12 simulation
- **Tablet**: iPad simulation

### Responsive Testing

- Desktop: 1920x1080
- Tablet: 768x1024
- Mobile: 375x667

## Running Tests

### Prerequisites

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install
```

### Basic Test Execution

```bash
# Run all E2E tests
npx playwright test

# Run specific test suite
npx playwright test tests/e2e/accessibility/

# Run with custom timeout
npx playwright test --timeout=60000

# Run with HTML reporter
npx playwright test --reporter=html
```

### Custom Test Runner

```bash
# Run comprehensive test suite with reporting
node tests/run-e2e-tests.js
```

## Test Features

### Cross-Browser Testing

- Tests run across all major browsers
- Consistent behavior validation
- Browser-specific feature testing

### Accessibility Testing

- WCAG 2.1 AA compliance validation
- Keyboard navigation testing
- Screen reader compatibility
- Color contrast verification
- Japanese text accessibility (furigana support)

### Performance Testing

- Core Web Vitals measurement
- First Contentful Paint (FCP) tracking
- Largest Contentful Paint (LCP) monitoring
- Cumulative Layout Shift (CLS) detection
- Network condition simulation

### Security Testing

- XSS attack prevention
- Input sanitization validation
- Security header verification
- Rate limiting protection

### PWA Testing

- Service Worker functionality
- Offline capability testing
- Manifest validation
- Cache management verification

## Test Data and Fixtures

### Mock Data

- Sample search queries (valid/invalid)
- Test issue data
- Performance thresholds
- Security test payloads

### Test Configurations

- Browser viewport settings
- Network condition presets
- Performance benchmark thresholds
- Accessibility test parameters

## Reporting

### HTML Reports

- Detailed test execution results
- Screenshot capture on failures
- Video recordings of test runs
- Performance metrics visualization

### Console Output

- Real-time test progress
- Performance metrics logging
- Error details and stack traces
- Test summary statistics

## Performance Thresholds

### Page Load Times

- DOM Content Loaded: < 1000ms
- Full Page Load: < 2000ms
- First Contentful Paint: < 800ms
- Mobile Load Time: < 1500ms

### Core Web Vitals

- LCP: < 2.5s
- FID: < 100ms
- CLS: < 0.1

## Security Validations

### Headers

- Content-Security-Policy
- X-Frame-Options
- X-Content-Type-Options
- Strict-Transport-Security

### Input Validation

- XSS prevention
- SQL injection protection
- Command injection prevention
- Path traversal protection

## Accessibility Standards

### WCAG 2.1 AA Compliance

- Keyboard navigation support
- Screen reader compatibility
- Color contrast requirements
- Focus management
- Semantic HTML structure

### Japanese-Specific Features

- Furigana toggle functionality
- Japanese text rendering
- Character encoding validation
- Language declaration correctness

## Maintenance

### Updating Tests

1. Monitor application changes
2. Update test selectors as needed
3. Adjust performance thresholds
4. Update security test scenarios

### Adding New Tests

1. Follow existing test patterns
2. Use helper functions for common operations
3. Include proper error handling
4. Add descriptive test names and comments

## Integration with CI/CD

### GitHub Actions Integration

The E2E tests are designed to integrate with GitHub Actions for automated testing:

```yaml
- name: Run E2E Tests
  run: |
    cd services/web-frontend
    npm install
    npx playwright install
    npx playwright test --reporter=html
```

### Test Results

- Test results are captured in HTML format
- Screenshots and videos are preserved for debugging
- Performance metrics are logged for monitoring

## Troubleshooting

### Common Issues

1. **Browser Installation**: Run `npx playwright install` if browsers are missing
2. **Test Timeouts**: Increase timeout values for slow CI environments
3. **Element Not Found**: Update selectors after UI changes
4. **Performance Thresholds**: Adjust thresholds based on environment capabilities

### Debug Mode

```bash
# Run with debug output
npx playwright test --debug

# Run with headed browsers
npx playwright test --headed

# Run specific test with verbose output
npx playwright test tests/e2e/accessibility/accessibility.test.ts --verbose
```

## Implementation Summary

This E2E testing implementation provides:

✅ **Comprehensive Coverage**: All major application features tested
✅ **Cross-Browser Compatibility**: Tests across Chrome, Firefox, Safari, WebKit
✅ **Mobile Responsiveness**: Mobile and tablet device testing
✅ **Accessibility Compliance**: WCAG 2.1 AA standard validation
✅ **Performance Monitoring**: Core Web Vitals and load time tracking
✅ **Security Validation**: XSS, CSP, and input sanitization testing
✅ **PWA Functionality**: Service Worker and offline capability testing
✅ **Japanese Language Support**: Furigana and Japanese text accessibility
✅ **Test Infrastructure**: Helper functions, fixtures, and utilities
✅ **Reporting**: HTML reports with screenshots and videos
✅ **CI/CD Integration**: GitHub Actions compatible test execution

The implementation fulfills all requirements for T40 - エンドツーエンドテスト and provides a robust foundation for ongoing quality assurance of the Diet Issue Tracker application.
