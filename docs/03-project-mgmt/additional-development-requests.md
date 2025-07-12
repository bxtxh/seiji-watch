# TOPページ改修要件定義書 - 国会争点Kanbanボード

*作成日: 2025-07-11*  
*ステータス: 要件定義完了 → 開発チーム引き渡し準備*

---

## 1. 改修の背景と目的

### 1.1 現状の課題
- **空白TOPページ問題**: 初回訪問時にコンテンツが見えず、ユーザが価値を感じる前に離脱
- **検索前離脱**: 新規ユーザが「今国会で何が起きているか」を把握できない
- **プロダクト体験の悪化**: 検索ボックスのみでは能動的なアクションが必要

### 1.2 改修目的
- **概要俯瞰 → ドリルダウン導線**: 直近1ヶ月の争点・議案を一覧表示
- **受動的情報取得**: 検索なしで現在の国会状況を把握可能
- **エンゲージメント向上**: 興味のある論点から詳細ページへの自然な遷移

---

## 2. 機能要件

### 2.1 Kanbanボード全体仕様

| 項目 | 仕様 |
|------|------|
| **データ範囲** | 直近30日間に国会で議論された法案に紐づくイシューのみ |
| **表示列数** | 4列固定: `審議前` / `審議中` / `採決待ち` / `成立` |
| **レイアウト** | 横スクロール固定 (`overflow-x-auto` + マウス/ドラッグ対応) |
| **モバイル対応** | スナップスクロール (`snap-x mandatory`) で1列単位停止 |
| **最大表示件数** | 各列8件まで、超過時は「+N件」プレースホルダ表示 |

### 2.2 イシューカード詳細仕様

#### 必須表示項目
1. **イシュー名** (20文字以内ガイドライン)
2. **ステージバッジ** (右肩、色分けあり)
3. **スケジュールチップ** (審議期間表示)
4. **カテゴリタグ** (最大3個)
5. **関連法案リスト** (最大5件、各行にステージバッジ)
6. **最終更新日** (`YYYY-MM-DD`形式)
7. **詳細CTAリンク** (`詳細を見る →`)

#### UI/UX仕様
```html
<!-- カード基本構造 -->
<article class="bg-white rounded-xl shadow-sm p-4 w-[300px] space-y-2" role="listitem">
  <!-- ヘッダー: タイトル + ステージバッジ -->
  <div class="flex items-start justify-between">
    <h3 class="font-medium text-sm leading-snug line-clamp-2">夫婦別姓制度導入</h3>
    <span class="badge-stage px-2 py-0.5 text-xs rounded-full">審議中</span>
  </div>

  <!-- スケジュールチップ -->
  <div class="flex items-center gap-1 text-xs text-gray-600">
    <svg class="w-4 h-4" aria-hidden="true"><!-- カレンダーアイコン --></svg>
    2025年6月15日〜7月10日
  </div>

  <!-- カテゴリタグ -->
  <div class="flex flex-wrap gap-1 text-xs">
    <span class="badge-tag bg-purple-50 text-purple-700">家族法</span>
    <span class="badge-tag bg-blue-50 text-blue-700">民法改正</span>
  </div>

  <!-- 関連法案リスト -->
  <div class="space-y-1 mt-2">
    <h4 class="text-xs font-semibold text-gray-500">関連法案 (2件)</h4>
    <div class="bill-item p-2 text-xs border rounded hover:bg-gray-50">
      民法の一部を改正する法律案
      <span class="badge-bill ml-1">審議中</span>
    </div>
  </div>

  <!-- フッター -->
  <div class="flex justify-between items-center text-xs text-gray-500 mt-2">
    <time datetime="2025-07-10">最終更新: 2025-07-10</time>
    <a href="/issues/ISS123" class="text-primary hover:underline">詳細を見る →</a>
  </div>
</article>
```

### 2.3 カラーパレット仕様

| ステージ | バッジ背景 | テキスト色 | 説明 |
|----------|------------|------------|------|
| 審議前 | `bg-gray-100` | `text-gray-700` | 未審議・タグ付け済み |
| 審議中 | `bg-indigo-50` | `text-indigo-700` | 委員会・本会議審議中 |
| 採決待ち | `bg-yellow-50` | `text-yellow-700` | 審議完了・採決日程待ち |
| 成立 | `bg-green-50` | `text-green-700` | 可決成立・否決完了 |

