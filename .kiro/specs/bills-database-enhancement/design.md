# Bills Database Enhancement - Design Document

## Overview

本設計は、現在の法案データベースを拡張し、参議院・衆議院の両議会から包括的な法案情報を取得・管理するシステムを構築する。特に、法案の提出背景や詳細な目的を含む「議案要旨」相当の情報を適切に構造化して保存し、ユーザーが法案の本質を理解できるデータベース設計を実現する。

## Architecture

### Data Source Integration
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   参議院サイト    │    │   衆議院サイト    │    │   統合データ     │
│   法案一覧       │───▶│   法案一覧       │───▶│   ベース        │
│   + 詳細ページ   │    │   + 詳細ページ   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Enhanced Bills Database                      │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Basic Info    │  Detailed Info  │    Process Tracking         │
│   (共通)        │  (議案要旨等)    │    (審議進捗)               │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## Components and Interfaces

### 1. Enhanced Bill Model

現在のBillモデルを拡張し、以下のフィールドグループに分類：

#### Basic Information (基本情報)
- `bill_number`: 法案番号
- `title`: 法案名
- `bill_type`: 法案種別 (内閣提出/議員提出)
- `diet_session`: 国会回次
- `house_of_origin`: 提出元議院

#### Detailed Content (詳細内容)
- `bill_outline`: 法案概要 (議案要旨相当の長文)
- `background_context`: 提出背景・経緯
- `expected_effects`: 期待される効果・影響
- `key_provisions`: 主要条項・ポイント
- `implementation_date`: 施行予定日
- `related_laws`: 関連法律

#### Submission Information (提出情報)
- `submitter_type`: 提出者種別 (政府/議員)
- `submitting_members`: 提出議員一覧
- `supporting_members`: 賛成議員一覧 (衆議院のみ)
- `sponsoring_ministry`: 主管省庁
- `submission_date`: 提出日

#### Process Tracking (審議進捗)
- `current_stage`: 現在の審議段階
- `committee_assignments`: 委員会付託情報
- `voting_results`: 採決結果
- `amendments`: 修正内容
- `inter_house_status`: 両院間の状況

#### Source Metadata (ソースメタデータ)
- `source_house`: データ取得元議院
- `source_url`: 元データURL
- `last_updated`: 最終更新日時
- `data_quality_score`: データ品質スコア

### 2. Data Mapping Strategy

#### 参議院フォーマット対応
```python
# 参議院の法案ページから取得する情報
SANGIIN_FIELD_MAPPING = {
    "件名": "title",
    "種別": "bill_type", 
    "提出回次": "diet_session",
    "提出番号": "bill_number",
    "議案要旨": "bill_outline",  # 長文の詳細情報
    "提出日": "submission_date",
    "付託委員会等": "committee_assignments",
    "議決": "voting_results"
}
```

#### 衆議院フォーマット対応
```python
# 衆議院の法案ページから取得する情報
SHUGIIN_FIELD_MAPPING = {
    "議案件名": "title",
    "議案種類": "bill_type",
    "議案提出回次": "diet_session", 
    "議案番号": "bill_number",
    "議案提出者": "submitting_members",
    "議案提出の賛成者": "supporting_members",  # 衆議院特有
    "議案提出会派": "submitting_party"
}
```

### 3. Data Collection Enhancement

#### Multi-Source Scraper Architecture
```python
class EnhancedBillScraper:
    def __init__(self):
        self.sangiin_scraper = SangiinBillScraper()
        self.shugiin_scraper = ShugiinBillScraper()
        self.data_merger = BillDataMerger()
    
    async def collect_comprehensive_bill_data(self, session_number: int):
        # 両議会からデータを並行取得
        sangiin_bills = await self.sangiin_scraper.fetch_bills(session_number)
        shugiin_bills = await self.shugiin_scraper.fetch_bills(session_number)
        
        # データの統合・重複排除
        merged_bills = self.data_merger.merge_bill_data(
            sangiin_bills, shugiin_bills
        )
        
        return merged_bills
```

#### Detail Page Processing
```python
class BillDetailProcessor:
    def extract_bill_outline(self, soup: BeautifulSoup, source_house: str):
        if source_house == "参議院":
            return self._extract_sangiin_outline(soup)
        elif source_house == "衆議院":
            return self._extract_shugiin_outline(soup)
    
    def _extract_sangiin_outline(self, soup):
        # 参議院の議案要旨セクションを抽出
        outline_section = soup.find('div', class_='gian-youshi')
        if outline_section:
            return self._clean_outline_text(outline_section.get_text())
        return None
```

