# 可観測性・モニタリングシステム (T43)

## 概要

Diet Issue Tracker Webフロントエンドの包括的な可観測性・モニタリングシステムです。リアルタイムでアプリケーションのパフォーマンス、エラー、ユーザーインタラクションを追跡し、データドリブンな改善を可能にします。

## 主要機能

### 1. Core Web Vitals監視

- **FCP (First Contentful Paint)**: 初回コンテンツ描画時間
- **LCP (Largest Contentful Paint)**: 最大コンテンツ描画時間
- **FID (First Input Delay)**: 初回入力遅延
- **CLS (Cumulative Layout Shift)**: 累積レイアウトシフト
- **TTFB (Time to First Byte)**: 初回バイト受信時間

### 2. パフォーマンスメトリクス

- ページロード時間測定
- API呼び出し応答時間
- 検索操作の実行時間
- リソース読み込み時間
- Navigation Timing API活用

### 3. エラー追跡

- JavaScript実行エラー
- API呼び出しエラー
- ネットワークエラー
- バリデーションエラー
- セキュリティ関連エラー

### 4. ユーザーインタラクション分析

- ページビュー追跡
- 検索クエリ分析
- ナビゲーション行動
- フォーム送信
- クリックイベント

### 5. システム状態監視

- ネットワーク接続状態
- PWAスタンドアロンモード
- ブラウザ情報
- セッション管理

## アーキテクチャ

### コンポーネント構成

```
src/
├── lib/
│   └── observability.ts          # メイン監視ライブラリ
├── pages/
│   └── api/
│       └── observability.ts      # データ収集API
├── components/
│   └── ObservabilityDashboard.tsx # 監視ダッシュボード
└── pages/
    ├── _app.tsx                   # グローバル監視設定
    └── index.tsx                  # ページレベル監視
```

### データフロー

1. **データ収集**
   - Web Vitals API
   - Performance Observer API
   - カスタムイベント追跡

2. **データ処理**
   - ローカルバッファリング
   - 定期的なデータフラッシュ（30秒間隔）
   - エラー時の即座送信

3. **データ送信**
   - `/api/observability` エンドポイント
   - JSON形式でPOST送信
   - Rate limiting対応

4. **データ分析**
   - リアルタイム集計
   - 閾値ベースアラート
   - トレンド分析

## 使用方法

### 基本的な使用

```typescript
import { useObservability } from "@/lib/observability";

function MyComponent() {
  const { recordMetric, recordError, recordInteraction } = useObservability();

  const handleClick = () => {
    recordInteraction({
      type: "click",
      element: "my-button",
      value: "action-name",
    });
  };

  const handleError = (error: Error) => {
    recordError({
      error,
      context: "my-component",
      timestamp: Date.now(),
    });
  };
}
```

### パフォーマンス測定

```typescript
// 単発測定
const stopTimer = startTimer("operation-name");
// ... 処理実行
stopTimer();

// 非同期処理測定
const result = await measureAsync("async-operation", async () => {
  return await apiCall();
});
```

### カスタムメトリクス

```typescript
recordMetric({
  name: "custom.metric",
  value: 123,
  timestamp: Date.now(),
  tags: {
    category: "user-action",
    feature: "search",
  },
});
```

## 監視ダッシュボード

### アクセス方法

開発環境で左下の青いアイコンをクリックしてダッシュボードを開きます。

### 表示項目

- **セッション情報**: セッションID、メトリクス数、エラー数
- **Core Web Vitals**: リアルタイム性能指標
- **パフォーマンス評価**: 良好/要改善/不良の分類
- **ブラウザ情報**: User Agent、画面サイズ、接続状態
- **エラー状況**: 検出されたエラーの概要

### 自動更新

ダッシュボードは5秒間隔で自動更新され、最新の状態を反映します。

## メトリクス一覧

### Core Web Vitals

| メトリクス | 良好   | 要改善 | 不良   |
| ---------- | ------ | ------ | ------ |
| FCP        | ≤1.8s  | ≤3.0s  | >3.0s  |
| LCP        | ≤2.5s  | ≤4.0s  | >4.0s  |
| FID        | ≤100ms | ≤300ms | >300ms |
| CLS        | ≤0.1   | ≤0.25  | >0.25  |
| TTFB       | ≤800ms | ≤1.8s  | >1.8s  |

### カスタムメトリクス

#### システム関連

- `system.health_check.success` - システムヘルスチェック成功
- `system.health_check.failure` - システムヘルスチェック失敗
- `network.status_change` - ネットワーク状態変更
- `pwa.standalone_mode` - PWAスタンドアロンモード使用

#### 検索関連

- `search.success` - 検索成功時間
- `search.result_count` - 検索結果数
- `search.validation_error` - 検索バリデーションエラー
- `search.rate_limit` - 検索レート制限

#### API関連

- `api.request_duration` - API呼び出し時間
- `api.request_failure` - API呼び出し失敗