---

## 3. API設計仕様

### 3.1 エンドポイント定義

```http
GET /api/issues/kanban?range=30d
```

### 3.2 レスポンス形式

```json
{
  "metadata": {
    "total_issues": 24,
    "last_updated": "2025-07-11T10:00:00Z",
    "date_range": {
      "from": "2025-06-11",
      "to": "2025-07-11"
    }
  },
  "stages": {
    "審議前": [
      {
        "id": "ISS-001",
        "title": "夫婦別姓制度導入",
        "stage": "審議前",
        "schedule": {
          "from": "2025-06-15",
          "to": "2025-07-10"
        },
        "tags": ["家族法", "民法改正"],
        "related_bills": [
          {
            "bill_id": "B217-13",
            "title": "民法の一部を改正する法律案",
            "stage": "審議前",
            "bill_number": "第217回国会第13号"
          }
        ],
        "updated_at": "2025-07-10"
      }
    ],
    "審議中": [...],
    "採決待ち": [...],
    "成立": [...]
  }
}
```

### 3.3 パラメータ仕様

| パラメータ | 型 | デフォルト | 説明 |
|------------|----|-----------:|------|
| `range` | string | `30d` | 取得期間 (`7d`/`30d`/`90d`) |
| `max_per_stage` | integer | `8` | 各ステージの最大表示件数 |

---

## 4. フロントエンド実装仕様

### 4.1 コンポーネント構成

```
pages/index.tsx
├── KanbanBoard.tsx
│   ├── StageColumn.tsx (4個)
│   │   ├── IssueCard.tsx (最大8個)
│   │   │   ├── StageBadge.tsx
│   │   │   ├── CategoryTag.tsx
│   │   │   └── BillListItem.tsx
│   │   └── MorePlaceholder.tsx (+N件表示)
│   └── KanbanSkeleton.tsx
└── ErrorBoundary.tsx
```

### 4.2 レスポンシブ設計

```css
/* デスクトップ: 4列全表示 */
.kanban-container {
  @apply grid grid-flow-col auto-cols-[300px] gap-6 overflow-x-auto pb-4;
}

/* モバイル: 横スクロール + スナップ */
@media (max-width: 768px) {
  .kanban-container {
    @apply auto-cols-[280px] snap-x snap-mandatory;
  }
  
  .stage-column {
    @apply snap-start;
  }
}
```

### 4.3 状態管理

```typescript
// types/kanban.ts
interface KanbanState {
  issues: KanbanIssue[];
  loading: boolean;
  error: string | null;
  lastUpdated: string;
}

interface KanbanIssue {
  id: string;
  title: string;
  stage: '審議前' | '審議中' | '採決待ち' | '成立';
  schedule: { from: string; to: string };
  tags: string[];
  related_bills: BillItem[];
  updated_at: string;
}
```

---

## 5. パフォーマンス要件

| 指標 | 目標値 | 測定方法 |
|------|--------|----------|
| **First Contentful Paint** | ≤ 200ms | Chrome DevTools / Lighthouse |
| **Largest Contentful Paint** | ≤ 2.5s | Lighthouse CI |
| **Interaction Delay** | ≤ 100ms | `prefetch="hover"` 実装 |
| **Accessibility Score** | ≥ 95 | Lighthouse a11y audit |

### 5.1 最適化手法

1. **SSG事前生成**: API データを build 時にフェッチ
2. **CDN配信**: 静的アセットの Edge Cache 活用
3. **Prefetch**: ホバー時の詳細ページ先読み
4. **Skeleton UI**: 初期表示時のちらつき防止

---

## 6. アクセシビリティ仕様

### 6.1 キーボードナビゲーション

```typescript
// キーボード操作仕様
const keyboardHandlers = {
  'ArrowLeft': () => scrollToPreviousColumn(),
  'ArrowRight': () => scrollToNextColumn(), 
  'Tab': () => focusNextCard(),
  'Enter': () => openIssueDetail(),
  'Space': () => openIssueDetail()
};
```