## Data Models

### Enhanced Bill Schema
```python
class EnhancedBill(BaseRecord):
    # Basic Information
    bill_number: str
    title: str
    bill_type: str
    diet_session: str
    house_of_origin: str
    
    # Detailed Content (新規追加)
    bill_outline: Optional[str]          # 議案要旨 (長文)
    background_context: Optional[str]    # 提出背景
    expected_effects: Optional[str]      # 期待される効果
    key_provisions: Optional[List[str]]  # 主要条項
    implementation_date: Optional[str]   # 施行日
    related_laws: Optional[List[str]]    # 関連法律
    
    # Submission Information (拡張)
    submitter_type: str                  # 政府/議員
    submitting_members: Optional[List[str]]
    supporting_members: Optional[List[str]]  # 衆議院のみ
    submitting_party: Optional[str]
    sponsoring_ministry: Optional[str]
    submission_date: Optional[str]
    
    # Process Tracking (新規追加)
    current_stage: str
    committee_assignments: Optional[Dict[str, Any]]
    voting_results: Optional[Dict[str, Any]]
    amendments: Optional[List[Dict[str, Any]]]
    inter_house_status: Optional[str]
    
    # Source Metadata (新規追加)
    source_house: str                    # 参議院/衆議院
    source_url: str
    last_updated: datetime
    data_quality_score: float
```

### Bill Process History
```python
class BillProcessHistory(BaseRecord):
    bill_id: str
    stage: str                          # 審議段階
    house: str                          # 議院
    committee: Optional[str]            # 委員会
    action_date: datetime               # 実施日
    action_type: str                    # アクション種別
    result: Optional[str]               # 結果
    details: Optional[Dict[str, Any]]   # 詳細情報
    notes: Optional[str]                # 備考
```

## Error Handling

### Data Quality Management
```python
class BillDataValidator:
    def validate_bill_data(self, bill_data: Dict) -> ValidationResult:
        errors = []
        warnings = []
        
        # 必須フィールドチェック
        required_fields = ['bill_number', 'title', 'diet_session']
        for field in required_fields:
            if not bill_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # データ品質チェック
        if bill_data.get('bill_outline'):
            if len(bill_data['bill_outline']) < 50:
                warnings.append("Bill outline seems too short")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_score=self._calculate_quality_score(bill_data)
        )
```

### Fallback Mechanisms
- 一方の議院からデータ取得に失敗した場合の他院データ利用
- 詳細ページアクセス失敗時の基本情報のみ保存
- データ品質スコアに基づく段階的データ更新

## Testing Strategy

### Unit Testing
- 各議院のスクレイパーの個別テスト
- データマッピング機能のテスト
- バリデーション機能のテスト

### Integration Testing
- 両議院データの統合テスト
- データベース保存・取得のテスト
- API経由でのデータアクセステスト

### Data Quality Testing
- 実際の法案データを用いた品質検証
- 欠損データの検出・処理テスト
- 重複データの排除テスト

## Performance Considerations

### Caching Strategy
- 法案詳細ページの24時間キャッシュ
- 議案要旨データの長期キャッシュ (7日間)
- 差分更新による効率的なデータ同期

### Rate Limiting
- 参議院サイト: 2秒間隔
- 衆議院サイト: 2秒間隔
- 並行処理時の総リクエスト数制限

### Database Optimization
- bill_outline フィールドのフルテキストインデックス
- 複合インデックス (diet_session, house_of_origin)
- パーティショニング (国会回次別)

## Migration Strategy

### Phase 1: Schema Extension
1. 新しいフィールドをBillsテーブルに追加
2. 既存データの互換性確保
3. デフォルト値の設定

### Phase 2: Data Collection Enhancement
1. 衆議院スクレイパーの実装
2. 詳細ページ処理機能の追加
3. データ統合ロジックの実装

### Phase 3: Quality Improvement
1. データバリデーション機能の実装
2. 品質スコア算出機能の追加
3. 自動データ修正機能の実装

## Security Considerations

### Data Privacy
- 公開情報のみを取得・保存
- 個人情報の除外 (議員名は公人として扱い)
- アクセスログの適切な管理

### Scraping Ethics
- robots.txt の遵守
- 適切なUser-Agentの設定
- サーバー負荷を考慮したアクセス頻度

### Data Integrity
- データ改ざん検出機能
- バックアップ・復旧機能
- 監査ログの保持