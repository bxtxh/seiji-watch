# 衆議院PDF処理システム (T23)

## 概要

衆議院PDF処理システムは、衆議院Webサイトから投票データを含むPDFファイルを自動収集・処理し、構造化データとしてデータベースに統合するシステムです。参議院データ処理システムを補完し、国会全体の投票記録を包括的に収集します。

## 主要機能

### 1. 高度なPDF発見・分類システム
- **自動PDF発見**: 衆議院Webサイトから投票関連PDFを自動検出
- **インテリジェント分類**: PDFタイプの自動分類（記名投票、委員会採決、本会議表決）
- **優先度判定**: PDFの重要度に基づく処理順序の最適化
- **メタデータ抽出**: URL、ファイル名、日付から情報を自動抽出

### 2. 多段階抽出戦略
- **テキスト抽出**: PyMuPDFによる高速テキスト抽出
- **OCR フォールバック**: Tesseractを使った画像ベースOCR処理
- **ハイブリッド手法**: パターンマッチングと推論による補完
- **品質評価**: 抽出データの信頼性自動評価

### 3. データ正規化・統合
- **議員名照合**: 既存議員データベースとの高精度名前マッチング
- **競合解決**: データ不整合の自動検出・解決
- **品質保証**: データ完全性・一貫性の自動検証
- **統計追跡**: 処理性能・品質メトリクスの詳細収集

## システムアーキテクチャ

```
衆議院Webサイト
        ↓
    PDF発見・分類
        ↓
    優先度付け処理
        ↓
   多段階データ抽出
        ↓
    品質評価・検証
        ↓
   データベース統合
```

### コンポーネント構成

#### 1. Enhanced HR Scraper (`enhanced_hr_scraper.py`)
- **PDFProcessingResult**: 処理結果の詳細追跡
- **EnhancedVotingSession**: 拡張投票セッションデータ
- **EnhancedHRProcessor**: メイン処理エンジン

#### 2. Data Integration (`hr_data_integration.py`)
- **HRDataIntegrator**: データベース統合ロジック
- **DataConflictStrategy**: 競合解決戦略定義
- **IntegrationResult**: 統合結果の詳細レポート

#### 3. API Endpoints (main.py)
- `POST /hr/process`: PDF処理実行
- `GET /hr/status`: 処理状況確認

## 使用方法

### 基本的な処理実行

```bash
# API経由での処理実行
curl -X POST "http://localhost:8080/hr/process" \
  -H "Content-Type: application/json" \
  -d '{
    "days_back": 7,
    "max_concurrent": 2,
    "dry_run": false
  }'
```

### Pythonスクリプトでの直接実行

```python
from pipeline.hr_data_integration import run_hr_integration_pipeline

# 完全パイプライン実行
result = await run_hr_integration_pipeline(
    days_back=7,
    dry_run=False,
    max_concurrent=2
)

print(f"処理結果: {result['success']}")
print(f"セッション数: {result['integration_results'].sessions_processed}")
```

### テスト実行

```bash
# 包括的テスト実行
python test_hr_processing.py

# 特定機能のテスト
python -c "
import asyncio
from test_hr_processing import test_basic_hr_processing
asyncio.run(test_basic_hr_processing())
"
```

## PDF分類・優先度システム

### PDFタイプ分類

| 分類 | 説明 | 優先度 | 検出パターン |
|------|------|--------|--------------|
| `roll_call_vote` | 記名投票結果 | 10 | `記名投票`, `採決結果` |
| `plenary_vote` | 本会議表決 | 8 | `本会議.*採決` |
| `committee_vote` | 委員会採決 | 6 | `委員会.*採決` |
| `unknown` | 不明 | 1 | その他 |

### 優先度計算要素

1. **日付**: 最近のPDFほど高優先度
   - 7日以内: +10点
   - 30日以内: +5点

2. **PDFタイプ**: 記名投票が最高優先度
3. **重要キーワード**: 予算、法案、決議等で加点

