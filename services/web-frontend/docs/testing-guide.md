# Frontend Testing Guide

## テスト戦略

Diet Issue Trackerフロントエンドでは、以下の3層のテスト戦略を採用しています：

1. **Unit Tests** - コンポーネントとユーティリティ関数のテスト
2. **Integration Tests** - API統合のテスト
3. **E2E Tests** - Playwrightを使用した全体的なユーザーフローのテスト

## Unit Tests

### セットアップ

```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom jest-environment-jsdom
```

### テストの実行

```bash
# すべてのテストを実行
npm test

# ウォッチモードで実行
npm test -- --watch

# カバレッジレポート付きで実行
npm test -- --coverage
```

### テストの書き方

```typescript
// components/__tests__/BillCard.test.tsx
import { render, screen } from '@testing-library/react';
import BillCard from '../BillCard';

describe('BillCard', () => {
  it('renders bill title and summary', () => {
    const bill = {
      id: '1',
      bill_number: 'HB001',
      title: 'テスト法案',
      summary: 'これはテスト法案です',
      category: 'テスト',
      status: '審議中',
      diet_url: 'https://example.com',
    };

    render(<BillCard bill={bill} />);
    
    expect(screen.getByText('テスト法案')).toBeInTheDocument();
    expect(screen.getByText('これはテスト法案です')).toBeInTheDocument();
  });
});
```

## Integration Tests

### APIモックの設定

```typescript
// __tests__/api/bills.test.ts
import { api } from '@/lib/api-client';

// モックの設定
jest.mock('@/lib/api-client');

describe('Bills API Integration', () => {
  it('fetches bills successfully', async () => {
    const mockData = {
      success: true,
      results: [/* mock bills */],
      total_found: 10,
    };

    (api.bills.search as jest.Mock).mockResolvedValue(mockData);

    const result = await api.bills.search({ query: 'test' });
    
    expect(result.success).toBe(true);
    expect(result.total_found).toBe(10);
  });
});
```

## E2E Tests with Playwright

### セットアップ

```bash
# Playwrightのインストール
npm install --save-dev @playwright/test

# ブラウザのインストール
npx playwright install
```

### 設定

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
  },
});
```

### E2Eテストの例

```typescript
// tests/e2e/bills.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Bills Page', () => {
  test('should display bills list', async ({ page }) => {
    await page.goto('/bills');
    
    // ページタイトルの確認
    await expect(page).toHaveTitle(/法案一覧/);
    
    // 検索フォームの確認
    await expect(page.locator('input[placeholder*="法案名"]')).toBeVisible();
    
    // 法案カードの表示を待つ
    await page.waitForSelector('[data-testid="bill-card"]', { timeout: 10000 });
    
    // 少なくとも1つの法案が表示されることを確認
    const billCards = await page.locator('[data-testid="bill-card"]').count();
    expect(billCards).toBeGreaterThan(0);
  });

  test('should filter bills by status', async ({ page }) => {
    await page.goto('/bills');
    
    // ステータスフィルターを選択
    await page.selectOption('select[id="status"]', '成立');
    
    // フィルター適用を待つ
    await page.waitForTimeout(1000);
    
    // フィルターが適用されたことを確認
    const url = page.url();
    expect(url).toContain('status=成立');
  });
});
```

### E2Eテストの実行

```bash
# すべてのE2Eテストを実行
npm run test:e2e

# UIモードで実行（デバッグに便利）
npx playwright test --ui

# 特定のテストファイルのみ実行
npx playwright test bills.spec.ts

# ヘッドレスモードを無効にして実行
npx playwright test --headed
```

## テストのベストプラクティス

### 1. テストIDの使用

コンポーネントにdata-testid属性を追加：

```tsx
<div data-testid="bill-card" className="...">
  {/* content */}
</div>
```

### 2. 非同期処理の適切な待機

```typescript
// ❌ 悪い例
await page.click('button');
expect(await page.locator('.result').count()).toBe(10);

// ✅ 良い例
await page.click('button');
await page.waitForSelector('.result');
expect(await page.locator('.result').count()).toBe(10);
```

### 3. 環境変数のモック

```typescript
// テスト用の環境変数を設定
beforeAll(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8080';
});
```

## CI/CDでのテスト実行

GitHub Actionsでの設定例：

```yaml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          
      - name: Install dependencies
        run: npm ci
        
      - name: Run unit tests
        run: npm test -- --ci
        
      - name: Install Playwright browsers
        run: npx playwright install --with-deps
        
      - name: Run E2E tests
        run: npm run test:e2e
```

## トラブルシューティング

### テストがタイムアウトする

```typescript
// タイムアウトを増やす
test('slow test', async ({ page }) => {
  test.setTimeout(60000); // 60秒
  // ...
});
```

### API接続エラー

E2Eテスト用のモックサーバーを使用：

```typescript
// tests/e2e/setup/mock-server.ts
import { test as base } from '@playwright/test';

export const test = base.extend({
  // APIモックを自動的にセットアップ
  page: async ({ page }, use) => {
    await page.route('**/api/**', route => {
      // モックレスポンスを返す
      route.fulfill({
        status: 200,
        body: JSON.stringify({ success: true, results: [] }),
      });
    });
    await use(page);
  },
});
```