#### ナビゲーション関連

- `navigation.dom_content_loaded` - DOM読み込み完了時間
- `navigation.load_complete` - ページ読み込み完了時間
- `page.load_time` - ページロード時間

## アラート機能

### 自動アラート条件

- Core Web Vitalsが「不良」レベルに達した場合
- エラー発生時（即座に記録）
- API呼び出し失敗時
- ネットワーク接続切断時

### 通知方法

- 開発環境: コンソールログ
- 本番環境: 外部監視サービス（実装時）

## データ保持・プライバシー

### データ保持期間

- メモリ内バッファ: 最大30秒
- セッション継続中: フルデータ保持
- 個人情報: 収集なし

### プライバシー保護

- IPアドレス記録なし
- 個人識別情報収集なし
- 検索クエリの匿名化
- セッションIDのみでユーザー追跡

## パフォーマンス最適化

### バッファリング

- メモリ効率的なデータ構造
- 定期的なガベージコレクション
- 大量データ時の自動プルーニング

### ネットワーク最適化

- バッチ送信によるリクエスト数削減
- 圧縮送信
- 失敗時のリトライ機能

## 開発・デバッグ

### 開発環境での確認

```bash
# 開発サーバー起動
npm run dev

# ブラウザで http://localhost:3000 にアクセス
# 左下の青いアイコンで監視ダッシュボードを開く
```

### コンソールログ

開発環境では全ての監視データがコンソールに出力されます：

```
[Metrics] { name: 'search.success', value: 234, timestamp: 1672531200000 }
[Error] { context: 'api_request_failed', error: '...' }
[Interaction] { type: 'search', element: 'search_input', value: 'tax reform' }
```

### 本番環境での設定

```typescript
// 環境変数設定
NEXT_PUBLIC_ENABLE_OBSERVABILITY = true;

// 監視サービス統合（例）
// OBSERVABILITY_ENDPOINT=https://monitoring-service.com/api/data
// OBSERVABILITY_API_KEY=your-api-key
```

## 外部サービス統合

### サポート予定サービス

- **DataDog**: APM・インフラ監視
- **New Relic**: アプリケーション性能監視
- **Sentry**: エラー追跡・性能監視
- **Google Analytics**: ユーザー行動分析

### 統合方法

```typescript
// 例: DataDog統合
async function sendToDataDog(data) {
  await fetch("https://api.datadoghq.com/api/v1/series", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "DD-API-KEY": process.env.DATADOG_API_KEY,
    },
    body: JSON.stringify(data),
  });
}
```

## トラブルシューティング

### よくある問題

1. **Web Vitals データが表示されない**
   - ブラウザがWeb Vitals APIをサポートしているか確認
   - `web-vitals` パッケージが正しくインストールされているか確認

2. **データが送信されない**
   - ネットワーク接続状態確認
   - `/api/observability` エンドポイントの動作確認
   - Rate limiting設定確認

3. **ダッシュボードが開かない**
   - 開発環境（NODE_ENV=development）で実行しているか確認
   - JavaScript エラーがないかコンソール確認

### デバッグコマンド

```javascript
// ブラウザコンソールで実行
window.observability.getSessionSummary(); // セッション情報確認
window.observability.getWebVitals(); // Web Vitals確認
window.observability.flush(); // 手動データ送信
```

## 今後の拡張予定

### Phase 2 機能

- リアルタイムアラート機能
- 詳細なユーザージャーニー分析
- A/Bテスト統合
- 予測分析機能

### Phase 3 機能

- カスタムダッシュボード作成
- 自動レポート生成
- 機械学習ベース異常検知
- マルチテナント対応

## 関連リンク

- [Web Vitals Documentation](https://web.dev/vitals/)
- [Performance Observer API](https://developer.mozilla.org/en-US/docs/Web/API/PerformanceObserver)
- [Navigation Timing API](https://developer.mozilla.org/en-US/docs/Web/API/Navigation_timing_API)
- [Error Event](https://developer.mozilla.org/en-US/docs/Web/API/Window/error_event)

---

## 実装完了項目 ✅

1. **可観測性ライブラリ** (`observability.ts`)
   - Core Web Vitals監視
   - パフォーマンスメトリクス収集
   - エラー追跡機能
   - ユーザーインタラクション分析

2. **データ収集API** (`/api/observability`)
   - 監視データ受信処理
   - 構造化ログ出力
   - エラーハンドリング

3. **監視ダッシュボード** (`ObservabilityDashboard.tsx`)
   - リアルタイム監視画面
   - Core Web Vitals表示
   - セッション情報表示
   - 自動更新機能

4. **アプリケーション統合**
   - API呼び出し監視
   - 検索機能監視
   - ページビュー追跡
   - グローバルエラー処理

5. **開発ツール統合**
   - 開発環境でのダッシュボードアクセス
   - コンソールログ出力
   - デバッグ機能

**T43 - 可観測性・モニタリング**: 完全実装完了 🎉
