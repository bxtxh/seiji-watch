# Hybrid Ingestion Pipeline — NDL API × Whisper

## 概要

第217回国会（2025年1月24日〜2025年6月21日）以前のデータについては国会図書館Minutes APIを利用し、第218回国会以降については従来のWhisper/STTパイプラインを使用するハイブリッド方式のデータインジェスションシステム。

## 背景・課題

### 現行システムの課題

- **STTコスト**: Whisperによる音声認識処理コストが高額
- **処理時間**: 大量の過去データ処理に長時間を要する
- **メタデータ不足**: 音声からのみでは議事録の詳細情報が不完全

### NDL API活用の利点

- **コスト削減**: テキストデータの直接取得により音声処理コスト削減
- **データ品質**: 公式議事録による高品質なテキストデータ
- **メタデータ完備**: 発言者、所属政党、発言時刻等の詳細情報
- **処理速度**: APIからの直接取得により大幅な時間短縮

## スコープ定義

### Phase 1: NDL API統合 (過去データ)

- **対象期間**: 第217回国会まで (meetings ≤ 2025-06-21)
- **データソース**: 国会図書館Minutes API
- **対象データ**:
  - 本会議議事録
  - 委員会議事録
  - 発言詳細・メタデータ

### Phase 2: Whisper継続 (現在データ)

- **対象期間**: 第218回国会以降 (meetings ≥ 2025-06-22)
- **データソース**: Diet TV + Whisper STT
- **遅延目標**: ≤24時間以内の最新データ反映

## 技術アーキテクチャ

### データフロー概要

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NDL API       │    │   Diet TV       │    │   Airtable      │
│ (≤2025-06-21)   │───▶│ + Whisper STT   │───▶│  (統合格納)     │
│   JSON データ   │    │ (≥2025-06-22)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### コンポーネント設計

#### 1. NDL API インジェスタ

```python
class NDLAPIIngester:
    """国会図書館Minutes API からのデータ取得"""

    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=3, per_seconds=1)
        self.base_url = "https://kokkai.ndl.go.jp/api/"

    async def fetch_meetings(self, date_range: DateRange) -> List[Meeting]:
        """指定期間の会議データを取得"""
        pass

    async def fetch_speeches(self, meeting_id: str) -> List[Speech]:
        """特定会議の発言データを取得"""
        pass
```

#### 2. データ統合コーディネータ

```python
class HybridIngestionCoordinator:
    """NDL API と Whisper STT の統合管理"""

    def __init__(self):
        self.ndl_ingester = NDLAPIIngester()
        self.whisper_pipeline = WhisperSTTPipeline()
        self.cutoff_date = datetime(2025, 6, 21)

    async def ingest_data(self, target_date: datetime):
        """日付に応じて適切なインジェスタを選択"""
        if target_date <= self.cutoff_date:
            return await self.ndl_ingester.process(target_date)
        else:
            return await self.whisper_pipeline.process(target_date)
```

## API仕様

### NDL Minutes API エンドポイント

#### 会議一覧取得

```http
GET https://kokkai.ndl.go.jp/api/meeting?startRecord=1&maximumRecords=10&meetingDate={YYYY-MM-DD}
```

#### 発言詳細取得

```http
GET https://kokkai.ndl.go.jp/api/speech?startRecord=1&maximumRecords=100&meetingId={meeting_id}
```

### レスポンス例

```json
{
  "numberOfRecords": 1,
  "numberOfReturns": 1,
  "startRecord": 1,
  "speechRecord": [
    {
      "speechID": "123456789",
      "meetingId": "987654321",
      "speakerName": "山田太郎",
      "speakerGroup": "○○党",
      "speechType": "答弁",
      "speechOrder": 1,
      "speech": "ただいまの質問にお答えいたします...",
      "speechDateTime": "2025-06-15T14:30:00Z"
    }
  ]
}
```

## データマッピング

### NDL API → Airtable スキーマ対応

| NDL API フィールド | Airtableテーブル | フィールド   | 備考           |
| ------------------ | ---------------- | ------------ | -------------- |
| `meetingId`        | Meetings         | `meeting_id` | 主キー         |
| `speechID`         | Speeches         | `speech_id`  | 主キー         |
| `speakerName`      | Members          | `name`       | 名前正規化処理 |
| `speakerGroup`     | Parties          | `name`       | 政党マッピング |
| `speech`           | Speeches         | `content`    | 発言内容       |
| `speechDateTime`   | Speeches         | `timestamp`  | ISO8601形式    |

### データ正規化処理

#### 1. 議員名正規化

```python
def normalize_speaker_name(name: str) -> str:
    """議員名の表記揺れを統一"""
    # 敬語表現の除去 ("○○君" → "○○")
    # 漢字・ひらがな表記の統一
    # 姓名分離処理
    pass
```

#### 2. 政党名マッピング

```python
PARTY_MAPPING = {
    "自由民主党": "自民党",
    "立憲民主党": "立憲民主党",
    "日本維新の会": "維新",
    # ... 略
}
```

## レート制限・エラーハンドリング

### NDL API レート制限

- **制限**: 3 requests/second (推奨値)
- **実装**: `asyncio.Semaphore` + `time.sleep()` による制御
- **リトライロジック**: 指数バックオフ (初期1秒, 最大60秒)

### エラーハンドリング戦略

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=60)
)
async def api_request_with_retry(url: str) -> Dict:
    """エラー時自動リトライ付きAPI呼び出し"""
    try:
        response = await httpx.get(url, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:  # Rate limit
            await asyncio.sleep(60)  # 1分待機
            raise
        elif 500 <= e.response.status_code < 600:  # Server error
            raise
        else:
            logger.error(f"API request failed: {e}")
            raise
```

## 実装フェーズ

### Phase 1: NDL API 基盤構築 (Week 1-2)

- [ ] NDL API クライアント実装
- [ ] データ取得・変換ロジック構築
- [ ] Airtableスキーマ拡張
- [ ] 統合テスト環境構築

### Phase 2: 過去データ一括取込 (Week 3-4)

- [ ] 第217回国会データ取得スクリプト実行
- [ ] データ品質検証・補正処理
- [ ] パフォーマンス最適化
- [ ] ログ・監視体制構築

### Phase 3: Whisper統合 (Week 5-6)

- [ ] ハイブリッドコーディネータ実装
- [ ] 日付ベース振り分けロジック
- [ ] 統合テスト・E2Eテスト
- [ ] 本番デプロイ

## 監視・運用

### キーメトリクス

- **NDL API応答時間**: P95 < 2秒
- **データ取得成功率**: > 99.5%
- **データ新鮮度**: 過去データ完全性、現在データ24時間以内
- **コスト削減率**: Whisper処理コスト75%減を目標

### アラート設定

- API応答エラー率 > 1%
- データ取得遅延 > 1日
- レート制限超過検出

## セキュリティ・コンプライアンス

### データ取扱い

- **著作権**: 国会図書館API利用規約準拠
- **個人情報**: 公人（国会議員）情報のみ処理
- **データ保持**: 議事録の永続保存（法的要件）

### API認証

- NDL API: 認証不要（パブリックAPI）
- 利用規約: 商用利用可、出典明記必須

---

**Document Version**: 1.0  
**Created**: 2025-07-13  
**Author**: Engineering Team  
**Review Cycle**: Bi-weekly during implementation phase

## 関連ドキュメント

- [Infrastructure Specification](./infrastructure-specification.md)
- [Development Tickets](./development-tickets-final.md)
- [Product Roadmap](../../00-overview/roadmap.md)