## データ抽出戦略

### 1. テキスト抽出 (第一手法)
- PyMuPDFによる高速処理
- 品質評価: 文字数、日本語比率
- 成功条件: 100文字以上の有効テキスト

### 2. OCR処理 (フォールバック)
- Tesseract + 日本語モデル
- 画像前処理: ノイズ除去、二値化
- 信頼度スコア: 0.7以上で採用

### 3. ハイブリッド手法 (最終手段)
- パターンマッチング
- 既知フォーマット対応
- 部分データから推論

## 品質評価システム

### 品質メトリクス

1. **完全性スコア** (0.0-1.0)
   - 全必須フィールドの充足率
   - 閾値: 0.7以上

2. **信頼性スコア** (0.0-1.0)
   - OCR信頼度の平均
   - 閾値: 0.5以上

3. **一貫性スコア** (0.0-1.0)
   - 重複データ、政党分布の合理性
   - 閾値: 0.5以上

### 品質チェック項目

```python
quality_thresholds = {
    'min_member_count': 50,        # 最小議員数
    'min_text_length': 200,        # 最小テキスト長
    'min_confidence_score': 0.6,   # 最小信頼度
    'max_missing_data_ratio': 0.2  # 最大欠損率
}
```

## データベース統合

### 統合プロセス

1. **法案データ処理**
   - 既存法案の更新 or 新規作成
   - 衆議院起源フラグ設定

2. **議員データ処理**
   - 名前照合・正規化
   - 政党・選挙区情報更新
   - 競合検出・解決

3. **投票データ処理**
   - 投票セッション作成
   - 個別投票記録作成
   - 集計データ自動計算

4. **競合解決戦略**
   - `SKIP`: 競合データをスキップ
   - `OVERWRITE`: 新データで上書き
   - `MERGE`: インテリジェント統合
   - `MANUAL`: 手動確認フラグ

### データモデル統合

```sql
-- 衆議院データの識別
SELECT * FROM bills WHERE house_origin = '衆議院';
SELECT * FROM members WHERE house = '衆議院';
SELECT * FROM votes WHERE house = '衆議院';
```

## パフォーマンス・監視

### 処理統計

```json
{
  "total_pdfs_processed": 45,
  "successful_extractions": 38,
  "failed_extractions": 7,
  "ocr_fallbacks": 12,
  "avg_processing_time": 45.2,
  "avg_quality_score": 0.82,
  "success_rate": 0.84
}
```

### 監視メトリクス

- **処理時間**: PDF単位の処理時間追跡
- **成功率**: 抽出成功率の監視
- **品質スコア**: データ品質の定量評価
- **エラー率**: 各段階でのエラー発生率

## エラーハンドリング

### 一般的なエラー

1. **PDF取得失敗**
   - 原因: ネットワークエラー、リンク切れ
   - 対処: リトライ機構、ログ記録

2. **テキスト抽出失敗**
   - 原因: PDF破損、非標準フォーマット
   - 対処: OCRフォールバック

3. **データ解析失敗**
   - 原因: 予期しないPDFレイアウト
   - 対処: ハイブリッド手法、手動確認フラグ

4. **データベース競合**
   - 原因: 重複データ、不整合
   - 対処: 競合解決戦略適用

### ログレベル

- **INFO**: 正常処理進行
- **WARNING**: 回復可能なエラー
- **ERROR**: 処理失敗、要対応

## 設定・カスタマイズ

### 処理設定

```python
config = {
    'max_concurrent_pdfs': 3,
    'pdf_timeout_seconds': 300,
    'ocr_language': 'jpn+eng',
    'quality_threshold': 0.7,
    'conflict_strategy': 'MERGE'
}
```

### 監視設定

```python
monitoring_config = {
    'enable_detailed_logging': True,
    'save_processing_results': True,
    'alert_on_failure_rate': 0.3,
    'performance_threshold_seconds': 120
}
```