### 6.2 スクリーンリーダー対応

```html
<!-- セマンティック構造 -->
<main>
  <section aria-label="国会イシュー Kanban ボード">
    <h2>直近1ヶ月の議論</h2>
    <div role="list" aria-label="ステージ別イシュー一覧">
      <div role="group" aria-labelledby="stage-review-label">
        <h3 id="stage-review-label">審議中 (3件)</h3>
        <article role="listitem" aria-labelledby="issue-123-title">
          <!-- カード内容 -->
        </article>
      </div>
    </div>
  </section>
</main>
```

---

## 7. 実装タスク分解

### 7.1 Phase 1: バックエンドAPI (優先度: 高)
- [ ] `/api/issues/kanban` エンドポイント実装
- [ ] 30日間フィルタリングロジック
- [ ] ステージ別データ整理・ソート機能
- [ ] レスポンス形式の標準化

### 7.2 Phase 2: フロントエンド基盤 (優先度: 高)
- [ ] `KanbanBoard.tsx` 基盤コンポーネント
- [ ] `StageColumn.tsx` 列レイアウト
- [ ] `IssueCard.tsx` カードUI
- [ ] 横スクロール + スナップ機能

### 7.3 Phase 3: UI/UX詳細 (優先度: 中)
- [ ] カラーパレット・バッジシステム
- [ ] Skeleton ローディング状態
- [ ] エラーハンドリング UI
- [ ] ホバーエフェクト・アニメーション

### 7.4 Phase 4: パフォーマンス (優先度: 中)
- [ ] SSG事前生成設定
- [ ] Prefetch機能実装
- [ ] Lighthouse CI設定
- [ ] アクセシビリティ監査

---

## 8. テスト仕様

### 8.1 単体テスト
```typescript
// components/__tests__/IssueCard.test.tsx
describe('IssueCard', () => {
  it('should render issue title correctly', () => {
    render(<IssueCard issue={mockIssue} />);
    expect(screen.getByText('夫婦別姓制度導入')).toBeInTheDocument();
  });

  it('should display correct stage badge', () => {
    render(<IssueCard issue={{...mockIssue, stage: '審議中'}} />);
    expect(screen.getByText('審議中')).toHaveClass('text-indigo-700');
  });
});
```

### 8.2 E2Eテスト
```typescript
// tests/e2e/kanban-board.spec.ts
test('should allow horizontal scrolling through stages', async ({ page }) => {
  await page.goto('/');
  
  const kanbanBoard = page.locator('[data-testid="kanban-board"]');
  await expect(kanbanBoard).toBeVisible();
  
  // 横スクロールテスト
  await kanbanBoard.hover();
  await page.mouse.wheel(100, 0);
  
  // 2列目にフォーカス移動確認
  await expect(page.locator('[data-stage="審議中"]')).toBeInViewport();
});
```

---

## 9. 将来拡張計画 (非MVP)

### 9.1 Phase 2機能 (2025 Q4)
- **賛否趨勢バー**: 各イシューカードに投票傾向グラフ追加
- **フィルタパネル**: タグ・期間・キーワードによる絞り込み
- **検索統合**: 検索結果をKanban形式で表示

### 9.2 Phase 3機能 (2026 Q1)
- **ドラッグ&ドロップ**: 管理者用ステージ移動機能
- **リアルタイム更新**: WebSocket でライブ更新
- **パーソナライゼーション**: ユーザー関心領域のフィルタリング

---

## 10. 成功指標・KPI

| 指標 | 現状 | 目標 | 測定方法 |
|------|------|------|----------|
| **TOPページ滞在時間** | 10秒 | 60秒+ | Google Analytics |
| **詳細ページ遷移率** | 5% | 25%+ | 内部リンククリック追跡 |
| **検索前離脱率** | 70% | 40%以下 | ファネル分析 |
| **モバイル利用率** | 不明 | 60%+ | User Agent 分析 |

---

**承認・引き渡し**  
✅ 要件定義完了  
⏳ 開発チーム割り当て待ち  
⏳ 実装スケジュール調整  

*文責: AI Assistant (Claude) / レビュー: プロダクトオーナー*