## トラブルシューティング

### よくある問題

1. **PDFが見つからない**
   ```bash
   # 検索URL確認
   curl "https://www.shugiin.go.jp/internet/itdb_rchome.nsf/Xhtml/result/vote_list.html"
   ```

2. **OCR品質が低い**
   ```python
   # Tesseract設定確認
   pytesseract.get_tesseract_version()
   pytesseract.get_languages()
   ```

3. **処理が遅い**
   ```python
   # 並行数調整
   await processor.process_enhanced_hr_data(max_concurrent=1)
   ```

4. **データ競合**
   ```python
   # 競合解決戦略変更
   integrator = HRDataIntegrator(conflict_strategy=DataConflictStrategy.SKIP)
   ```

### デバッグモード

```python
# 詳細ログ有効化
import logging
logging.getLogger().setLevel(logging.DEBUG)

# ドライラン実行
result = await run_hr_integration_pipeline(dry_run=True)
```

## API仕様

### POST /hr/process

衆議院PDF処理を実行

**リクエスト**:
```json
{
  "days_back": 7,
  "session_numbers": [208, 209],
  "max_concurrent": 2,
  "dry_run": false
}
```

**レスポンス**:
```json
{
  "success": true,
  "message": "HR PDF processing completed successfully",
  "sessions_processed": 5,
  "processing_time": 142.5,
  "bills_created": 2,
  "bills_updated": 1,
  "members_created": 12,
  "members_updated": 8,
  "votes_created": 5,
  "vote_records_created": 245,
  "conflicts_detected": 3,
  "errors": []
}
```

### GET /hr/status

処理状況と統計情報を取得

**レスポンス**:
```json
{
  "status": "ready",
  "service": "enhanced_hr_processor",
  "version": "1.0.0",
  "capabilities": [
    "pdf_text_extraction",
    "ocr_fallback",
    "member_name_matching",
    "quality_assessment",
    "data_validation",
    "conflict_resolution"
  ],
  "processing_statistics": {
    "total_pdfs_processed": 45,
    "successful_extractions": 38,
    "avg_processing_time": 45.2
  },
  "last_check": "2025-07-05T10:30:00Z"
}
```

## 依存関係

### Python パッケージ

```txt
PyMuPDF>=1.23.0      # PDF処理
pytesseract>=0.3.10  # OCR
Pillow>=9.0.0        # 画像処理
opencv-python>=4.7.0 # 画像前処理
beautifulsoup4>=4.11.0 # HTML解析
aiohttp>=3.8.0       # 非同期HTTP
requests>=2.28.0     # HTTP通信
SQLAlchemy>=1.4.0    # データベース
```

### システム依存関係

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-jpn

# macOS
brew install tesseract tesseract-lang

# 日本語データ確認
tesseract --list-langs | grep jpn
```

## 今後の拡張計画

### Phase 2 機能
- **リアルタイム処理**: Webhook による自動処理
- **機械学習強化**: PDFレイアウト学習
- **詳細分析**: 投票パターン分析
- **API拡張**: より細かな制御オプション

### Phase 3 機能
- **多言語対応**: 英語レポート生成
- **予測機能**: 投票結果予測
- **統計ダッシュボード**: リアルタイム可視化
- **外部連携**: 他システムとのAPI連携

## 実装完了項目 ✅

1. **Enhanced HR Scraper**: 高度なPDF処理エンジン
2. **Data Integration**: データベース統合機能
3. **Quality Assessment**: 品質評価システム
4. **Error Handling**: 包括的エラー処理
5. **API Endpoints**: REST API提供
6. **Testing Framework**: 自動テストスイート
7. **Documentation**: 詳細技術文書
8. **Monitoring**: 処理統計・監視機能

**T23 - 衆議院PDF処理**: 完全実装完了 🎉

---

*最終更新: 2025-07-05*
*ドキュメントバージョン: 1.0.0*